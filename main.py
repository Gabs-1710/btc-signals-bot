import requests
import time
import datetime
import pytz

TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"
API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"

HEADERS = {
    "X-CoinAPI-Key": API_KEY
}

URL = "https://rest.coinapi.io/v1/exchangerate/BTC/USD"

sent_trade_test = False

def get_btc_price():
    try:
        response = requests.get(URL, headers=HEADERS)
        data = response.json()
        return float(data['rate'])
    except Exception as e:
        print("Erreur récupération prix:", e)
        return None

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message
    }
    try:
        response = requests.post(url, data=payload)
        if response.status_code != 200:
            print("Erreur Telegram:", response.text)
    except Exception as e:
        print("Erreur envoi Telegram:", e)

def send_trade_test():
    global sent_trade_test
    if sent_trade_test:
        return

    price = get_btc_price()
    if price is None:
        print("Impossible de récupérer le prix BTC.")
        return

    tp1 = round(price + 300, 2)
    tp2 = round(price + 1000, 2)
    sl = round(price - 150, 2)
    now = datetime.datetime.now(pytz.timezone('Europe/Paris')).strftime("%H:%M:%S")

    message = f"**ACHAT BTCUSD**\nPE : {price}\nTP1 : {tp1}\nTP2 : {tp2}\nSL : {sl}\nConfiance : 100%\nHorodatage : {now}"
    send_telegram_message(message)
    print("Trade test envoyé.")
    sent_trade_test = True

def analyze_signals():
    print("Analyse des signaux gagnants en cours...")
    send_telegram_message("Analyse des signaux gagnants en cours...")

if __name__ == '__main__':
    send_trade_test()
    analyze_signals()
