import requests
import pandas as pd
import time
import telebot
import ta

# CONFIGURATION
API_KEY = 'd7ddc825488f4b078fba7af6d01c32c5'
TELEGRAM_TOKEN = '7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU'
CHAT_ID = '2128959111'
SYMBOL = 'BTC/USD'
INTERVAL = '1min'
bot = telebot.TeleBot(TELEGRAM_TOKEN)

def get_live_data():
    url = f'https://api.twelvedata.com/time_series?symbol={SYMBOL}&interval={INTERVAL}&apikey={API_KEY}&outputsize=500'
    r = requests.get(url)
    data = r.json()
    if 'values' not in data:
        return None
    df = pd.DataFrame(data['values'])
    df['close'] = pd.to_numeric(df['close'])
    df = df.iloc[::-1]
    return df

def detect_order_block(df):
    return df['close'].iloc[-2] < df['open'].iloc[-2] and df['close'].iloc[-1] > df['open'].iloc[-1]

def detect_fvg(df):
    prev_low = df['low'].iloc[-2]
    curr_high = df['high'].iloc[-1]
    return curr_high - prev_low > (df['high'].max() - df['low'].min()) * 0.01

def detect_choch_bos(df):
    return df['high'].iloc[-1] > df['high'].iloc[-2] and df['low'].iloc[-1] > df['low'].iloc[-2]

def apply_strategies(df):
    df['ema'] = df['close'].ewm(span=10, adjust=False).mean()
    df['rsi'] = ta.momentum.rsi(df['close'], window=14)
    signals = []
    if (df['close'].iloc[-1] > df['ema'].iloc[-1] and 
        df['rsi'].iloc[-1] < 70 and 
        detect_order_block(df) and 
        detect_fvg(df) and 
        detect_choch_bos(df)):
        signals.append('BUY')
    if (df['close'].iloc[-1] < df['ema'].iloc[-1] and 
        df['rsi'].iloc[-1] > 30 and 
        detect_order_block(df) and 
        detect_fvg(df) and 
        detect_choch_bos(df)):
        signals.append('SELL')
    return signals

def simulate_trade(entry, tp1, sl, df):
    for price in df['close']:
        if price <= sl:
            return False
        if price >= tp1:
            return True
    return False

def send_telegram(message):
    bot.send_message(CHAT_ID, message)

def main():
    # Trade test au démarrage (une seule fois)
    price_data = get_live_data()
    if price_data is not None:
        price = price_data['close'].iloc[-1]
        send_telegram(f"Trade test (moteur prêt)\nPE : {price}\nTP1 : {price + 300}\nTP2 : {price + 1000}\nSL : {price - 150}")

    while True:
        df = get_live_data()
        if df is None:
            send_telegram("Erreur API : prix non disponible")
            time.sleep(120)
            continue

        signals = apply_strategies(df)
        for signal in signals:
            price = df['close'].iloc[-1]
            pe = price
            tp1 = pe + 300 if signal == 'BUY' else pe - 300
            sl = pe - 150 if signal == 'BUY' else pe + 150

            if simulate_trade(pe, tp1, sl, df):
                message = f"{'ACHAT' if signal == 'BUY' else 'VENTE'}\nPE : {round(pe, 2)}\nTP1 : {round(tp1, 2)}\nTP2 : {round(tp1 + 700 if signal == 'BUY' else tp1 - 700, 2)}\nSL : {round(sl, 2)}"
                send_telegram(message)
        time.sleep(60)

if __name__ == "__main__":
    main()
