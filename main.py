import time
import requests
from datetime import datetime
import random

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"  # Pour usage futur

# === ENVOI DU MESSAGE ===
def envoyer_signal_test():
    prix = random.uniform(91300, 91450)
    prix = round(prix, 2)
    tp1 = round(prix + 300, 2)
    tp2 = round(prix + 1000, 2)
    sl = round(prix - 150, 2)
    timestamp = datetime.now().strftime("%H:%M:%S")

    message = (
        "**TRADE TEST BTCUSD**\n"
        f"Entrée : {prix}\n"
        f"TP1 : {tp1}\n"
        f"TP2 : {tp2}\n"
        f"SL : {sl}\n"
        f"Confiance : 100%\n"
        f"Horodatage : {timestamp}"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    print("Signal test envoyé → Statut :", response.status_code)

# === EXÉCUTER UNE FOIS ET QUITTER ===
envoyer_signal_test()
import sys
sys.exit()
