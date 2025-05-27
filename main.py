import requests
import time
from datetime import datetime

TELEGRAM_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"

API_KEY_PRINCIPALE = "2055fb1ec82c4ff5b487ce449faf8370"
API_KEY_SECOURS = "d7ddc825488f4b078fba7af6d01c32c5"

symbol = "BTC/USD"
interval = "5min"

trades_envoyes = []
combinaisons_gagnantes = set()
patterns_recents = []

# === Données ===
def get_btc_price():
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={API_KEY_PRINCIPALE}&format=JSON&outputsize=1000"
    response = requests.get(url)
    data = response.json()
    if "values" in data:
        return data["values"]
    url_secours = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={API_KEY_SECOURS}&format=JSON&outputsize=1000"
    response = requests.get(url_secours)
    return response.json().get("values", [])

# === Telegram ===
def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": CHAT_ID, "text": message})

# === Outils stratégiques ===
def calculate_ema(prices, period):
    k = 2 / (period + 1)
    ema = prices[0]
    for price in prices[1:]:
        ema = price * k + ema * (1 - k)
    return ema

def calculate_rsi(closes, period=14):
    gains, losses = [], []
    for i in range(1, period + 1):
        delta = closes[i - 1] - closes[i]
        gains.append(max(0, delta))
        losses.append(max(0, -delta))
    avg_gain, avg_loss = sum(gains)/period, sum(losses)/period
    if avg_loss == 0:
        return 100
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# === Détection stratégie parfaite ===
def strategie_parfaite(bougies):
    closes = [float(c['close']) for c in bougies[:50]]
    highs = [float(c['high']) for c in bougies[:50]]
    lows = [float(c['low']) for c in bougies[:50]]
    opens = [float(c['open']) for c in bougies[:50]]

    ema8 = calculate_ema(closes[:8], 8)
    ema21 = calculate_ema(closes[:21], 21)
    rsi = calculate_rsi(closes[:15])

    trend_up = ema8 > ema21
    momentum_ok = rsi > 52

    choch = highs[1] > highs[2] and lows[0] < lows[1]
    bos = lows[1] < lows[2] and highs[0] > highs[1]
    ob = closes[1] < opens[1] and closes[2] > closes[1]
    fvg = lows[2] > highs[0]
    fibo_reject = lows[0] > (lows[2] + 0.618 * (highs[2] - lows[2]))
    compression = max(highs[:5]) - min(lows[:5]) < 0.005 * closes[0]
    sfp = highs[0] > highs[1] and closes[0] < highs[1]
    volatilite = max(highs[:20]) - min(lows[:20])

    combinaison = "CHoCH + BOS + OB + FVG + Fibo + EMA + RSI + Compression + SFP"
    contexte_favorable = momentum_ok and compression and (0.001 < volatilite < 0.06)
    pattern_recent = combinaison in patterns_recents

    if ob and fibo_reject and contexte_favorable:
        if combinaison not in combinaisons_gagnantes:
            combinaisons_gagnantes.add(combinaison)
        if combinaison not in patterns_recents:
            patterns_recents.append(combinaison)
            if len(patterns_recents) > 10:
                patterns_recents.pop(0)
        return True, combinaison, 100

    if fvg and sfp and contexte_favorable:
        return True, "FVG + SFP + contexte IA", 100

    if compression and sfp and contexte_favorable:
        return True, "Compression + SFP", 100

    if ob and choch and contexte_favorable:
        return True, "OB + CHoCH + Contexte IA", 100

    return False, None, 0

# === Trade test ===
def trade_test():
    bougies = get_btc_price()
    if bougies:
        prix_actuel = float(bougies[0]['close'])
        PE = prix_actuel
        TP1 = round(PE + 300 / 10000, 2)
        TP2 = round(PE + 1000 / 10000, 2)
        SL = round(PE - 150 / 10000, 2)
        msg = f"TRADE TEST\nACHAT\nPE : {PE}\nTP1 : {TP1}\nTP2 : {TP2}\nSL : {SL}"
        send_telegram(msg)

# === Main loop ===
if __name__ == "__main__":
    trade_test()
    while True:
        bougies = get_btc_price()
        valide, strat, proba = strategie_parfaite(bougies)

        if valide:
            PE = float(bougies[0]['close'])
            TP1 = round(PE + 300 / 10000, 2)
            TP2 = round(PE + 1000 / 10000, 2)
            SL = round(PE - 150 / 10000, 2)
            prix_actuel = PE

            volatilite_locale = max([float(c['high']) - float(c['low']) for c in bougies[:10]])
            tol = max(0.5, round(volatilite_locale * 0.6, 2))

            if abs(prix_actuel - PE) <= tol:
                heure = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
                msg = f"🚨 SIGNAL BTCUSD M5 🚨\nACHAT\nPE : {PE}\nTP1 : {TP1}\nTP2 : {TP2}\nSL : {SL}\nStratégie : {strat}\nRéussite estimée : {proba}%\nHeure : {heure}"
                send_telegram(msg)
                trades_envoyes.append({"PE": PE, "TP1": TP1, "SL": SL, "strategie": strat})

        for trade in trades_envoyes[:]:
            prix_actuel = float(bougies[0]['close'])
            if prix_actuel >= trade['TP1']:
                send_telegram(f"✅ TP1 atteint pour le trade PE : {trade['PE']}\nStratégie : {trade['strategie']}")
                trades_envoyes.remove(trade)
            elif prix_actuel <= trade['SL']:
                send_telegram(f"❌ SL touché pour le trade PE : {trade['PE']}\nStratégie suspendue : {trade['strategie']}")
                trades_envoyes.remove(trade)
                combinaisons_gagnantes.discard(trade['strategie'])

        time.sleep(300)
