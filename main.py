import requests
import pandas as pd
import time
from datetime import datetime
import telebot

# === CONFIGURATION ===
API_KEY = "2055fb1ec82c4ff5b487ce449faf8370"  # TwelveData
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "1min"
TP1 = 300
TP2 = 1000
SL = 300
TOLERANCE_PIPS = 50
BOUGIES_PASSES = 500
BOUGIES_FUTURES = 300

bot = telebot.TeleBot(BOT_TOKEN)
derniers_signaux = []

def envoyer_message(msg):
    try:
        bot.send_message(CHAT_ID, msg)
    except Exception as e:
        print("Erreur envoi message :", e)

def get_bougies(limit=1000):
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize={limit}&apikey={API_KEY}"
    r = requests.get(url)
    data = r.json()
    if "values" not in data:
        return None
    df = pd.DataFrame(data["values"])
    df["time"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("time").reset_index(drop=True)
    for col in ["open", "high", "low", "close"]:
        df[col] = df[col].astype(float)
    return df

def valider_strategie(df):
    ema8 = df["close"].rolling(8).mean()
    ema21 = df["close"].rolling(21).mean()
    ema_ok = ema8.iloc[-1] > ema21.iloc[-1]

    # Pattern engulfing simple
    bullish = (
        df["close"].iloc[-2] < df["open"].iloc[-2] and
        df["close"].iloc[-1] > df["open"].iloc[-1] and
        df["close"].iloc[-1] > df["open"].iloc[-2]
    )
    bearish = (
        df["close"].iloc[-2] > df["open"].iloc[-2] and
        df["close"].iloc[-1] < df["open"].iloc[-1] and
        df["close"].iloc[-1] < df["open"].iloc[-2]
    )

    if ema_ok and bullish:
        return "ACHAT"
    elif not ema_ok and bearish:
        return "VENTE"
    else:
        return None

def simuler_trade(bougies_futures, sens, pe):
    for i in range(len(bougies_futures)):
        h, l = bougies_futures["high"].iloc[i], bougies_futures["low"].iloc[i]
        if sens == "ACHAT":
            if l <= pe - SL:
                return False
            if h >= pe + TP1:
                return True
        elif sens == "VENTE":
            if h >= pe + SL:
                return False
            if l <= pe - TP1:
                return True
    return False

def detecter_signal(df):
    global derniers_signaux
    historique = df.iloc[-BOUGIES_PASSES:]
    sens = valider_strategie(historique)
    if not sens:
        return None

    pe = round(historique["close"].iloc[-1], 2)
    futures = df.iloc[-BOUGIES_FUTURES:]

    # Évite les doublons
    if any(abs(pe - float(sig.split("_")[1])) < 5 for sig in derniers_signaux):
        return None

    if not simuler_trade(futures, sens, pe):
        return None

    if abs(pe - df["close"].iloc[-1]) > TOLERANCE_PIPS:
        return None

    tp1 = pe + TP1 if sens == "ACHAT" else pe - TP1
    tp2 = pe + TP2 if sens == "ACHAT" else pe - TP2
    sl = pe - SL if sens == "ACHAT" else pe + SL
    id_sig = f"{sens}_{pe}"
    derniers_signaux.append(id_sig)

    return {
        "type": sens,
        "PE": pe,
        "TP1": round(tp1, 2),
        "TP2": round(tp2, 2),
        "SL": round(sl, 2),
        "UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

def envoyer_trade_test(df):
    pe = round(df["close"].iloc[-1], 2)
    msg = f"""TRADE TEST
ACHAT
PE : {pe}
TP1 : {pe + TP1}
TP2 : {pe + TP2}
SL : {pe - SL}"""
    envoyer_message(msg)

def main():
    print("Robot trader parfait lancé.")
    df = get_bougies(1000)
    if df is not None:
        envoyer_trade_test(df)
    time.sleep(5)

    while True:
        df = get_bougies(1000)
        if df is not None:
            signal = detecter_signal(df)
            if signal:
                msg = f"""{signal['type']}
PE : {signal['PE']}
TP1 : {signal['TP1']}
TP2 : {signal['TP2']}
SL : {signal['SL']}
UTC : {signal['UTC']}"""
                envoyer_message(msg)
        time.sleep(60)

if __name__ == "__main__":
    main()
