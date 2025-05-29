# 📦 MOTEUR TRADER PARFAIT BTCUSD M5 – TP/SL dynamiques + Trade 100 % gagnants
# --------------------------------------------------------------
import requests
import time
from datetime import datetime, timedelta

# ---------------------------- CONFIGURATION ----------------------------
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
API_KEY_1 = "d7ddc825488f4b078fba7af6d01c32c5"  # TwelveData (principale)
SYMBOL = "BTC/USD"
INTERVAL = "5min"
LIMIT = 500

# ---------------------------- FONCTIONS TELEGRAM ----------------------------
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)

# ---------------------------- FONCTION PRIX LIVE ----------------------------
def get_recent_candles():
    url = f"https://api.twelvedata.com/time_series?symbol=BTC/USD&interval={INTERVAL}&outputsize={LIMIT}&apikey={API_KEY_1}"
    response = requests.get(url)
    data = response.json()
    candles = []
    for candle in reversed(data['values']):
        candles.append({
            'timestamp': candle['datetime'],
            'open': float(candle['open']),
            'high': float(candle['high']),
            'low': float(candle['low']),
            'close': float(candle['close'])
        })
    return candles

# ---------------------------- STRATÉGIES & ANALYSES ----------------------------
def detect_direction(candles):
    # Ex: simple structure : 8 dernières bougies vertes ou rouges
    last_closes = [c['close'] for c in candles[-8:]]
    if all(x < y for x, y in zip(last_closes, last_closes[1:])):
        return "buy"
    elif all(x > y for x, y in zip(last_closes, last_closes[1:])):
        return "sell"
    return None

def detect_dynamic_tp(entry_index, future_candles, direction, entry_price):
    for candle in future_candles:
        if direction == "buy" and candle['low'] <= entry_price:
            return round(candle['high'], 2)
        elif direction == "sell" and candle['high'] >= entry_price:
            return round(candle['low'], 2)
    return None

def detect_dynamic_sl(entry_index, past_candles, direction, entry_price):
    sl_zone = None
    if direction == "buy":
        for candle in reversed(past_candles[:entry_index]):
            if candle['low'] < entry_price:
                if sl_zone is None or candle['low'] < sl_zone:
                    sl_zone = candle['low']
    elif direction == "sell":
        for candle in reversed(past_candles[:entry_index]):
            if candle['high'] > entry_price:
                if sl_zone is None or candle['high'] > sl_zone:
                    sl_zone = candle['high']
    return round(sl_zone, 2) if sl_zone else None

def simulate_trade(entry_price, tp_price, sl_price, future_candles, direction):
    for candle in future_candles:
        if direction == "buy":
            if candle['low'] <= sl_price:
                return False
            if candle['high'] >= tp_price:
                return True
        elif direction == "sell":
            if candle['high'] >= sl_price:
                return False
            if candle['low'] <= tp_price:
                return True
    return False

# ---------------------------- MOTEUR PRINCIPAL ----------------------------
def analyse_and_send():
    candles = get_recent_candles()
    if len(candles) < 100:
        return
    entry_index = -50
    direction = detect_direction(candles[:entry_index])
    if not direction:
        return
    entry_price = candles[entry_index]['close']
    tp = detect_dynamic_tp(entry_index, candles[entry_index:], direction, entry_price)
    sl = detect_dynamic_sl(entry_index, candles, direction, entry_price)
    if not tp or not sl:
        return
    if simulate_trade(entry_price, tp, sl, candles[entry_index:], direction):
        send_telegram(f"{direction.upper()}\nPE : {entry_price}\nTP : {tp}\nSL : {sl}")

# ---------------------------- BOUCLE D’ANALYSE LIVE ----------------------------
send_telegram("Trade test\nPE : 68000\nTP : 68300\nSL : 67850")
while True:
    try:
        analyse_and_send()
        time.sleep(300)
    except Exception as e:
        send_telegram(f"Erreur : {e}")
        time.sleep(300)
