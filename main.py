import requests
import time
from telegram import Bot
from datetime import datetime

# === CONFIGURATION ===
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = 2128959111
CMC_API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
SYMBOL = "BTC"

# === INITIALISATION TELEGRAM ===
bot = Bot(token=TELEGRAM_TOKEN)
test_sent = False

# === RÉCUPÉRATION DU PRIX BTCUSD ===
def get_btc_price():
    headers = { "X-CMC_PRO_API_KEY": CMC_API_KEY }
    params = { "symbol": SYMBOL, "convert": "USD" }
    try:
        response = requests.get(CMC_URL, headers=headers, params=params)
        data = response.json()
        return round(float(data["data"]["BTC"]["quote"]["USD"]["price"]), 2)
    except Exception as e:
        print("Erreur récupération BTC:", e)
        return None

# === ENVOI DU TRADE TEST ===
def send_trade_test(price):
    tp1 = round(price + 300, 2)
    tp2 = round(price + 1000, 2)
    sl = round(price - 150, 2)
    now = datetime.now().strftime("%H:%M:%S")
    message = (
        f"**TRADE TEST BTCUSD**\n"
        f"ACHAT\n"
        f"PE : {price}\n"
        f"TP1 : {tp1}\n"
        f"TP2 : {tp2}\n"
        f"SL : {sl}\n"
        f"Horodatage : {now}"
    )
    bot.send_message(chat_id=CHAT_ID, text=message)

# === SIMULATION D'UNE STRATÉGIE GAGNANTE ===
def detect_strategie_gagnante():
    # Simulation : renvoie un trade fictif si les conditions étaient remplies
    # À remplacer par ta vraie logique avec FVG, OB, BOS, CHoCH, EMA, etc.
    # Renvoie None si pas de trade, ou un dict avec les infos du trade si trouvé
    return None

# === ENVOI D'UN SIGNAL VRAIMENT GAGNANT ===
def envoyer_signal(signal):
    message = (
        f"{signal['type']}\n"
        f"PE : {signal['pe']}\n"
        f"TP1 : {signal['tp1']}\n"
        f"TP2 : {signal['tp2']}\n"
        f"SL : {signal['sl']}"
    )
    bot.send_message(chat_id=CHAT_ID, text=message)

# === MAIN LOOP ===
def main():
    global test_sent
    if not test_sent:
        prix = get_btc_price()
        if prix:
            send_trade_test(prix)
            test_sent = True
    while True:
        signal = detect_strategie_gagnante()
        if signal:
            envoyer_signal(signal)
        time.sleep(60)  # vérifie toutes les 60 secondes

if __name__ == "__main__":
    main()
