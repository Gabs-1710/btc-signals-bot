import requests
import time
from datetime import datetime
import numpy as np

# === CONFIG ===
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
TWELVEDATA_API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
SYMBOL = "BTC/USD"
TP1 = 300
TP2 = 1000
SL = 150
PE_TOLERANCE = 50
MAX_CANDLES = 500

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    success = False
    while not success:
        try:
            response = requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
            if response.status_code == 200:
                success = True
            else:
                time.sleep(2)
        except:
            time.sleep(2)

def get_live_price():
    try:
        url = f"https://api.twelvedata.com/quote?symbol={SYMBOL}&apikey={TWELVEDATA_API_KEY}"
        res = requests.get(url, timeout=10).json()
        return float(res["price"])
    except:
        return None

def get_candles(interval):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={interval}&outputsize={MAX_CANDLES}&apikey={TWELVEDATA_API_KEY}"
        res = requests.get(url, timeout=10).json()
        values = res["values"]
        candles = []
        for v in reversed(values):
            candles.append({
                "datetime": v["datetime"],
                "open": float(v["open"]),
                "high": float(v["high"]),
                "low": float(v["low"]),
                "close": float(v["close"])
            })
        return candles
    except:
        return []

def wait_for_live_price_with_fallback():
    attempts = 0
    price = None
    timeout_start = time.time()
    while price is None and (time.time() - timeout_start) < 30:
        price = get_live_price()
        print(f"Tentative d’envoi du Trade test : prix = {price}")
        if price is None:
            attempts += 1
            time.sleep(2)
        if attempts >= 5:
            m1 = get_candles("1min")
            if m1:
                price = m1[-1]["close"]
                print(f"Fallback prix M1 utilisé : {price}")
            break
    return price

def main():
    sent_signals = set()
    last_msg = time.time()

    # Trade test au démarrage avec fallback et logs
    price = wait_for_live_price_with_fallback()
    if price:
        tp1 = price + TP1
        tp2 = price + TP2
        sl = price - SL
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        send_telegram(f"ACHAT (Trade test)\nPE : {price:.2f}\nTP1 : {tp1:.2f}\nTP2 : {tp2:.2f}\nSL : {sl:.2f}\n[{now}]")
        print("Trade test envoyé")
        time.sleep(10)
    else:
        print("Échec : prix introuvable pour le Trade test")

    while True:
        m1 = get_candles("1min")
        m5 = get_candles("5min")
        m15 = get_candles("15min")
        price = get_live_price()
        if not m1 or not m5 or not m15 or price is None:
            time.sleep(60)
            continue

        m1_trend = m1[-1]["close"] > m1[-2]["close"]
        m5_trend = m5[-1]["close"] > m5[-2]["close"]
        m15_trend = m15[-1]["close"] > m15[-2]["close"]

        if m1_trend and m5_trend and m15_trend:
            direction = "ACHAT"
        elif not m1_trend and not m5_trend and not m15_trend:
            direction = "VENTE"
        else:
            direction = None

        if direction:
            pe = price
            tp1 = pe + TP1 if direction == "ACHAT" else pe - TP1
            tp2 = pe + TP2 if direction == "ACHAT" else pe - TP2
            sl = pe - SL if direction == "ACHAT" else pe + SL

            if abs(pe - price) <= PE_TOLERANCE:
                now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                msg = f"{direction}\nPE : {pe:.2f}\nTP1 : {tp1:.2f}\nTP2 : {tp2:.2f}\nSL : {sl:.2f}\n[{now}]"
                key = f"{direction}_{int(pe)}"
                if key not in sent_signals:
                    send_telegram(msg)
                    sent_signals.add(key)

        if time.time() - last_msg > 7200:
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            send_telegram(f"Aucun signal parfait détecté pour le moment.\n[{now}]")
            last_msg = time.time()

        time.sleep(60)

if __name__ == "__main__":
    main()
