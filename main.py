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
LIMIT = 600
TP1_PIPS = 300
TP2_PIPS = 1000
SL_PIPS = 150
TOLERANCE = 20

bot = telebot.TeleBot(BOT_TOKEN)
envoyes = set()
test_envoye = False

def envoyer_message(msg):
    try:
        bot.send_message(CHAT_ID, msg)
    except Exception as e:
        print("Erreur Telegram :", e)

def get_bougies():
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize={LIMIT}&apikey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    if "values" not in data:
        return None
    df = pd.DataFrame(data["values"])
    df = df.rename(columns={"datetime": "time"})
    df["time"] = pd.to_datetime(df["time"])
    df = df.sort_values("time").reset_index(drop=True)
    df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
    return df

def simuler_trade(df, sens, pe):
    future = df[df["time"] > df[df["close"] == pe]["time"].values[0]]
    sl = pe - SL_PIPS if sens == "ACHAT" else pe + SL_PIPS
    tp = pe + TP1_PIPS if sens == "ACHAT" else pe - TP1_PIPS

    for _, row in future.iterrows():
        if sens == "ACHAT":
            if row["low"] <= sl:
                return False
            if row["high"] >= tp:
                return True
        else:
            if row["high"] >= sl:
                return False
            if row["low"] <= tp:
                return True
    return False

def detecter_signal(df):
    for i in range(30, len(df)-50):
        zone = df.iloc[i-20:i]
        bougie = df.iloc[i]
        future = df.iloc[i+1:i+500]

        compression = zone["high"].max() - zone["low"].min() < 300
        if not compression:
            continue

        if bougie["close"] > bougie["open"]:
            sens = "ACHAT"
        elif bougie["close"] < bougie["open"]:
            sens = "VENTE"
        else:
            continue

        pe = round(bougie["close"], 2)
        if simuler_trade(df.iloc[i:], sens, pe):
            return (sens, pe)
    return None

def generer_message(sens, pe):
    tp1 = pe + TP1_PIPS if sens == "ACHAT" else pe - TP1_PIPS
    tp2 = pe + TP2_PIPS if sens == "ACHAT" else pe - TP2_PIPS
    sl = pe - SL_PIPS if sens == "ACHAT" else pe + SL_PIPS
    return f"{sens}\nPE : {round(pe,2)}\nTP1 : {round(tp1,2)}\nTP2 : {round(tp2,2)}\nSL : {round(sl,2)}"

def envoyer_trade_test(df):
    prix = df.iloc[-1]["close"]
    pe = round(prix, 2)
    msg = f"TRADE TEST\nACHAT\nPE : {pe}\nTP1 : {pe + TP1_PIPS}\nTP2 : {pe + TP2_PIPS}\nSL : {pe - SL_PIPS}"
    envoyer_message(msg)

# === BOUCLE PRINCIPALE ===
while True:
    try:
        df = get_bougies()
        if df is not None and len(df) >= 100:
            if not test_envoye:
                envoyer_trade_test(df)
                test_envoye = True

            signal = detecter_signal(df)
            if signal:
                sens, pe = signal
                cle = (sens, round(pe, 1))
                prix_reel = df.iloc[-1]["close"]

                if cle not in envoyes and abs(prix_reel - pe) <= TOLERANCE:
                    msg = generer_message(sens, pe)
                    envoyer_message(msg)
                    envoyes.add(cle)

        time.sleep(60)

    except Exception as e:
        print("Erreur boucle :", e)
        time.sleep(60)
