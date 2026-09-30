"""
Bu skriptni FAQAT BIR MARTA ishlatasiz — Google Sheet ichida kerakli
varaqlarni, sarlavhalarni, avtomatik formulalar va CHIROYLI DIZAYNNI
yaratib beradi (KPI kartalar, kategoriyalar breakdown, shartli ranglar).

Ishlatish: python setup_sheet.py
"""
import os
import time
from dotenv import load_dotenv
import gspread
from google.oauth2.service_account import Credentials

load_dotenv()

# 429 (quota) xatolarida avtomatik kutib qayta urinish
_http_request = gspread.http_client.HTTPClient.request
def _retry_request(self, *args, **kwargs):
    for urinish in range(6):
        try:
            return _http_request(self, *args, **kwargs)
        except gspread.exceptions.APIError as e:
            if "429" in str(e) and urinish < 5:
                time.sleep(25)
                continue
            raise
gspread.http_client.HTTPClient.request = _retry_request

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

T = "Tranzaksiyalar"

# Ranglar
RANG_TITLE_BG = {"red": 0.13, "green": 0.38, "blue": 0.28}      # to'q yashil
RANG_TITLE_FG = {"red": 1, "green": 1, "blue": 1}
RANG_YASHIL_BG = {"red": 0.85, "green": 0.95, "blue": 0.85}     # och yashil
RANG_QIZIL_BG = {"red": 0.99, "green": 0.89, "blue": 0.89}      # och qizil
RANG_KOK_BG = {"red": 0.85, "green": 0.91, "blue": 0.99}        # och ko'k
RANG_SARLAVHA_BG = {"red": 0.20, "green": 0.29, "blue": 0.37}   # to'q ko'k-kulrang
RANG_SEKTION_BG = {"red": 0.93, "green": 0.93, "blue": 0.93}    # kulrang
RANG_JAMI_BG = {"red": 0.98, "green": 0.92, "blue": 0.73}       # och sariq
SUMMA_FORMAT = '#,##0" so\'m"'


def _rang_format(bg=None, fg=None, bold=None, size=None, halign=None):
    fmt = {}
    if bg:
        fmt["backgroundColor"] = bg
    if fg or bold is not None or size is not None:
        tf = {}
        if fg:
            tf["foregroundColor"] = fg
        if bold is not None:
            tf["bold"] = bold
        if size is not None:
            tf["fontSize"] = size
        fmt["textFormat"] = tf
    if halign:
        fmt["horizontalAlignment"] = halign
    return fmt


def _kpi_karta(dash, diapazon_label, diapazon_qiymat, matn, formula, bg):
    """Ikkita birlashtirilgan katakdan iborat KPI karta yaratadi."""
    dash.merge_cells(diapazon_label)
    dash.merge_cells(diapazon_qiymat)
    dash.update(diapazon_label, [[matn]], value_input_option="RAW")
    dash.update(diapazon_qiymat, [[formula]], value_input_option="USER_ENTERED")
    dash.format(diapazon_label, _rang_format(bg=bg, bold=True, size=10))
    dash.format(diapazon_qiymat, _rang_format(bg=bg, bold=True, size=14, halign="CENTER"))
    dash.format(diapazon_qiymat, {"numberFormat": {"type": "NUMBER", "pattern": SUMMA_FORMAT}})


def asosiy():
    from categories import DAROMAD_KATEGORIYALARI, HARAJAT_KATEGORIYALARI

    creds_fayl = os.getenv("GOOGLE_CREDENTIALS_FILE", "credentials.json")
    creds = Credentials.from_service_account_file(creds_fayl, scopes=SCOPES)
    client = gspread.authorize(creds)
    sheet = client.open_by_key(os.getenv("GOOGLE_SHEET_ID"))

    # --- 1. Tranzaksiyalar varag'i ---
    try:
        tranz = sheet.worksheet("Tranzaksiyalar")
    except gspread.WorksheetNotFound:
        tranz = sheet.add_worksheet(title="Tranzaksiyalar", rows=2000, cols=10)

    tranz.update(
        "A1:G1",
        [["Sana", "Vaqt", "Turi", "Kategoriya", "Summa", "Izoh", "Original matn"]],
    )
    tranz.format(
        "A1:G1",
        _rang_format(bg=RANG_SARLAVHA_BG, fg=RANG_TITLE_FG, bold=True, halign="CENTER"),
    )
    tranz.format("A2:A2000", {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"}})
    tranz.format("B2:B2000", {"numberFormat": {"type": "TIME", "pattern": "HH:mm"}})
    tranz.format("E2:E2000", {"numberFormat": {"type": "NUMBER", "pattern": SUMMA_FORMAT}})
    tranz.format("C2:C2000", {"horizontalAlignment": "CENTER"})
    tranz.freeze(rows=1)
    tranz.columns_auto_resize(0, 7)

    # Shartli formatlash: Daromad -> yashil, Harajat -> qizil
    requests = []
    for matn, bg, fg in [
        ("Daromad", RANG_YASHIL_BG, {"red": 0.0, "green": 0.5, "blue": 0.0}),
        ("Harajat", RANG_QIZIL_BG, {"red": 0.75, "green": 0.0, "blue": 0.0}),
    ]:
        requests.append({
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{
                        "sheetId": tranz.id,
                        "startRowIndex": 1, "endRowIndex": 2000,
                        "startColumnIndex": 0, "endColumnIndex": 7,
                    }],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": matn}]},
                        "format": {"backgroundColor": bg, "textFormat": {"foregroundColor": fg}},
                    },
                },
                "index": len(requests),
            }
        })
    sheet.batch_update({"requests": requests})

    # Tranzaksiyalar uchun navbatlashib bo'yash (banding) va filtr tugmalari
    banding = {
        "addBanding": {
            "bandedRange": {
                "bandedRangeId": 1,
                "range": {"sheetId": tranz.id, "startRowIndex": 1, "endRowIndex": 2000,
                          "startColumnIndex": 0, "endColumnIndex": 7},
                "rowProperties": {
                    "headerBandSize": 1,
                    "firstBandColor": {"red": 0.96, "green": 0.97, "blue": 0.98},
                    "secondBandColor": {"red": 0.99, "green": 0.99, "blue": 1},
                },
            }
        }
    }
    basic_filter = {
        "setBasicFilter": {
            "filter": {
                "range": {"sheetId": tranz.id, "startRowIndex": 0, "endRowIndex": 2000,
                          "startColumnIndex": 0, "endColumnIndex": 7},
            }
        }
    }
    try:
        sheet.batch_update({"requests": [banding, basic_filter]})
    except Exception as e:
        logger_warning = print
        logger_warning(f"Banding/filter: {e} (already applied?)")

    # >>> DASHBOARD QISMI <<<
    _dashboard_yarat(sheet, dash_title="Dashboard",
                     daromad_kat=DAROMAD_KATEGORIYALARI,
                     harajat_kat=HARAJAT_KATEGORIYALARI)
    _dashboard_yarat(sheet, dash_title="Dashboard",
                     daromad_kat=DAROMAD_KATEGORIYALARI,
                     harajat_kat=HARAJAT_KATEGORIYALARI)

    print("Tayyor! Dashboard chiroyli dizayn bilan sozlandi ✨")


def _dashboard_yarat(sheet, dash_title, daromad_kat, harajat_kat):
    """Dashboard varag'ini KPI kartalar va kategoriyalar breakdown bilan yaratadi."""
    try:
        dash = sheet.worksheet(dash_title)
    except gspread.WorksheetNotFound:
        dash = sheet.add_worksheet(title=dash_title, rows=40, cols=8)
    dash.resize(rows=40, cols=8)

    # Eski ma'lumot va merge'larni tozalash
    sheet.batch_update({"requests": [{
        "unmergeCells": {"range": {"sheetId": dash.id, "startRowIndex": 0,
                                   "endRowIndex": 40, "startColumnIndex": 0,
                                   "endColumnIndex": 8}}
    }]})
    dash.clear()

    # Sarlavha
    dash.merge_cells("A1:F1")
    dash.update("A1", [["💰 MOLIYA DASHBOARD"]], value_input_option="RAW")
    dash.format("A1", _rang_format(bg=RANG_TITLE_BG, fg=RANG_TITLE_FG, bold=True, size=16, halign="CENTER"))
    dash.format("A1", {"verticalAlignment": "MIDDLE"})

    # --- Filtr: Dan / Gacha (user o'zi o'zgartirishi mumkin) ---
    dash.merge_cells("A3:F3")
    dash.update("A3", [["🎛 TANLANGAN DAVR FILTRI — sanalarni o'zgartiring, kartalar avtomatik hisoblanadi"]],
                value_input_option="RAW")
    dash.format("A3", _rang_format(bg=RANG_SEKTION_BG, bold=True, size=11))

    dash.update("A4", [["Dan:"]], value_input_option="RAW")
    dash.update("C4", [["Gacha:"]], value_input_option="RAW")
    # Default: shu oy boshi -> bugun
    dash.update("B4", [["=EOMONTH(TODAY();-1)+1"]], value_input_option="USER_ENTERED")
    dash.update("D4", [["=TODAY()"]], value_input_option="USER_ENTERED")
    dash.format("A4:C4", {"textFormat": {"bold": True}, "horizontalAlignment": "RIGHT"})
    dash.format("B4", {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"},
                       "backgroundColor": RANG_JAMI_BG, "horizontalAlignment": "CENTER"})
    dash.format("D4", {"numberFormat": {"type": "DATE", "pattern": "yyyy-mm-dd"},
                       "backgroundColor": RANG_JAMI_BG, "horizontalAlignment": "CENTER"})
    # Sana validatsiyasi (oddiy: date-after 2000-01-01)
    sheet.batch_update({"requests": [{
        "setDataValidation": {
            "range": {"sheetId": dash.id, "startRowIndex": 3, "endRowIndex": 4,
                      "startColumnIndex": 1, "endColumnIndex": 2},
            "rule": {"condition": {"type": "DATE_AFTER",
                                   "values": [{"userEnteredValue": "2000-01-01"}]},
                     "inputMessage": "Sanani yyyy-mm-dd ko'rinishida kiriting", "strict": False},
        }
    }]})

    # --- Tanlangan davr KPI kartalari (B4 va D4 ga bog'langan) ---
    _kpi_karta(dash, "A6:B6", "A7:B7", "🟢 DAVR DAROMADI",
               f'=SUMIFS({T}!E2:E2000;{T}!C2:C2000;"Daromad";{T}!A2:A2000;">="&B4;{T}!A2:A2000;"<="&D4)',
               RANG_YASHIL_BG)
    _kpi_karta(dash, "C6:D6", "C7:D7", "🔴 DAVR HARAJATI",
               f'=SUMIFS({T}!E2:E2000;{T}!C2:C2000;"Harajat";{T}!A2:A2000;">="&B4;{T}!A2:A2000;"<="&D4)',
               RANG_QIZIL_BG)
    _kpi_karta(dash, "E6:F6", "E7:F7", "⚖️ DAVR BALANSI", "=A7-C7", RANG_KOK_BG)

    # --- Umumiy KPI kartalar ---
    _kpi_karta(dash, "A9:B9", "A10:B10", "🟢 UMUMIY DAROMAD",
               f'=SUMIF({T}!C2:C2000;"Daromad";{T}!E2:E2000)', RANG_YASHIL_BG)
    _kpi_karta(dash, "C9:D9", "C10:D10", "🔴 UMUMIY HARAJAT",
               f'=SUMIF({T}!C2:C2000;"Harajat";{T}!E2:E2000)', RANG_QIZIL_BG)
    _kpi_karta(dash, "E9:F9", "E10:F10", "💼 JORIY BALANS", "=A10-C10", RANG_KOK_BG)

    # --- Oy / hafta KPI kartalar ---
    oy_boshi = 'TEXT(EOMONTH(TODAY();-1)+1;"yyyy-mm-dd")'
    hafta_boshi = 'TEXT(TODAY()-WEEKDAY(TODAY();2)+1;"yyyy-mm-dd")'
    _kpi_karta(dash, "A12:B12", "A13:B13", "📅 SHU OY DAROMAD",
               f'=SUMIFS({T}!E2:E2000;{T}!C2:C2000;"Daromad";{T}!A2:A2000;">="&{oy_boshi})',
               RANG_YASHIL_BG)
    _kpi_karta(dash, "C12:D12", "C13:D13", "📅 SHU OY HARAJAT",
               f'=SUMIFS({T}!E2:E2000;{T}!C2:C2000;"Harajat";{T}!A2:A2000;">="&{oy_boshi})',
               RANG_QIZIL_BG)
    _kpi_karta(
        dash, "E12:F12", "E13:F13", "🗓 SHU HAFTA BALANS",
        f'=SUMIFS({T}!E2:E2000;{T}!C2:C2000;"Daromad";{T}!A2:A2000;">="&{hafta_boshi})'
        f'-SUMIFS({T}!E2:E2000;{T}!C2:C2000;"Harajat";{T}!A2:A2000;">="&{hafta_boshi})',
        RANG_KOK_BG,
    )

    # --- Kategoriyalar breakdown (shu oy) ---
    dash.merge_cells("A15:C15")
    dash.update("A15", [["📊 KATEGORIYALAR BO'YICHA (SHU OY)"]], value_input_option="RAW")
    dash.format("A15", _rang_format(bg=RANG_SEKTION_BG, bold=True, size=12))

    oy_boshi_f = 'TEXT(EOMONTH(TODAY();-1)+1;"yyyy-mm-dd")'
    qatorlar = [["Kategoriya", "Daromad", "Harajat"]]
    for kat in daromad_kat:
        qatorlar.append([kat,
            f'=SUMIFS({T}!E2:E2000;{T}!C2:C2000;"Daromad";{T}!D2:D2000;"{kat}";{T}!A2:A2000;">="&{oy_boshi_f})',
            ""])
    for kat in harajat_kat:
        qatorlar.append([kat,
            "",
            f'=SUMIFS({T}!E2:E2000;{T}!C2:C2000;"Harajat";{T}!D2:D2000;"{kat}";{T}!A2:A2000;">="&{oy_boshi_f})'])

    boshlanish = 16
    oxirgi = boshlanish + len(qatorlar)  # jami qatori ham shu ichida
    dash.update(f"A{boshlanish}:C{oxirgi - 1}", qatorlar, value_input_option="USER_ENTERED")

    # JAMI qatori
    jami = oxirgi
    dash.update(f"A{jami}:C{jami}",
                [["JAMI", f"=SUM(B{boshlanish + 1}:B{jami - 1})",
                  f"=SUM(C{boshlanish + 1}:C{jami - 1})"]],
                value_input_option="USER_ENTERED")

    # Breakdown formatlash
    dash.format(f"A{boshlanish}:C{boshlanish}",
                _rang_format(bg=RANG_SARLAVHA_BG, fg=RANG_TITLE_FG, bold=True, halign="CENTER"))
    dash.format(f"A{boshlanish + 1}:A{jami}", {"textFormat": {"bold": True}})
    dash.format(f"B{boshlanish + 1}:C{jami}",
                {"numberFormat": {"type": "NUMBER", "pattern": SUMMA_FORMAT}})
    dash.format(f"A{jami}:C{jami}", _rang_format(bg=RANG_JAMI_BG, bold=True))

    dash.columns_auto_resize(0, 3)

    # --- Grafiklar ---
    _grafiklar_qosh(sheet, dash.id, boshlanish, jami)


def _grafiklar_qosh(sheet, dash_sheet_id, boshlanish, jami):
    """Dashboard'ga doira va ustunli grafiklar qo'shadi."""
    kat_range = {
        "sheetId": dash_sheet_id,
        "startRowIndex": boshlanish, "endRowIndex": jami,
        "startColumnIndex": 0, "endColumnIndex": 1,
    }
    daromad_range = {
        "sheetId": dash_sheet_id,
        "startRowIndex": boshlanish, "endRowIndex": jami,
        "startColumnIndex": 1, "endColumnIndex": 2,
    }
    harajat_range = {
        "sheetId": dash_sheet_id,
        "startRowIndex": boshlanish, "endRowIndex": jami,
        "startColumnIndex": 2, "endColumnIndex": 3,
    }

    def rang(num):
        return {"red": (num >> 16 & 255) / 255,
                "green": (num >> 8 & 255) / 255,
                "blue": (num & 255) / 255}

    ranglar = [0x2E7D32, 0xC62828, 0x1565C0, 0xF9A825, 0x6A1B9A,
               0x00838F, 0xEF6C00, 0x4527A0, 0x2E7D32, 0xAD1457,
               0x00695C, 0x9E9D24, 0x5D4037, 0x0277BD, 0xB71C1C]

    kat_sr = {"sourceRange": {"sources": [kat_range]}}
    pie_series = {"sourceRange": {"sources": [harajat_range]}}
    pie_spec = {
        "title": "🥧 Harajatlar tuzilishi (shu oy)",
        "pieChart": {
            "domain": kat_sr,
            "pieHole": 0.45,
            "series": pie_series,
            "legendPosition": "RIGHT_LEGEND",
        },
    }

    col_spec = {
        "title": "📊 Daromad vs Harajat (kategoriyalar bo'yicha, shu oy)",
        "basicChart": {
            "chartType": "COLUMN",
            "legendPosition": "BOTTOM_LEGEND",
            "domains": [{"domain": {"sourceRange": {"sources": [kat_range]}}}],
            "series": [
                {"series": {"sourceRange": {"sources": [daromad_range]}}, "targetAxis": "LEFT_AXIS",
                 "color": rang(ranglar[0])},
                {"series": {"sourceRange": {"sources": [harajat_range]}}, "targetAxis": "LEFT_AXIS",
                 "color": rang(ranglar[1])},
            ],
            "headerCount": 1,
            "axis": [
                {"position": "BOTTOM_AXIS", "title": "Kategoriya"},
                {"position": "LEFT_AXIS", "title": "Summa (so'm)"},
            ],
        },
    }

    requests = [
        {"updateChartSpec": {
            "chartId": 101,
            "spec": pie_spec,
        }},
        {"updateChartSpec": {
            "chartId": 102,
            "spec": col_spec,
        }},
    ]
    try:
        sheet.batch_update({"requests": requests})
    except Exception:
        # Grafik mavjud bo'lmasa — yangi yaratamiz
        requests = [
            {"addChart": {"chart": {
                "chartId": 101,
                "spec": pie_spec,
                "position": {"overlayPosition": {
                    "anchorCell": {"sheetId": dash_sheet_id, "rowIndex": 15, "columnIndex": 4},
                    "offsetXPixels": 10, "offsetYPixels": 10,
                    "widthPixels": 520, "heightPixels": 300,
                }},
            }}},
            {"addChart": {"chart": {
                "chartId": 102,
                "spec": col_spec,
                "position": {"overlayPosition": {
                    "anchorCell": {"sheetId": dash_sheet_id, "rowIndex": 31, "columnIndex": 4},
                    "offsetXPixels": 10, "offsetYPixels": 10,
                    "widthPixels": 520, "heightPixels": 320,
                }},
            }}},
        ]
        sheet.batch_update({"requests": requests})


if __name__ == "__main__":
    asosiy()
