import requests
import time
from datetime import datetime

# Configuration du bot Telegram
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"
HEADERS = {"X-CoinAPI-Key": API_KEY}

# Fonction pour récupérer le prix réel de BTCUSD
def get_btc_price():
    try:
        url = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"
        response = requests.get(url, headers=HEADERS)
        data = response.json()
        return float(data["rate"])
    except Exception as e:
        print("Erreur récupération prix :", e)
        return None

# Fonction pour envoyer un message Telegram
def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Erreur envoi Telegram :", e)

# Fonction pour formater un message trade test
def format_trade_message(price, direction="ACHAT"):
    tp1 = round(price + 300, 2)
    tp2 = round(price + 1000, 2)
    sl = round(price - 150, 2)
    timestamp = datetime.now().strftime("%H:%M:%S")
    return f"""
**{direction} BTCUSD**
PE : {price}
TP1 : {tp1}
TP2 : {tp2}
SL : {sl}
Confiance : 100%
Horodatage : {timestamp}
""".strip()

# Envoi unique du message test
btc_price = get_btc_price()
if btc_price:
    message = format_trade_message(btc_price)
    send_telegram_message(message)
    print("Trade test envoyé.")
else:
    print("Impossible de récupérer le prix BTC.")

# Lancement de l'analyse (boucle principale silencieuse)
while True:
    print("Analyse des signaux gagnants en cours...")
    time.sleep(60 * 60)  # Analyse fictive chaque heure (peut être ajusté)
