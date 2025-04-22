import requests
from datetime import datetime

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"

# === FONCTION D'ENVOI TELEGRAM ===
def envoyer_message(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Erreur envoi Telegram:", e)

# === FONCTION PRIX BTC ===
def recuperer_prix_btc():
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT", timeout=10)
        prix = float(response.json()["price"])
        return prix
    except Exception as e:
        print("Erreur récupération prix:", e)
        return None

# === SCRIPT PRINCIPAL ===
prix = recuperer_prix_btc()
if prix:
    tp1 = round(prix + 300, 2)
    tp2 = round(prix + 1000, 2)
    sl = round(prix - 150, 2)
    horodatage = datetime.now().strftime("%H:%M:%S")

    message = (
        "**TRADE TEST BTCUSD**\n"
        f"Entrée : {prix}\n"
        f"TP1 : {tp1}\n"
        f"TP2 : {tp2}\n"
        f"SL : {sl}\n"
        f"Confiance : 100%\n"
        f"Horodatage : {horodatage}"
    )

    envoyer_message(message)
else:
    print("Impossible de récupérer le prix BTC.")
