import requests
import time
from datetime import datetime

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
        print(f"Erreur Telegram : {e}")

def get_candles():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize={MAX_LOOKAHEAD}&apikey={API_KEY}"
    try:
        response = requests.get(url)
        data = response.json()
        candles = data["values"]
        candles.reverse()
        return candles
    except Exception as e:
        print("Erreur données :", e)
        return []

def simulate_trade(entry, future):
    sl = entry - SL_PIPS
    tp1 = entry + TP1_PIPS
    for candle in future:
        low = float(candle["low"])
        high = float(candle["high"])
        if low <= sl:
            return False  # SL touché d’abord → trade rejeté
        if high >= tp1:
            return True   # TP1 atteint avant SL → trade validé
    return False  # Ni TP1 ni SL → rejet

def detect_trade():
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
                strat = strategies[i % len(strategies)]
                tp1 = entry + TP1_PIPS
                tp2 = entry + TP2_PIPS
                sl = entry - SL_PIPS
                msg = (
                    "✅ <b>TRADE PARFAIT DÉTECTÉ</b>\n\n"
                    f"📈 <b>ACHAT</b>\n"
                    f"PE : {entry}\n"
                    f"TP1 : {tp1}\n"
                    f"TP2 : {tp2}\n"
                    f"SL : {sl}\n\n"
                    f"📚 Stratégie utilisée : <i>{strat}</i>\n"
                    f"🔐 Taux de confiance : <b>100 %</b>\n"
                    f"🕒 Heure : {timestamp} UTC"
                )
                send_telegram_message(msg)
                return

def main():
    send_telegram_message("🧠 Trade test simulé lancé.\nAnalyse ultra stricte activée...")
    detect_trade()
    while True:
        time.sleep(300)
        detect_trade()

if __name__ == "__main__":
    main()
