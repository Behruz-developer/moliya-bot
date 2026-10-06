"""
Har bir foydalanuvchining ma'lumotlari alohida JSON faylda saqlanadi:
data/<chat_id>.json — Google Sheets kerak emas!
"""
import datetime
import json
import os
import threading
from collections import defaultdict
from zoneinfo import ZoneInfo

DATA_JILD = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
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
    with open(_fayl_yuli(chat_id), "w", encoding="utf-8") as f:
        json.dump(yozuvlar, f, ensure_ascii=False, indent=2)


def yozuv_qosh(chat_id, natija: dict):
    """AI natijasini (turi, kategoriya, summa...) shu user jadvaliga qo'shadi."""
    hozir = datetime.datetime.now(ZoneInfo("Asia/Tashkent"))
    yozuv = {
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


def til_olish(chat_id) -> str:
    til = _users_yukla().get(str(chat_id), {}).get("til", DEFAULT_TIL)
    return til if til in ("uz", "ru") else DEFAULT_TIL


def til_saqla(chat_id, til: str):
    if til not in ("uz", "ru"):
        til = DEFAULT_TIL
    with _qulf:
        users = _users_yukla()
        users[str(chat_id)] = {"til": til}
        _users_saqla(users)

