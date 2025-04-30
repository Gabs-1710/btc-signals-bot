import requests

# === CONFIG
TWELVE_API_KEY = "d7ddc825488f4b078fba7af6d01c32c5"
TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
TELEGRAM_CHAT_ID = "2128959111"

# === ENVOI TELEGRAM
def send_telegram_message(text):
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text}
        requests.post(url, data=payload)
    except Exception as e:
        print("Erreur Telegram :", e)

# === RÉCUPÉRATION DERNIÈRE CLÔTURE M5 BTCUSD (TwelveData)
def get_latest_btc_close():
    try:
        url = f"https://api.twelvedata.com/time_series"
        params = {
            "symbol": "BTC/USD",
            "interval": "5min",
            "outputsize": 1,
            "apikey": TWELVE_API_KEY
        }
        res = requests.get(url, params=params, timeout=10)
        res.raise_for_status()
        data = res.json()
        last_close = float(data["values"][0]["close"])
        timestamp = data["values"][0]["datetime"]
        return last_close, timestamp
    except Exception as e:
        return None, str(e)

# === TRADE TEST
def send_trade_test():
    price, info = get_latest_btc_close()
    if price is None:
        send_telegram_message(f"Erreur TwelveData : {info}")
        return
    tp1 = price + 300
    tp2 = price + 1000
    sl = price - 150
    msg = (
        f"ACHAT (Trade test)\n"
        f"PE : {price:.2f}\n"
        f"TP1 : {tp1:.2f}\n"
        f"TP2 : {tp2:.2f}\n"
        f"SL : {sl:.2f}\n"
        f"[{info} UTC]"
    )
    send_telegram_message(msg)

# === LANCEMENT
if __name__ == "__main__":
    send_trade_test()
