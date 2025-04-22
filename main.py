import requests
from datetime import datetime
import os

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
TEST_FLAG_FILE = "trade_test_done.txt"

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

    # Créer un fichier pour marquer que le test a été fait
    with open(TEST_FLAG_FILE, "w") as f:
        f.write("ok")

# === ANALYSE ET ENVOI DES VRAIS SIGNAUX ===
def analyser_et_envoyer_les_signaux_gagnants():
    # Ici viendra ton moteur d'analyse final avec toutes les conditions smart
    print("Analyse des signaux en cours...")
    # Exemple : tu pourras appeler send_telegram_message("VRAI SIGNAL") si toutes les conditions sont remplies
    pass

# === LANCEMENT ===
if __name__ == "__main__":
    if not os.path.exists(TEST_FLAG_FILE):
        envoyer_trade_test()
    else:
        analyser_et_envoyer_les_signaux_gagnants()
