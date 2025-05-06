import requests
import time
from datetime import datetime

# === CONFIGURATION ===
API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "5min"
TP1 = 300
TP2 = 1000
SL = 150
PE_TOLERANCE = 50
MAX_HISTORY = 500

sent_signals = set()
last_direction = None
trade_test_sent = False

# === FONCTIONS TELEGRAM ===
def send_telegram(msg):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    try:
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except:
        pass

# === PRIX EN DIRECT ===
def get_live_price():
    url = f"https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        return float(res.json()["price"])
    except:
        return None

# === RÉCUPÉRATION DES BOUGIES ===
def get_candles():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize={MAX_HISTORY}&apikey={API_KEY}"
    try:
        res = requests.get(url, timeout=10).json()
        if "values" not in res:
            return []
        candles = res["values"]
        for c in candles:
            for key in ["open", "high", "low", "close"]:
                c[key] = float(c[key])
        return list(reversed(candles))
    except:
        return []

# === SIMULATION TP1 / SL ===
def simulate_future(df, i, entry, direction):
    future = df[i+1:]
    tp1 = entry + TP1 if direction == "ACHAT" else entry - TP1
    tp2 = entry + TP2 if direction == "ACHAT" else entry - TP2
    sl = entry - SL if direction == "ACHAT" else entry + SL

    for candle in future:
        if direction == "ACHAT":
            if candle["low"] <= sl:
                return None
            if candle["high"] >= tp1:
                return {"type": "ACHAT", "pe": entry, "tp1": tp1, "tp2": tp2, "sl": sl}
        else:
            if candle["high"] >= sl:
                return None
            if candle["low"] <= tp1:
                return {"type": "VENTE", "pe": entry, "tp1": tp1, "tp2": tp2, "sl": sl}
    return None

# === DÉTECTION LOGIQUE PUISSANTE ===
def detect_signal(df, price_now):
    global last_direction
    for i in range(2, len(df)-10):
        c1, c2 = df[i-2], df[i-1]
        if c1["close"] < c1["open"] and c2["close"] > c2["open"] and c2["close"] > c1["high"]:
            entry = c2["close"]
            if abs(price_now - entry) <= PE_TOLERANCE and last_direction != "VENTE":
                sim = simulate_future(df, i, entry, "ACHAT")
                if sim and abs(price_now - sim["pe"]) <= PE_TOLERANCE:
                    last_direction = "ACHAT"
                    return sim
        if c1["close"] > c1["open"] and c2["close"] < c2["open"] and c2["close"] < c1["low"]:
            entry = c2["close"]
            if abs(price_now - entry) <= PE_TOLERANCE and last_direction != "ACHAT":
                sim = simulate_future(df, i, entry, "VENTE")
                if sim and abs(price_now - sim["pe"]) <= PE_TOLERANCE:
                    last_direction = "VENTE"
                    return sim
    return None

# === FORMAT MESSAGE ===
def format_msg(trade):
    return (
        f"{trade['type']}\n"
        f"PE : {trade['pe']:.2f}\n"
        f"TP1 : {trade['tp1']:.2f}\n"
        f"TP2 : {trade['tp2']:.2f}\n"
        f"SL : {trade['sl']:.2f}\n"
        f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}]"
    )

# === MAIN LOOP ===
def main():
    global sent_signals, trade_test_sent
    last_msg = time.time()

    while True:
        candles = get_candles()
        price = get_live_price()
        if not candles or price is None:
            time.sleep(60)
            continue

        if not trade_test_sent:
            test_pe = price
            test_tp1 = test_pe + TP1
            test_tp2 = test_pe + TP2
            test_sl = test_pe - SL
            send_telegram(f"ACHAT (Trade test)\nPE : {test_pe:.2f}\nTP1 : {test_tp1:.2f}\nTP2 : {test_tp2:.2f}\nSL : {test_sl:.2f}")
            trade_test_sent = True

        trade = detect_signal(candles, price)
        if trade:
            key = f"{trade['type']}_{int(trade['pe'])}"
            if key not in sent_signals:
                send_telegram(format_msg(trade))
                sent_signals.add(key)

        if time.time() - last_msg > 7200:
            send_telegram(f"Aucun signal parfait détecté pour le moment.\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}]")
            last_msg = time.time()

        time.sleep(300)

if __name__ == "__main__":
    main()
