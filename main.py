import requests
import time
import telebot

# CONFIG PERSONNALISÉE
API_KEY = 'd7ddc825488f4b078fba7af6d01c32c5'
SYMBOL = 'BTC/USD'
TIMEFRAME = '1min'
BOT_TOKEN = '7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU'
CHAT_ID = '2128959111'
CHECK_INTERVAL = 60  # seconds

bot = telebot.TeleBot(BOT_TOKEN)

def get_live_price():
    url = f'https://api.twelvedata.com/price?symbol={SYMBOL}&apikey={API_KEY}'
    response = requests.get(url)
    data = response.json()
    if 'price' in data:
        return float(data['price'])
    return None

def analyze_signal(price_history):
    last = price_history[-1]
    ema = sum(price_history[-10:]) / 10
    trend_up = last > ema
    fibo_support = min(price_history[-50:]) * 1.05
    fibo_resistance = max(price_history[-50:]) * 0.95
    if trend_up and last > fibo_resistance:
        return 'ACHAT'
    if not trend_up and last < fibo_support:
        return 'VENTE'
    return None

def backtest(price_history, direction):
    TP1 = 300 * 0.01
    SL = 150 * 0.01
    entry = price_history[-1]
    tp1_price = entry + TP1 if direction == 'ACHAT' else entry - TP1
    sl_price = entry - SL if direction == 'ACHAT' else entry + SL
    for future in price_history[-500:]:
        if direction == 'ACHAT' and future <= sl_price:
            return False
        if direction == 'VENTE' and future >= sl_price:
            return False
        if direction == 'ACHAT' and future >= tp1_price:
            return True
        if direction == 'VENTE' and future <= tp1_price:
            return True
    return False

def send_signal(signal, price):
    TP1 = price + 300 * 0.01 if signal == 'ACHAT' else price - 300 * 0.01
    TP2 = price + 1000 * 0.01 if signal == 'ACHAT' else price - 1000 * 0.01
    SL = price - 150 * 0.01 if signal == 'ACHAT' else price + 150 * 0.01
    msg = f"{signal}\nPE : {round(price,2)}\nTP1 : {round(TP1,2)}\nTP2 : {round(TP2,2)}\nSL : {round(SL,2)}"
    bot.send_message(CHAT_ID, msg)

def main():
    price_history = []
    while True:
        price = get_live_price()
        if price:
            price_history.append(price)
            if len(price_history) > 500:
                signal = analyze_signal(price_history)
                if signal and backtest(price_history, signal):
                    send_signal(signal, price)
                price_history.pop(0)
            else:
                bot.send_message(CHAT_ID, f"Trade test (moteur prêt)\nPE : {price}\nTP1 : {round(price + 300 * 0.01,2)}\nTP2 : {round(price + 1000 *0.01,2)}\nSL : {round(price -150 *0.01,2)}")
        else:
            bot.send_message(CHAT_ID, "Erreur API : prix non disponible")
        time.sleep(CHECK_INTERVAL)

if __name__ == '__main__':
    main()
