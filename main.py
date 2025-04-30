import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from itertools import combinations

# === CONFIG
CMC_API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"

# === ENVOI TELEGRAM
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erreur Telegram : {e}")

# === RÉCUPÉRATION PRIX BTC/USD SPOT (CMC)
def get_btc_price_cmc():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": "BTC", "convert": "USD"}
    headers = {"Accepts": "application/json", "X-CMC_PRO_API_KEY": CMC_API_KEY}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        return round(data["data"]["BTC"]["quote"]["USD"]["price"], 2)
    except Exception as e:
        print("Erreur CoinMarketCap :", e)
        return None

# === TRADE TEST
def send_trade_test():
    price = get_btc_price_cmc()
    if price is None:
        send_telegram_message("Trade test impossible : erreur prix CMC.")
        return
    tp1 = price + 300
    tp2 = price + 1000
    sl = price - 150
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    msg = (
        f"ACHAT (Trade test)\n"
        f"PE : {price:.2f}\n"
        f"TP1 : {tp1:.2f}\n"
        f"TP2 : {tp2:.2f}\n"
        f"SL : {sl:.2f}\n"
        f"[{now} UTC]"
    )
    send_telegram_message(msg)

# === PLACEHOLDER : Bougies réelles à intégrer si CMC envoie des M5 (non dispo actuellement)
# Pour simulation uniquement (à remplacer par vraies bougies si accessibles un jour via CMC)

def get_fake_bars():
    now = pd.Timestamp.utcnow().floor("5min")
    bars = []
    price = get_btc_price_cmc()
    if price is None:
        return pd.DataFrame()
    for i in range(1000):
        time_i = now - pd.Timedelta(minutes=5*i)
        close = price - i * 5
        open_ = close + 2
        high = close + 10
        low = close - 10
        bars.append([time_i, open_, high, low, close])
    df = pd.DataFrame(bars, columns=["open_time", "open", "high", "low", "close"])
    df = df.sort_values("open_time").reset_index(drop=True)
    return df

# === INDICATEURS
def compute_indicators(df):
    df["ema21"] = df["close"].ewm(span=21).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    return df

# === MODULES DE STRATÉGIE
def module_choch(df, i):
    return (df["high"].iloc[i] > max(df["high"].iloc[i-5:i]) and df["close"].iloc[i] > df["open"].iloc[i],
            df["low"].iloc[i] < min(df["low"].iloc[i-5:i]) and df["close"].iloc[i] < df["open"].iloc[i])

def module_order_block(df, i):
    return (df["low"].iloc[i] < df["low"].iloc[i-1] and df["close"].iloc[i] > df["open"].iloc[i],
            df["high"].iloc[i] > df["high"].iloc[i-1] and df["close"].iloc[i] < df["open"].iloc[i])

def module_fvg(df, i):
    body = abs(df["close"].iloc[i] - df["open"].iloc[i])
    prev = abs(df["close"].iloc[i-1] - df["open"].iloc[i-1])
    next_ = abs(df["close"].iloc[i+1] - df["open"].iloc[i+1])
    return (body > prev * 1.5 and body > next_ * 1.5 and df["close"].iloc[i] > df["open"].iloc[i],
            body > prev * 1.5 and body > next_ * 1.5 and df["close"].iloc[i] < df["open"].iloc[i])

def module_ema(df, i):
    return (df["ema21"].iloc[i] > df["ema50"].iloc[i] > df["ema200"].iloc[i],
            df["ema21"].iloc[i] < df["ema50"].iloc[i] < df["ema200"].iloc[i])

def module_rsi(df, i):
    return (df["rsi"].iloc[i] < 30, df["rsi"].iloc[i] > 70)

def module_double_bottom(df, i):
    return (abs(df["low"].iloc[i] - df["low"].iloc[i-3]) < df["low"].iloc[i] * 0.001,
            abs(df["high"].iloc[i] - df["high"].iloc[i-3]) < df["high"].iloc[i] * 0.001)

def generate_all_strategy_combinations(df):
    modules = [
        ("CHoCH", module_choch),
        ("OrderBlock", module_order_block),
        ("FVG", module_fvg),
        ("EMA", module_ema),
        ("RSI", module_rsi),
        ("DoubleBottom", module_double_bottom)
    ]
    strategies = []
    for r in range(2, len(modules)+1):
        for combo in combinations(modules, r):
            funcs = [m[1] for m in combo]
            def strat(df, funcs=funcs):
                signals = []
                for i in range(20, len(df)-20):
                    if all(f(df, i)[0] for f in funcs):
                        signals.append({"index": i, "type": "buy"})
                    elif all(f(df, i)[1] for f in funcs):
                        signals.append({"index": i, "type": "sell"})
                return signals
            strategies.append((" + ".join([m[0] for m in combo]), strat))
    return strategies

# === BACKTEST
def backtest_strategy(df, strategy_function, sl_pips=150, tp1_pips=300):
    trades = []
    signals = strategy_function(df)
    for signal in signals:
        i = signal["index"]
        if i >= len(df) - 1:
            continue
        entry = df.iloc[i]["close"]
        future = df.iloc[i+1:i+20]
        tp1 = entry + tp1_pips if signal["type"] == "buy" else entry - tp1_pips
        sl  = entry - sl_pips if signal["type"] == "buy" else entry + sl_pips
        hit_tp1 = hit_sl = False
        for _, row in future.iterrows():
            if signal["type"] == "buy":
                if row["low"] <= sl: hit_sl = True; break
                if row["high"] >= tp1: hit_tp1 = True; break
            else:
                if row["high"] >= sl: hit_sl = True; break
                if row["low"] <= tp1: hit_tp1 = True; break
        if hit_tp1 and not hit_sl:
            trades.append({
                "index": i, "type": signal["type"], "entry": entry,
                "tp1": tp1, "tp2": entry + 1000 if signal["type"] == "buy" else entry - 1000,
                "sl": sl, "time": df.iloc[i]["open_time"]
            })
    return trades

# === FORMAT MESSAGE
def format_telegram_message(trade):
    s = "ACHAT" if trade["type"] == "buy" else "VENTE"
    return (
        f"{s}\n"
        f"PE : {trade['entry']:.2f}\n"
        f"TP1 : {trade['tp1']:.2f}\n"
        f"TP2 : {trade['tp2']:.2f}\n"
        f"SL : {trade['sl']:.2f}"
    )

# === MOTEUR
def main_loop():
    send_trade_test()
    last_alert = datetime.utcnow() - timedelta(hours=2)

    while True:
        df = get_fake_bars()
        if df.empty:
            send_telegram_message("Erreur : données CoinMarketCap indisponibles.")
            time.sleep(300)
            continue

        df = compute_indicators(df)
        strategies = generate_all_strategy_combinations(df)
        found = False
        for name, strat in strategies:
            trades = backtest_strategy(df, strat)
            if trades:
                for t in trades:
                    send_telegram_message(format_telegram_message(t))
                found = True
                break

        if not found and datetime.utcnow() - last_alert > timedelta(hours=2):
            send_telegram_message("Aucun signal parfait détecté pour le moment.")
            last_alert = datetime.utcnow()

        time.sleep(300)

# === LANCEMENT
if __name__ == "__main__":
    main_loop()
