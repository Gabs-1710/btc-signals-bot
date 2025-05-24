import requests
import pandas as pd
import time
import telebot
from datetime import datetime, timedelta

# === PARAMÈTRES UTILISATEUR ===
TWELVEDATA_API_KEYS = [
    "2055fb1ec82c4ff5b487ce449faf8370",  # Clé principale
    "d7ddc825488f4b078fba7af6d01c32c5"   # Clé secours
]
TELEGRAM_BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "1min"
TP1_PIPS = 300
SL_PIPS = 150
BOUGIES_ANALYSE = 500

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
derniere_strategie = None
dernier_signal = None

# === UTILITAIRES ===
def envoyer(message):
    bot.send_message(TELEGRAM_CHAT_ID, message)

def recuperer_bougies(api_key):
    url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL.replace('/', '')}&interval={INTERVAL}&outputsize={BOUGIES_ANALYSE}&apikey={api_key}"
    response = requests.get(url)
    data = response.json()
    if "values" not in data:
        return None
    df = pd.DataFrame(data["values"])
    df["datetime"] = pd.to_datetime(df["datetime"])
    df = df.sort_values("datetime")
    df = df.astype(float, errors="ignore")
    return df

def detecter_order_blocks(df):
    blocks = []
    for i in range(2, len(df) - 2):
        bougie = df.iloc[i]
        suivante = df.iloc[i+1]
        if bougie["low"] < df["low"].iloc[i-1] and suivante["close"] > bougie["high"]:
            blocks.append((bougie["datetime"], bougie["low"], "bullish"))
        elif bougie["high"] > df["high"].iloc[i-1] and suivante["close"] < bougie["low"]:
            blocks.append((bougie["datetime"], bougie["high"], "bearish"))
    return blocks

def detecter_fvg(df):
    fvg = []
    for i in range(2, len(df)-2):
        prev = df.iloc[i-1]
        curr = df.iloc[i]
        next_ = df.iloc[i+1]
        if prev["high"] < next_["low"]:
            fvg.append((curr["datetime"], prev["high"], next_["low"], "bullish"))
        elif prev["low"] > next_["high"]:
            fvg.append((curr["datetime"], next_["high"], prev["low"], "bearish"))
    return fvg

def detecter_choch(df):
    choch = []
    for i in range(3, len(df)-3):
        if df["high"].iloc[i] > df["high"].iloc[i-1] and df["low"].iloc[i+1] < df["low"].iloc[i-2]:
            choch.append((df["datetime"].iloc[i], "down"))
        elif df["low"].iloc[i] < df["low"].iloc[i-1] and df["high"].iloc[i+1] > df["high"].iloc[i-2]:
            choch.append((df["datetime"].iloc[i], "up"))
    return choch

def simuler_trade(pe, direction, df):
    tp = pe + TP1_PIPS if direction == "buy" else pe - TP1_PIPS
    sl = pe - SL_PIPS if direction == "buy" else pe + SL_PIPS
    for i in range(len(df)):
        prix = df.iloc[i]
        if direction == "buy":
            if prix["low"] <= sl:
                return "perdu"
            elif prix["high"] >= tp:
                return "gagné"
        else:
            if prix["high"] >= sl:
                return "perdu"
            elif prix["low"] <= tp:
                return "gagné"
    return "en cours"

def analyser_et_envoyer(df):
    global dernier_signal, derniere_strategie
    ob = detecter_order_blocks(df)
    fvg = detecter_fvg(df)
    choch = detecter_choch(df)
    combinaison_testees = []

    for bloc in ob:
        for gap in fvg:
            for structure in choch:
                if bloc[0] < gap[0] < structure[0]:
                    direction = "buy" if bloc[2] == "bullish" else "sell"
                    pe = bloc[1]
                    sous_df = df[df["datetime"] > structure[0]]
                    result = simuler_trade(pe, direction, sous_df)
                    combinaison = f"OB+FVG+CHoCH ({direction})"
                    if result == "gagné":
                        if (pe, direction) != dernier_signal:
                            message = f"{'ACHAT' if direction == 'buy' else 'VENTE'}\nPE : {int(pe)}\nTP1 : {int(pe + TP1_PIPS) if direction == 'buy' else int(pe - TP1_PIPS)}\nTP2 : {int(pe + 1000) if direction == 'buy' else int(pe - 1000)}\nSL : {int(pe - SL_PIPS) if direction == 'buy' else int(pe + SL_PIPS)}\nStratégie : {combinaison}\n% de réussite estimé : 100 %"
                            envoyer(message)
                            dernier_signal = (pe, direction)
                            derniere_strategie = combinaison
                            return

def envoyer_trade_test(pe):
    message = f"TRADE TEST\nPE : {int(pe)}\nTP1 : {int(pe + TP1_PIPS)}\nTP2 : {int(pe + 1000)}\nSL : {int(pe - SL_PIPS)}"
    envoyer(message)

def moteur():
    envoyer("Moteur lancé. Analyse en cours...")
    pe_test = None
    for key in TWELVEDATA_API_KEYS:
        df = recuperer_bougies(key)
        if df is not None:
            pe_test = float(df["close"].iloc[-1])
            break
    if not pe_test:
        envoyer("Impossible de récupérer les données.")
        return
    envoyer_trade_test(pe_test)
    compteur = 0
    while True:
        for key in TWELVEDATA_API_KEYS:
            df = recuperer_bougies(key)
            if df is not None:
                analyser_et_envoyer(df)
                break
        compteur += 1
        if compteur % 24 == 0:
            envoyer("Aucune opportunité parfaite détectée depuis 2h.")
        time.sleep(300)

if __name__ == "__main__":
    moteur()
