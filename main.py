import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from itertools import combinations

# === Bloc 1 : Bougies Binance ===
def get_binance_m5_bars(symbol="BTCUSDT", interval="5m", limit=1000):
    url = "https://api.binance.com/api/v3/klines"
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        raw_data = response.json()
        df = pd.DataFrame(raw_data, columns=[
            "open_time", "open", "high", "low", "close", "volume",
            "close_time", "quote_asset_volume", "number_of_trades",
            "taker_buy_base_volume", "taker_buy_quote_volume", "ignore"
        ])
        df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
        df["close_time"] = pd.to_datetime(df["close_time"], unit="ms")
        df[["open", "high", "low", "close", "volume"]] = df[["open", "high", "low", "close", "volume"]].astype(float)
        return df[["open_time", "open", "high", "low", "close"]]
    except Exception as e:
        print(f"Erreur récupération Binance : {e}")
        return pd.DataFrame()

# === Bloc 2 : Backtest ===
def backtest_strategy(df, strategy_function, sl_pips=150, tp1_pips=300, tp2_pips=1000):
    valid_trades = []
    signals = strategy_function(df)
    for signal in signals:
        idx = signal["index"]
        if idx >= len(df) - 1:
            continue
        entry = df.iloc[idx]["close"]
        next_bars = df.iloc[idx + 1:idx + 20]
        tp1 = entry + tp1_pips if signal["type"] == "buy" else entry - tp1_pips
        tp2 = entry + tp2_pips if signal["type"] == "buy" else entry - tp2_pips
        sl  = entry - sl_pips  if signal["type"] == "buy" else entry + sl_pips
        hit_tp1 = hit_sl = False
        for _, row in next_bars.iterrows():
            if signal["type"] == "buy":
                if row["low"] <= sl: hit_sl = True; break
                if row["high"] >= tp1: hit_tp1 = True; break
            else:
                if row["high"] >= sl: hit_sl = True; break
                if row["low"] <= tp1: hit_tp1 = True; break
        if hit_tp1 and not hit_sl:
            valid_trades.append({
                "index": idx, "type": signal["type"], "entry": entry,
                "tp1": tp1, "tp2": tp2, "sl": sl, "time": df.iloc[idx]["open_time"]
            })
    return valid_trades

# === Bloc 3 : Stratégies combinées ===
def module_choch(df, i):
    return (df["high"].iloc[i] > max(df["high"].iloc[i-5:i]) and df["close"].iloc[i] > df["open"].iloc[i],
            df["low"].iloc[i] < min(df["low"].iloc[i-5:i]) and df["close"].iloc[i] < df["open"].iloc[i])

def module_order_block(df, i):
    return (df["low"].iloc[i] < df["low"].iloc[i-1] and df["close"].iloc[i] > df["open"].iloc[i],
            df["high"].iloc[i] > df["high"].iloc[i-1] and df["close"].iloc[i] < df["open"].iloc[i])

def module_fvg(df, i):
    body = abs(df["close"].iloc[i] - df["open"].iloc[i])
    prev = abs(df["close"].iloc[i-1] - df["open"].iloc[i-1])
    next_ = abs(df["close"].iloc[i+1] - df["open"].iloc[i+1])
    return (body > prev * 1.5 and body > next_ * 1.5 and df["close"].iloc[i] > df["open"].iloc[i],
            body > prev * 1.5 and body > next_ * 1.5 and df["close"].iloc[i] < df["open"].iloc[i])

def module_ema_aligned(df, i):
    return (df["ema21"].iloc[i] > df["ema50"].iloc[i] > df["ema200"].iloc[i],
            df["ema21"].iloc[i] < df["ema50"].iloc[i] < df["ema200"].iloc[i])

def module_rsi(df, i):
    return (df["rsi"].iloc[i] < 30, df["rsi"].iloc[i] > 70)

def module_double_bottom(df, i):
    return (abs(df["low"].iloc[i] - df["low"].iloc[i-3]) < df["low"].iloc[i] * 0.001,
            abs(df["high"].iloc[i] - df["high"].iloc[i-3]) < df["high"].iloc[i] * 0.001)

def generate_all_strategy_combinations(df):
    modules = [
        ("CHoCH", module_choch),
        ("OrderBlock", module_order_block),
        ("FVG", module_fvg),
        ("EMA", module_ema_aligned),
        ("RSI", module_rsi),
        ("DoubleBottom", module_double_bottom)
    ]
    strategy_functions = []
    for r in range(2, len(modules)+1):
        for combo in combinations(modules, r):
            combo_names = [m[0] for m in combo]
            combo_funcs = [m[1] for m in combo]
            def strategy(df, funcs=combo_funcs):
                signals = []
                for i in range(20, len(df)-20):
                    longs, shorts = [], []
                    for f in funcs:
                        b, s = f(df, i)
                        longs.append(b)
                        shorts.append(s)
                    if all(longs): signals.append({"index": i, "type": "buy"})
                    elif all(shorts): signals.append({"index": i, "type": "sell"})
                return signals
            strategy_functions.append((" + ".join(combo_names), strategy))
    return strategy_functions

# === Bloc 4 : Format message Telegram ===
def format_telegram_message(trade):
    direction = "ACHAT" if trade["type"] == "buy" else "VENTE"
    return (
        f"{direction}\n"
        f"PE : {trade['entry']:.2f}\n"
        f"TP1 : {trade['tp1']:.2f}\n"
        f"TP2 : {trade['tp2']:.2f}\n"
        f"SL : {trade['sl']:.2f}"
    )

# === Bloc 5 : Envoi Telegram ===
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"

def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
    try:
        response = requests.post(url, data=payload)
        response.raise_for_status()
        print("Message envoyé Telegram.")
    except Exception as e:
        print(f"Erreur Telegram : {e}")

# === Bloc 6 : Boucle continue ===
def main_loop():
    last_alert_time = datetime.utcnow() - timedelta(hours=2)
    while True:
        print(f"Analyse à {datetime.utcnow()}")

        df = get_binance_m5_bars()
        if df.empty:
            time.sleep(300)
            continue

        df["ema21"] = df["close"].ewm(span=21).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()
        df["ema200"] = df["close"].ewm(span=200).mean()
        delta = df["close"].diff()
        gain = delta.clip(lower=0).rolling(14).mean()
        loss = -delta.clip(upper=0).rolling(14).mean()
        rs = gain / loss
        df["rsi"] = 100 - (100 / (1 + rs))

        strategies = generate_all_strategy_combinations(df)
        found_signal = False

        for name, func in strategies:
            trades = backtest_strategy(df, func)
            if len(trades) > 0:
                print(f"Stratégie détectée : {name}")
                for trade in trades:
                    msg = format_telegram_message(trade)
                    send_telegram_message(msg)
                found_signal = True
                break

        if not found_signal and datetime.utcnow() - last_alert_time > timedelta(hours=2):
            send_telegram_message("Aucun signal parfait détecté pour le moment.")
            last_alert_time = datetime.utcnow()

        time.sleep(300)

# === Lancement ===
if __name__ == "__main__":
    main_loop()
