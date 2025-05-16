import requests
import pandas as pd
import time
import telebot

# === PARAMÈTRES ===
API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "1min"
HIST_LIMIT = 500
TP1_PIPS = 300
TP2_PIPS = 1000
SL_PIPS = 150

bot = telebot.TeleBot(BOT_TOKEN)
envoyes = set()
trade_test_envoye = False

def envoyer_message(msg):
    try:
        bot.send_message(CHAT_ID, msg)
    except:
        pass

def recuperer_bougies():
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

def strategie_dominante(df):
    signals = []
    for i in range(10, len(df) - 20):
        zone = df.iloc[i-10:i]
        future = df.iloc[i:i+20]
        range_zone = zone["high"].max() - zone["low"].min()
        candle = df.iloc[i]
        if range_zone < 300:
            if candle["close"] > candle["open"]:
                tp = candle["close"] + TP1_PIPS
                sl = candle["close"] - SL_PIPS
                if future["low"].min() > sl and future["high"].max() >= tp:
                    signals.append(("ACHAT", candle["close"], df.iloc[i+1:]))
            elif candle["close"] < candle["open"]:
                tp = candle["close"] - TP1_PIPS
                sl = candle["close"] + SL_PIPS
                if future["high"].max() < sl and future["low"].min() <= tp:
                    signals.append(("VENTE", candle["close"], df.iloc[i+1:]))
    return signals[-1] if signals else None

def signal_exploitable(signal, pe_reel):
    sens, pe_simule, _ = signal
    return abs(pe_simule - pe_reel) <= 20

def generer_message(signal):
    sens, pe, _ = signal
    tp1 = round(pe + TP1_PIPS, 2) if sens == "ACHAT" else round(pe - TP1_PIPS, 2)
    tp2 = round(pe + TP2_PIPS, 2) if sens == "ACHAT" else round(pe - TP2_PIPS, 2)
    sl = round(pe - SL_PIPS, 2) if sens == "ACHAT" else round(pe + SL_PIPS, 2)
    return f"{sens}\nPE : {round(pe,2)}\nTP1 : {tp1}\nTP2 : {tp2}\nSL : {sl}"

def envoyer_trade_test(df):
    if df is None or len(df) < 10:
        return
    prix = df.iloc[-1]["close"]
    pe = round(prix, 2)
    tp1 = pe + TP1_PIPS
    tp2 = pe + TP2_PIPS
    sl = pe - SL_PIPS
    msg = f"TRADE TEST\nACHAT\nPE : {pe}\nTP1 : {tp1}\nTP2 : {tp2}\nSL : {sl}"
    envoyer_message(msg)

# === BOUCLE PRINCIPALE ===
while True:
    try:
        df = recuperer_bougies()
        if df is not None and len(df) > 100:
            if not trade_test_envoye:
                envoyer_trade_test(df)
                trade_test_envoye = True

            signal = strategie_dominante(df)
            if signal:
                sens, pe, _ = signal
                cle = (sens, round(pe, 1))
                if cle not in envoyes:
                    pe_reel = df.iloc[-1]["close"]
                    if signal_exploitable(signal, pe_reel):
                        msg = generer_message(signal)
                        envoyer_message(msg)
                        envoyes.add(cle)
        time.sleep(60)

    except Exception as e:
        print("Erreur :", e)
        time.sleep(60)
