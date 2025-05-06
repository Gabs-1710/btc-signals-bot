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

# === TELEGRAM ===
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except:
        pass

# === PRIX TEMPS RÉEL ===
def get_live_price():
    url = f"https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={API_KEY}"
    try:
        res = requests.get(url, timeout=10)
        return float(res.json()["price"])
    except:
        return None

# === HISTORIQUE DES BOUGIES ===
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

# === BLOC 1 : STRUCTURES PUISSANTES ===
def detect_structures(df):
    structures = []
    for i in range(50, len(df)-10):
        c = df[i]
        prev = df[i-1]
        pre_prev = df[i-2]

        is_bull_bos = pre_prev["high"] < prev["high"] < c["high"] and prev["close"] > pre_prev["high"]
        is_bear_bos = pre_prev["low"] > prev["low"] > c["low"] and prev["close"] < pre_prev["low"]

        is_bull_ob = c["open"] < c["close"] and df[i+1]["high"] > c["high"]
        is_bear_ob = c["open"] > c["close"] and df[i+1]["low"] < c["low"]

        fvg_up = df[i-1]["low"] > c["high"]
        fvg_down = df[i-1]["high"] < c["low"]

        sfp_buy = c["low"] < df[i-1]["low"] and c["close"] > c["open"]
        sfp_sell = c["high"] > df[i-1]["high"] and c["close"] < c["open"]

        compressed = (
            abs(df[i-2]["high"] - df[i-2]["low"]) > abs(df[i-1]["high"] - df[i-1]["low"]) > abs(c["high"] - c["low"])
        )

        score = sum([is_bull_bos, is_bull_ob, fvg_up, sfp_buy, compressed])
        if score >= 3:
            structures.append({
                "type": "ACHAT",
                "index": i,
                "price": c["close"],
                "elements": score,
                "timestamp": df[i]["datetime"]
            })

        score = sum([is_bear_bos, is_bear_ob, fvg_down, sfp_sell, compressed])
        if score >= 3:
            structures.append({
                "type": "VENTE",
                "index": i,
                "price": c["close"],
                "elements": score,
                "timestamp": df[i]["datetime"]
            })

    return structures

# === BLOC 2 : SIMULATEUR TP1/SL ===
def simulate_trades(df, structures):
    validated = []

    for s in structures:
        i = s["index"]
        direction = s["type"]
        entry = s["price"]

        tp1 = entry + TP1 if direction == "ACHAT" else entry - TP1
        tp2 = entry + TP2 if direction == "ACHAT" else entry - TP2
        sl = entry - SL if direction == "ACHAT" else entry + SL

        future = df[i+1:]
        tp1_hit = False
        sl_hit = False

        for candle in future:
            high, low = candle["high"], candle["low"]

            if direction == "ACHAT":
                if low <= sl:
                    sl_hit = True
                    break
                if high >= tp1:
                    tp1_hit = True
                    break
            else:
                if high >= sl:
                    sl_hit = True
                    break
                if low <= tp1:
                    tp1_hit = True
                    break

        if tp1_hit and not sl_hit:
            validated.append({
                "type": direction,
                "pe": entry,
                "tp1": tp1,
                "tp2": tp2,
                "sl": sl,
                "timestamp": s["timestamp"]
            })

    return validated

# === BLOC 4 : ANTI-DOUBLON / CONTRADICTION ===
def is_duplicate_or_conflict(trade, sent_signals, last_signal):
    key = f"{trade['type']}_{int(trade['pe'])}_{trade['timestamp']}"
    if key in sent_signals:
        return True
    if last_signal:
        if last_signal["type"] != trade["type"]:
            t1 = datetime.strptime(trade["timestamp"], "%Y-%m-%d %H:%M:%S")
            t2 = datetime.strptime(last_signal["timestamp"], "%Y-%m-%d %H:%M:%S")
            if abs((t1 - t2).total_seconds()) < 1800:
                return True
    return False

# === BOUCLE PRINCIPALE ===
def main():
    sent_signals = set()
    last_signal = None
    last_msg = time.time()
    test_sent = False

    while True:
        df = get_candles()
        live_price = get_live_price()
        if not df or live_price is None:
            time.sleep(60)
            continue

        # Envoi Trade test au démarrage
        if not test_sent:
            pe = live_price
            tp1 = pe + TP1
            tp2 = pe + TP2
            sl = pe - SL
            send_telegram(f"ACHAT (Trade test)\nPE : {pe:.2f}\nTP1 : {tp1:.2f}\nTP2 : {tp2:.2f}\nSL : {sl:.2f}")
            test_sent = True

        structures = detect_structures(df)
        validated_trades = simulate_trades(df, structures)

        for trade in validated_trades:
            if is_duplicate_or_conflict(trade, sent_signals, last_signal):
                continue
            if abs(trade["pe"] - live_price) <= PE_TOLERANCE:
                msg = (
                    f"{trade['type']}\n"
                    f"PE : {trade['pe']:.2f}\n"
                    f"TP1 : {trade['tp1']:.2f}\n"
                    f"TP2 : {trade['tp2']:.2f}\n"
                    f"SL : {trade['sl']:.2f}\n"
                    f"[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}]"
                )
                send_telegram(msg)
                key = f"{trade['type']}_{int(trade['pe'])}_{trade['timestamp']}"
                sent_signals.add(key)
                last_signal = trade

        if time.time() - last_msg > 7200:
            send_telegram(f"Aucun signal parfait détecté pour le moment.\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}]")
            last_msg = time.time()

        time.sleep(300)

if __name__ == "__main__":
    main()
