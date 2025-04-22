import requests
import time
from datetime import datetime
from telegram import Bot

# === CONFIGURATION ===
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = 2128959111
CMC_API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
SYMBOL = "BTC"
CURRENCY = "USD"

# === INITIALISATION DU BOT ===
bot = Bot(token=TELEGRAM_TOKEN)

last_check = time.time()
trade_test_sent = False

def get_btc_price():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": SYMBOL, "convert": CURRENCY}
    try:
        response = requests.get(CMC_URL, headers=headers, params=params)
        response.raise_for_status()
        return float(response.json()["data"][SYMBOL]["quote"][CURRENCY]["price"])
    except Exception as e:
        print("Erreur prix BTC :", e)
        return None

def send_trade_test(price):
    message = (
        f"**TRADE TEST BTCUSD**\n"
        f"ACHAT\n"
        f"PE : {price:.2f}\n"
        f"TP1 : {price + 300:.2f}\n"
        f"TP2 : {price + 1000:.2f}\n"
        f"SL : {price - 150:.2f}\n"
        f"Horodatage : {datetime.now().strftime('%H:%M:%S')}"
    )
    bot.send_message(chat_id=CHAT_ID, text=message)

def send_status_message():
    bot.send_message(chat_id=CHAT_ID, text="Aucun signal ultra gagnant détecté pour le moment. Analyse toujours en cours...")

def send_trade_signal(price, direction="ACHAT"):
    tp1 = price + 300 if direction == "ACHAT" else price - 300
    tp2 = price + 1000 if direction == "ACHAT" else price - 1000
    sl = price - 150 if direction == "ACHAT" else price + 150
    message = (
        f"**{direction} BTCUSD**\n"
        f"PE : {price:.2f}\n"
        f"TP1 : {tp1:.2f}\n"
        f"TP2 : {tp2:.2f}\n"
        f"SL : {sl:.2f}"
    )
    bot.send_message(chat_id=CHAT_ID, text=message)

# === BOUCLE PRINCIPALE ===
while True:
    now = time.time()
    price = get_btc_price()

    if price:
        if not trade_test_sent:
            send_trade_test(price)
            trade_test_sent = True
        else:
            # === ICI : LOGIQUE POUR DETECTER UN TRADE GAGNANT ===
            if int(price) % 137 == 0:  # Exemples simples de critère factice
                send_trade_signal(price, direction="ACHAT")

    # Toutes les 2 heures = 7200 secondes
    if now - last_check > 7200:
        send_status_message()
        last_check = now

    time.sleep(60)
