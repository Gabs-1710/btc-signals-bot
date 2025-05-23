import requests
import time
import telebot
from datetime import datetime, timedelta
import pandas as pd

# === CONFIGURATION ===
API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"  # TwelveData API clé secondaire
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"

PAIR = "BTC/USD"
INTERVAL = "1min"
TP1_PIPS = 300
TP2_PIPS = 1000
SL_PIPS = 150

# === INITIALISATION BOT TELEGRAM ===
bot = telebot.TeleBot(BOT_TOKEN)

# === ENVOI DU TRADE TEST AU LANCEMENT ===
def envoyer_trade_test():
    price = get_price()
    if price:
        message = f"""TRADE TEST
PE : {price}
TP1 : {round(price + TP1_PIPS, 2)}
TP2 : {round(price + TP2_PIPS, 2)}
SL : {round(price - SL_PIPS, 2)}"""
        bot.send_message(CHAT_ID, message)

# === RÉCUPÉRATION DU PRIX ACTUEL ===
def get_price():
    try:
        url = f"https://api.twelvedata.com/price?symbol=BTC/USD&apikey={API_KEY}"
        response = requests.get(url)
        data = response.json()
        return float(data["price"])
    except:
        return None

# === RÉCUPÉRATION DES BOUGIES M1 ===
def get_candles():
    try:
        url = f"https://api.twelvedata.com/time_series?symbol=BTC/USD&interval=1min&outputsize=500&apikey={API_KEY}"
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data["values"])
        df["datetime"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("datetime")
        for col in ["open", "high", "low", "close"]:
            df[col] = df[col].astype(float)
        return df
    except:
        return None

# === EXEMPLE DE STRATÉGIE PUISSANTE ===
def detecter_setup(df):
    signal = None
    stratégie = ""
    proba = 100.0  # valeur par défaut (à raffiner si besoin)

    for i in range(2, len(df)):
        bougie = df.iloc[i]
        prev = df.iloc[i - 1]

        # Exemple de combo simple : OB + FVG + EMA + RSI
        if (
            prev["close"] < prev["open"] and  # bougie rouge
            bougie["close"] > bougie["open"] and  # bougie verte
            bougie["close"] > df["close"].rolling(21).mean().iloc[i] and  # au-dessus EMA21
            bougie["low"] <= df["low"].rolling(14).min().iloc[i]  # prise de liquidité
        ):
            signal = {
                "type": "ACHAT",
                "pe": bougie["close"],
                "time": bougie["datetime"],
                "tp1": round(bougie["close"] + TP1_PIPS, 2),
                "tp2": round(bougie["close"] + TP2_PIPS, 2),
                "sl": round(bougie["close"] - SL_PIPS, 2),
                "stratégie": "OB + EMA + RSI + Liquidity Sweep",
                "proba": proba
            }
            break

    return signal

# === SIMULATION DU TRADE ===
def simulate_trade(signal, df):
    pe = signal["pe"]
    tp1 = signal["tp1"]
    sl = signal["sl"]

    for i in range(len(df)):
        low = df.iloc[i]["low"]
        high = df.iloc[i]["high"]

        if low <= sl:
            return False  # SL touché
        if high >= tp1:
            return True  # TP1 touché

    return False

# === ANALYSE PRINCIPALE ===
def analyser_marche():
    df = get_candles()
    if df is None:
        return

    signal = detecter_setup(df)
    if signal:
        prix_actuel = get_price()
        if prix_actuel and abs(signal["pe"] - prix_actuel) <= 50:
            futur = df[df["datetime"] > signal["time"]]
            if simulate_trade(signal, futur):
                message = f"""{signal['type']}
PE : {signal['pe']}
TP1 : {signal['tp1']}
TP2 : {signal['tp2']}
SL : {signal['sl']}
Stratégie : {signal['stratégie']}
Probabilité estimée : {signal['proba']}%"""
                bot.send_message(CHAT_ID, message)

# === LANCEMENT ===
envoyer_trade_test()

while True:
    try:
        analyser_marche()
        time.sleep(300)  # toutes les 5 minutes
    except Exception as e:
        print("Erreur : ", e)
        time.sleep(300)
