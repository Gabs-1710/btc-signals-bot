import requests
import pandas as pd
import time
import telebot

# === CONFIGURATION ===
API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "1min"
HIST_LIMIT = 500
TP1_PIPS = 300
TP2_PIPS = 1000
SL_PIPS = 150
TOLERANCE = 20

bot = telebot.TeleBot(BOT_TOKEN)
envoyes = set()
trade_test_envoye = False

def envoyer_message(msg):
    try:
        bot.send_message(CHAT_ID, msg)
    except Exception as e:
        print("Erreur Telegram :", e)

def recuperer_bougies():
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize={HIST_LIMIT}&apikey={API_KEY}"
        r = requests.get(url)
        data = r.json()
        if "values" not in data:
            return None
        df = pd.DataFrame(data["values"])
        df = df.rename(columns={"datetime": "time"})
        df["time"] = pd.to_datetime(df["time"])
        df = df.sort_values("time")
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        return df.reset_index(drop=True)
    except Exception as e:
        print("Erreur récupération bougies :", e)
        return None

def strategie_intelligente(df):
    for i in range(30, len(df) - 50):
        zone = df.iloc[i-20:i]
        candle = df.iloc[i]
        future = df.iloc[i+1:i+50]
        compression = zone["high"].max() - zone["low"].min() < 300

        if compression:
            if candle["close"] > candle["open"]:  # ACHAT
                pe = candle["close"]
                tp1 = pe + TP1_PIPS
                tp2 = pe + TP2_PIPS
                sl = pe - SL_PIPS
                low_future = future["low"].min()
                high_future = future["high"].max()
                if low_future > sl and high_future >= tp1:
                    return ("ACHAT", pe, tp1, tp2, sl)
            elif candle["close"] < candle["open"]:  # VENTE
                pe = candle["close"]
                tp1 = pe - TP1_PIPS
                tp2 = pe - TP2_PIPS
                sl = pe + SL_PIPS
                high_future = future["high"].max()
                low_future = future["low"].min()
                if high_future < sl and low_future <= tp1:
                    return ("VENTE", pe, tp1, tp2, sl)
    return None

def exploitable(signal, prix_reel):
    if not signal: return False
    sens, pe, _, _, _ = signal
    return abs(pe - prix_reel) <= TOLERANCE

def generer_message(signal):
    sens, pe, tp1, tp2, sl = signal
    return f"{sens}\nPE : {round(pe,2)}\nTP1 : {round(tp1,2)}\nTP2 : {round(tp2,2)}\nSL : {round(sl,2)}"

def envoyer_trade_test(df):
    if df is None or len(df) < 10: return
    prix = df.iloc[-1]["close"]
    pe = round(prix, 2)
    msg = f"TRADE TEST\nACHAT\nPE : {pe}\nTP1 : {pe + TP1_PIPS}\nTP2 : {pe + TP2_PIPS}\nSL : {pe - SL_PIPS}"
    envoyer_message(msg)

# === MOTEUR ===
while True:
    try:
        df = recuperer_bougies()
        if df is not None and len(df) >= 100:
            if not trade_test_envoye:
                envoyer_trade_test(df)
                trade_test_envoye = True

            signal = strategie_intelligente(df)
            if signal:
                sens, pe, _, _, _ = signal
                cle = (sens, round(pe, 1))
                prix_reel = df.iloc[-1]["close"]

                if cle not in envoyes and exploitable(signal, prix_reel):
                    msg = generer_message(signal)
                    envoyer_message(msg)
                    envoyes.add(cle)

        time.sleep(60)

    except Exception as e:
        print("Erreur principale :", e)
        time.sleep(60)
