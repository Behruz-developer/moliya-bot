"""
LOKAL ADMIN DASHBOARD — faqat sizning kompyuteringizda ishlaydi.

Ishga tushirish:  python3 dashboard.py
Manzil:            http://127.0.0.1:5050

Ko'rsatadi:
- Ro'yxatdan o'tgan barcha foydalanuvchilar (ism, username, ID, til, manba,
  birinchi/oxirgi faollik)
- Har bir foydalanuvchining BARCHA kirim/chiqimlari (sana, vaqt, turi,
  kategoriya, summa, izoh, asl matn)
- Umumiy statistika (userlar soni, jami yozuvlar, daromad, xarajat, balans)

Xavfsizlik:
- Faqat 127.0.0.1'da tinglaydi — internetdan hech kim ko'ra olmaydi
- FAQAT O'QISH rejimida — ma'lumotlarni buzib qo'ya olmaydi
- Eski userlarning ism/username'i avtomatik to'ldiriladi (Telegram getChat)
- Yozuvlar `data/*.json`da + GitHub zaxirada (gh_zaxira.py) — hech qachon
  yo'qolmaydi
"""
import json
import os
import threading
import urllib.request
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask

import data_store

# Lokal dashboard'da Mini App'ni ham brauzerda ko'rish mumkin (Telegram'siz):
# http://127.0.0.1:5050/app — faqat 127.0.0.1, internetga ochiq emas
os.environ.setdefault("LOCAL_DEV", "1")
import miniapp

load_dotenv()

app = Flask(__name__)
miniapp.register(app)

# Eski odat uchun: /miniapp.html ham xuddi /app kabi ishlaydi
@app.route("/miniapp.html")
def miniapp_html_alias():
    from flask import Response
    return Response(miniapp._html_olish(), mimetype="text/html")

DASH_PORT = int(os.getenv("DASH_PORT", 5050))

# 30 sekundda avtomatik yangilanadi
REFRESH = int(os.getenv("DASH_REFRESH", 30))


def _fmt(n) -> str:
    return f"{data_store._son_qil(n):,}".replace(",", " ")


def eski_profillarni_toldir():
    """Ism/username'siz qolgan eski userlarni Telegram getChat orqali to'ldiradi."""
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        print("⚠️ TELEGRAM_BOT_TOKEN yo'q — eski userlar profili to'ldirilmaydi")
        return
    for chat_id, _ in list(data_store._users_yukla().items()):
        mavjud = data_store.user_olish(chat_id)
        if mavjud.get("ism"):
            continue  # allaqachon to'liq
        try:
            url = f"https://api.telegram.org/bot{token}/getChat?chat_id={chat_id}"
            with urllib.request.urlopen(url, timeout=10) as r:
                javob = json.loads(r.read().decode("utf-8"))
            if javob.get("ok"):
                ch = javob["result"]
                ism = " ".join(x for x in (ch.get("first_name", ""), ch.get("last_name", "")) if x).strip()
                data_store.user_faollik(chat_id, ism, ch.get("username", ""), manba="getchat")
                print(f"✅ Profil to'ldirildi: {chat_id} — {ism}")
        except Exception as e:
            print(f"⚠️ {chat_id} profili olinmadi: {e}")


def _yozuvlar_qatori(y: dict) -> str:
    tur = y.get("turi", "")
    belgi = "🟢" if tur == "Daromad" else "🔴"
    rang = "daromad" if tur == "Daromad" else "harajat"
    asl = (y.get("asl_matn") or "").strip()
    izoh = (y.get("izoh") or "").strip()
    return (
        f"<tr class='{rang}'>"
        f"<td>{y.get('sana', '')} <span class='vaqt'>{y.get('vaqt', '')}</span></td>"
        f"<td>{belgi} {tur}</td>"
        f"<td>{y.get('kategoriya', '')}</td>"
        f"<td class='summa'>{_fmt(y.get('summa', 0))} so'm</td>"
        f"<td>{izoh}</td>"
        f"<td class='asl'>{asl}</td>"
        f"</tr>"
    )


def _user_karta(i: int, x: dict) -> str:
    username = f"@{x['username']}" if x["username"] else "—"
    manba = x["manba"] or "bot"
    birinchi = (x["birinchi"] or "")[:10] or "—"
    oxirgi = (x["oxirgi"] or "")[:10] or "—"
    yozuvlar = data_store.barchasi(x["chat_id"])
    if yozuvlar:
        qatorlar = "".join(_yozuvlar_qatori(y) for y in yozuvlar)
        jadval = (
            "<details><summary>📄 Barcha yozuvlar (" + str(len(yozuvlar))
            + ") — bosing va oching</summary>"
            "<table><tr><th>Sana</th><th>Turi</th><th>Kategoriya</th><th>Summa</th>"
            "<th>Izoh</th><th>Asl matn</th></tr>" + qatorlar + "</table></details>"
        )
    else:
        jadval = "<p class='bosh'>📭 Hozircha yozuv yo'q</p>"
    return (
        f"<div class='karta'><div class='sarlavha'><span class='raqam'>{i}</span>"
        f"<div><b>{x['ism'] or '—'}</b> <span class='username'>{username}</span>"
        f"<div class='kichik'>🆔 {x['chat_id']} · 🌐 {x['til']} · 📡 {manba}</div></div></div>"
        f"<div class='statlar'><span>🧾 {x['yozuvlar']} yozuv</span>"
        f"<span class='d'>🟢 {_fmt(x['daromad'])} so'm</span>"
        f"<span class='h'>🔴 {_fmt(x['harajat'])} so'm</span>"
        f"<span class='b'>💼 {_fmt(x['balans'])} so'm</span></div>"
        f"<div class='kichik'>📅 {birinchi} dan beri · oxirgi faollik: {oxirgi}</div>"
        f"{jadval}</div>"
    )
HTML_SHABLON = """<!doctype html>
<html lang="uz"><head>
<meta charset="utf-8">
<meta http-equiv="refresh" content="@@REFRESH@@">
<title>Moliya bot — Admin Dashboard</title>
<style>
* { box-sizing: border-box; margin: 0; }
body { font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; background: #0f1420; color: #e6e9ef; padding: 24px; }
h1 { font-size: 22px; margin-bottom: 4px; }
.kichik { font-size: 12px; color: #8b93a7; }
.yuqori { background: #171d2b; border: 1px solid #232b3d; border-radius: 14px; padding: 16px 20px; margin-bottom: 20px; }
.statlar-yuqori { display: flex; flex-wrap: wrap; gap: 18px; margin-top: 10px; }
.statlar-yuqori span { font-size: 15px; }
.statlar-yuqori b { font-size: 17px; }
.d, .b { color: #4ade80; }
.h { color: #f87171; }
.karta { background: #171d2b; border: 1px solid #232b3d; border-radius: 14px; padding: 16px 20px; margin-bottom: 14px; }
.sarlavha { display: flex; align-items: center; gap: 12px; margin-bottom: 10px; }
.raqam { background: #232b3d; border-radius: 50%; width: 28px; height: 28px; display: flex; align-items: center; justify-content: center; font-size: 13px; flex-shrink: 0; }
.username { color: #7dd3fc; font-size: 13px; }
.statlar { display: flex; flex-wrap: wrap; gap: 16px; margin: 8px 0; font-size: 14px; }
details { margin-top: 10px; }
summary { cursor: pointer; color: #7dd3fc; font-size: 14px; padding: 6px 0; }
table { width: 100%; border-collapse: collapse; margin-top: 8px; font-size: 13px; }
th { text-align: left; color: #8b93a7; font-weight: 500; padding: 6px 8px; border-bottom: 1px solid #232b3d; }
td { padding: 6px 8px; border-bottom: 1px solid #1d2433; }
tr.harajat td:nth-child(4) { color: #f87171; }
tr.daromad td:nth-child(4) { color: #4ade80; }
.vaqt { color: #8b93a7; font-size: 11px; }
.asl { color: #8b93a7; font-style: italic; max-width: 220px; }
.bosh { color: #8b93a7; }
.yangilash { color: #8b93a7; font-size: 12px; }
</style>
</head><body>
<div class="yuqori">
  <h1>📊 Moliya bot — Admin Dashboard</h1>
  <div class="kichik">Jarayon: @@Hozir@@ · har @@REFRESH@@ sekundda avtomatik yangilanadi · faqat o'qish rejimi</div>
  <div class="statlar-yuqori">
    <span>👥 <b>@@Userlar@@</b> foydalanuvchi</span>
    <span>🧾 <b>@@Yozuvlar@@</b> yozuv</span>
    <span class="d">🟢 <b>@@Daromad@@</b> so'm</span>
    <span class="h">🔴 <b>@@Harajat@@</b> so'm</span>
    <span class="b">💼 <b>@@Balans@@</b> so'm</span>
  </div>
</div>
@@Kartalar@@
<p class="yangilash" style="text-align:center;margin:20px 0">🔄 Yangilash uchun sahifani qayta oching (yoki @@REFRESH@@ sekund kutib turing)</p>
</body></html>"""


@app.route("/")
def index():
    userlar = data_store.foydalanuvchilar_royxati()
    # Eng so'nggi faol birinchi
    userlar.sort(key=lambda x: (x["oxirgi"] or ""), reverse=True)
    jami_yozuv = sum(x["yozuvlar"] for x in userlar)
    jami_daromad = sum(x["daromad"] for x in userlar)
    jami_harajat = sum(x["harajat"] for x in userlar)
    jami_balans = jami_daromad - jami_harajat
    hozir = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    kartalar = "".join(_user_karta(i, x) for i, x in enumerate(userlar, 1)) or (
        "<p class='bosh' style='text-align:center;padding:40px'>📭 Hozircha ro'yxatdan"
        " o'tgan foydalanuvchi yo'q. Biror kishi botga /start bersa — shu yerda paydo bo'ladi.</p>"
    )
    return (
        HTML_SHABLON
        .replace("@@Hozir@@", hozir)
        .replace("@@Kartalar@@", kartalar)
        .replace("@@Userlar@@", str(len(userlar)))
        .replace("@@Yozuvlar@@", str(jami_yozuv))
        .replace("@@Daromad@@", _fmt(jami_daromad))
        .replace("@@Harajat@@", _fmt(jami_harajat))
        .replace("@@Balans@@", _fmt(jami_balans))
        .replace("@@REFRESH@@", str(REFRESH))
    )


if __name__ == "__main__":
    # Eski userlar profilini fon rejimida to'ldirish (botni bloklamasin)
    threading.Thread(target=eski_profillarni_toldir, daemon=True).start()
    url = f"http://127.0.0.1:{DASH_PORT}"
    print(f"📊 Admin Dashboard: {url}")
    print(f"📱 Mini App (brauzerda):  {url}/app")
    print("   (faqat shu kompyuterdan ochiladi — yopish: Ctrl+C)")
    # Brauzerni o'zi ochadi — to'g'ri manzillarda (2 sekunddan keyin)
    try:
        import webbrowser
        threading.Timer(2.0, lambda: webbrowser.open(url + "/")).start()
        threading.Timer(3.5, lambda: webbrowser.open(url + "/app")).start()
    except Exception:
        pass
    app.run(host="127.0.0.1", port=DASH_PORT, debug=False)
