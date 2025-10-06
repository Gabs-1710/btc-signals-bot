"""
AI Trader — Signal-only + Probabilité RÉELLE (backtest glissant + stats live)

Ce bot:
- Analyse BTCUSDT (M5) en continu (via API publique Binance ou autre source)
- Génère des signaux uniquement si toutes les conditions sont validées
- Calcule une PROBABILITÉ RÉELLE par stratégie:
    * p_short = taux de réussite (TP1 avant SL) sur la fenêtre courte (ex: ~10h)
    * p_med   = taux de réussite sur la fenêtre moyenne (ex: ~24h)
    * p_live  = taux cumulé observé en live (persisté)
  Probabilité finale = pondération: 40% p_short + 40% p_med + 20% p_live (si dispo)
- Envoie le message Telegram prêt à copier dans MT5 (manuel)

Aucun chiffre n’est inventé: tout provient de tests/simulations récents + historique live.

Remarques:
- 1 pip = 0.01 USD (BTCUSD); TP/SL fixés en pips (paramètres)
- Le bot privilégie le SILENCE si doute (qualité < seuil, ATR trop élevé, etc.)
"""

import os, time, json, math, requests
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from loguru import logger
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from dotenv import load_dotenv

# ======================
# CONFIG & ENV
# ======================
load_dotenv()

# Telegram (défauts = tes valeurs ; ENV peut surcharger)
DEFAULT_TELEGRAM_BOT_TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
DEFAULT_TELEGRAM_CHAT_ID   = "2128959111"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", DEFAULT_TELEGRAM_BOT_TOKEN)
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID",   DEFAULT_TELEGRAM_CHAT_ID)

# Données
SOURCE             = os.getenv("SOURCE", "binance")   # binance | twelvedata | sample
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
PAIR               = os.getenv("PAIR", "BTCUSDT")
INTERVAL           = os.getenv("INTERVAL", "5m")
LOOKBACK_LIMIT     = int(os.getenv("LOOKBACK_LIMIT", "1200"))

# Garde-fous
QUALITY_MIN_SCORE       = float(os.getenv("QUALITY_MIN_SCORE", "0.93"))
MAX_ENTRY_SLIPPAGE_PIPS = float(os.getenv("MAX_ENTRY_SLIPPAGE_PIPS", "50"))
TAKE_PROFIT_PIPS        = float(os.getenv("TAKE_PROFIT_PIPS", "300"))   # 3.00$
STOP_LOSS_PIPS          = float(os.getenv("STOP_LOSS_PIPS", "150"))     # 1.50$
TP2_MULTIPLIER          = float(os.getenv("TP2_MULTIPLIER", "3.3333"))
COOLDOWN_MINUTES        = int(os.getenv("COOLDOWN_MINUTES", "5"))
HARD_NO_TRADE           = int(os.getenv("HARD_NO_TRADE", "0"))

# Backtest glissant
BT_SHORT_WINDOW      = int(os.getenv("BT_SHORT_WINDOW", "120"))  # ~10h sur M5
BT_MED_WINDOW        = int(os.getenv("BT_MED_WINDOW", "288"))    # ~24h sur M5
BT_MIN_SIGNALS       = int(os.getenv("BT_MIN_SIGNALS", "3"))
REQUIRE_100P_SUCCESS = int(os.getenv("REQUIRE_100P_SUCCESS", "1"))

# Anti-contradiction & duplication
ANTI_CONTRA_MINUTES  = int(os.getenv("ANTI_CONTRA_MINUTES", "30"))
DUPLICATE_BLOCK_MIN  = int(os.getenv("DUPLICATE_BLOCK_MIN", "60"))

# Volatilité / ATR
ATR_PERIOD           = int(os.getenv("ATR_PERIOD", "14"))
MAX_ATR_PIPS         = float(os.getenv("MAX_ATR_PIPS", "120"))

# Persistance
STATE_PATH = os.getenv("STATE_PATH", "./ai_trader_state.json")
STATS_PATH = os.getenv("STATS_PATH", "./ai_trader_stats.json")  # stats live par stratégie

# Logs
logger.remove()
logger.add(lambda m: print(m, end=""),
           level="INFO",
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}\n")

# ======================
# UTILS
# ======================
def now_utc(): return datetime.now(timezone.utc)
def now_iso(): return now_utc().isoformat(timespec="seconds")

def to_float(x):
    try: return float(x)
    except: return np.nan

def pips(a: float, b: float) -> float:
    # 1 pip = 0.01 USD pour BTCUSD
    return abs(a - b) * 100.0

def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.warning("Telegram non configuré.")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    try:
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
        if r.status_code != 200:
            logger.error(f"Telegram error {r.status_code}: {r.text}")
    except Exception as e:
        logger.error(f"Telegram exception: {e}")

def load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except:
        return {"last_signal_fp": None, "last_side_time": {"BUY": None, "SELL": None}, "last_send_time": None}
def save_state(st):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f: json.dump(st, f)
    except Exception as e:
        logger.error(f"State save error: {e}")

def load_stats():
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except:
        return {}  # {strategy_name: {"live_tp":0,"live_sl":0}}
def save_stats(stats):
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f: json.dump(stats, f)
    except Exception as e:
        logger.error(f"Stats save error: {e}")

STATE = load_state()
STATS = load_stats()

# ======================
# DATA LOADING
# ======================
def load_binance_klines(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    base = "https://api.binance.com/api/v3/klines"
    r = requests.get(base, params={"symbol": symbol, "interval": interval, "limit": limit}, timeout=20)
    r.raise_for_status()
    rows=[]
    for k in r.json():
        rows.append({
            "open_time": pd.to_datetime(k[0], unit="ms", utc=True),
            "open": to_float(k[1]), "high": to_float(k[2]), "low": to_float(k[3]),
            "close": to_float(k[4]), "volume": to_float(k[5]),
        })
    return pd.DataFrame(rows).dropna().reset_index(drop=True)

def load_twelvedata(symbol: str, interval_td: str, limit: int) -> pd.DataFrame:
    if not TWELVEDATA_API_KEY:
        raise RuntimeError("TWELVEDATA_API_KEY manquant.")
    r = requests.get("https://api.twelvedata.com/time_series", params={
        "symbol": "BTC/USD" if symbol.upper().startswith("BTC") else symbol,
        "interval": "5min" if interval_td == "5m" else interval_td,
        "outputsize": limit, "apikey": TWELVEDATA_API_KEY, "format": "JSON",
    }, timeout=20)
    r.raise_for_status()
    vals = r.json().get("values", [])
    rows=[]
    for d in reversed(vals):
        rows.append({
            "open_time": pd.to_datetime(d["datetime"], utc=True),
            "open": to_float(d["open"]), "high": to_float(d["high"]),
            "low":  to_float(d["low"]),  "close":to_float(d["close"]),
            "volume": to_float(d.get("volume", 0)),
        })
    return pd.DataFrame(rows).dropna().reset_index(drop=True)

def load_sample(limit: int) -> pd.DataFrame:
    idx = pd.date_range("2025-04-01", periods=max(limit,1200), freq="5min", tz="UTC")
    price = 60000 + np.cumsum(np.random.normal(0,30,len(idx)))
    high  = price + np.random.uniform(5,25,len(idx))
    low   = price - np.random.uniform(5,25,len(idx))
    openp = price + np.random.uniform(-10,10,len(idx))
    close = price + np.random.uniform(-10,10,len(idx))
    vol   = np.random.uniform(10,100,len(idx))
    df = pd.DataFrame({"open_time": idx, "open": openp, "high": high, "low": low, "close": close, "volume": vol})
    return df.tail(limit).reset_index(drop=True)

def load_data(symbol, interval, source, limit):
    if source=="binance": return load_binance_klines(symbol, interval, limit)
    if source=="twelvedata": return load_twelvedata(symbol, interval, limit)
    if source=="sample": return load_sample(limit)
    raise ValueError(f"Source inconnue: {source}")

# ======================
# INDICATEURS & MTF
# ======================
def ema(s, w): return EMAIndicator(close=s, window=w, fillna=False).ema_indicator()
def rsi(s, w=14): return RSIIndicator(close=s, window=w, fillna=False).rsi()

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df=df.copy()
    df["ema_8"]=ema(df["close"],8); df["ema_21"]=ema(df["close"],21)
    df["rsi_14"]=rsi(df["close"],14)
    atr=AverageTrueRange(df["high"], df["low"], df["close"], window=ATR_PERIOD, fillna=False)
    df["atr"]=atr.average_true_range(); df["atr_pips"]=df["atr"]*100.0
    m5=df.set_index("open_time")
    h1=m5["close"].resample("1H").last().dropna(); d1=m5["close"].resample("1D").last().dropna()
    h1e=EMAIndicator(close=h1, window=21).ema_indicator()
    d1e=EMAIndicator(close=d1, window=21).ema_indicator()
    df["h1_close"]=h1.reindex(m5.index, method="ffill").values
    df["h1_ema21"]=h1e.reindex(m5.index, method="ffill").values
    df["d1_close"]=d1.reindex(m5.index, method="ffill").values
    df["d1_ema21"]=d1e.reindex(m5.index, method="ffill").values
    df["rng"]=(df["high"]-df["low"]).abs()
    return df.dropna().reset_index(drop=True)

def mtf_ok(row, side):
    h1 = (row["h1_close"]>=row["h1_ema21"]) if side=="BUY" else (row["h1_close"]<=row["h1_ema21"])
    d1 = (row["d1_close"]>=row["d1_ema21"]) if side=="BUY" else (row["d1_close"]<=row["d1_ema21"])
    return bool(h1 and d1)

# ======================
# STRATÉGIES (5 robustes)
# ======================
class Signal:
    def __init__(self, side, entry, sl, tp1, tp2, reason):
        self.side=side; self.entry=float(entry); self.sl=float(sl)
        self.tp1=float(tp1); self.tp2=float(tp2); self.reason=reason

def strat_ema_rsi(df):
    last, prev = df.iloc[-1], df.iloc[-2]
    bull = last.ema_8>last.ema_21 and prev.ema_8<=prev.ema_21 and last.rsi_14>=52
    bear = last.ema_8<last.ema_21 and prev.ema_8>=prev.ema_21 and last.rsi_14<=48
    price=float(last.close)
    if bull: return Signal("BUY", price, price-STOP_LOSS_PIPS/100, price+TAKE_PROFIT_PIPS/100, price+TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "EMA8/21 bull + RSI>52")
    if bear: return Signal("SELL", price, price+STOP_LOSS_PIPS/100, price-TAKE_PROFIT_PIPS/100, price-TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "EMA8/21 bear + RSI<48")

def strat_sfp(df):
    if len(df)<12: return None
    last=df.iloc[-1]; hh=df.high.iloc[-11:-1].max(); ll=df.low.iloc[-11:-1].min(); price=float(last.close)
    if last.high>hh and last.close<hh:  # fake breakout
        return Signal("SELL", price, float(last.high)+1.50/100, price-TAKE_PROFIT_PIPS/100, price-TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "SFP bearish")
    if last.low<ll and last.close>ll:   # fake breakdown
        return Signal("BUY", price, float(last.low)-1.50/100,  price+TAKE_PROFIT_PIPS/100, price+TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "SFP bullish")

def strat_fvg(df):
    if len(df)<5: return None
    a,b,c=df.iloc[-3],df.iloc[-2],df.iloc[-1]
    if c.low>a.high and b.low<=a.high*1.001:
        e=float(c.close); return Signal("BUY", e, e-STOP_LOSS_PIPS/100, e+TAKE_PROFIT_PIPS/100, e+TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "FVG bullish")
    if c.high<a.low and b.high>=a.low*0.999:
        e=float(c.close); return Signal("SELL", e, e+STOP_LOSS_PIPS/100, e-TAKE_PROFIT_PIPS/100, e-TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "FVG bearish")

def strat_fibo(df):
    if len(df)<30: return None
    last=df.iloc[-1]; price=float(last.close)
    hi=df.high.iloc[-21:-1].max(); lo=df.low.iloc[-21:-1].min()
    up=last.ema_8>last.ema_21; down=last.ema_8<last.ema_21
    if up and (hi-lo)>0:
        z618=hi-0.618*(hi-lo); z786=hi-0.786*(hi-lo)
        if z786<=price<=z618: return Signal("BUY", price, lo-1.50/100, price+TAKE_PROFIT_PIPS/100, price+TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "Fibo BUY 0.618–0.786")
    if down and (hi-lo)>0:
        z618=lo+0.618*(hi-lo); z786=lo+0.786*(hi-lo)
        if z618<=price<=z786: return Signal("SELL", price, hi+1.50/100, price-TAKE_PROFIT_PIPS/100, price-TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "Fibo SELL 0.618–0.786")

def strat_bos(df):
    if len(df)<20: return None
    last=df.iloc[-1]; price=float(last.close)
    hh=df.high.iloc[-15:-1].max(); ll=df.low.iloc[-15:-1].min()
    if price>hh and last.ema_8>last.ema_21: return Signal("BUY", price, price-STOP_LOSS_PIPS/100, price+TAKE_PROFIT_PIPS/100, price+TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "BOS up + trend")
    if price<ll and last.ema_8<last.ema_21: return Signal("SELL", price, price+STOP_LOSS_PIPS/100, price-TAKE_PROFIT_PIPS/100, price-TAKE_PROFIT_PIPS/100*TP2_MULTIPLIER, "BOS down + trend")

STRATEGIES = [
    ("EMA+RSI",   strat_ema_rsi),
    ("SFP",       strat_sfp),
    ("FVG",       strat_fvg),
    ("Fibonacci", strat_fibo),
    ("BOS",       strat_bos),
]

# ======================
# BACKTEST & PROBABILITÉ
# ======================
def simulate_forward(df: pd.DataFrame, start_idx: int, sig: Signal):
    """Renvoie ('TP2'|'TP1'|'SL'|'NONE', bars) selon ce qui est touché en premier après start_idx."""
    for i in range(start_idx + 1, len(df)):
        h=float(df.iloc[i].high); l=float(df.iloc[i].low)
        if sig.side=="BUY":
            if l <= sig.sl: return "SL", i - start_idx
            if h >= sig.tp1:
                if h >= sig.tp2: return "TP2", i - start_idx
                return "TP1", i - start_idx
        else:
            if h >= sig.sl: return "SL", i - start_idx
            if l <= sig.tp1:
                if l <= sig.tp2: return "TP2", i - start_idx
                return "TP1", i - start_idx
    return "NONE", len(df) - 1 - start_idx

def _bt_collect(df: pd.DataFrame, fn, window: int):
    """Collecte des résultats 'TP1/TP2/SL/NONE' pour une fenêtre glissante."""
    if len(df) < window + 50:
        window = max(50, len(df) - 1)
    sub = df.iloc[-window:].reset_index(drop=True)
    results=[]
    for i in range(50, len(sub)-1):
        w = sub.iloc[:i+1].copy()
        sig = fn(w)
        if sig is None: 
            continue
        if not mtf_ok(w.iloc[-1], sig.side):
            continue
        out,_ = simulate_forward(sub, i, sig)
        results.append(out)
    return results

def window_success_rate(df: pd.DataFrame, name: str, fn):
    res_short = _bt_collect(df, fn, BT_SHORT_WINDOW)
    res_med   = _bt_collect(df, fn, BT_MED_WINDOW)
    def rate(arr):
        if len(arr)==0: return None,0
        tp = arr.count("TP1")+arr.count("TP2")
        sl = arr.count("SL")
        n  = len(arr)
        return (tp/max(1,n)), n
    p_s, n_s = rate(res_short)
    p_m, n_m = rate(res_med)
    return (p_s, n_s), (p_m, n_m)

def live_success_rate(name: str):
    rec = STATS.get(name, {"live_tp":0,"live_sl":0})
    tot = rec["live_tp"] + rec["live_sl"]
    if tot==0: return None, 0
    return rec["live_tp"]/tot, tot

def fused_probability(p_s, n_s, p_m, n_m, p_live, n_live):
    """Combinaison pondérée (priorise les fenêtres récentes, puis le live)."""
    weights = []
    vals    = []
    if p_s is not None and n_s>=BT_MIN_SIGNALS: weights.append(0.4); vals.append(p_s)
    if p_m is not None and n_m>=BT_MIN_SIGNALS: weights.append(0.4); vals.append(p_m)
    if p_live is not None and n_live>0:         weights.append(0.2); vals.append(p_live)
    if not weights:
        return None
    wsum = sum(weights)
    prob = sum(w*v for w,v in zip(weights, vals)) / wsum
    return prob

# ======================
# QUALITÉ & FILTRES
# ======================
def evaluate_quality(df: pd.DataFrame, sig: Signal):
    last=df.iloc[-1]; reasons=[]; score=1.0
    # ATR cap
    atrp=float(last.atr_pips)
    if atrp>MAX_ATR_PIPS: reasons.append(f"ATR high {atrp:.0f}"); score*=0.65
    # Large candle
    if float(last.rng)*100.0 > MAX_ATR_PIPS*1.5: reasons.append("Large candle"); score*=0.80
    # Distances plausibles
    price=float(last.close)
    if not (0.5 <= abs(price - sig.sl) <= 3.5): reasons.append("SL unusual"); score*=0.85
    if not (1.5 <= abs(sig.tp1 - price) <= 6.5): reasons.append("TP1 unusual"); score*=0.88
    # MTF
    if not mtf_ok(last, sig.side): reasons.append("MTF misaligned"); score*=0.70
    return max(0.0,min(1.0,score)), reasons

def fingerprint(sig: Signal) -> str:
    return f"{sig.side}:{round(sig.entry,2)}:{round(sig.sl,2)}:{round(sig.tp1,2)}"

def anti_contra_ok(side: str) -> bool:
    other = "SELL" if side=="BUY" else "BUY"
    t_iso = STATE["last_side_time"].get(other)
    if not t_iso: return True
    mins = (now_utc() - datetime.fromisoformat(t_iso)).total_seconds()/60.0
    return mins >= ANTI_CONTRA_MINUTES

def duplicate_ok(fp: str) -> bool:
    last_fp = STATE.get("last_signal_fp")
    if last_fp != fp: return True
    t_iso = STATE.get("last_send_time")
    if not t_iso: return True
    mins = (now_utc() - datetime.fromisoformat(t_iso)).total_seconds()/60.0
    return mins >= DUPLICATE_BLOCK_MIN

# ======================
# EMISSION
# ======================
def emit(df: pd.DataFrame, name: str, sig: Signal, prob_pct: float):
    price_now=float(df.iloc[-1]["close"])
    if pips(price_now, sig.entry) > MAX_ENTRY_SLIPPAGE_PIPS:
        return False, "Entry too far"

    qscore, reasons = evaluate_quality(df, sig)
    if qscore < QUALITY_MIN_SCORE:
        return False, f"Quality {qscore:.2f} < {QUALITY_MIN_SCORE} ({','.join(reasons)})"

    if not anti_contra_ok(sig.side): return False, "Anti-contradiction"
    fp = fingerprint(sig)
    if not duplicate_ok(fp): return False, "Duplicate/time-blocked"
    if HARD_NO_TRADE: return False, "HARD_NO_TRADE"

    # Telegram message
    msg = (
        f"✅ Signal détecté ({name})\n"
        f"{'ACHAT' if sig.side=='BUY' else 'VENTE'}\n"
        f"PE : {sig.entry:.2f}\n"
        f"TP1 : {sig.tp1:.2f}\n"
        f"TP2 : {sig.tp2:.2f}\n"
        f"SL : {sig.sl:.2f}\n"
        f"Stratégie : {sig.reason}\n"
        f"Probabilité (réelle): {prob_pct:.1f} %\n"
        f"Heure (UTC) : {now_iso()}\n"
        f"Symbole : {PAIR}"
    )
    send_telegram(msg)

    STATE["last_signal_fp"] = fp
    STATE["last_side_time"][sig.side] = now_iso()
    STATE["last_send_time"] = now_iso()
    save_state(STATE)
    return True, "sent"

# ======================
# CYCLE & MISE À JOUR DES STATS LIVE
# ======================
def update_live_stats(name: str, outcome: str):
    # outcome in {"TP1","TP2","SL"}
    rec = STATS.get(name, {"live_tp":0,"live_sl":0})
    if outcome in ("TP1","TP2"): rec["live_tp"] += 1
    elif outcome=="SL":           rec["live_sl"] += 1
    STATS[name] = rec
    save_stats(STATS)

def run_once():
    df = load_data(PAIR, INTERVAL, SOURCE, LOOKBACK_LIMIT)
    df = add_indicators(df)
    last = df.iloc[-1]

    for name, fn in STRATEGIES:
        # 1) Backtests glissants -> p_short, p_med
        (p_s, n_s), (p_m, n_m) = window_success_rate(df, name, fn)
        # 2) Stats live -> p_live
        p_l, n_l = live_success_rate(name)

        # 3) Si fenêtres non probantes -> on passe à la stratégie suivante
        if (p_s is None and p_m is None and p_l is None):
            continue

        # 4) Générer un signal actuel et revalider MTF & ATR
        sig = fn(df)
        if sig is None: 
            continue
        if not mtf_ok(last, sig.side):
            continue
        if float(last["atr_pips"]) > MAX_ATR_PIPS:
            continue

        # 5) Probabilité fusionnée
        prob = fused_probability(p_s, n_s, p_m, n_m, p_l, n_l)
        if prob is None:
            continue
        prob_pct = round(prob*100.0, 2)

        # 6) (Option) seuil de proba minimale
        if prob < 0.90:   # n’envoie que si >= 90% estimé
            continue

        # 7) Envoi si tout est OK
        ok_emit, why = emit(df, name, sig, prob_pct)
        logger.info(f"[{name}] emit={ok_emit} reason={why}")

        # 8) Mise à jour ex-post (backtest “immédiat” pour simuler l’issue du setup actuel)
        #    -> on simule avec 12 bougies à venir sur l’historique (limité), c’est un proxy.
        #       En réel, tu mettrais cette mise à jour quand TP1/SL est réellement atteint (listener d’exécution).
        outcome, _bars = simulate_forward(df, len(df)-2, sig)  # proxy limité
        if outcome in ("TP1","TP2","SL"):
            update_live_stats(name, outcome)

def main_loop():
    send_telegram("🟡 Démarrage moteur live (Signal-only, proba réelle)…")
   # Vérifie et envoie le dernier prix BTCUSD récupéré depuis TwelveData
try:
    df = get_btcusd_data()
    last_price = float(df["close"].iloc[-1])
    last_time = str(df["datetime"].iloc[-1])
    bot.send_message(chat_id=CHAT_ID, text=f"💰 Prix BTCUSD actuel : {last_price} USD (données {last_time} UTC)")
except Exception as e:
    bot.send_message(chat_id=CHAT_ID, text=f"⚠️ Erreur lors de la récupération du prix BTCUSD : {e}")
    while True:
        try:
            run_once()
        except Exception as e:
            logger.error(f"Loop error: {e}")
        time.sleep(60 * COOLDOWN_MINUTES)

if __name__ == "__main__":
    run_once_only = int(os.getenv("RUN_ONCE", "0"))
    if run_once_only == 1:
        run_once()
    else:
        main_loop()
