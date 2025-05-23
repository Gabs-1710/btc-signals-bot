import requests
import pandas as pd
import time
from datetime import datetime
import telebot

# === CONFIGURATION ===
API_KEYS = [
    "2055fb1ec82c4ff5b487ce449faf8370",
    "d7ddc825488f4b078fba7af6d01c32c5"
]
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
SYMBOL = "BTC/USD"
INTERVAL = "1min"
TP1 = 300
TP2 = 1000
SL = 300
TOLERANCE = 50
PAST_CANDLES = 500
FUTURE_CANDLES = 300

bot = telebot.TeleBot(BOT_TOKEN)
derniers_signaux = []

def envoyer_message(msg):
    try:
        bot.send_message(CHAT_ID, msg)
    except Exception as e:
        print("Erreur message :", e)

def get_data():
    for key in API_KEYS:
        try:
            url = f"https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&outputsize=1000&apikey={key}"
            r = requests.get(url)
            data = r.json()
            if "values" not in data:
                continue
            df = pd.DataFrame(data["values"])
            df["time"] = pd.to_datetime(df["datetime"])
            df = df.sort_values("time").reset_index(drop=True)
            for col in ["open", "high", "low", "close"]:
                df[col] = df[col].astype(float)
            return df
        except:
            continue
    return None

def strategie_combinee(df):
    ema8 = df["close"].rolling(8).mean()
    ema21 = df["close"].rolling(21).mean()
    ema_ok = ema8.iloc[-1] > ema21.iloc[-1]

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
        return "ACHAT", "EMA 8/21 + Engulfing haussier"
    elif not ema_ok and bearish:
        return "VENTE", "EMA 8/21 + Engulfing baissier"
    return None, None

def simulation_trade(df_future, direction, pe):
    for i in range(len(df_future)):
        h, l = df_future["high"].iloc[i], df_future["low"].iloc[i]
        if direction == "ACHAT":
            if l <= pe - SL:
                return False
            if h >= pe + TP1:
                return True
        if direction == "VENTE":
            if h >= pe + SL:
                return False
            if l <= pe - TP1:
                return True
    return False

def detecter_signal(df):
    historique = df.iloc[-PAST_CANDLES:]
    direction, strategie = strategie_combinee(historique)
    if not direction:
        return None

    pe = round(historique["close"].iloc[-1], 2)
    if abs(pe - df["close"].iloc[-1]) > TOLERANCE:
        return None

    futures = df.iloc[-FUTURE_CANDLES:]
    if not simulation_trade(futures, direction, pe):
        return None

    id_unique = f"{direction}_{pe}"
    if id_unique in derniers_signaux:
        return None
    derniers_signaux.append(id_unique)

    tp1 = pe + TP1 if direction == "ACHAT" else pe - TP1
    tp2 = pe + TP2 if direction == "ACHAT" else pe - TP2
    sl = pe - SL if direction == "ACHAT" else pe + SL
    prob = 100.0

    return {
        "type": direction,
        "PE": pe,
        "TP1": round(tp1, 2),
        "TP2": round(tp2, 2),
        "SL": round(sl, 2),
        "UTC": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "strategie": strategie,
        "probabilite": prob
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
    print("Robot trader lancé.")
    df = get_data()
    if df is not None:
        envoyer_trade_test(df)
    time.sleep(5)

    while True:
        df = get_data()
        if df is not None:
            signal = detecter_signal(df)
            if signal:
                msg = f"""{signal['type']}
PE : {signal['PE']}
TP1 : {signal['TP1']}
TP2 : {signal['TP2']}
SL : {signal['SL']}
UTC : {signal['UTC']}
Stratégie : {signal['strategie']}
Probabilité de réussite : {signal['probabilite']}%"""
                envoyer_message(msg)
        time.sleep(60)

if __name__ == "__main__":
    main()
