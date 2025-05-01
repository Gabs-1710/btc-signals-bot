import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from itertools import combinations

# === CONFIG
TWELVE_API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
MAX_PRICE_DIFF = 50  # Tolérance de ±50 pips pour considérer le signal tradable

# === TELEGRAM
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    except:
        print("Erreur Telegram")

# === PRIX LIVE
def get_live_price():
    url = f"https://api.twelvedata.com/price"
    params = {"symbol": "BTC/USD", "apikey": TWELVE_API_KEY}
    try:
        res = requests.get(url, params=params, timeout=10)
        return float(res.json()["price"])
    except:
        return None

# === BOUGIES
def get_bars():
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": "BTC/USD",
        "interval": "5min",
        "outputsize": 100,
        "apikey": TWELVE_API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.rename(columns={"datetime": "open_time"})
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        df = df.sort_values("open_time").reset_index(drop=True)
        return df
    except:
        return pd.DataFrame()

# === INDICATEURS
def add_indicators(df):
    df["ema21"] = df["close"].ewm(span=21).mean()
    df["ema50"] = df["close"].ewm(span=50).mean()
    df["ema200"] = df["close"].ewm(span=200).mean()
    delta = df["close"].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = -delta.clip(upper=0).rolling(14).mean()
    rs = gain / loss
    df["rsi"] = 100 - (100 / (1 + rs))
    return df

# === MODULES STRATÉGIQUES
def module_choch(df, i):
    return df["high"][i] > max(df["high"][i-5:i]) and df["close"][i] > df["open"][i], \
           df["low"][i] < min(df["low"][i-5:i]) and df["close"][i] < df["open"][i]

def module_order_block(df, i):
    return df["low"][i] < df["low"][i-1] and df["close"][i] > df["open"][i], \
           df["high"][i] > df["high"][i-1] and df["close"][i] < df["open"][i]

def module_fvg(df, i):
    body = abs(df["close"][i] - df["open"][i])
    prev = abs(df["close"][i-1] - df["open"][i-1])
    next_ = abs(df["close"][i+1] - df["open"][i+1])
    return body > prev * 1.5 and body > next_ * 1.5 and df["close"][i] > df["open"][i], \
           body > prev * 1.5 and body > next_ * 1.5 and df["close"][i] < df["open"][i]

def module_ema(df, i):
    return df["ema21"][i] > df["ema50"][i] > df["ema200"][i], \
           df["ema21"][i] < df["ema50"][i] < df["ema200"][i]

def module_rsi(df, i):
    return df["rsi"][i] < 30, df["rsi"][i] > 70

def module_double_bottom(df, i):
    return abs(df["low"][i] - df["low"][i-3]) < df["low"][i] * 0.001, \
           abs(df["high"][i] - df["high"][i-3]) < df["high"][i] * 0.001

# === COMBOS DE STRATÉGIES
def generate_strategies(df):
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
                i = len(df) - 2  # Dernière bougie clôturée
                if all(f(df, i)[0] for f in funcs):
                    signals.append({"index": i, "type": "buy"})
                elif all(f(df, i)[1] for f in funcs):
                    signals.append({"index": i, "type": "sell"})
                return signals
            strategies.append((" + ".join([m[0] for m in combo]), strat))
    return strategies

# === BACKTEST ULTRA SÉCURISÉ
def backtest(df, strategy_fn, sl_pips=150, tp1_pips=300):
    trades = []
    signals = strategy_fn(df)
    for s in signals:
        i = s["index"]
        if i >= len(df) - 1: continue
        entry = df["close"][i]
        future = df.iloc[i+1:i+20]
        tp1 = entry + tp1_pips if s["type"] == "buy" else entry - tp1_pips
        sl = entry - sl_pips if s["type"] == "buy" else entry + sl_pips
        hit_tp1 = hit_sl = False
        for _, row in future.iterrows():
            if s["type"] == "buy":
                if row["low"] <= sl: hit_sl = True; break
                if row["high"] >= tp1: hit_tp1 = True; break
            else:
                if row["high"] >= sl: hit_sl = True; break
                if row["low"] <= tp1: hit_tp1 = True; break
        if hit_tp1 and not hit_sl:
            trades.append({
                "type": s["type"],
                "entry": entry,
                "tp1": tp1,
                "tp2": entry + 1000 if s["type"] == "buy" else entry - 1000,
                "sl": sl,
                "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            })
    return trades

def format_message(trade):
    label = "ACHAT" if trade["type"] == "buy" else "VENTE"
    return (
        f"{label}\n"
        f"PE : {trade['entry']:.2f}\n"
        f"TP1 : {trade['tp1']:.2f}\n"
        f"TP2 : {trade['tp2']:.2f}\n"
        f"SL : {trade['sl']:.2f}\n"
        f"[{trade['time']}]"
    )

def send_trade_test(df):
    last = df.iloc[-1]
    entry = last["close"]
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    msg = (
        f"ACHAT (Trade test)\n"
        f"PE : {entry:.2f}\n"
        f"TP1 : {entry+300:.2f}\n"
        f"TP2 : {entry+1000:.2f}\n"
        f"SL : {entry-150:.2f}\n"
        f"[{now}]"
    )
    send_telegram_message(msg)

# === MAIN LOOP
def main_loop():
    df = get_bars()
    if df.empty:
        send_telegram_message("Erreur récupération données TwelveData.")
        return

    df = add_indicators(df)
    send_trade_test(df)
    trades_sent = set()
    last_alert = datetime.utcnow() - timedelta(hours=2)

    while True:
        df = get_bars()
        if df.empty:
            time.sleep(300)
            continue

        df = add_indicators(df)
        price_live = get_live_price()
        if price_live is None:
            time.sleep(300)
            continue

        strategies = generate_strategies(df)
        found = False
        for name, strat in strategies:
            trades = backtest(df, strat)
            for t in trades:
                key = f"{t['type']}_{round(t['entry'],2)}_{t['time']}"
                if key not in trades_sent:
                    if abs(t["entry"] - price_live) <= MAX_PRICE_DIFF:
                        trades_sent.add(key)
                        send_telegram_message(format_message(t))
                        found = True
            if found:
                break

        if not found and datetime.utcnow() - last_alert > timedelta(hours=2):
            send_telegram_message("Aucun signal parfait détecté pour le moment.")
            last_alert = datetime.utcnow()

        time.sleep(300)

if __name__ == "__main__":
    main_loop()
