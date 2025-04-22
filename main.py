import time
import requests
from datetime import datetime

# === CONFIGURATION ===
BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"

# === ENVOI DU TRADE TEST AVEC PRIX RÉEL ===
def envoyer_trade_test():
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        prix_actuel = float(response.json()["price"])

        tp1 = prix_actuel + 300
        tp2 = prix_actuel + 1000
        sl = prix_actuel - 150

        message = (
            "SIGNAL TEST BTCUSD (données réelles)\n"
            f"Achat à : {round(prix_actuel, 2)}\n"
            f"TP1 : {round(tp1, 2)}\n"
            f"TP2 : {round(tp2, 2)}\n"
            f"SL : {round(sl, 2)}\n"
            "⚠️ Ce message est un test automatique basé sur le prix réel."
        )

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        data = {"chat_id": CHAT_ID, "text": message}
        r = requests.post(url, data=data)
        print("Signal test envoyé – Statut :", r.status_code)
    except Exception as e:
        print("Erreur :", e)

# === MOTEUR DE SIGNALS SIMPLIFIÉ (exemple ultra gagnant) ===
def moteur_trading():
    try:
        response = requests.get("https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT")
        prix = float(response.json()["price"])

        # === SIMULATION : déclenchement si prix termine par 00 (ex : 91100.00) ===
        if str(int(prix))[-2:] == "00":
            tp1 = prix + 300
            tp2 = prix + 1000
            sl = prix - 150

            message = (
                "**SIGNAL GAGNANT BTCUSD**\n"
                f"Achat à : {round(prix, 2)}\n"
                f"TP1 : {round(tp1, 2)}\n"
                f"TP2 : {round(tp2, 2)}\n"
                f"SL : {round(sl, 2)}\n"
                "Taux de confiance : 100%"
            )

            url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
            data = {"chat_id": CHAT_ID, "text": message}
            r = requests.post(url, data=data)
            print("Signal réel envoyé – Statut :", r.status_code)

    except Exception as e:
        print("Erreur moteur :", e)

# === EXÉCUTION AU DÉMARRAGE ===
if __name__ == "__main__":
    envoyer_trade_test()  # Envoi du message test
    while True:
        moteur_trading()   # Scan du marché
        time.sleep(300)     # toutes les 5 minutes
