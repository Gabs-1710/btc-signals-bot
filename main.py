import requests
import pandas as pd
import time
from datetime import datetime, timedelta

# === CONFIG
TWELVE_API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
MAX_PRICE_DIFF = 80  # élargi
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

# === DERNIÈRES BOUGIES
def get_recent_candles():
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": "BTC/USD",
        "interval": "5min",
        "outputsize": 3,
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
        return df.iloc[-2], df.iloc[-1]
    except:
        return None, None

# === STRATÉGIE SIMPLE
def signal_from_candle(candle):
    body = abs(candle["close"] - candle["open"])
    if candle["close"] > candle["open"] and body > 30:  # corps réduit
        return "buy"
    if candle["close"] < candle["open"] and body > 30:
        return "sell"
    return None

# === VALIDATION ADAPTÉE
def validate_signal(signal_type, entry, future_candle, price_live):
    if signal_type == "buy":
        tp1 = entry + TP1_PIPS
        tp2 = entry + TP2_PIPS
        sl = entry - SL_PIPS
        if future_candle["high"] < tp1:
            return None
        if future_candle["low"] < sl:
            return None
        if price_live <= sl or abs(price_live - entry) > MAX_PRICE_DIFF:
            return None
    elif signal_type == "sell":
        tp1 = entry - TP1_PIPS
        tp2 = entry - TP2_PIPS
        sl = entry + SL_PIPS
        if future_candle["low"] > tp1:
            return None
        if future_candle["high"] > sl:
            return None
        if price_live >= sl or abs(price_live - entry) > MAX_PRICE_DIFF:
            return None
    else:
        return None

    return {
        "type": signal_type,
        "entry": entry,
        "tp1": tp1,
        "tp2": tp2,
        "sl": sl,
        "time": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    }

# === FORMATAGE
def format_trade(trade):
    label = "ACHAT" if trade["type"] == "buy" else "VENTE"
    return (
        f"{label}\n"
        f"PE : {trade['entry']:.2f}\n"
        f"TP1 : {trade['tp1']:.2f}\n"
        f"TP2 : {trade['tp2']:.2f}\n"
        f"SL : {trade['sl']:.2f}\n"
        f"[{trade['time']}]"
    )

# === BOUCLE PRINCIPALE
def main_loop():
    send_telegram_message("Trade test (moteur ajusté pour signaux quotidiens sécurisés)")
    last_sent_time = None
    last_status_time = time.time()

    while True:
        candle, next_candle = get_recent_candles()
        price_live = get_live_price()

        if candle is None or next_candle is None or price_live is None:
            time.sleep(300)
            continue

        signal = signal_from_candle(candle)
        sent = False

        if signal:
            entry = candle["close"]
            trade = validate_signal(signal, entry, next_candle, price_live)
            if trade:
                if not last_sent_time or (datetime.utcnow() - last_sent_time > timedelta(minutes=10)):
                    send_telegram_message(format_trade(trade))
                    last_sent_time = datetime.utcnow()
                    sent = True

        now = time.time()
        if not sent and now - last_status_time > 7200:
            current_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            send_telegram_message(f"Aucun signal parfait détecté pour le moment.\n[{current_time}]")
            last_status_time = now

        time.sleep(300)

if __name__ == "__main__":
    main_loop()
