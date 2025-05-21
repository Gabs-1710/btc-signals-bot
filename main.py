import requests
import pandas as pd
import time
from datetime import datetime
import telebot

# === PARAMÈTRES UTILISATEUR ===
API_KEY = "2055fb1ec82c4ff5b487ce449faf8370"
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "1min"
TP1_PIPS = 300
TP2_PIPS = 1000
SL_PIPS = 150

bot = telebot.TeleBot(BOT_TOKEN)
dernier_signal = None
trade_envoyes = []

# === FONCTIONS DE BASE ===
def envoyer_message(msg):
    try:
        bot.send_message(CHAT_ID, msg)
    except Exception as e:
        print("Erreur Telegram :", e)

def get_bougies(limit=500):
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize={limit}&apikey={API_KEY}"
        r = requests.get(url)
        data = r.json()
        if "values" not in data:
            print("Erreur API :", data)
            return None
        df = pd.DataFrame(data["values"])
        df = df.rename(columns={"datetime": "time"}).iloc[::-1]
        df["open"] = df["open"].astype(float)
        df["high"] = df["high"].astype(float)
        df["low"] = df["low"].astype(float)
        df["close"] = df["close"].astype(float)
        df["time"] = pd.to_datetime(df["time"])
        return df.reset_index(drop=True)
    except Exception as e:
        print("Erreur récupération bougies :", e)
        return None

def envoyer_trade_test(df):
    prix = df["close"].iloc[-1]
    msg = f"""TRADE TEST
ACHAT
PE : {round(prix, 2)}
TP1 : {round(prix + TP1_PIPS, 2)}
TP2 : {round(prix + TP2_PIPS, 2)}
SL : {round(prix - SL_PIPS, 2)}"""
    envoyer_message(msg)

# === STRATÉGIES PUISSANTES ===
def strategies_valides(df):
    recent = df.tail(5)
    haussier = all(recent["close"] > recent["open"])
    baissier = all(recent["close"] < recent["open"])
    ema_fast = df["close"].rolling(5).mean()
    ema_slow = df["close"].rolling(20).mean()
    croisement_ema = ema_fast.iloc[-1] > ema_slow.iloc[-1]
    ob_detecte = df["open"].iloc[-2] < df["close"].iloc[-2] and df["open"].iloc[-1] > df["close"].iloc[-1]
    fvg_detecte = abs(df["high"].iloc[-2] - df["low"].iloc[-1]) > 0.5
    compression = df["high"].tail(10).max() - df["low"].tail(10).min() < 1000

    valid_achat = haussier and croisement_ema and not ob_detecte and compression
    valid_vente = baissier and not croisement_ema and ob_detecte and compression

    if valid_achat:
        return "ACHAT"
    elif valid_vente:
        return "VENTE"
    else:
        return None

# === SIMULATION TP1 / SL (sur 200 bougies max) ===
def simuler_tp_sl(df, sens, pe):
    for i in range(1, 200):
        if i >= len(df):
            break
        high = df["high"].iloc[-i]
        low = df["low"].iloc[-i]
        if sens == "ACHAT":
            if low <= pe - SL_PIPS:
                return False
            if high >= pe + TP1_PIPS:
                return True
        elif sens == "VENTE":
            if high >= pe + SL_PIPS:
                return False
            if low <= pe - TP1_PIPS:
                return True
    return False

# === DÉTECTION PRINCIPALE ===
def detecter_signal(df):
    global dernier_signal
    if len(df) < 200:
        return None

    pe = round(df["close"].iloc[-1], 2)
    sens = strategies_valides(df)

    if not sens:
        return None

    if not simuler_tp_sl(df[::-1], sens, pe):
        return None

    id_signal = f"{sens}_{pe}"
    if id_signal == dernier_signal or id_signal in trade_envoyes:
        return None

    tp1 = round(pe + TP1_PIPS if sens == "ACHAT" else pe - TP1_PIPS, 2)
    tp2 = round(pe + TP2_PIPS if sens == "ACHAT" else pe - TP2_PIPS, 2)
    sl = round(pe - SL_PIPS if sens == "ACHAT" else pe + SL_PIPS, 2)
    dernier_signal = id_signal
    trade_envoyes.append(id_signal)

    return {
        "type": sens,
        "PE": pe,
        "TP1": tp1,
        "TP2": tp2,
        "SL": sl,
        "UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    }

# === BOUCLE PRINCIPALE ===
def main():
    print("Lancement du robot trader parfait...")
    df = get_bougies()
    if df is not None:
        envoyer_trade_test(df)
        time.sleep(2)

    while True:
        df = get_bougies()
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
