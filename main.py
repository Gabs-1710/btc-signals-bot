import time
import random
from datetime import datetime
import requests

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"

# === SIMULATION D'UN TRADE TEST ===
def envoyer_signal_test():
    heure = datetime.utcnow().strftime("%H:%M")
    if heure == "19:15":  # UTC = 21h15 CEST
        prix = random.randint(60000, 67000)
        tp = prix + 300
        sl = prix - 150
        message = (
            "**NOUVEAU SIGNAL TEST BTCUSD**\n"
            f"Achat à {prix}\n"
            f"TP1 : {tp}\n"
            f"SL : {sl}\n"
            "Confiance : 100%\n"
        )
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            data={"chat_id": CHAT_ID, "text": message}
        )
        print("Signal test envoyé -> Statut :", response.status_code)

# === LANCEMENT AUTOMATIQUE ===
while True:
    envoyer_signal_test()
    time.sleep(60)  # vérifie chaque minute
