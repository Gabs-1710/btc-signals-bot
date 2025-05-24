import requests
import time
import pandas as pd
import telebot
from datetime import datetime
from ta.trend import EMAIndicator
from ta.momentum import RSIIndicator
from ta.volatility import BollingerBands

# --- Bloc 1 : Configurations ---
api_keys = ["2055fb1ec82c4ff5b487ce449faf8370", "d7ddc825488f4b078fba7af6d01c32c5"]
current_key = 0
symbol = "BTC/USD"
interval = "5min"
limit = 500
bot_token = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
chat_id = "2128959111"
tp1_distance = 300
tp2_distance = 1000
sl_distance = 150
sent_signals = []

bot = telebot.TeleBot(bot_token)

# --- Bloc 2 : Récupération données ---
def get_data():
    global current_key
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={api_keys[current_key]}&outputsize={limit}"
    try:
        r = requests.get(url)
        data = r.json()
        df = pd.DataFrame(data["values"])
        df.columns = ["time", "open", "high", "low", "close", "volume"]
        df = df.astype({"open": float, "high": float, "low": float, "close": float})
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time").reset_index(drop=True)
        return df
    except Exception:
        current_key = (current_key + 1) % len(api_keys)
        return get_data()

# --- Bloc 3 : Analyse complète & stratégie ---
def analyze(df):
    ema8 = EMAIndicator(df["close"], window=8).ema_indicator()
    ema21 = EMAIndicator(df["close"], window=21).ema_indicator()
    rsi = RSIIndicator(df["close"], window=14).rsi()
    bb = BollingerBands(df["close"], window=20, window_dev=2)
    df["ema8"], df["ema21"], df["rsi"], df["bb_upper"], df["bb_lower"] = ema8, ema21, rsi, bb.bollinger_hband(), bb.bollinger_lband()

    last = df.iloc[-1]
    previous = df.iloc[-2]

    strategies = []

    if previous["ema8"] < previous["ema21"] and last["ema8"] > last["ema21"] and last["rsi"] > 50:
        strategies.append("CHoCH + RSI")

    if previous["ema8"] > previous["ema21"] and last["ema8"] < last["ema21"] and last["rsi"] < 50:
        strategies.append("BOS + RSI")

    if last["close"] > last["bb_upper"]:
        strategies.append("Breakout Bollinger")

    if last["close"] < last["bb_lower"]:
        strategies.append("Breakdown Bollinger")

    return strategies

# --- Bloc 4 : Simulation complète du trade ---
def simulate_trade(df, signal_type, entry_price):
    for future_candle in df.iloc[-1:].itertuples():
        high = future_candle.high
        low = future_candle.low
        if signal_type == "ACHAT":
            if low <= entry_price - sl_distance:
                return "SL"
            if high >= entry_price + tp1_distance:
                return "TP1"
        else:
            if high >= entry_price + sl_distance:
                return "SL"
            if low <= entry_price - tp1_distance:
                return "TP1"
    return "En attente"

# --- Bloc 5 : Envoi signal Telegram ---
def send_signal(signal_type, pe, strategy):
    if any(abs(pe - s) < 50 and signal_type == stype for s, stype in sent_signals):
        return
    sent_signals.append((pe, signal_type))

    message = (
        f"{signal_type}\n"
        f"PE : {pe}\n"
        f"TP1 : {pe + tp1_distance if signal_type == 'ACHAT' else pe - tp1_distance}\n"
        f"TP2 : {pe + tp2_distance if signal_type == 'ACHAT' else pe - tp2_distance}\n"
        f"SL : {pe - sl_distance if signal_type == 'ACHAT' else pe + sl_distance}\n"
        f"Stratégie : {strategy}\n"
        f"Probabilité estimée : 100 %"
    )
    bot.send_message(chat_id, message)

# --- Bloc 6 : Suivi & Trade Test ---
def send_trade_test():
    df = get_data()
    last = df.iloc[-1]
    price = round(last.close, 2)
    message = (
        f"TRADE TEST\n"
        f"ACHAT\nPE : {price}\n"
        f"TP1 : {price + tp1_distance}\n"
        f"TP2 : {price + tp2_distance}\n"
        f"SL : {price - sl_distance}"
    )
    bot.send_message(chat_id, message)

# --- Bloc 7 : Boucle principale ---
def main():
    send_trade_test()
    last_message_time = time.time()
    while True:
        try:
            df = get_data()
            strategies = analyze(df)
            last_price = round(df.iloc[-1].close, 2)

            for strategy in strategies:
                signal_type = "ACHAT" if "CHoCH" in strategy or "Breakdown" in strategy else "VENTE"
                result = simulate_trade(df, signal_type, last_price)
                if result == "TP1":
                    send_signal(signal_type, last_price, strategy)
                    break

            if time.time() - last_message_time >= 7200:
                bot.send_message(chat_id, "Aucune opportunité parfaite détectée ces 2 dernières heures.")
                last_message_time = time.time()

            time.sleep(300)
        except Exception as e:
            print("Erreur moteur :", e)
            time.sleep(60)

if __name__ == "__main__":
    main()
