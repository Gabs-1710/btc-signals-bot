"""
AI Trader — Signal-only (Telegram) ENSEMBLE
- Source: TwelveData (fiable sur Render)
- Envoie le prix BTCUSD au démarrage
- Nombreux setups: EMA/RSI, FVG, SFP, BOS/CHoCH, Order Block (proxy), Pullback EMA200,
  Breakout-Retest, RSI Divergence
- Backtests glissants par setup (court/moyen) + stats live => probabilité par setup
- COMBINE les setups alignés (même sens) => proba confluente + bonus de confluence
- Filtres: MTF H1/D1, ATR, qualité distances, anti-duplication, anti-contradiction
"""

import os, time, json, requests, math
import numpy as np
import pandas as pd
from datetime import datetime, timezone
from loguru import logger
from ta.momentum import RSIIndicator
from ta.trend import EMAIndicator
from ta.volatility import AverageTrueRange
from dotenv import load_dotenv

# ======================
# CONFIG
# ======================
load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN",
    "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU")
TELEGRAM_CHAT_ID   = os.getenv("TELEGRAM_CHAT_ID", "2128959111")

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "2055fb1ec82c4ff5b487ce449faf8370")
PAIR               = os.getenv("PAIR", "BTC/USD")          # TwelveData symbol
INTERVAL           = os.getenv("INTERVAL", "5min")
LOOKBACK_LIMIT     = int(os.getenv("LOOKBACK_LIMIT", "900"))  # ~3 jours M5

# Risk/TP-SL (BTC pip=0.01$)
TAKE_PROFIT_PIPS   = float(os.getenv("TAKE_PROFIT_PIPS", "300"))    # +3.00$
STOP_LOSS_PIPS     = float(os.getenv("STOP_LOSS_PIPS", "150"))      # -1.50$
TP2_MULTIPLIER     = float(os.getenv("TP2_MULTIPLIER", "3.3333"))

# Filters / thresholds
SEUIL_PROBA_SETUP  = float(os.getenv("SEUIL_PROBA_SETUP", "0.70"))   # proba min d'un setup seul pour entrer en combinaison
SEUIL_PROBA_FINAL  = float(os.getenv("SEUIL_PROBA_FINAL", "0.90"))   # proba finale requise
QUALITY_MIN_SCORE  = float(os.getenv("QUALITY_MIN_SCORE", "0.93"))
MAX_ENTRY_SLIPPAGE_PIPS = float(os.getenv("MAX_ENTRY_SLIPPAGE_PIPS", "60"))
ATR_PERIOD         = int(os.getenv("ATR_PERIOD", "14"))
MAX_ATR_PIPS       = float(os.getenv("MAX_ATR_PIPS", "140"))
COOLDOWN_MINUTES   = int(os.getenv("COOLDOWN_MINUTES", "5"))
ANTI_CONTRA_MIN    = int(os.getenv("ANTI_CONTRA_MINUTES", "30"))
DUPLICATE_BLOCK_MIN= int(os.getenv("DUPLICATE_BLOCK_MIN", "60"))
HARD_NO_TRADE      = int(os.getenv("HARD_NO_TRADE", "0"))

# Backtests glissants
BT_SHORT_WINDOW    = int(os.getenv("BT_SHORT_WINDOW", "120"))
BT_MED_WINDOW      = int(os.getenv("BT_MED_WINDOW", "288"))
BT_MIN_SIGNALS     = int(os.getenv("BT_MIN_SIGNALS", "3"))

STATE_PATH = os.getenv("STATE_PATH", "./ai_trader_state.json")
STATS_PATH = os.getenv("STATS_PATH", "./ai_trader_stats.json")

# Logs
logger.remove()
logger.add(lambda m: print(m, end=""),
           level="INFO",
           format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | {message}\n")

# ======================
# Utils
# ======================
def now_utc(): return datetime.now(timezone.utc)
def now_iso(): return now_utc().isoformat(timespec="seconds")
def pips(a,b): return abs(a-b)*100.0  # BTC pip=0.01$

def send_tg(text):
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": text}, timeout=10)
    except Exception as e:
        logger.error(f"Telegram error: {e}")

def load_state():
    try:
        with open(STATE_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: return {"last_fp": None, "last_side_time":{"BUY":None,"SELL":None}, "last_send": None}

def save_state(st):
    try:
        with open(STATE_PATH, "w", encoding="utf-8") as f: json.dump(st, f)
    except Exception as e: logger.error(f"save_state: {e}")

def load_stats():
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f: return json.load(f)
    except: return {}  # {setup_name: {"live_tp":0,"live_sl":0}}

def save_stats(stats):
    try:
        with open(STATS_PATH, "w", encoding="utf-8") as f: json.dump(stats, f)
    except Exception as e: logger.error(f"save_stats: {e}")

STATE = load_state()
STATS = load_stats()

# ======================
# Data (TwelveData)
# ======================
def load_twelvedata(symbol: str, interval: str, limit: int) -> pd.DataFrame:
    r = requests.get("https://api.twelvedata.com/time_series", params={
        "symbol": symbol, "interval": interval, "outputsize": limit,
        "apikey": TWELVEDATA_API_KEY, "format": "JSON",
    }, timeout=20)
    r.raise_for_status()
    vals = r.json().get("values", [])
    if not vals: raise RuntimeError("TwelveData empty")
    rows=[]
    for d in reversed(vals):
        rows.append({
            "open_time": pd.to_datetime(d["datetime"], utc=True),
            "open": float(d["open"]), "high": float(d["high"]),
            "low": float(d["low"]), "close": float(d["close"]),
            "volume": float(d.get("volume", 0.0))
        })
    return pd.DataFrame(rows).reset_index(drop=True)

def load_data():
    return load_twelvedata(PAIR, INTERVAL, LOOKBACK_LIMIT)

# ======================
# Indicators & MTF
# ======================
def ema(s,w): return EMAIndicator(close=s, window=w, fillna=False).ema_indicator()
def rsi(s,w=14): return RSIIndicator(close=s, window=w, fillna=False).rsi()

def add_indicators(df: pd.DataFrame) -> pd.DataFrame:
    df=df.copy()
    df["ema_8"]=ema(df["close"],8); df["ema_21"]=ema(df["close"],21); df["ema_200"]=ema(df["close"],200)
    df["rsi_14"]=rsi(df["close"],14)
    atr=AverageTrueRange(df["high"], df["low"], df["close"], window=ATR_PERIOD, fillna=False)
    df["atr"]=atr.average_true_range(); df["atr_pips"]=df["atr"]*100.0
    m5=df.set_index("open_time")
    h1=m5["close"].resample("1H").last().dropna(); d1=m5["close"].resample("1D").last().dropna()
    h1e=EMAIndicator(h1,21).ema_indicator(); d1e=EMAIndicator(d1,21).ema_indicator()
    df["h1_close"]=h1.reindex(m5.index, method="ffill").values
    df["h1_ema21"]=h1e.reindex(m5.index, method="ffill").values
    df["d1_close"]=d1.reindex(m5.index, method="ffill").values
    df["d1_ema21"]=d1e.reindex(m5.index, method="ffill").values
    df["rng"]=(df["high"]-df["low"]).abs()
    return df.dropna().reset_index(drop=True)

def mtf_ok(row, side):
    h1_ok = (row["h1_close"]>=row["h1_ema21"]) if side=="BUY" else (row["h1_close"]<=row["h1_ema21"])
    d1_ok = (row["d1_close"]>=row["d1_ema21"]) if side=="BUY" else (row["d1_close"]<=row["d1_ema21"])
    return bool(h1_ok and d1_ok)

# ======================
# Signals
# ======================
class Sig:
    def __init__(self, name, side, entry, sl, tp1, tp2, reason):
        self.name=name; self.side=side; self.entry=float(entry); self.sl=float(sl)
        self.tp1=float(tp1); self.tp2=float(tp2); self.reason=reason

def make_sig(name, side, price, sl_off_pips=STOP_LOSS_PIPS, tp_off_pips=TAKE_PROFIT_PIPS):
    if side=="BUY":
        sl=price - sl_off_pips/100; tp1=price + tp_off_pips/100; tp2=price + (tp_off_pips/100)*TP2_MULTIPLIER
    else:
        sl=price + sl_off_pips/100; tp1=price - tp_off_pips/100; tp2=price - (tp_off_pips/100)*TP2_MULTIPLIER
    return Sig(name, side, price, sl, tp1, tp2, name)

# --- Setups (détections légères mais robustes) ---
def setup_ema_rsi(df):
    last, prev=df.iloc[-1], df.iloc[-2]; price=float(last.close)
    if last.ema_8>last.ema_21 and prev.ema_8<=prev.ema_21 and last.rsi_14>=52:
        return make_sig("EMA+RSI", "BUY", price)
    if last.ema_8<last.ema_21 and prev.ema_8>=prev.ema_21 and last.rsi_14<=48:
        return make_sig("EMA+RSI", "SELL", price)

def setup_fvg(df):
    if len(df)<5: return None
    a,b,c=df.iloc[-3],df.iloc[-2],df.iloc[-1]; price=float(c.close)
    if c.low>a.high and b.low<=a.high*1.001:   # gap haussier comblé
        return make_sig("FVG", "BUY", price)
    if c.high<a.low and b.high>=a.low*0.999:   # gap baissier comblé
        return make_sig("FVG", "SELL", price)

def setup_sfp(df):
    if len(df)<12: return None
    last=df.iloc[-1]; hh=df.high.iloc[-11:-1].max(); ll=df.low.iloc[-11:-1].min(); price=float(last.close)
    if last.high>hh and last.close<hh: return make_sig("SFP", "SELL", price)
    if last.low<ll and last.close>ll:  return make_sig("SFP", "BUY",  price)

def setup_bos(df):
    if len(df)<20: return None
    last=df.iloc[-1]; price=float(last.close); hh=df.high.iloc[-15:-1].max(); ll=df.low.iloc[-15:-1].min()
    if price>hh and last.ema_8>last.ema_21: return make_sig("BOS", "BUY", price)
    if price<ll and last.ema_8<last.ema_21: return make_sig("BOS", "SELL", price)

def setup_ob_proxy(df):
    # proxy OB: pullback proche d'une bougie impulsive (rng>percentile) + rejet EMA21
    last=df.iloc[-1]; price=float(last.close)
    rng_th=np.percentile(df.rng.tail(50), 75)
    imp=df.rng.iloc[-2]>rng_th
    if imp and last.ema_8>last.ema_21 and abs(price-last.ema_21)<(STOP_LOSS_PIPS/100)*1.2:
        return make_sig("OB", "BUY", price)
    if imp and last.ema_8<last.ema_21 and abs(price-last.ema_21)<(STOP_LOSS_PIPS/100)*1.2:
        return make_sig("OB", "SELL", price)

def setup_pullback_ema200(df):
    last=df.iloc[-1]; price=float(last.close)
    if last.ema_8>last.ema_200 and abs(price-last.ema_200)<(STOP_LOSS_PIPS/100)*1.5:
        return make_sig("PB_EMA200","BUY",price)
    if last.ema_8<last.ema_200 and abs(price-last.ema_200)<(STOP_LOSS_PIPS/100)*1.5:
        return make_sig("PB_EMA200","SELL",price)

def setup_breakout_retest(df):
    last=df.iloc[-1]; price=float(last.close)
    hh=df.high.iloc[-25:-1].max(); ll=df.low.iloc[-25:-1].min()
    # faux-retour simple
    if price>hh and abs(price-hh)/(hh+1e-9) < 0.002 and last.ema_8>last.ema_21:
        return make_sig("BRK_RT","BUY",price)
    if price<ll and abs(price-ll)/(ll+1e-9) < 0.002 and last.ema_8<last.ema_21:
        return make_sig("BRK_RT","SELL",price)

def setup_rsi_div(df):
    # divergence RSI basique
    p1,p0=df.iloc[-3],df.iloc[-1]
    if p0.close>p1.close and p0.rsi_14<p1.rsi_14 and p0.ema_8< p0.ema_21:
        return make_sig("RSI_DIV","SELL",float(p0.close))
    if p0.close<p1.close and p0.rsi_14>p1.rsi_14 and p0.ema_8> p0.ema_21:
        return make_sig("RSI_DIV","BUY", float(p0.close))

SETUPS = [
    ("EMA+RSI", setup_ema_rsi),
    ("FVG", setup_fvg),
    ("SFP", setup_sfp),
    ("BOS", setup_bos),
    ("OB", setup_ob_proxy),
    ("PB_EMA200", setup_pullback_ema200),
    ("BRK_RT", setup_breakout_retest),
    ("RSI_DIV", setup_rsi_div),
]

# ======================
# Backtests & proba
# ======================
def simulate_forward(df: pd.DataFrame, start_idx: int, sig: Sig):
    for i in range(start_idx+1, len(df)):
        h=float(df.iloc[i].high); l=float(df.iloc[i].low)
        if sig.side=="BUY":
            if l<=sig.sl: return "SL", i-start_idx
            if h>=sig.tp1:
                if h>=sig.tp2: return "TP2", i-start_idx
                return "TP1", i-start_idx
        else:
            if h>=sig.sl: return "SL", i-start_idx
            if l<=sig.tp1:
                if l<=sig.tp2: return "TP2", i-start_idx
                return "TP1", i-start_idx
    return "NONE", len(df)-1-start_idx

def _bt_collect(df: pd.DataFrame, fn, window: int):
    if len(df)<window+50: window=max(50, len(df)-1)
    sub=df.iloc[-window:].reset_index(drop=True)
    out=[]
    for i in range(50, len(sub)-1):
        w=sub.iloc[:i+1]
        sig=fn(w)
        if sig is None: continue
        if not mtf_ok(w.iloc[-1], sig.side): continue
        r,_=simulate_forward(sub, i, sig)
        out.append(r)
    return out

def rate(arr):
    if not arr: return None,0
    tp=arr.count("TP1")+arr.count("TP2"); n=len(arr)
    return tp/max(1,n), n

def window_success_rate(df, name, fn):
    rs=_bt_collect(df, fn, BT_SHORT_WINDOW); rm=_bt_collect(df, fn, BT_MED_WINDOW)
    p_s,n_s=rate(rs); p_m,n_m=rate(rm); return (p_s,n_s),(p_m,n_m)

def live_success_rate(name):
    rec=STATS.get(name, {"live_tp":0,"live_sl":0})
    tot=rec["live_tp"]+rec["live_sl"]
    if tot==0: return None,0
    return rec["live_tp"]/tot, tot

def fused_probability(p_s,n_s,p_m,n_m,p_live,n_live):
    w=[]; v=[]
    if p_s is not None and n_s>=BT_MIN_SIGNALS: w.append(0.4); v.append(p_s)
    if p_m is not None and n_m>=BT_MIN_SIGNALS: w.append(0.4); v.append(p_m)
    if p_live is not None and n_live>0:         w.append(0.2); v.append(p_live)
    if not w: return None
    return sum(a*b for a,b in zip(w,v))/sum(w)

# ======================
# Quality & emission
# ======================
def quality_ok(df, sig: Sig):
    last=df.iloc[-1]; score=1.0
    if float(last.atr_pips)>MAX_ATR_PIPS: score*=0.6
    if float(last.rng)*100.0 > MAX_ATR_PIPS*1.5: score*=0.8
    price=float(last.close)
    if not (0.5<=abs(price-sig.sl)<=3.8): score*=0.85
    if not (1.5<=abs(sig.tp1-price)<=6.8): score*=0.88
    return score>=QUALITY_MIN_SCORE

def fp(sig: Sig): return f"{sig.side}:{round(sig.entry,2)}:{round(sig.sl,2)}:{round(sig.tp1,2)}"

def anti_contra(side: str)->bool:
    other="SELL" if side=="BUY" else "BUY"
    t=STATE["last_side_time"].get(other)
    if not t: return True
    mins=(now_utc()-datetime.fromisoformat(t)).total_seconds()/60.0
    return mins>=ANTI_CONTRA_MIN

def dedup_ok(fprint: str)->bool:
    if STATE["last_fp"]!=fprint: return True
    t=STATE.get("last_send")
    if not t: return True
    mins=(now_utc()-datetime.fromisoformat(t)).total_seconds()/60.0
    return mins>=DUPLICATE_BLOCK_MIN

def emit(sig: Sig, prob_final: float, parts: list):
    if HARD_NO_TRADE: return False,"HARD_NO_TRADE"
    f=fp(sig); STATE["last_fp"]=f
    STATE["last_side_time"][sig.side]=now_iso(); STATE["last_send"]=now_iso(); save_state(STATE)
    setups_str=", ".join(parts)
    msg=(f"✅ Signal détecté (Confluence: {setups_str})\n"
         f"{'ACHAT' if sig.side=='BUY' else 'VENTE'}\n"
         f"PE : {sig.entry:.2f}\nTP1 : {sig.tp1:.2f}\nTP2 : {sig.tp2:.2f}\nSL : {sig.sl:.2f}\n"
         f"Probabilité (réelle): {prob_final*100:.1f} %\nHeure (UTC) : {now_iso()}\nSymbole : BTCUSD")
    send_tg(msg)
    return True,"sent"

# ======================
# ENSEMBLE ENGINE
# ======================
def run_once():
    df=add_indicators(load_data())
    last=df.iloc[-1]
    price=float(last.close)

    # 1) évaluer tous les setups
    candidates=[]
    probs={}
    for name,fn in SETUPS:
        # backtests
        (p_s,n_s),(p_m,n_m)=window_success_rate(df, name, fn)
        p_l,n_l=live_success_rate(name)
        prob=fused_probability(p_s,n_s,p_m,n_m,p_l,n_l)
        probs[name]=prob
        if prob is None or prob < SEUIL_PROBA_SETUP:
            continue
        sig=fn(df)
        if not sig: continue
        if not mtf_ok(last, sig.side): continue
        if float(last.atr_pips)>MAX_ATR_PIPS: continue
        if pips(price, sig.entry)>MAX_ENTRY_SLIPPAGE_PIPS: continue
        if not quality_ok(df, sig): continue
        candidates.append((name, sig, prob))

    if not candidates:
        logger.info("No candidate setups.")
        return

    # 2) regrouper par side et proximité d'entrée, puis combiner
    by_side={"BUY":[], "SELL":[]}
    for name,sig,prob in candidates:
        by_side[sig.side].append((name,sig,prob))
    for side, group in by_side.items():
        if not group: continue
        # pick base = plus haute proba setup
        group.sort(key=lambda x: x[2], reverse=True)
        base_name, base_sig, base_prob = group[0]
        parts=[base_name]; probs_used=[base_prob]
        # ajouter confluences compatibles (même sens, entry proche)
        for name,sig,prob in group[1:]:
            if pips(sig.entry, base_sig.entry)<=MAX_ENTRY_SLIPPAGE_PIPS*1.5:
                parts.append(name); probs_used.append(prob)
        # proba finale = moyenne pondérée + bonus de confluence
        if probs_used:
            prob_final = sum(probs_used)/len(probs_used)
            bonus = min(0.05*(len(parts)-1), 0.10)  # +5% par setup additionnel, max +10%
            prob_final = min(0.999, prob_final + bonus)
            # checks finaux
            if not anti_contra(side): 
                continue
            if not dedup_ok(fp(base_sig)):
                continue
            if prob_final >= SEUIL_PROBA_FINAL:
                ok,why=emit(base_sig, prob_final, parts)
                logger.info(f"EMIT {side} {parts} prob={prob_final:.3f} -> {ok}/{why}")
            else:
                logger.info(f"Confluence {parts} prob={prob_final:.3f} < seuil {SEUIL_PROBA_FINAL:.2f}")

# proxy live update (simplifié)
def update_live_stats(name: str, outcome: str):
    rec=STATS.get(name, {"live_tp":0,"live_sl":0})
    if outcome in ("TP1","TP2"): rec["live_tp"]+=1
    elif outcome=="SL":          rec["live_sl"]+=1
    STATS[name]=rec; save_stats(STATS)

def main_loop():
    send_tg("🟡 Démarrage moteur live (Ensemble)…")
    # prix au démarrage
    try:
        df0=load_data(); last_price=float(df0["close"].iloc[-1]); t=str(df0["open_time"].iloc[-1])
        send_tg(f"💰 Prix BTCUSD actuel : {last_price:.2f} USD (données {t} UTC)")
    except Exception as e:
        send_tg(f"⚠️ Erreur prix BTCUSD : {e}")

    while True:
        try:
            run_once()
        except Exception as e:
            logger.error(f"Loop error: {e}")
        time.sleep(60*COOLDOWN_MINUTES)

if __name__=="__main__":
    main_loop()
