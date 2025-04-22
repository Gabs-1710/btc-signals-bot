import time
import requests
from datetime import datetime

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
CMC_API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"

# === OBTENIR PRIX ACTUEL DU BTCUSD ===
def get_prix_btc():
    url = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
    parameters = {
        'symbol': 'BTC',
        'convert': 'USD'
    }
    headers = {
        'Accepts': 'application/json',
        'X-CMC_PRO_API_KEY': CMC_API_KEY,
    }
    response = requests.get(url, headers=headers, params=parameters)
    data = response.json()
    prix = data['data']['BTC']['quote']['USD']['price']
    return round(prix, 2)

# === ENVOI DU MESSAGE TELEGRAM ===
def envoyer_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, data=payload)
        print("Signal envoyé -> Statut :", response.status_code)
    except Exception as e:
        print("Erreur lors de l'envoi du signal:", e)

# === ENVOYER LE TRADE TEST ===
def envoyer_signal_test():
    prix = get_prix_btc()
    tp1 = round(prix + 300, 2)
    tp2 = round(prix + 1000, 2)
    sl = round(prix - 150, 2)
    message = (
        "**TRADE TEST BTCUSD**\n"
        f"Entrée : {prix}\n"
        f"TP1 : {tp1}\n"
        f"TP2 : {tp2}\n"
        f"SL : {sl}\n"
        f"Confiance : 100%\n"
        f"Horodatage : {datetime.now().strftime('%H:%M:%S')}"
    )
    envoyer_telegram(message)

# === EXÉCUTION DU SCRIPT ===
if __name__ == "__main__":
    envoyer_signal_test()
