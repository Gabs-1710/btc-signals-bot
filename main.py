from datetime import datetime
import requests
import random
import time

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"

# === ENVOI D'UN TRADE TEST AVEC PRIX ACTUEL ===
def envoyer_trade_test():
    try:
        prix_actuel = get_prix_btc()
        tp1 = prix_actuel + 300
        tp2 = prix_actuel + 1000
        sl = prix_actuel - 150
        message = (
            "NOUVEAU SIGNAL TEST BTCUSD\n"
            f"Achat à {prix_actuel}\n"
            f"TP1 : {tp1}\n"
            f"TP2 : {tp2}\n"
            f"SL : {sl}\n"
            "Confiance : 100%\n"
        )
        send_telegram(message)
        print("Message test envoyé")
    except Exception as e:
        print(f"Erreur lors de l'envoi du test : {e}")

# === MOTEUR DE TRADING (message à heure précise) ===
def moteur_trading():
    heure_actuelle = datetime.utcnow().strftime("%H:%M")
    if heure_actuelle == "20:00":  # UTC ! (22:00 heure française)
        envoyer_trade_test()

# === OBTENIR LE PRIX BTCUSD (depuis Binance) ===
def get_prix_btc():
    url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
    response = requests.get(url)
    data = response.json()
    return int(float(data["price"]))

# === ENVOYER MESSAGE TELEGRAM ===
def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    response = requests.post(url, data=payload)
    print(f"Réponse Telegram : {response.status_code}")

# === DEMARRAGE ===
if __name__ == "__main__":
    envoyer_trade_test()
    while True:
        moteur_trading()
        time.sleep(300)
