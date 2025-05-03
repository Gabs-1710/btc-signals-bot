import requests
import pandas as pd
import time
from datetime import datetime, timedelta

# === CONFIGURATION ===
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
        print("Erreur envoi Telegram.")

# === DONNÉES LIVE
def get_live_price():
    try:
        r = requests.get(
            f"https://api.twelvedata.com/price",
            params={"symbol": "BTC/USD", "apikey": TWELVE_API_KEY},
            timeout=10
        )
        return float(r.json()["price"])
    except:
        return None

def get_recent_candles():
    try:
        r = requests.get(
            f"https://api.twelvedata.com/time_series",
            params={
                "symbol": "BTC/USD",
                "interval": "5min",
                "outputsize": 500,
                "apikey": TWELVE_API_KEY
            },
            timeout=10
        )
        data = r.json()["values"]
        df = pd.DataFrame(data)
        df["datetime"] = pd.to_datetime(df["datetime"])
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        df = df.sort_values("datetime").reset_index(drop=True)
        return df
    except:
        return pd.DataFrame()

# === CONTEXTE & LOGIQUE
def is_strong_bullish(df, i):
    body = df["close"][i] - df["open"][i]
    return body > 30 and df["close"][i] > df["open"][i] and df["close"][i] > df["close"][i-1]

def is_strong_bearish(df, i):
    body = df["open"][i] - df["close"][i]
    return body > 30 and df["close"][i] < df["open"][i] and df["close"][i] < df["close"][i-1]

# === VALIDATION
def simulate_future(df, i, entry, signal_type, price_live):
    future = df.iloc[i+1:i+5]  # regarde les 4 bougies suivantes max

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

# === FORMATAGE
def format_signal(trade):
    label = "ACHAT" if trade["type"] == "buy" else "VENTE"
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    return (
        f"{label}\n"
        f"PE : {trade['entry']:.2f}\n"
        f"TP1 : {trade['tp1']:.2f}\n"
        f"TP2 : {trade['tp2']:.2f}\n"
        f"SL : {trade['sl']:.2f}\n"
        f"[{now}]"
    )

# === MOTEUR PRINCIPAL
def main_loop():
    send_telegram_message("Trade test (moteur prédictif en ligne)")
    trades_sent = set()
    last_status_time = time.time()

    while True:
        df = get_recent_candles()
        price_live = get_live_price()

        if df.empty or price_live is None:
            time.sleep(300)
            continue

        for i in range(len(df) - 5, len(df) - 1):
            signal = None
            if is_strong_bullish(df, i):
                signal = "buy"
            elif is_strong_bearish(df, i):
                signal = "sell"

            if signal:
                entry = df["close"][i]
                key = f"{signal}_{df['datetime'][i]}"
                if key in trades_sent:
                    continue

                validated = simulate_future(df, i, entry, signal, price_live)
                if validated:
                    send_telegram_message(format_signal(validated))
                    trades_sent.add(key)
                    break  # un seul signal par cycle

        # message de statut toutes les 2h
        if time.time() - last_status_time > 7200:
            now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            send_telegram_message(f"Aucun signal parfait détecté pour le moment.\n[{now}]")
            last_status_time = time.time()

        time.sleep(300)

if __name__ == "__main__":
    main_loop()
