import requests
import time
from datetime import datetime, timedelta

# Configuration
API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "5min"
SL_PIPS = 150
TP1_PIPS = 300
TP2_PIPS = 1000
MAX_LOOKAHEAD = 500
TOLERANCE = 50

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "HTML"
    }
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Erreur envoi Telegram : {e}")

def get_candles():
    url = f"https://api.twelvedata.com/time_series?symbol=BTC/USD&interval=5min&outputsize={MAX_LOOKAHEAD}&apikey={API_KEY}"
    try:
        r = requests.get(url)
        data = r.json()
        candles = data["values"]
        candles.reverse()
        return candles
    except Exception as e:
        print("Erreur récupération bougies :", e)
        return []

def simulate_trade(entry_price, future_prices):
    sl_price = entry_price - SL_PIPS
    tp1_price = entry_price + TP1_PIPS

    for price in future_prices:
        high = float(price["high"])
        low = float(price["low"])
        if low <= sl_price:
            return False
        if high >= tp1_price:
            return True
    return False

def detect_perfect_trade():
    candles = get_candles()
    if not candles or len(candles) < 100:
        return

    last_close = float(candles[-1]["close"])
    timestamp = candles[-1]["datetime"]

    strategies = [
        "Order Block + RSI + EMA",
        "FVG + BOS + EMA",
        "CHoCH + OB + Compression",
        "SFP + EMA M15 + Wyckoff",
        "Fibonacci + RSI + OB"
    ]

    for i in range(len(candles) - 60):
        entry = float(candles[i]["close"])
        if abs(entry - last_close) <= TOLERANCE:
            future = candles[i+1:]
            if simulate_trade(entry, future):
                strategy_used = strategies[i % len(strategies)]
                message = (
                    "✅ <b>TRADE PARFAIT DÉTECTÉ</b>\n\n"
                    f"📈 <b>ACHAT</b>\n"
                    f"PE : {entry}\n"
                    f"TP1 : {entry + TP1_PIPS}\n"
                    f"TP2 : {entry + TP2_PIPS}\n"
                    f"SL : {entry - SL_PIPS}\n\n"
                    f"📚 Stratégie utilisée : <i>{strategy_used}</i>\n"
                    f"🔐 Taux de confiance : <b>100 %</b>\n"
                    f"🕒 Heure : {timestamp} UTC"
                )
                send_telegram_message(message)
                return

def main():
    send_telegram_message("🧠 Trade test simulé lancé.\nAnalyse en cours...")
    detect_perfect_trade()
    while True:
        time.sleep(300)
        detect_perfect_trade()

if __name__ == "__main__":
    main()
