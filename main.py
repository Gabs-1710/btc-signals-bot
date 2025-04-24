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

# === INITIALISATION ===
bot = Bot(token=TELEGRAM_TOKEN)
trade_test_sent = False
last_status_time = time.time()

# === FONCTIONS ===
def get_btc_price():
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    params = {"symbol": SYMBOL, "convert": CURRENCY}
    try:
        response = requests.get(CMC_URL, headers=headers, params=params)
        response.raise_for_status()
        return float(response.json()["data"][SYMBOL]["quote"][CURRENCY]["price"])
    except Exception as e:
        print("[ERREUR] Récupération prix BTC:", e)
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

def send_trade_signal(price, direction):
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

def send_status():
    bot.send_message(chat_id=CHAT_ID, text="Aucune opportunité parfaite détectée pour le moment. Analyse toujours en cours...")

def detect_ultra_gagnant(price):
    # === LOGIQUE DE DÉTECTION FINALE ===
    # Version simple : à remplacer par un moteur structuré à base de backtests réels
    # Ici, on simule des conditions très filtrées : ex. structure + pattern gagnant
    if int(price) % 137 == 0 and int(price) % 5 == 1:
        return "ACHAT" if int(price) % 2 == 0 else "VENTE"
    return None

# === BOUCLE PRINCIPALE ===
while True:
    now = time.time()
    price = get_btc_price()

    if price:
        if not trade_test_sent:
            send_trade_test(price)
            trade_test_sent = True
        else:
            signal = detect_ultra_gagnant(price)
            if signal:
                send_trade_signal(price, signal)

    if now - last_status_time > 7200:
        send_status()
        last_status_time = now

    time.sleep(60)
