"""Google Sheets bilan ishlash: har bir foydalanuvchi o'z jadvaliga yozadi."""
import datetime
import json
import os
from collections import defaultdict

import gspread
from google.oauth2.service_account import Credentials

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

TRANZAKSIYA_VARAQ = "Tranzaksiyalar"
DASHBOARD_VARAQ = "Dashboard"
SARLAVHALAR = ["Sana", "Vaqt", "Turi", "Kategoriya", "Summa", "Izoh", "Asl matn"]

_client = None
_jadvallar = {}  # sheet_id -> gspread.Spreadsheet (kesh)


def _kredensiallar():
    global _client
    if _client is None:
        if os.path.exists("/etc/secrets/credentials.json"):
            creds_fayl = "/etc/secrets/credentials.json"
        else:
            creds_fayl = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
        creds = Credentials.from_service_account_file(creds_fayl, scopes=SCOPES)
        _client = gspread.authorize(creds)
    return _client


def xizmat_akkaunt_email() -> str:
    """credentials.json dagi service account email'ni qaytaradi (foydalanuvchilarga ulash uchun)."""
    if os.path.exists("/etc/secrets/credentials.json"):
        creds_fayl = "/etc/secrets/credentials.json"
    else:
        creds_fayl = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    with open(creds_fayl, encoding="utf-8") as f:
        return json.load(f).get("client_email", "(noma'lum)")


def _jadval_ol(sheet_id=None):
    """Berilgan sheet_id uchun jadvalni qaytaradi (kesh bilan)."""
    if not sheet_id:
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if sheet_id not in _jadvallar:
        _jadvallar[sheet_id] = _kredensiallar().open_by_key(sheet_id)
    return _jadvallar[sheet_id]


def jadval_ochiladimi(sheet_id: str) -> bool:
    """Foydalanuvchi jadvaliga bot kira olishini tekshiradi."""
    try:
        _kredensiallar().open_by_key(sheet_id)
        return True
    except Exception:
        return False


def yangi_jadvalni_tayyorla(sheet_id: str):
    """Yangi foydalanuvchi jadvaliga Tranzaksiyalar va Dashboard varaqlarini
    CHIROYLI DIZAYN bilan (KPI kartalar, grafiklar) yaratadi.
    setup_sheet.py'dagi to'liq UI quruvchidan foydalanadi."""
    from setup_sheet import toliq_tayyorla

    sheet = _jadval_ol(sheet_id)
    toliq_tayyorla(sheet)
    # keshni yangilaymiz
    _jadvallar.pop(sheet_id, None)


# --- Barcha funksiyalar endi sheet_id parametrini oladi (None bo'lsa .env'dagi jadval) ---

def tranzaksiya_qoshish(yozuv: dict, sheet_id=None):
    """Bitta tranzaksiyani 'Tranzaksiyalar' varagiga qator qilib qo'shadi."""
    sheet = _jadval_ol(sheet_id)
    ws = sheet.worksheet(TRANZAKSIYA_VARAQ)
    ws.append_row(
        [
            yozuv["sana"],
            yozuv["vaqt"],
            "Daromad" if yozuv["turi"] == "daromad" else "Harajat",
            yozuv["kategoriya"],
            yozuv["summa"],
            yozuv.get("izoh", ""),
            yozuv.get("original_matn", ""),
        ],
        value_input_option="USER_ENTERED",
    )


def barcha_yozuvlarni_olish(sheet_id=None) -> list:
    """'Tranzaksiyalar' varag'idagi barcha yozuvlarni (sarlavha bilan) qaytaradi."""
    sheet = _jadval_ol(sheet_id)
    ws = sheet.worksheet(TRANZAKSIYA_VARAQ)
    return ws.get_all_values()


def oxirgi_yozuvlarni_olish(soni: int = 5, sheet_id=None) -> list:
    """Oxirgi N yozuvni [(qator_raqami, [qiymatlar]), ...] ko'rinishida qaytaradi."""
    sheet = _jadval_ol(sheet_id)
    ws = sheet.worksheet(TRANZAKSIYA_VARAQ)
    barchasi = ws.get_all_values()
    natija = []
    for qator_raqami, qiymatlar in enumerate(barchasi, start=1):
        if qator_raqami == 1 or len(qiymatlar) < 5 or not qiymatlar[0]:
            continue  # sarlavha yoki bo'sh qator
        natija.append((qator_raqami, qiymatlar))
    return natija[-soni:]


def yozuvni_ochirish(qator_raqami: int, sheet_id=None):
    """Berilgan qatordagi yozuvni o'chiradi."""
    sheet = _jadval_ol(sheet_id)
    ws = sheet.worksheet(TRANZAKSIYA_VARAQ)
    ws.delete_rows(qator_raqami)


def yozuvni_yangilash(qator_raqami: int, qiymatlar: list, sheet_id=None):
    """Berilgan qatordagi yozuvni yangi qiymatlar bilan almashtiradi."""
    sheet = _jadval_ol(sheet_id)
    ws = sheet.worksheet(TRANZAKSIYA_VARAQ)
    ws.update(f"A{qator_raqami}:G{qator_raqami}", [qiymatlar],
              value_input_option="USER_ENTERED")


def tranzaksiyalarni_tozalash(sheet_id=None) -> int:
    """Barcha tranzaksiya yozuvlarini o'chiradi (sarlavha qoladi). O'chirilgan sonini qaytaradi."""
    sheet = _jadval_ol(sheet_id)
    ws = sheet.worksheet(TRANZAKSIYA_VARAQ)
    jami = len(ws.get_all_values())
    ochirilgan = max(jami - 1, 0)
    if ochirilgan:
        # delete_rows end_index ni INKLYUZIV oladi: 2-qatordan (2+son-1)-qatorgacha
        ws.delete_rows(2, 1 + ochirilgan)
    return ochirilgan


def dashboard_matnini_olish(sheet_id=None) -> str:
    """Hisobotni TO'G'RIDA Tranzaksiyalar ma'lumotlaridan hisoblaydi
    (Dashboard formulalari keshi eski qiymat qaytarishi mumkin bo'lgani uchun).
    Davr chegaralarini Dashboard'dagi Dan/Gacha kataklaridan o'qiydi."""
    import datetime
    from collections import defaultdict

    sheet = _jadval_ol(sheet_id)
    try:
        dash = sheet.worksheet(DASHBOARD_VARAQ)
    except gspread.WorksheetNotFound:
        dash = None

    # Dashboard'dagi filtr sanalarini o'qish (bo'lmasa — shu oy)
    bugun = datetime.date.today()
    oy_boshi = bugun.replace(day=1)
    hafta_boshi = bugun - datetime.timedelta(days=bugun.weekday())
    try:
        s1 = dash.get("B4")[0][0].strip()
        s2 = dash.get("D4")[0][0].strip()
        sana1 = datetime.date.fromisoformat(s1[:10]) if s1[:10].count("-") == 2 else oy_boshi
        sana2 = datetime.date.fromisoformat(s2[:10]) if s2[:10].count("-") == 2 else bugun
    except Exception:
        sana1, sana2 = oy_boshi, bugun

    def somga(v):
        """'3\xa0000\xa0000 so'm' / '3000000' kabi qiymatni songa aylantiradi."""
        if v is None:
            return 0
        s = str(v).replace('"', "").replace("so'm", "")
        s = s.replace("\xa0", "").replace(",", "").replace(" ", "").strip()
        try:
            return int(float(s))
        except (ValueError, TypeError):
            return 0

    def sanaga(v):
        try:
            return datetime.date.fromisoformat(str(v).strip()[:10])
        except (ValueError, TypeError):
            return None

    # Tranzaksiyalarni to'g'ridan-to'g'ri o'qib hisoblaymiz
    qatorlar = barcha_yozuvlarni_olish()[1:]
    umumiy_d, umumiy_h = 0, 0
    davr_d, davr_h = 0, 0
    oy_d, oy_h = 0, 0
    hafta_d, hafta_h = 0, 0
    kat_oy = defaultdict(lambda: {"daromad": 0, "harajat": 0})

    for r in qatorlar:
        if len(r) < 5:
            continue
        sana = sanaga(r[0])
        if sana is None:
            continue
        turi = str(r[2]).strip().lower()
        kat = str(r[3]).strip()
        summa = somga(r[4])
        if turi == "daromad":
            umumiy_d += summa
        elif turi == "harajat":
            umumiy_h += summa
        else:
            continue
        if sana1 <= sana <= sana2:
            if turi == "daromad":
                davr_d += summa
            else:
                davr_h += summa
        if sana >= oy_boshi:
            if turi == "daromad":
                oy_d += summa
            else:
                oy_h += summa
            kat_oy[kat]["daromad" if turi == "daromad" else "harajat"] += summa
        if sana >= hafta_boshi:
            if turi == "daromad":
                hafta_d += summa
            else:
                hafta_h += summa

    fmt = lambda n: f"{n:,}".replace(",", " ")
    qatorlar_out = [
        f"🎛 Tanlangan davr ({sana1.isoformat()} → {sana2.isoformat()}):",
        f"  🟢 Daromad: {fmt(davr_d)} so'm",
        f"  🔴 Harajat: {fmt(davr_h)} so'm",
        f"  ⚖️ Balans: {fmt(davr_d - davr_h)} so'm",
        "",
        f"🟢 Umumiy daromad: {fmt(umumiy_d)} so'm",
        f"🔴 Umumiy harajat: {fmt(umumiy_h)} so'm",
        f"💼 Joriy balans: {fmt(umumiy_d - umumiy_h)} so'm",
        "",
        f"📅 Shu oy daromad: {fmt(oy_d)} so'm",
        f"📅 Shu oy harajat: {fmt(oy_h)} so'm",
        f"🗓 Shu hafta balans: {fmt(hafta_d - hafta_h)} so'm",
    ]

    kategoriyalar = []
    for kat, v in kat_oy.items():
        if v["daromad"]:
            kategoriyalar.append(f"  🟢 {kat}: {fmt(v['daromad'])} so'm")
        if v["harajat"]:
            kategoriyalar.append(f"  🔴 {kat}: {fmt(v['harajat'])} so'm")
    if kategoriyalar:
        qatorlar_out.append("")
        qatorlar_out.append("📊 Shu oy kategoriyalar bo'yicha:")
        qatorlar_out.extend(kategoriyalar)

    return "\n".join(qatorlar_out)
