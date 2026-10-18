"""
Har bir foydalanuvchining ma'lumotlari alohida JSON faylda saqlanadi:
data/<chat_id>.json — Google Sheets kerak emas!
"""
import datetime
import json
import os
import threading
import uuid
from collections import defaultdict
from zoneinfo import ZoneInfo

import gh_zaxira

DATA_JILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_qulf = threading.Lock()


def _fayl_yuli(chat_id) -> str:
    os.makedirs(DATA_JILD, exist_ok=True)
    return os.path.join(DATA_JILD, f"{chat_id}.json")


def _yukla(chat_id) -> list:
    try:
        with open(_fayl_yuli(chat_id), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _saqla(chat_id, yozuvlar: list):
    yuli = _fayl_yuli(chat_id)
    with open(yuli, "w", encoding="utf-8") as f:
        json.dump(yozuvlar, f, ensure_ascii=False, indent=2)
    # GitHub repoga zaxira (Render ephemeral disk muammosiga qarshi)
    try:
        rel = os.path.relpath(yuli, _REPO_ROOT)
        gh_zaxira.fon_zaxira(
            rel,
            json.dumps(yozuvlar, ensure_ascii=False, indent=2).encode("utf-8"),
            f"Moliya: {chat_id} yozuvlari zaxiralandi",
        )
    except Exception:
        pass


def yozuv_qosh(chat_id, natija: dict):
    """AI natijasini (turi, kategoriya, summa...) shu user jadvaliga qo'shadi."""
    hozir = datetime.datetime.now(ZoneInfo("Asia/Tashkent"))
    yozuv = {
        "id": uuid.uuid4().hex[:8],
        "sana": hozir.date().isoformat(),
        "vaqt": hozir.strftime("%H:%M"),
        "turi": "Daromad" if natija["turi"] == "daromad" else "Harajat",
        "kategoriya": natija["kategoriya"],
        "summa": natija["summa"],
        "izoh": natija.get("izoh", ""),
        "asl_matn": natija.get("original_matn", ""),
    }
    with _qulf:
        yozuvlar = _yukla(chat_id)
        yozuvlar.append(yozuv)
        _saqla(chat_id, yozuvlar)
    return yozuv


def barchasi(chat_id) -> list:
    with _qulf:
        return _yukla(chat_id)


def oxirgi_yozuvlar(chat_id, soni: int = 5) -> list:
    """[(indeks, yozuv), ...] — indeks listdagi o'rni."""
    with _qulf:
        yozuvlar = _yukla(chat_id)
    return list(enumerate(yozuvlar))[-soni:]


def yozuvni_ochirish(chat_id, indeks: int):
    with _qulf:
        yozuvlar = _yukla(chat_id)
        if 0 <= indeks < len(yozuvlar):
            yozuvlar.pop(indeks)
            _saqla(chat_id, yozuvlar)


def yozuvni_yangilash(chat_id, indeks: int, yangi_yozuv: dict):
    with _qulf:
        yozuvlar = _yukla(chat_id)
        if 0 <= indeks < len(yozuvlar):
            hozir = datetime.datetime.now(ZoneInfo("Asia/Tashkent"))
            yangi_yozuv = {
                "sana": hozir.date().isoformat(),
                "vaqt": hozir.strftime("%H:%M"),
                "turi": "Daromad" if yangi_yozuv["turi"] == "daromad" else "Harajat",
                "kategoriya": yangi_yozuv["kategoriya"],
                "summa": yangi_yozuv["summa"],
                "izoh": yangi_yozuv.get("izoh", ""),
                "asl_matn": yangi_yozuv.get("original_matn", ""),
            }
            yozuvlar[indeks] = yangi_yozuv
            _saqla(chat_id, yozuvlar)


def yozuvlar_id_bilan(chat_id) -> list:
    """Barcha yozuvlar; eskilarida 'id' bo'lmasa bir marta berib qo'yadi (lazy migratsiya)."""
    with _qulf:
        yozuvlar = _yukla(chat_id)
        ozi = False
        for y in yozuvlar:
            if not y.get("id"):
                y["id"] = uuid.uuid4().hex[:8]
                ozi = True
        if ozi:
            _saqla(chat_id, yozuvlar)
    return yozuvlar


def yozuvni_ochirish_id(chat_id, yozuv_id) -> bool:
    with _qulf:
        yozuvlar = _yukla(chat_id)
        yangi = [y for y in yozuvlar if y.get("id") != yozuv_id]
        if len(yangi) == len(yozuvlar):
            return False
        _saqla(chat_id, yangi)
        return True


def yozuvni_yangilash_id(chat_id, yozuv_id, o_zgarishlar: dict) -> bool:
    """Mini App'dagi tahrirlash: faqat berilgan maydonlarni yangilaydi."""
    with _qulf:
        yozuvlar = _yukla(chat_id)
        for i, y in enumerate(yozuvlar):
            if y.get("id") == yozuv_id:
                # turi berilmagan bo'lsa — eski qiymatini SAQLAYDI (Mini App'dan
                # sanani yangilashda xarajat daromadga aylanib ketish xatosi tuzatildi).
                # income/expense (Mini App) va daromad/harajat (bot) Ikkalasi ham qabul qilinadi.
                turi_xom = str(o_zgarishlar.get("turi", y.get("turi", ""))).lower()
                if turi_xom in ("daromad", "income"):
                    yangi_turi = "Daromad"
                elif turi_xom in ("harajat", "xarajat", "expense"):
                    yangi_turi = "Harajat"
                else:
                    yangi_turi = y.get("turi", "Harajat")
                yozuvlar[i] = {
                    "id": yozuv_id,
                    "sana": o_zgarishlar.get("sana", y["sana"]),
                    "vaqt": o_zgarishlar.get("vaqt", y["vaqt"]),
                    "turi": yangi_turi,
                    "kategoriya": o_zgarishlar.get("kategoriya", y["kategoriya"]),
                    "summa": o_zgarishlar.get("summa", y["summa"]),
                    "izoh": o_zgarishlar.get("izoh", y.get("izoh", "")),
                    "asl_matn": y.get("asl_matn", ""),
                }
                _saqla(chat_id, yozuvlar)
                return True
        return False


def tozalash(chat_id) -> int:
    with _qulf:
        yozuvlar = _yukla(chat_id)
        soni = len(yozuvlar)
        _saqla(chat_id, [])
        return soni


def _son_qil(n) -> int:
    """Har xil formatdagi summani songa aylantiradi ("4 000 so'm", "200\xa0000" ...)."""
    s = str(n).replace("\xa0", "").replace(" ", "").replace(",", "")
    s = s.replace("so'm", "").replace("so`m", "").replace("сум", "").strip()
    try:
        return int(float(s))
    except (ValueError, TypeError):
        return 0


def fmt(n) -> str:
    return f"{_son_qil(n):,}".replace(",", " ")


def stat_olish(chat_id) -> dict:
    """Sahifa va /balans uchun barcha ko'rsatkichlarni hisoblaydi."""
    bugun = datetime.date.today()
    oy_boshi = bugun.replace(day=1)
    hafta_boshi = bugun - datetime.timedelta(days=bugun.weekday())

    stat = {
        "umumiy_daromad": 0, "umumiy_harajat": 0,
        "oy_daromad": 0, "oy_harajat": 0,
        "hafta_balans": 0,
        "kategoriyalar": defaultdict(lambda: {"daromad": 0, "harajat": 0}),
        "jami_yozuvlar": 0,
    }
    with _qulf:
        yozuvlar = _yukla(chat_id)
    stat["jami_yozuvlar"] = len(yozuvlar)
    for y in yozuvlar:
        try:
            sana = datetime.date.fromisoformat(str(y["sana"])[:10])
            summa = _son_qil(y["summa"])
        except (ValueError, KeyError, TypeError):
            continue
        if y["turi"] == "Daromad":
            stat["umumiy_daromad"] += summa
        else:
            stat["umumiy_harajat"] += summa
        if sana >= oy_boshi:
            if y["turi"] == "Daromad":
                stat["oy_daromad"] += summa
            else:
                stat["oy_harajat"] += summa
            stat["kategoriyalar"][y["kategoriya"]]["daromad" if y["turi"] == "Daromad" else "harajat"] += summa
        if sana >= hafta_boshi:
            stat["hafta_balans"] += summa if y["turi"] == "Daromad" else -summa
    stat["kategoriyalar"] = dict(stat["kategoriyalar"])
    return stat


def balans_matni(chat_id) -> str:
    """/balans buyrug'i uchun matn."""
    stat = stat_olish(chat_id)
    fmt_l = lambda n: fmt(n)
    qatorlar = [
        f"🟢 Umumiy daromad: {fmt_l(stat['umumiy_daromad'])} so'm",
        f"🔴 Umumiy harajat: {fmt_l(stat['umumiy_harajat'])} so'm",
        f"💼 Joriy balans: {fmt_l(stat['umumiy_daromad'] - stat['umumiy_harajat'])} so'm",
        "",
        f"📅 Shu oy daromad: {fmt_l(stat['oy_daromad'])} so'm",
        f"📅 Shu oy harajat: {fmt_l(stat['oy_harajat'])} so'm",
        f"🗓 Shu hafta balans: {fmt_l(stat['hafta_balans'])} so'm",
    ]
    kat = []
    for nom, v in stat["kategoriyalar"].items():
        if v["daromad"]:
            kat.append(f"  🟢 {nom}: {fmt_l(v['daromad'])} so'm")
        if v["harajat"]:
            kat.append(f"  🔴 {nom}: {fmt_l(v['harajat'])} so'm")
    if kat:
        qatorlar.append("")
        qatorlar.append("📊 Shu oy kategoriyalar bo'yicha:")
        qatorlar.extend(kat)
    return "\n".join(qatorlar)


# --- Til sozlamalari (har bir foydalanuvchi uchun: "uz" yoki "ru") ---

USERS_JSON = os.path.join(DATA_JILD, "users.json")

DEFAULT_TIL = "uz"


def _users_yukla() -> dict:
    try:
        with open(USERS_JSON, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _users_saqla(users: dict):
    os.makedirs(DATA_JILD, exist_ok=True)
    with open(USERS_JSON, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)
    try:
        rel = os.path.relpath(USERS_JSON, _REPO_ROOT)
        gh_zaxira.fon_zaxira(
            rel,
            json.dumps(users, ensure_ascii=False, indent=2).encode("utf-8"),
            "Moliya: foydalanuvchi sozlamalari zaxiralandi",
        )
    except Exception:
        pass


def til_olish(chat_id) -> str:
    """Eski {"til": "uz"} ham, eski-oddiy "uz" (str) format ham moslashadi."""
    mavjud = _users_yukla().get(str(chat_id), {})
    til = mavjud.get("til") if isinstance(mavjud, dict) else mavjud
    return til if til in ("uz", "ru") else DEFAULT_TIL


def til_saqla(chat_id, til: str):
    """Tilni saqlaydi — user rejestri ma'lumotlarini (ism, sana...) yo'qotmaydi."""
    if til not in ("uz", "ru"):
        til = DEFAULT_TIL
    with _qulf:
        users = _users_yukla()
        mavjud = users.get(str(chat_id), {})
        if isinstance(mavjud, str):
            mavjud = {"til": mavjud}
        mavjud["til"] = til
        users[str(chat_id)] = mavjud
        _users_saqla(users)


# ============================ FOYDALANUVCHI REGISTRI ============================
# Har bir user to'liq saqlanadi: ID, ism, username, til, manba (bot/miniapp),
# birinchi ko'rilgan sana, oxirgi faollik. /foydalanuvchilar buyrug'i orqali
# bot egasi barcha userlarni yozuvlari bilan birga ko'rishi mumkin.

def user_olish(chat_id) -> dict:
    """User ma'lumotlari (eski {"til": ...} va eski-oddiy str format ham moslashadi)."""
    mavjud = _users_yukla().get(str(chat_id), {})
    if isinstance(mavjud, str):
        mavjud = {"til": mavjud}
    return dict(mavjud)


def user_faollik(chat_id, ism: str = "", username: str = "", manba: str = "bot"):
    """User registratsiyasi/yangilash. Bir kunda bir marta yozadi (spam yo'q).
    Qaytaradi: (profil, yangi_user) — yangi_user=True bo'lsa bu user
    birinchi marta ro'yxatdan o'tdi (bot egasiga xabar berish uchun)."""
    hozir_s = datetime.datetime.now(ZoneInfo("Asia/Tashkent")).isoformat(timespec="seconds")
    users = _users_yukla()
    mavjud = users.get(str(chat_id), {})
    if isinstance(mavjud, str):
        mavjud = {"til": mavjud}
    yangi_user = not mavjud.get("birinchi")
    o_zgar = False

    ism = (ism or "").strip()
    if ism and mavjud.get("ism") != ism:
        mavjud["ism"] = ism
        o_zgar = True
    un = (username or "").strip().lstrip("@")
    if un and mavjud.get("username", "") != un:
        mavjud["username"] = un
        o_zgar = True
    if not mavjud.get("birinchi"):
        mavjud["birinchi"] = hozir_s
        o_zgar = True
    if (mavjud.get("oxirgi") or "")[:10] != hozir_s[:10]:
        mavjud["oxirgi"] = hozir_s
        o_zgar = True
    if not mavjud.get("manba"):
        mavjud["manba"] = manba
        o_zgar = True

    if o_zgar:
        users[str(chat_id)] = mavjud
        _users_saqla(users)
    return mavjud, yangi_user


def foydalanuvchilar_royxati() -> list:
    """Registratsiyadan o'tgan barcha userlar + ularning hisob-kitobi."""
    users = _users_yukla()
    natija = []
    for chat_id, mavjud in sorted(users.items()):
        if isinstance(mavjud, str):
            mavjud = {"til": mavjud}
        yozuvlar = _yukla(chat_id)
        dar = sum(_son_qil(y.get("summa", 0)) for y in yozuvlar if y.get("turi") == "Daromad")
        har = sum(_son_qil(y.get("summa", 0)) for y in yozuvlar if y.get("turi") == "Harajat")
        natija.append({
            "chat_id": chat_id,
            "ism": mavjud.get("ism", ""),
            "username": mavjud.get("username", ""),
            "til": mavjud.get("til", DEFAULT_TIL),
            "birinchi": mavjud.get("birinchi", ""),
            "oxirgi": mavjud.get("oxirgi", ""),
            "manba": mavjud.get("manba", ""),
            "yozuvlar": len(yozuvlar),
            "daromad": dar,
            "harajat": har,
            "balans": dar - har,
        })
    return natija

