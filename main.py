import requests
import pandas as pd
import time
import telebot
from datetime import datetime, timedelta

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
HISTO = 500
ANNONCES = []  # Les annonces sont ajoutées automatiquement (format: "HH:MM")

bot = telebot.TeleBot(BOT_TOKEN)
trades_suivis = []
test_envoye = False

# === FONCTIONS ===

def envoyer_message(msg):
    try:
        bot.send_message(CHAT_ID, msg)
    except Exception as e:
        print("Erreur Telegram :", e)

def get_bougies():
    try:
        url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize={LIMIT}&apikey={API_KEY}"
        r = requests.get(url)
        data = r.json()
        if "values" not in data:
            return None
        df = pd.DataFrame(data["values"])
        df["time"] = pd.to_datetime(df["datetime"])
        df = df.sort_values("time").reset_index(drop=True)
        df[["open", "high", "low", "close"]] = df[["open", "high", "low", "close"]].astype(float)
        return df
    except Exception as e:
        print("Erreur récupération bougies :", e)
        return None

def ema(df, period):
    return df["close"].ewm(span=period, adjust=False).mean()

def detect_order_block(df, sens):
    zone = df.iloc[-15:]
    if sens == "ACHAT":
        return zone["low"].min()
    else:
        return zone["high"].max()

def in_fibonacci_zone(pe, retracement):
    fib_618 = retracement * 0.618
    fib_786 = retracement * 0.786
    return fib_786 <= pe <= fib_618 or fib_618 <= pe <= fib_786

def simuler_trade(df, sens, pe):
    sl = pe - SL_PIPS if sens == "ACHAT" else pe + SL_PIPS
    tp1 = pe + TP1_PIPS if sens == "ACHAT" else pe - TP1_PIPS
    for i in range(min(HISTO, len(df))):
        row = df.iloc[i]
        if sens == "ACHAT":
            if row["low"] <= sl:
                return False
            if row["high"] >= tp1:
                return True
        else:
            if row["high"] >= sl:
                return False
            if row["low"] <= tp1:
                return True
    return False

def detecter_signal(df):
    ema_fast = ema(df, 50)
    ema_slow = ema(df, 200)
    for i in range(20, len(df) - HISTO):
        zone = df.iloc[i-20:i]
        bougie = df.iloc[i]
        prix = bougie["close"]
        sens = "ACHAT" if bougie["close"] > bougie["open"] else "VENTE"
        if sens == "ACHAT" and not (ema_fast[i] > ema_slow[i]):
            continue
        if sens == "VENTE" and not (ema_fast[i] < ema_slow[i]):
            continue
        retracement = zone["high"].max() - zone["low"].min()
        if not in_fibonacci_zone(prix, retracement):
            continue
        ob = detect_order_block(zone, sens)
        if sens == "ACHAT" and prix < ob:
            continue
        if sens == "VENTE" and prix > ob:
            continue
        if simuler_trade(df.iloc[i:], sens, prix):
            return sens, prix
    return None

def generer_message(sens, pe):
    tp1 = pe + TP1_PIPS if sens == "ACHAT" else pe - TP1_PIPS
    tp2 = pe + TP2_PIPS if sens == "ACHAT" else pe - TP2_PIPS
    sl = pe - SL_PIPS if sens == "ACHAT" else pe + SL_PIPS
    return f"{sens}\nPE : {round(pe, 2)}\nTP1 : {round(tp1, 2)}\nTP2 : {round(tp2, 2)}\nSL : {round(sl, 2)}"

def verifier_suivi(df):
    global trades_suivis
    nouveaux_suivis = []
    for trade in trades_suivis:
        sens, pe = trade["sens"], trade["pe"]
        sl = pe - SL_PIPS if sens == "ACHAT" else pe + SL_PIPS
        tp1 = pe + TP1_PIPS if sens == "ACHAT" else pe - TP1_PIPS
        for i in range(len(df)):
            low, high = df.iloc[i]["low"], df.iloc[i]["high"]
            if sens == "ACHAT":
                if low <= sl:
                    envoyer_message(f"SL touché – Trade à {pe} perdu ❌")
                    break
                if high >= tp1:
                    envoyer_message(f"TP1 atteint – Trade à {pe} réussi ✅")
                    break
            else:
                if high >= sl:
                    envoyer_message(f"SL touché – Trade à {pe} perdu ❌")
                    break
                if low <= tp1:
                    envoyer_message(f"TP1 atteint – Trade à {pe} réussi ✅")
                    break
        else:
            nouveaux_suivis.append(trade)
    trades_suivis = nouveaux_suivis

def est_dans_une_announcement():
    heure_actuelle = datetime.utcnow().strftime("%H:%M")
    for h in ANNONCES:
        h_utc = datetime.strptime(h, "%H:%M")
        debut = (h_utc - timedelta(minutes=30)).strftime("%H:%M")
        fin = (h_utc + timedelta(minutes=30)).strftime("%H:%M")
        if debut <= heure_actuelle <= fin:
            return True
    return False

def envoyer_trade_test(df):
    if df is None or len(df) < 10:
        return
    prix = df.iloc[-1]["close"]
    msg = f"TRADE TEST\nACHAT\nPE : {prix:.2f}\nTP1 : {prix + TP1_PIPS:.2f}\nTP2 : {prix + TP2_PIPS:.2f}\nSL : {prix - SL_PIPS:.2f}"
    envoyer_message(msg)

# === BOUCLE PRINCIPALE ===
while True:
    try:
        df = get_bougies()
        if df is not None and len(df) >= 100:
            if not test_envoye:
                envoyer_trade_test(df)
                test_envoye = True

            verifier_suivi(df)

            if not est_dans_une_announcement():
                signal = detecter_signal(df)
                if signal:
                    sens, pe = signal
                    prix_reel = df.iloc[-1]["close"]
                    if abs(prix_reel - pe) <= TOLERANCE:
                        msg = generer_message(sens, pe)
                        envoyer_message(msg)
                        trades_suivis.append({"sens": sens, "pe": pe})
        time.sleep(60)

    except Exception as e:
        print("Erreur principale :", e)
        time.sleep(60)
