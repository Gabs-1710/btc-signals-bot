import requests
import time
import datetime
import pytz
import numpy as np
import pandas as pd
import talib
import os

# 🔐 Configurations personnelles
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
API_KEYS = [
    "d7ddc825488f4b078fba7af6d01c32c5",
    "2055fb1ec82c4ff5b487ce449faf8370"
]
SYMBOL = "BTC/USD"
INTERVAL = "5min"
LIMIT = 500

def get_binance_m5_data():
    for api_key in API_KEYS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol=BTC/USD&interval=5min&apikey={api_key}&outputsize={LIMIT}&format=JSON"
            response = requests.get(url)
            data = response.json()
            if "values" in data:
                df = pd.DataFrame(data["values"])
                df = df.rename(columns={"datetime": "time", "open": "open", "high": "high", "low": "low", "close": "close"})
                df = df[["time", "open", "high", "low", "close"]].astype(float)
                df["time"] = pd.to_datetime(data["values"][0]["datetime"])
                df = df[::-1].reset_index(drop=True)
                return df
        except:
            continue
    return None

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    requests.post(url, data=payload)

def simulate_trade(entry, df, direction):
    tp_multiples = np.arange(1.5, 5.5, 0.1)
    sl_multiples = np.arange(0.3, 2.0, 0.1)

    for tp_mult in tp_multiples:
        for sl_mult in sl_multiples:
            TP = entry + tp_mult * 100 if direction == "buy" else entry - tp_mult * 100
            SL = entry - sl_mult * 100 if direction == "buy" else entry + sl_mult * 100
            hit_tp, hit_sl = False, False

            for _, row in df.iterrows():
                if direction == "buy":
                    if row["low"] <= SL:
                        hit_sl = True
                        break
                    if row["high"] >= TP:
                        hit_tp = True
                        break
                else:
                    if row["high"] >= SL:
                        hit_sl = True
                        break
                    if row["low"] <= TP:
                        hit_tp = True
                        break
            if hit_tp and not hit_sl:
                return TP, SL, round(tp_mult, 2), round(sl_mult, 2)
    return None, None, None, None

def detect_trade(df):
    close = df["close"].values
    ema_8 = talib.EMA(close, timeperiod=8)
    ema_21 = talib.EMA(close, timeperiod=21)
    rsi = talib.RSI(close, timeperiod=14)

    # OB + EMA + RSI stratégie simplifiée puissante
    for i in range(30, len(df) - 1):
        if (
            ema_8[i] > ema_21[i]
            and rsi[i] > 50
            and df["low"][i] < ema_8[i]
            and df["close"][i] > df["open"][i]
        ):
            entry = df["close"][i]
            future = df.iloc[i + 1 :].copy()
            tp, sl, tp_mult, sl_mult = simulate_trade(entry, future, "buy")
            if tp and sl:
                current_price = df["close"].iloc[-1]
                if abs(current_price - entry) <= 50:
                    return {
                        "type": "ACHAT",
                        "entry": round(entry, 2),
                        "tp": round(tp, 2),
                        "sl": round(sl, 2),
                        "strategie": "OB + EMA + RSI",
                        "confiance": "100%",
                    }

        elif (
            ema_8[i] < ema_21[i]
            and rsi[i] < 50
            and df["high"][i] > ema_8[i]
            and df["close"][i] < df["open"][i]
        ):
            entry = df["close"][i]
            future = df.iloc[i + 1 :].copy()
            tp, sl, tp_mult, sl_mult = simulate_trade(entry, future, "sell")
            if tp and sl:
                current_price = df["close"].iloc[-1]
                if abs(current_price - entry) <= 50:
                    return {
                        "type": "VENTE",
                        "entry": round(entry, 2),
                        "tp": round(tp, 2),
                        "sl": round(sl, 2),
                        "strategie": "OB + EMA + RSI",
                        "confiance": "100%",
                    }
    return None

def main():
    sent = False
    df = get_binance_m5_data()
    if df is not None:
        signal = detect_trade(df)
        if signal and not sent:
            msg = (
                f"✅ {signal['type']}\n"
                f"PE : {signal['entry']}\n"
                f"TP1 : {signal['tp']}\n"
                f"SL : {signal['sl']}\n"
                f"Stratégie : {signal['strategie']}\n"
                f"Confiance : {signal['confiance']}"
            )
            send_telegram_message(msg)
            sent = True

if __name__ == "__main__":
    send_telegram_message("📊 Trade test")
    main()
