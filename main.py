import requests
import pandas as pd
import time
from datetime import datetime
import telebot

# === CONFIG UTILISATEUR ===
API_KEY = "2055fb1ec82c4ff5b487ce449faf8370"  # TwelveData
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"  # Telegram
CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "1min"
TP1 = 300
TP2 = 1000
SL = 300
TOLERANCE_PIPS = 50

# === INIT BOT TELEGRAM ===
bot = telebot.TeleBot(BOT_TOKEN)
derniers_signaux = []

def envoyer_message(msg):
    try:
        bot.send_message(CHAT_ID, msg)
    except:
        pass

# === RÉCUPÉRATION BOUCLES ===
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

# === STRATÉGIES VALIDES ===
def valider_strategie(df):
    ema_fast = df["close"].rolling(8).mean()
    ema_slow = df["close"].rolling(21).mean()
    ema_cross = ema_fast.iloc[-1] > ema_slow.iloc[-1]
    compression = (df["high"].tail(20).max() - df["low"].tail(20).min()) < 1000
    engulfing = (
        df["close"].iloc[-2] < df["open"].iloc[-2] and
        df["close"].iloc[-1] > df["open"].iloc[-1] and
        df["close"].iloc[-1] > df["open"].iloc[-2]
    )
    valid_achat = ema_cross and engulfing and compression
    valid_vente = not ema_cross and not engulfing and compression
    return "ACHAT" if valid_achat else "VENTE" if valid_vente else None

# === SIMULATEUR TP1/SL ===
def simuler(df, sens, pe):
    for i in range(1, 200):
        if i >= len(df): break
        h, l = df["high"].iloc[-i], df["low"].iloc[-i]
        if sens == "ACHAT":
            if l <= pe - SL: return False
            if h >= pe + TP1: return True
        if sens == "VENTE":
            if h >= pe + SL: return False
            if l <= pe - TP1: return True
    return False

# === DÉTECTION DE TRADE GAGNANT ===
def detecter(df):
    global derniers_signaux
    sens = valider_strategie(df)
    if not sens: return None
    pe = round(df["close"].iloc[-1], 2)
    if any(abs(pe - float(sig.split("_")[1])) < 5 for sig in derniers_signaux):
        return None
    if not simuler(df[::-1], sens, pe): return None
    if abs(pe - df["close"].iloc[-1]) > TOLERANCE_PIPS: return None
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

# === TRADE TEST ===
def envoyer_trade_test(df):
    pe = round(df["close"].iloc[-1], 2)
    msg = f"""TRADE TEST
ACHAT
PE : {pe}
TP1 : {pe + TP1}
TP2 : {pe + TP2}
SL : {pe - SL}"""
    envoyer_message(msg)

# === BOUCLE PRINCIPALE ===
def main():
    print("Robot trader parfait lancé.")
    df = get_bougies()
    if df is not None:
        envoyer_trade_test(df)
    time.sleep(5)

    while True:
        df = get_bougies()
        if df is not None:
            signal = detecter(df)
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
