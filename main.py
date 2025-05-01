import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from itertools import combinations

# === CONFIG
TWELVE_API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
MAX_PRICE_DIFF = 50
TP1_PIPS = 300
TP2_PIPS = 1000
SL_PIPS = 150

# === TELEGRAM
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": text})
    except:
        print("Erreur Telegram")

# === PRIX LIVE
def get_live_price():
    try:
        res = requests.get(
            f"https://api.twelvedata.com/price",
            params={"symbol": "BTC/USD", "apikey": TWELVE_API_KEY},
            timeout=10
        )
        return float(res.json()["price"])
    except:
        return None

# === BOUGIES
def get_last_candle():
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": "BTC/USD",
        "interval": "5min",
        "outputsize": 2,
        "apikey": TWELVE_API_KEY
    }
    try:
        res = requests.get(url, params=params, timeout=10)
        data = res.json()["values"]
        df = pd.DataFrame(data)
        df["datetime"] = pd.to_datetime(df["datetime"])
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        df = df.sort_values("datetime").reset_index(drop=True)
        return df.iloc[-2]  # dernière bougie clôturée
    except:
        return None

# === STRATÉGIES GAGNANTES (exemples ici)
def apply_strategies(candle):
    signals = []
    if candle["close"] > candle["open"] and (candle["close"] - candle["open"]) > 50:
        signals.append("buy")
    if candle["close"] < candle["open"] and (candle["open"] - candle["close"]) > 50:
        signals.append("sell")
    return signals

# === VALIDATION LIVE
def validate_trade(type_, entry, price_live):
    tp1 = entry + TP1_PIPS if type_ == "buy" else entry - TP1_PIPS
    tp2 = entry + TP2_PIPS if type_ == "buy" else entry - TP2_PIPS
    sl = entry - SL_PIPS if type_ == "buy" else entry + SL_PIPS

    if abs(price_live - entry) > MAX_PRICE_DIFF:
        return None
    if type_ == "buy" and price_live <= sl:
        return None
    if type_ == "sell" and price_live >= sl:
        return None

    return {
        "type": type_,
        "entry": entry,
        "tp1": tp1,
        "tp2": tp2,
        "sl": sl,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

# === FORMATAGE
def format_signal(trade):
    label = "ACHAT" if trade["type"] == "buy" else "VENTE"
    return (
        f"{label}\n"
        f"PE : {trade['entry']:.2f}\n"
        f"TP1 : {trade['tp1']:.2f}\n"
        f"TP2 : {trade['tp2']:.2f}\n"
        f"SL : {trade['sl']:.2f}\n"
        f"[{trade['time']}]"
    )

# === MAIN LOOP
def main_loop():
    send_telegram_message("Trade test (démarrage moteur)")
    trades_sent = set()

    while True:
        candle = get_last_candle()
        price_live = get_live_price()

        if candle is None or price_live is None:
            time.sleep(300)
            continue

        entry = candle["close"]
        timestamp = candle["datetime"]

        signals = apply_strategies(candle)
        for sig in signals:
            key = f"{sig}_{timestamp}"
            if key in trades_sent:
                continue
            trade = validate_trade(sig, entry, price_live)
            if trade:
                send_telegram_message(format_signal(trade))
                trades_sent.add(key)
                break  # un seul trade par cycle

        time.sleep(300)

if __name__ == "__main__":
    main_loop()
