import requests
from datetime import datetime
import os

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
ENVOYER_TRADE_TEST = True  # Passe à False si tu veux sauter le test

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

# === ENVOI DU TRADE TEST ===
def envoyer_trade_test():
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
    print("Trade test envoyé.")

# === ANALYSE ET ENVOI DES VRAIS SIGNAUX ===
def analyser_et_envoyer_les_signaux_gagnants():
    print("Analyse des signaux gagnants en cours...")
    # Ici sera ajouté le moteur final
    pass

# === LANCEMENT ===
if __name__ == "__main__":
    if ENVOYER_TRADE_TEST:
        envoyer_trade_test()
    analyser_et_envoyer_les_signaux_gagnants()
