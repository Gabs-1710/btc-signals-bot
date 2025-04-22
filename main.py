import requests
from datetime import datetime

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"

# === FONCTION POUR OBTENIR LE PRIX BTC ===
def get_btc_price():
    try:
        response = requests.get("https://api.coinbase.com/v2/prices/BTC-USD/spot", timeout=5)
        data = response.json()
        return float(data["data"]["amount"])
    except Exception as e:
        print("Erreur récupération prix Coinbase:", e)
        return None

# === FONCTION POUR ENVOYER UN MESSAGE TELEGRAM ===
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        requests.post(url, json=payload)
    except Exception as e:
        print("Erreur envoi Telegram:", e)

# === ENVOI DU MESSAGE "TRADE TEST" UNE FOIS ===
def envoyer_signal_test():
    prix = get_btc_price()
    if prix is None:
        print("Impossible de récupérer le prix BTC.")
        return

    tp1 = round(prix + 300, 2)
    tp2 = round(prix + 1000, 2)
    sl = round(prix - 150, 2)
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
    send_telegram_message(message)
    print("Message envoyé.")

# === LANCEMENT UNE SEULE FOIS ===
if __name__ == "__main__":
    envoyer_signal_test()
    envoyer_signal_test()

import sys
sys.exit()
