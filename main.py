import time
import random
from datetime import datetime
import requests

# === CONFIGURATION ===
BOT_TOKEN = "TON_TOKEN_ICI"
CHAT_ID = "TON_CHAT_ID_ICI"

# === SIMULATION D'UN TRADE TEST ===
def envoyer_signal_test():
    heure = datetime.utcnow().strftime("%H:%M")
    prix = random.randint(60000, 67000)
    tp = prix + 300
    sl = prix - 150
    message = (
        "NOUVEAU SIGNAL TEST BTCUSD\n"
        f"Achat à {prix}\n"
        f"TP1 : {tp}\n"
        f"SL : {sl}\n"
        "Confiance : 100%\n"
        "#BTC #SIGNAL"
    )

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    response = requests.post(url, data=data)
    print(f"Signal envoyé ({heure}) → Statut : {response.status_code}")

# === LANCEMENT AUTOMATIQUE TEST ===
if __name__ == "__main__":
    envoyer_signal_test()
