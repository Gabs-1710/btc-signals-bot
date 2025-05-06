import requests
import time
from datetime import datetime

# === CONFIGURATION ===
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
SYMBOL = "BTCUSDT"
INTERVAL = "5m"
TP1 = 300
TP2 = 1000
SL = 150
PE_TOLERANCE = 50
MAX_CANDLES = 500

# === TELEGRAM ===
def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except:
        pass

# === PRIX TEMPS RÉEL (Binance) ===
def get_live_price():
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"
        res = requests.get(url, timeout=10)
        return float(res.json()["price"])
    except:
        return None

# === BOUGIES M5 (Binance) ===
def get_candles():
    try:
        url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit={MAX_CANDLES}"
        res = requests.get(url, timeout=10).json()
        candles = []
        for c in res:
            candles.append({
                "datetime": datetime.utcfromtimestamp(c[0] / 1000).strftime('%Y-%m-%d %H:%M:%S'),
                "open": float(c[1]),
                "high": float(c[2]),
                "low": float(c[3]),
                "close": float(c[4])
            })
        return candles
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
                "timestamp": df[i]["datetime"]
            })

        score = sum([is_bear_bos, is_bear_ob, fvg_down, sfp_sell, compressed])
        if score >= 3:
            structures.append({
                "type": "VENTE",
                "index": i,
                "price": c["close"],
                "timestamp": df[i]["datetime"]
            })

    return structures

# === BLOC 2 : SIMULATEUR ULTRA STRICT JUSQU’À TP1 / SL ===
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

# === BLOC 3 : ANTI-DOUBLON & CONTRADICTION ===
def is_duplicate_or_conflict(trade, sent_signals, last_signal):
    key = f"{trade['type']}_{int(trade['pe'])}_{trade['timestamp']}"
    if key in sent_signals:
        return True
    if last_signal and last_signal["type"] != trade["type"]:
        return True
    return False

# === BLOC 4 : SUIVI POSITION EN TEMPS RÉEL ===
def update_virtual_positions(df, open_trades):
    closed = []
    for trade in open_trades:
        direction = trade["type"]
        tp1 = trade["tp1"]
        sl = trade["sl"]
        pe = trade["pe"]

        for candle in df[-10:]:
            high, low = candle["high"], candle["low"]
            if direction == "ACHAT":
                if low <= sl:
                    send_telegram(f"❌ SL touché (ACHAT)\nEntrée : {pe:.2f}\nSL : {sl:.2f}")
                    closed.append(trade)
                    break
                if high >= tp1:
                    send_telegram(f"✅ TP1 atteint (ACHAT)\nEntrée : {pe:.2f}\nTP1 : {tp1:.2f}")
                    closed.append(trade)
                    break
            else:
                if high >= sl:
                    send_telegram(f"❌ SL touché (VENTE)\nEntrée : {pe:.2f}\nSL : {sl:.2f}")
                    closed.append(trade)
                    break
                if low <= tp1:
                    send_telegram(f"✅ TP1 atteint (VENTE)\nEntrée : {pe:.2f}\nTP1 : {tp1:.2f}")
                    closed.append(trade)
                    break
    for trade in closed:
        if trade in open_trades:
            open_trades.remove(trade)

# === BOUCLE PRINCIPALE ===
def main():
    sent_signals = set()
    open_trades = []
    last_signal = None
    last_msg = time.time()
    test_sent = False

    while True:
        df = get_candles()
        live_price = get_live_price()
        if not df or live_price is None:
            time.sleep(60)
            continue

        if not test_sent:
            pe = live_price
            tp1 = pe + TP1
            tp2 = pe + TP2
            sl = pe - SL
            send_telegram(f"ACHAT (Trade test)\nPE : {pe:.2f}\nTP1 : {tp1:.2f}\nTP2 : {tp2:.2f}\nSL : {sl:.2f}")
            test_sent = True

        update_virtual_positions(df, open_trades)

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
                open_trades.append(trade)

        if time.time() - last_msg > 7200:
            send_telegram(f"Aucun signal parfait détecté pour le moment.\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}]")
            last_msg = time.time()

        time.sleep(300)

if __name__ == "__main__":
    main()
