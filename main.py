import requests
import pandas as pd
import time
from datetime import datetime
from telegram import Bot

# === CONFIGURATION ===
API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"  # TwelveData
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "5min"
LIMIT = 500

TP_MULTIPLIER = 2.0  # TP = 2 x SL

bot = Bot(token=TELEGRAM_TOKEN)

# === STRATÉGIES ===
def detect_choc_bos(df):
    return df['close'].iloc[-1] > df['high'].iloc[-3] and df['close'].iloc[-2] < df['low'].iloc[-4]

def detect_ob_fvg(df):
    return df['low'].iloc[-3] < df['low'].iloc[-2] < df['low'].iloc[-1] and df['volume'].iloc[-1] > df['volume'].mean()

def detect_ema_rsi_fibo(df):
    df['EMA8'] = df['close'].ewm(span=8, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['RSI'] = compute_rsi(df['close'], 14)
    return (
        df['EMA8'].iloc[-1] > df['EMA21'].iloc[-1]
        and df['RSI'].iloc[-1] < 35
        and df['close'].iloc[-1] > df['open'].iloc[-1]
    )

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# === RÉCUPÉRATION DES DONNÉES ===
def get_data():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL.replace('/', '')}&interval={INTERVAL}&outputsize={LIMIT}&apikey={API_KEY}"
    response = requests.get(url)
    data = response.json().get("values", [])
    df = pd.DataFrame(data)
    df = df.rename(columns={"datetime": "time"})
    df["time"] = pd.to_datetime(df["time"])
    df = df.astype({"open": float, "high": float, "low": float, "close": float, "volume": float})
    df = df.sort_values("time").reset_index(drop=True)
    return df

# === SIMULATION DU TRADE ===
def simulate_trade(df, entry, sl, tp):
    for i in range(len(df)):
        high = df.iloc[i]['high']
        low = df.iloc[i]['low']
        if low <= sl:
            return "SL"
        elif high >= tp:
            return "TP"
    return "En cours"

# === MAIN ===
def analyse():
    df = get_data()
    entry = df['close'].iloc[-1]
    sl = entry - 150
    tp = entry + 300
    prix_actuel = entry

    if abs(prix_actuel - entry) > 50:
        return  # trade déjà trop éloigné

    strat_detectee = []
    if detect_choc_bos(df):
        strat_detectee.append("CHoCH + BOS")
    if detect_ob_fvg(df):
        strat_detectee.append("OB + FVG")
    if detect_ema_rsi_fibo(df):
        strat_detectee.append("EMA + RSI + Fibo")

    if not strat_detectee:
        return

    result = simulate_trade(df.iloc[-50:], entry, sl, tp)

    if result == "TP":
        message = (
            f"ACHAT\nPE : {entry}\nTP1 : {tp}\nTP2 : {entry + 1000}\nSL : {sl}\n"
            f"Stratégie : {', '.join(strat_detectee)}\nConfiance : 100 %"
        )
        bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=message)

# === TRADE TEST ===
def trade_test():
    df = get_data()
    price = df['close'].iloc[-1]
    test = (
        f"TRADE TEST\nPE : {price}\nTP1 : {price + 300}\nTP2 : {price + 1000}\nSL : {price - 150}"
    )
    bot.send_message(chat_id=TELEGRAM_CHAT_ID, text=test)

if __name__ == "__main__":
    trade_test()
    while True:
        analyse()
        time.sleep(300)
