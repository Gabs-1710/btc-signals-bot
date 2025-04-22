import requests
from datetime import datetime
import time

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
CMC_API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"

def get_btc_price():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    params = {"symbol": "BTC", "convert": "USD"}
    headers = {"X-CMC_PRO_API_KEY": CMC_API_KEY}
    try:
        response = requests.get(url, params=params, headers=headers)
        data = response.json()
        return round(data["data"]["BTC"]["quote"]["USD"]["price"], 2)
    except Exception as e:
        print("Erreur API :", e)
        return None

def envoyer_signal_test():
    prix = get_btc_price()
    if prix is None:
        return

    tp1 = prix + 300
    tp2 = prix + 1000
    sl = prix - 150
    heure = datetime.now().strftime("%H:%M:%S")

    message = (
        "**TRADE TEST BTCUSD**\n"
        f"Entrée : {prix}\n"
        f"TP1 : {tp1}\n"
        f"TP2 : {tp2}\n"
        f"SL : {sl}\n"
        "Confiance : 100%\n"
        f"Horodatage : {heure}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    requests.post(url, data=data)

# === Lancer une seule fois ===
envoyer_signal_test()
