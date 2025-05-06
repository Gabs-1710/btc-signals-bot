import requests
import time
from datetime import datetime
import numpy as np

# === CONFIG ===
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
SYMBOL = "BTCUSDT"
INTERVAL = "5m"
TP1 = 300
TP2 = 1000
SL = 150
PE_TOLERANCE = 50
MAX_CANDLES = 500

def send_telegram(msg):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        requests.post(url, data={"chat_id": TELEGRAM_CHAT_ID, "text": msg})
    except:
        pass

def get_live_price():
    try:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={SYMBOL}"
        res = requests.get(url, timeout=10)
        return float(res.json()["price"])
    except:
        return None

def wait_for_live_price():
    price = None
    while price is None:
        price = get_live_price()
        if price is None:
            time.sleep(1)
    return price

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

def calculate_ema(series, period=20):
    return np.convolve(series, np.ones(period)/period, mode='valid')

def detect_perfect_structures(df, ema_m5, ema_m15, ema_h1, ema_d1):
    structures = []
    offset = len(df) - len(ema_m5)
    for i in range(50, len(df)-10):
        c = df[i]
        prev = df[i-1]
        pre = df[i-2]

        is_bull_bos = pre["high"] < prev["high"] < c["high"] and prev["close"] > pre["high"]
        is_bear_bos = pre["low"] > prev["low"] > c["low"] and prev["close"] < pre["low"]

        is_bull_ob = c["open"] < c["close"] and df[i+1]["high"] > c["high"]
        is_bear_ob = c["open"] > c["close"] and df[i+1]["low"] < c["low"]

        fvg_up = df[i-1]["low"] > c["high"]
        fvg_down = df[i-1]["high"] < c["low"]

        fib_up = fib_down = False
        if i >= 3:
            swing_low = min(df[i-3]["low"], df[i-2]["low"])
            swing_high = max(df[i-3]["high"], df[i-2]["high"])
            range_ = swing_high - swing_low + 1e-6
            retrace_up = (c["close"] - swing_low) / range_
            retrace_down = (swing_high - c["close"]) / range_
            fib_up = 0.618 <= retrace_up <= 0.786
            fib_down = 0.618 <= retrace_down <= 0.786

        compression = (
            abs(df[i-2]["high"] - df[i-2]["low"]) >
            abs(df[i-1]["high"] - df[i-1]["low"]) >
            abs(c["high"] - c["low"])
        )

        sfp_buy = c["low"] < df[i-1]["low"] and c["close"] > c["open"]
        sfp_sell = c["high"] > df[i-1]["high"] and c["close"] < c["open"]

        j = i - offset if i - offset < len(ema_m5) else -1
        ema_up = ema_m5[j] > ema_m15[j] > ema_h1[j] > ema_d1[j] if j >= 0 else False
        ema_down = ema_m5[j] < ema_m15[j] < ema_h1[j] < ema_d1[j] if j >= 0 else False

        wyck_buy = df[i-4]["low"] > df[i-3]["low"] > df[i-2]["low"] and c["close"] > df[i-2]["close"]
        wyck_sell = df[i-4]["high"] < df[i-3]["high"] < df[i-2]["high"] and c["close"] < df[i-2]["close"]

        if is_bull_bos and is_bull_ob and fvg_up and fib_up and compression and sfp_buy and ema_up and wyck_buy:
            structures.append({"type": "ACHAT", "index": i, "price": c["close"], "timestamp": c["datetime"]})
        if is_bear_bos and is_bear_ob and fvg_down and fib_down and compression and sfp_sell and ema_down and wyck_sell:
            structures.append({"type": "VENTE", "index": i, "price": c["close"], "timestamp": c["datetime"]})
    return structures

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
                if low <= sl: sl_hit = True; break
                if high >= tp1: tp1_hit = True; break
            else:
                if high >= sl: sl_hit = True; break
                if low <= tp1: tp1_hit = True; break
        if tp1_hit and not sl_hit:
            validated.append({
                "type": direction, "pe": entry, "tp1": tp1, "tp2": tp2, "sl": sl, "timestamp": s["timestamp"]
            })
    return validated

def is_duplicate_or_conflict(trade, sent_signals, last_signal):
    key = f"{trade['type']}_{int(trade['pe'])}_{trade['timestamp']}"
    if key in sent_signals: return True
    if last_signal and last_signal["type"] != trade["type"]: return True
    return False

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
                    send_telegram(f"â SL touchÃ© (ACHAT)\nEntrÃ©e : {pe:.2f}\nSL : {sl:.2f}")
                    closed.append(trade)
                    break
                if high >= tp1:
                    send_telegram(f"â TP1 atteint (ACHAT)\nEntrÃ©e : {pe:.2f}\nTP1 : {tp1:.2f}")
                    closed.append(trade)
                    break
            else:
                if high >= sl:
                    send_telegram(f"â SL touchÃ© (VENTE)\nEntrÃ©e : {pe:.2f}\nSL : {sl:.2f}")
                    closed.append(trade)
                    break
                if low <= tp1:
                    send_telegram(f"â TP1 atteint (VENTE)\nEntrÃ©e : {pe:.2f}\nTP1 : {tp1:.2f}")
                    closed.append(trade)
                    break
    for trade in closed:
        if trade in open_trades:
            open_trades.remove(trade)

def main():
    sent_signals = set()
    open_trades = []
    last_signal = None
    last_msg = time.time()

    # Trade test dÃ¨s le lancement avec prix garanti
    price = wait_for_live_price()
    tp1 = price + TP1
    tp2 = price + TP2
    sl = price - SL
    now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
    send_telegram(f"ACHAT (Trade test)\nPE : {price:.2f}\nTP1 : {tp1:.2f}\nTP2 : {tp2:.2f}\nSL : {sl:.2f}\n[{now}]")

    while True:
        df = get_candles()
        live_price = get_live_price()
        if not df or live_price is None:
            time.sleep(60)
            continue

        close_prices = [x["close"] for x in df]
        ema_m5 = calculate_ema(close_prices, 20)
        ema_m15 = calculate_ema(close_prices, 40)
        ema_h1 = calculate_ema(close_prices, 60)
        ema_d1 = calculate_ema(close_prices, 100)

        update_virtual_positions(df, open_trades)

        structures = detect_perfect_structures(df, ema_m5, ema_m15, ema_h1, ema_d1)
        validated_trades = simulate_trades(df, structures)

        for trade in validated_trades:
            if is_duplicate_or_conflict(trade, sent_signals, last_signal):
                continue
            if abs(trade["pe"] - live_price) <= PE_TOLERANCE:
                msg = (
                    f"{trade['type']}\nPE : {trade['pe']:.2f}\nTP1 : {trade['tp1']:.2f}\n"
                    f"TP2 : {trade['tp2']:.2f}\nSL : {trade['sl']:.2f}\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}]"
                )
                send_telegram(msg)
                key = f"{trade['type']}_{int(trade['pe'])}_{trade['timestamp']}"
                sent_signals.add(key)
                last_signal = trade
                open_trades.append(trade)

        if time.time() - last_msg > 7200:
            send_telegram(f"Aucun signal parfait dÃ©tectÃ© pour le moment.\n[{datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}]")
            last_msg = time.time()

        time.sleep(300)

if __name__ == "__main__":
    main()
