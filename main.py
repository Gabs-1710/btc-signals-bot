import time
import requests
from datetime import datetime

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"

def get_btc_price():
    try:
        url = f"https://api.taapi.io/price?secret={API_KEY}&exchange=binance&symbol=BTC/USDT&interval=1m"
        response = requests.get(url)
        data = response.json()
        return round(float(data["value"]), 2)
    except Exception as e:
        print("Erreur récupération prix :", e)
        return None

def envoyer_message(msg):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Erreur envoi Telegram :", e)

def envoyer_trade_test():
    prix = get_btc_price()
    if prix is None:
        print("Impossible de récupérer le prix BTC.")
        return
    tp1 = prix + 300
    tp2 = prix + 1000
    sl = prix - 150
    horodatage = datetime.now().strftime("%H:%M:%S")
    message = (
        "**TRADE TEST BTCUSD**\n"
        f"Entrée : {prix}\n"
        f"TP1 : {tp1}\n"
        f"TP2 : {tp2}\n"
        f"SL : {sl}\n"
        f"Confiance : 100%\n"
        f"Horodatage : {horodatage}"
    )
    envoyer_message(message)
    print("Trade test envoyé.")

# === AU DÉMARRAGE ===
envoyer_trade_test()
envoyer_message("Analyse des signaux gagnants en cours...")

# === BOUCLE EN CONTINU ===
while True:
    # Ici : future analyse des vrais signaux
    time.sleep(60)
