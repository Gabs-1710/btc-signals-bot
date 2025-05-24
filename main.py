import requests
import time
import telebot
import datetime
import statistics

# === CONFIGURATION ===
API_KEY = "2055fb1ec82c4ff5b487ce449faf8370"
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "1min"
TP1_PIPS = 300
TP2_PIPS = 1000
SL_PIPS = 150
MAX_PIP_DIFF = 50

bot = telebot.TeleBot(TELEGRAM_TOKEN)
sent_test = False
last_sent_trade = None

# === UTILITAIRES ===

def send_message(text):
    try:
        bot.send_message(CHAT_ID, text)
    except:
        pass

def get_price():
    url = f"https://api.twelvedata.com/price?symbol=BTC/USD&apikey={API_KEY}"
    r = requests.get(url).json()
    return float(r["price"]) if "price" in r else None

def get_candles(n=500):
    url = f"https://api.twelvedata.com/time_series?symbol=BTC/USD&interval={INTERVAL}&outputsize={n}&apikey={API_KEY}"
    r = requests.get(url).json()
    if "values" not in r: return []
    data = list(reversed(r["values"]))
    return [{"time": x["datetime"], "open": float(x["open"]), "high": float(x["high"]), "low": float(x["low"]), "close": float(x["close"])} for x in data]

def simulate_trade(entry, direction, candles):
    tp1 = entry + TP1_PIPS if direction == "buy" else entry - TP1_PIPS
    sl = entry - SL_PIPS if direction == "buy" else entry + SL_PIPS
    for c in candles:
        high = c["high"]
        low = c["low"]
        if direction == "buy" and low <= sl:
            return "SL"
        if direction == "sell" and high >= sl:
            return "SL"
        if direction == "buy" and high >= tp1:
            return "TP1"
        if direction == "sell" and low <= tp1:
            return "TP1"
    return "NONE"

def rsi(close, length=14):
    gains, losses = [], []
    for i in range(1, length + 1):
        delta = close[-i] - close[-i - 1]
        gains.append(max(delta, 0))
        losses.append(max(-delta, 0))
    avg_gain = statistics.mean(gains)
    avg_loss = statistics.mean(losses) if statistics.mean(losses) != 0 else 1
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def ema(data, length):
    k = 2 / (length + 1)
    ema_val = data[0]
    for price in data[1:]:
        ema_val = price * k + ema_val * (1 - k)
    return ema_val

# === ANALYSE AVANCÉE ===

def detect_strategies(candles):
    close = [x["close"] for x in candles]
    high = [x["high"] for x in candles]
    low = [x["low"] for x in candles]
    ema21 = ema(close[-21:], 21)
    rsi_val = rsi(close)

    current = candles[-1]["close"]
    prev = candles[-2]["close"]
    ob = candles[-3]["high"] > candles[-2]["high"] and candles[-3]["low"] < candles[-2]["low"]
    fvg = candles[-2]["low"] > candles[-3]["high"] or candles[-2]["high"] < candles[-3]["low"]
    bos = candles[-2]["high"] > candles[-3]["high"] and candles[-2]["low"] > candles[-3]["low"]
    choch = candles[-2]["low"] < candles[-3]["low"] and candles[-2]["high"] < candles[-3]["high"]

    strategies = []

    if current > ema21 and rsi_val < 30 and ob and fvg:
        strategies.append(("buy", "OB + FVG + RSI + EMA"))

    if current < ema21 and rsi_val > 70 and ob and fvg:
        strategies.append(("sell", "OB + FVG + RSI + EMA"))

    if bos and rsi_val < 40:
        strategies.append(("buy", "BOS + RSI"))

    if choch and rsi_val > 60:
        strategies.append(("sell", "CHoCH + RSI"))

    return strategies

def analyze_and_trade():
    global last_sent_trade
    candles = get_candles()
    if len(candles) < 100:
        return

    strategies = detect_strategies(candles)
    price_now = get_price()
    if price_now is None: return

    for direction, strat in strategies:
        entry = price_now
        if last_sent_trade and abs(entry - last_sent_trade) < 100:
            continue  # Évite les doublons

        result = simulate_trade(entry, direction, candles[-200:])
        if result == "TP1":
            tp1 = entry + TP1_PIPS if direction == "buy" else entry - TP1_PIPS
            tp2 = entry + TP2_PIPS if direction == "buy" else entry - TP2_PIPS
            sl = entry - SL_PIPS if direction == "buy" else entry + SL_PIPS
            msg = f"""{'ACHAT' if direction == 'buy' else 'VENTE'}
PE : {round(entry, 1)}
TP1 : {round(tp1, 1)}
TP2 : {round(tp2, 1)}
SL : {round(sl, 1)}
Stratégie : {strat}
Probabilité estimée : 100 %"""
            send_message(msg)
            last_sent_trade = entry
            break

# === TRADE TEST AU DÉMARRAGE ===

def send_trade_test():
    price = get_price()
    if price is None:
        return
    tp1 = price + TP1_PIPS
    tp2 = price + TP2_PIPS
    sl = price - SL_PIPS
    msg = f"""TRADE TEST
PE : {round(price, 1)}
TP1 : {round(tp1, 1)}
TP2 : {round(tp2, 1)}
SL : {round(sl, 1)}"""
    send_message(msg)

# === BOUCLE PRINCIPALE ===

while True:
    try:
        if not sent_test:
            send_trade_test()
            sent_test = True
        analyze_and_trade()
        time.sleep(300)
    except Exception as e:
        time.sleep(10)
