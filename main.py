import requests
from datetime import datetime
import time

BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"

def get_btc_price():
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        response = requests.get(url)
        response.raise_for_status()
        data = response.json()
        return float(data['price'])
    except Exception as e:
        print("Erreur récupération prix :", e)
        return None

def envoyer_signal_test(prix):
    tp1 = prix + 300
    tp2 = prix + 1000
    sl = prix - 150
    heure = datetime.now().strftime("%H:%M:%S")
    message = (
        "**TRADE TEST BTCUSD**\n"
        f"Entrée : {prix:.2f}\n"
        f"TP1 : {tp1:.2f}\n"
        f"TP2 : {tp2:.2f}\n"
        f"SL : {sl:.2f}\n"
        "Confiance : 100%\n"
        f"Horodatage : {heure}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, data=payload)
        print("Message envoyé.")
    except Exception as e:
        print("Erreur envoi message :", e)

# Lancer une seule fois au démarrage
prix_btc = get_btc_price()
if prix_btc:
    envoyer_signal_test(prix_btc)
else:
    print("Impossible de récupérer le prix BTC.")
