import requests
import random
from datetime import datetime

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "5670995083"

# === ENVOI D'UN TRADE TEST UNIQUE ===
def envoyer_signal_test():
    heure = datetime.utcnow().strftime("%H:%M")
    prix = random.randint(60000, 67000)
    tp = prix + 300
    sl = prix - 150
    message = (
        "SIGNAL TEST BTCUSD\n"
        f"Achat à {prix}\n"
        f"TP1 : {tp}\n"
        f"SL : {sl}\n"
        "⚠️ Ce message est un test automatique.\n"
    )
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=payload)
    print(f"Signal test envoyé ➜ Statut : {response.status_code}")

# === LANCEMENT AUTOMATIQUE À DÉMARRAGE ===
if __name__ == "__main__":
    envoyer_signal_test()
