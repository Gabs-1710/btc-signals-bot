import requests
import time
from datetime import datetime
import numpy as np

# === CONFIG ===
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
TWELVEDATA_API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd"
SYMBOL = "BTC/USD"
TP1 = 300
TP2 = 1000
SL = 150
PE_TOLERANCE = 50
MAX_CANDLES = 500
MAX_RETRIES = 3

strategy_stats = {"EMA+OB": [0, 0], "RSI": [0, 0], "FVG": [0, 0]}

def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg}, timeout=10)
    except:
        pass

def get_live_price():
    try:
        url = f"https://api.twelvedata.com/quote?symbol={SYMBOL}&apikey={TWELVEDATA_API_KEY}"
        res = requests.get(url, timeout=10).json()
        return float(res["price"])
    except:
        try:
            res = requests.get(COINGECKO_URL, timeout=10).json()
            return float(res["bitcoin"]["usd"])
        except:
            return None

def get_candles(interval):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={interval}&outputsize={MAX_CANDLES}&apikey={TWELVEDATA_API_KEY}"
        res = requests.get(url, timeout=10).json()
        return [{"datetime": v["datetime"], "open": float(v["open"]),
                 "high": float(v["high"]), "low": float(v["low"]), "close": float(v["close"])} 
                for v in reversed(res["values"])]
    except:
        return []

def evaluate_strategy(candles, strategy):
    wins, total = 0, 0
    for i in range(2, len(candles)):
        if strategy == "EMA+OB":
            signal = candles[i]["close"] > candles[i-1]["close"] > candles[i-2]["close"]
        elif strategy == "RSI":
            signal = np.mean([c["close"] for c in candles[i-14:i]]) < candles[i]["close"]
        elif strategy == "FVG":
            signal = abs(candles[i]["close"] - candles[i]["open"]) > 0.5
        else:
            signal = False

        if signal:
            total +=1
            if (candles[i]["high"] - candles[i]["close"]) >= TP1 and (candles[i]["low"] - candles[i]["close"]) < SL:
                wins +=1
    return wins, total

def select_best_strategy(candles):
    best, best_rate = None, 0
    for strat in strategy_stats.keys():
        wins, total = evaluate_strategy(candles, strat)
        strategy_stats[strat][0] += wins
        strategy_stats[strat][1] += total
        rate = (strategy_stats[strat][0] / strategy_stats[strat][1]) if strategy_stats[strat][1] else 0
        if rate > best_rate:
            best, best_rate = strat, rate
    return best

def main():
    sent_signals = set()
    last_msg = time.time()

    price = get_live_price()
    if price:
        send_telegram(f"ACHAT (Trade test)\nPE : {price:.2f}\nTP1 : {price+TP1:.2f}\nTP2 : {price+TP2:.2f}\nSL : {price-SL:.2f}")
    else:
        send_telegram("Erreur API : prix non disponible")
        return

    while True:
        m1 = get_candles("1min")
        m5 = get_candles("5min")
        m15 = get_candles("15min")
        price = get_live_price()
        if not m1 or not m5 or not m15 or price is None:
            time.sleep(60)
            continue

        best_strategy = select_best_strategy(m5)
        if not best_strategy:
            time.sleep(60)
            continue

        m1_trend = m1[-1]["close"] > m1[-2]["close"]
        m5_trend = m5[-1]["close"] > m5[-2]["close"]
        m15_trend = m15[-1]["close"] > m15[-2]["close"]

        direction = "ACHAT" if m1_trend and m5_trend and m15_trend else "VENTE" if not m1_trend and not m5_trend and not m15_trend else None

        if direction:
            pe = price
            tp1 = pe + TP1 if direction == "ACHAT" else pe - TP1
            tp2 = pe + TP2 if direction == "ACHAT" else pe - TP2
            sl = pe - SL if direction == "ACHAT" else pe + SL
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
            msg = f"{direction} ({best_strategy})\nPE : {pe:.2f}\nTP1 : {tp1:.2f}\nTP2 : {tp2:.2f}\nSL : {sl:.2f}\n[{now}]"
            key = f"{direction}_{best_strategy}_{int(pe)}"
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
