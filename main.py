import requests
import pandas as pd
import time
from datetime import datetime

# === CONFIG
TWELVE_API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
MAX_PRICE_DIFF = 80
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

# === PRIX ACTUEL
def get_live_price():
    try:
        res = requests.get(
            "https://api.twelvedata.com/price",
            params={"symbol": "BTC/USD", "apikey": TWELVE_API_KEY},
            timeout=10
        )
        return float(res.json()["price"])
    except:
        return None

# === BOUGIES M5
def get_candles():
    try:
        res = requests.get(
            "https://api.twelvedata.com/time_series",
            params={
                "symbol": "BTC/USD",
                "interval": "5min",
                "outputsize": 500,
                "apikey": TWELVE_API_KEY
            },
            timeout=10
        )
        data = res.json()["values"]
        df = pd.DataFrame(data)
        df["datetime"] = pd.to_datetime(df["datetime"])
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        df = df.sort_values("datetime").reset_index(drop=True)
        return df
    except:
        return pd.DataFrame()

# === DÉTECTION CONTEXTE
def is_strong_bullish(df, i):
    body = df["close"][i] - df["open"][i]
    return body > 30 and df["close"][i] > df["open"][i] and df["close"][i] > df["close"][i-1]

def is_strong_bearish(df, i):
    body = df["open"][i] - df["close"][i]
    return body > 30 and df["close"][i] < df["open"][i] and df["close"][i] < df["close"][i-1]

# === VALIDATION TP1/SL
def simulate_future(df, i, entry, signal_type, price_live):
    future = df.iloc[i+1:]
    tp1 = entry + TP1_PIPS if signal_type == "buy" else entry - TP1_PIPS
    tp2 = entry + TP2_PIPS if signal_type == "buy" else entry - TP2_PIPS
    sl  = entry - SL_PIPS     if signal_type == "buy" else entry + SL_PIPS

    for _, row in future.iterrows():
        if signal_type == "buy":
            if row["low"] <= sl:
                return None
            if row["high"] >= tp1:
                if price_live <= sl or abs(price_live - entry) > MAX_PRICE_DIFF:
                    return None
                return dict(type="buy", entry=entry, tp1=tp1, tp2=tp2, sl=sl)
        else:
            if row["high"] >= sl:
                return None
            if row["low"] <= tp1:
                if price_live >= sl or abs(price_live - entry) > MAX_PRICE_DIFF:
                    return None
                return dict(type="sell", entry=entry, tp1=tp1, tp2=tp2, sl=sl)
    return None

# === FORMAT
