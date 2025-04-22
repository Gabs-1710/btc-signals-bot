import requests
import time
import datetime
import telegram

# --- PARAMÈTRES ---
TOKEN = "64845225-701f-4e09-b2a2-c3fd8315cb13"
CHAT_ID = "2128959111"
bot = telegram.Bot(token=TOKEN)

# --- API COINMARKETCAP ---
CMC_API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
CMC_PARAMS = {
    "symbol": "BTC",
    "convert": "USD"
}
CMC_HEADERS = {
    "Accepts": "application/json",
    "X-CMC_PRO_API_KEY": CMC_API_KEY
}

# --- FONCTION POUR OBTENIR LE PRIX BTCUSD ---
def get_btc_price():
    try:
        response = requests.get(CMC_URL, headers=CMC_HEADERS, params=CMC_PARAMS)
        data = response.json()
        price = float(data['data']['BTC']['quote']['USD']['price'])
        return round(price, 2)
    except Exception as e:
        print("Erreur récupération prix:", e)
        return None

# --- ENVOYER LE MESSAGE DE TEST ---
def send_trade_test(price):
    pe = round(price, 2)
    tp1 = round(pe + 300, 2)
    tp2 = round(pe + 1000, 2)
    sl = round(pe - 150, 2)
    msg = (
        "**TRADE TEST BTCUSD**\n"
        f"ACHAT\n"
        f"PE : {pe}\n"
        f"TP1 : {tp1}\n"
        f"TP2 : {tp2}\n"
        f"SL : {sl}\n"
        f"Confiance : 100%\n"
        f"Horodatage : {datetime.datetime.now().strftime('%H:%M:%S')}"
    )
    bot.send_message(chat_id=CHAT_ID, text=msg)

# --- ANALYSE DES STRATÉGIES (SIMULÉE) ---
def analyse_gagnante():
    print("Analyse des signaux gagnants en cours...")
    pe = get_btc_price()
    if not pe:
        return
    tp1 = round(pe + 300, 2)
    tp2 = round(pe + 1000, 2)
    sl = round(pe - 150, 2)
    msg = (
        f"ACHAT\n"
        f"PE : {pe}\n"
        f"TP1 : {tp1}\n"
        f"TP2 : {tp2}\n"
        f"SL : {sl}"
    )
    bot.send_message(chat_id=CHAT_ID, text=msg)

# --- EXÉCUTION PRINCIPALE ---
if __name__ == "__main__":
    btc_price = get_btc_price()
    if btc_price:
        send_trade_test(btc_price)
        analyse_gagnante()
    else:
        bot.send_message(chat_id=CHAT_ID, text="Erreur : impossible de récupérer le prix BTCUSD réel.")
