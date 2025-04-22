import requests
from datetime import datetime
import random

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"

# === FONCTION POUR RÉCUPÉRER LE PRIX BTC ===
def get_btc_price():
    try:
        url = "https://api.taapi.io/price?secret=" + API_KEY + "&exchange=binance&symbol=BTC/USDT&interval=5m"
        response = requests.get(url)
        result = response.json()
        return float(result["value"])
    except Exception as e:
        print("Erreur récupération prix :", e)
        return random.uniform(30000, 35000)

# === ENVOYER LE MESSAGE TEST ===
def envoyer_signal_test():
    prix = get_btc_price()
    tp1 = prix + 300
    tp2 = prix + 1000
    sl = prix - 150
    horodatage = datetime.now().strftime("%H:%M:%S")

    message = (
        "**TRADE TEST BTCUSD**\n"
        f"Entrée : {round(prix, 2)}\n"
        f"TP1 : {round(tp1, 2)}\n"
        f"TP2 : {round(tp2, 2)}\n"
        f"SL : {round(sl, 2)}\n"
        "Confiance : 100%\n"
        f"Horodatage : {horodatage}"
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

# === LANCER UNE SEULE FOIS ===
if __name__ == "__main__":
    envoyer_signal_test()
