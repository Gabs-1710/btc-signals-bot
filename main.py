import requests
from datetime import datetime
import time

BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"

def get_btc_price():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    headers = {"X-MBX-APIKEY": API_KEY}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        return float(data["price"])
    except Exception as e:
        print("Erreur récupération prix :", e)
        return None

def envoyer_signal_test():
    prix = get_btc_price()
    if prix is None:
        print("Impossible de récupérer le prix BTC.")
        return
    tp1 = prix + 300
    tp2 = prix + 1000
    sl = prix - 150
    now = datetime.now().strftime("%H:%M:%S")
    message = (
        "**TRADE TEST BTCUSD**\n"
        f"Entrée : {prix:.2f}\n"
        f"TP1 : {tp1:.2f}\n"
        f"TP2 : {tp2:.2f}\n"
        f"SL : {sl:.2f}\n"
        "Confiance : 100%\n"
        f"Horodatage : {now}"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        r = requests.post(url, json=payload)
        if r.status_code == 200:
            print("Message envoyé.")
        else:
            print(f"Erreur Telegram : {r.status_code} - {r.text}")
    except Exception as e:
        print("Erreur envoi message :", e)

envoyer_signal_test()
