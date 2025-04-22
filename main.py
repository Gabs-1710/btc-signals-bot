import time
import random
from datetime import datetime
import requests

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "5670995083"  # Ton vrai chat_id

# === SIMULATION D'UN TRADE TEST ===
def envoyer_signal_test():
    heure = datetime.utcnow().strftime("%H:%M")
    if heure == "18:28":  # Change cette heure pour tester
        prix = random.randint(60000, 67000)
        tp = prix + 300
        sl = prix - 150
        message = (
            "NOUVEAU SIGNAL TEST BTCUSD\n"
            f"Achat à {prix}\n"
            f"TP1 : {tp}\n"
            f"SL : {sl}\n"
            "Confiance : 100%\n"
        )
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message
        }
        response = requests.post(url, data=payload)
        print(f"Signal envoyé ({heure}) ➜ Statut : {response.status_code}")

# === LANCEMENT PERMANENT ===
while True:
    envoyer_signal_test()
    time.sleep(60)
