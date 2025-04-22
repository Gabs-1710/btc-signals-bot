import requests
import time
import telegram
from datetime import datetime

# === CONFIGURATION ===
TELEGRAM_TOKEN = "TON_TOKEN_ICI"  # Remplace par ton vrai token
CHAT_ID = "2128959111"
COINMARKET_API_KEY = "64845225-701f-4e09-b2a2-c3fd8315cb13"
HEADERS = {"X-CMC_PRO_API_KEY": COINMARKET_API_KEY}
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
PARAMS = {"symbol": "BTC", "convert": "USD"}

# === INITIALISATION DU BOT TELEGRAM ===
bot = telegram.Bot(token=TELEGRAM_TOKEN)

# === FONCTION POUR RÉCUPÉRER LE PRIX ACTUEL DE BTC ===
def get_btc_price():
    try:
        response = requests.get(CMC_URL, headers=HEADERS, params=PARAMS)
        data = response.json()
        return float(data["data"]["BTC"]["quote"]["USD"]["price"])
    except Exception as e:
        print("Erreur récupération prix BTC:", e)
        return None

# === ENVOI DU TRADE TEST AU DÉMARRAGE ===
def send_trade_test(price):
    entry = round(price, 2)
    tp1 = round(entry + 300, 2)
    tp2 = round(entry + 1000, 2)
    sl = round(entry - 150, 2)
    message = (
        "**TRADE TEST BTCUSD**\n"
        f"ACHAT\n"
        f"PE : {entry}\n"
        f"TP1 : {tp1}\n"
        f"TP2 : {tp2}\n"
        f"SL : {sl}\n"
        f"Horodatage : {datetime.now().strftime('%H:%M:%S')}"
    )
    bot.send_message(chat_id=CHAT_ID, text=message)
    print("Trade test envoyé.")

# === DÉTECTION DES SIGNES ULTRA GAGNANTS (SIMULÉE ICI) ===
def analyse_des_signaux():
    while True:
        print("Analyse des signaux gagnants en cours...")
        time.sleep(600)  # 10 min entre chaque cycle (à adapter)

        # Simuler une détection de signal parfait (à remplacer par la vraie logique)
        signal_detecte = False

        if signal_detecte:
            pe = 9000  # Exemple
            tp1 = pe + 300
            tp2 = pe + 1000
            sl = pe - 150
            msg = (
                "**VENTE**\n"
                f"PE : {pe}\n"
                f"TP1 : {tp1}\n"
                f"TP2 : {tp2}\n"
                f"SL : {sl}"
            )
            bot.send_message(chat_id=CHAT_ID, text=msg)
            print("Signal ultra gagnant envoyé.")

# === MAIN ===
if __name__ == "__main__":
    prix = get_btc_price()
    if prix:
        send_trade_test(prix)
    analyse_des_signaux()
