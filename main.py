import requests
import time
import telegram
from datetime import datetime

# === CONFIGURATION ===
TELEGRAM_TOKEN = "64845225-701f-4e09-b2a2-c3fd8315cb13"
CHAT_ID = 2128959111
TRADE_SENT = False

# === INITIALISATION BOT TELEGRAM ===
bot = telegram.Bot(token=TELEGRAM_TOKEN)

def get_btc_price():
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        return float(response.json()['price'])
    except Exception as e:
        print("Erreur récupération prix BTC:", e)
        return None

def send_telegram_message(message):
    try:
        bot.send_message(chat_id=CHAT_ID, text=message)
    except Exception as e:
        print("Erreur envoi message:", e)

def trade_test():
    price = get_btc_price()
    if price:
        pe = round(price, 2)
        tp1 = round(pe + 300, 2)
        tp2 = round(pe + 1000, 2)
        sl = round(pe - 150, 2)
        message = f"**TRADE TEST BTCUSD**\nPE : {pe}\nTP1 : {tp1}\nTP2 : {tp2}\nSL : {sl}\nConfiance : 100%\nHorodatage : {datetime.now().strftime('%H:%M:%S')}"
        send_telegram_message(message)
        print("Trade test envoyé.")
    else:
        print("Prix BTC non récupéré pour le Trade test.")

def analyse_strategies():
    send_telegram_message("Analyse des signaux gagnants en cours...")
    print("Analyse des stratégies enclenchée...")
    # Ici, on implémente le moteur final d’analyse ultra filtrée :
    # (OB, FVG, CHoCH, BOS, EMA, tendance D1, R/R ≥ 2...)
    # Dès qu’un vrai signal ultra gagnant est détecté :
    # Exemple d’envoi :
    # send_telegram_message("ACHAT\nPE : 64200\nTP1 : 64500\nTP2 : 65200\nSL : 64050")

if not TRADE_SENT:
    trade_test()
    TRADE_SENT = True
    analyse_strategies()
