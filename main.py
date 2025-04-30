import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from itertools import combinations

# === CONFIG TELEGRAM
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"

def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erreur Telegram : {e}")

# === BLOC 1 : Bougies Binance M5 (corrigé)
def get_binance_m5_bars(symbol="BTCUSDT", interval="5m", limit=1000):
    url = "https://api1.binance.com/api/v3/klines"  # endpoint plus stable
    headers = {"User-Agent": "Mozilla/5.0"}  # empêche le blocage Render
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params, headers=headers, timeout=5)
        response.raise_for_status()
        data = response.json()
        df = pd.DataFrame(data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
        ])
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        return df[["open_time", "open", "high", "low", "close"]]
    except Exception as e:
        print(f"Erreur bougies Binance : {e}")
        return pd.DataFrame()

def get_binance_m5_bars_with_retry(retries=5, delay=1):
    for _ in range(retries):
        df = get_binance_m5_bars()
        if not df.empty:
            return df
        time.sleep(delay)
    return pd.DataFrame()

# === Trade test
def send_trade_test(df):
    try:
        last = df.iloc[-1]
        entry = last["close"]
        tp1 = entry + 300
        tp2 = entry + 1000
        sl = entry - 150
        msg = (
            f"ACHAT (Trade test)\n"
            f"PE : {entry:.2f}\n"
            f"TP1 : {tp1:.2f}\n"
            f"TP2 : {tp2:.2f}\n"
            f"SL : {sl:.2f}\n"
            f"[{last['open_time'].strftime('%Y-%m-%d %H:%M:%S')} UTC]"
        )
        send_telegram_message(msg)
    except:
        send_telegram_message("Trade test impossible : erreur bougie.")

# === Backtest
def backtest_strategy(df, strategy_function, sl_pips=150, tp1_pips=300, tp2_pips=1000):
    trades = []
    signals = strategy_function(df)
    for signal in signals:
        i = signal["index"]
        if i >= len(df) - 1:
            continue
        entry = df.iloc[i]["close"]
        future = df.iloc[i+1:i+20]
        tp1 = entry + tp1_pips if signal["type"] == "buy" else entry - tp1_pips
        tp2 = entry + tp2_pips if signal["type"] == "buy" else entry - tp2_pips
        sl = entry - sl_pips if signal["type"] == "buy" else entry + sl_pips
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
                "tp1": tp1, "tp2": tp2, "sl": sl, "time": df.iloc[i]["open_time"]
            })
    return trades

# === Stratégies
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

# === Message format
def format_telegram_message(trade):
    s = "ACHAT" if trade["type"] == "buy" else "VENTE"
    return (
        f"{s}\n"
        f"PE : {trade['entry']:.2f}\n"
        f"TP1 : {trade['tp1']:.2f}\n"
        f"TP2 : {trade['tp2']:.2f}\n"
        f"SL : {trade['sl']:.2f}"
    )

# === Moteur principal
def main_loop():
    df = get_binance_m5_bars_with_retry()
    if df.empty:
        send_telegram_message("Erreur : données Binance M5 non récupérables après 5 tentatives.")
        return

    df["ema21"] = df["close"].ewm(span=21).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))

    send_trade_test(df)
    last_alert = datetime.utcnow() - timedelta(hours=2)

    while True:
        df = get_binance_m5_bars_with_retry()
        if df.empty:
            time.sleep(300)
            continue

        df["ema21"] = df["close"].ewm(span=21).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()
        df["ema200"] = df["close"].ewm(span=200).mean()
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

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
