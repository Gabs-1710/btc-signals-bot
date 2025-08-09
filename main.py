#!/usr/bin/env python3
# Worker Render : envoie un update Telegram au démarrage puis toutes les 6h, sans aucune action manuelle.

import json
import time
import signal
import sys
from datetime import datetime
import urllib.request

# ✅ Tes infos Telegram (intégrées)
TOKEN = "7539711435:AAHQqle6mRgMEokKJtUdkmIMzSgZvteFKsU"
CHAT_ID = "2128959111"

# ⏱ Intervalle d'envoi (secondes) : 6h
SEND_INTERVAL = 6 * 60 * 60

# 📝 État courant (je le mettrai à jour côté moteur au fil des phases)
PHASE = "A"
PERCENT = 15
DONE = "Phase A en cours : accès Binance/Render/Telegram validés"
NEXT = "Phase B : backtest massif"

def send_telegram(text: str) -> bool:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    req = urllib.request.Request(url, data=json.dumps(data).encode(), headers={"Content-Type":"application/json"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            resp = json.loads(r.read().decode())
            return bool(resp.get("ok"))
    except Exception as e:
        print(f"⚠️  Envoi Telegram échoué : {e}", flush=True)
        return False

def build_message() -> str:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    lines = []
    lines.append("📢 <b>Update d’avancement (auto)</b>")
    lines.append(f"🗓 {now}\n")
    lines.append(f"📊 <b>Avancement global</b> : <b>{PERCENT} %</b>")
    lines.append(f"🏷 <b>Phase</b> : <b>{PHASE}</b>\n")
    lines.append("🛠 <b>Ce qui a été fait</b> :")
    lines.append(f"• {DONE}")
    lines.append("\n🔜 <b>Prochaine étape</b> :")
    lines.append(f"• {NEXT}")
    lines.append("\n" + "─" * 20)
    tableau = [
        ("A", "Audit & setup",        "✅" if PHASE > "A" or PERCENT == 100 else ("⏳" if PHASE == "A" else "—")),
        ("B", "Backtest & tri auto",  "✅" if PHASE > "B" or PERCENT == 100 else ("⏳" if PHASE == "B" else "—")),
        ("C", "Moteur live & gardes", "✅" if PHASE > "C" or PERCENT == 100 else ("⏳" if PHASE == "C" else "—")),
        ("D", "Déploiement & suivi",  "✅" if PHASE > "D" or PERCENT == 100 else ("⏳" if PHASE == "D" else "—")),
        ("E", "PineScript & pack",    "✅" if PHASE > "E" or PERCENT == 100 else ("⏳" if PHASE == "E" else "—")),
    ]
    lines.append("<b>Tableau de progression</b>")
    for code, desc, stat in tableau:
        lines.append(f"{code} — {desc} : {stat}")
    return "\n".join(lines)

# Arrêt propre
STOP = False
def handle_sigterm(signum, frame):
    global STOP
    STOP = True
signal.signal(signal.SIGTERM, handle_sigterm)
signal.signal(signal.SIGINT, handle_sigterm)

def main():
    # Envoi immédiat au démarrage
    text = build_message()
    ok = send_telegram(text)
    print("✅ Premier update envoyé" if ok else "⚠️ Premier update non envoyé", flush=True)

    # Boucle toutes les 6h
    while not STOP:
        # Dormir en tranches de 60s pour réagir vite à l’arrêt
        slept = 0
        while slept < SEND_INTERVAL and not STOP:
            time.sleep(60)
            slept += 60
        if STOP:
            break
        ok = send_telegram(build_message())
        print("✅ Update 6h envoyé" if ok else "⚠️ Update 6h non envoyé", flush=True)

    print("👋 Arrêt du worker", flush=True)

if __name__ == "__main__":
    main()
