"""
Moliya bot — Telegram orqali matn/ovozli xabarlarni qabul qilib,
AI bilan tahlil qiladi va har bir foydalanuvchining JSON fayliga yozadi.
Ikki til: o'zbekcha va ruscha (boshida tanlanadi, /til bilan o'zgartiriladi).
"""
# Render'da uxlamasligi uchun keep-alive server (lokalda flask bo'lmasa — o'tkazib yuboriladi)
try:
    from keep_alive import keep_alive
    keep_alive()
except ImportError:
    pass

import os
import io
import re
import time
import datetime
import tempfile
import logging

import httpx
from dotenv import load_dotenv
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    MenuButtonWebApp,
    WebAppInfo,
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)

from ai_parser import matnni_tahlil_qil, ovozni_tahlil_qil
import data_store
import xlsx_yoz

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# --- Har bir foydalanuvchiga alohida shaxsiy sahifa (Google Sheets kerak emas!) ---
BASE_URL = os.getenv("PUBLIC_URL", os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")).rstrip("/")


MINIAPP_URL = f"{BASE_URL}/app"

# Bot egasi (env'da OWNER_ID bo'lsa — u; yo'qsa default ID)
OWNER_ID = os.getenv("OWNER_ID", "1144941995").strip()


def _sahifa_link(chat_id) -> str:
    return f"{BASE_URL}/u/{chat_id}"


# ============================ TARJIMALAR (uz / ru) ============================

T = {
    "uz": {
        "salom_tanlash": "Assalomu alaykum! 👋\nIltimos, tilni tanlang 👇",
        "salom_tanlash_ru": "Ассалому алайкум! 👋\nПожалуйста, выберите язык 👇",
        "til_uz_tugma": "🇺🇿 O'zbekcha",
        "til_ru_tugma": "🇷🇺 Русский",
        "til_saqlandi": "✅ Til saqlandi: o'zbekcha",
"menu_tanlangan": (
    "🎉 Bot ishga tayyor!\n\n"
    "📝 Shunchaki yozing yoki 🎤 ovozli xabar yuboring:\n"
    "• “Bugun 4 million oylik oldim”\n"
    "• “Bozorga 150 ming sarfladim”\n\n"
    "Bot summa, kategoriya va turini o‘zi aniqlaydi.\n\n"
    "📊 /balans — hisobot\n"
    "🕓 /oxirgi — oxirgi yozuvlar\n"
    "📥 /eksport — Excel fayl\n"
    "🧹 /tozalash — barcha yozuvlarni o‘chirish\n"
    "🔗 /sahifa — moliya ilovasi\n"
    "🌐 /til — tilni o‘zgartirish\n\n"
    "💡 Barcha funksiyalar pastdagi menyuda ham mavjud."
),
        "balans_sarlavha": "📊 Hisobotingiz:",
        "balans_xato": "❌ Hisobotni olishda xatolik yuz berdi. Birozdan so'ng qaytadan urinib ko'ring.",
        "umumiy_daromad": "🟢 Umumiy daromad",
        "umumiy_harajat": "🔴 Umumiy harajat",
        "joriy_balans": "💼 Joriy balans",
        "oy_daromad": "📅 Shu oy daromad",
        "oy_harajat": "📅 Shu oy harajat",
        "hafta_balans": "🗓 Shu hafta balans",
        "kat_sarlavha": "📊 Shu oy kategoriyalar bo'yicha:",
        "som": "so'm",
        "qoshilmadi": (
            "Xabaringizdan moliyaviy ma'lumot topa olmadim 🤔\n"
            "Masalan shunday yozib ko'ring: \"Bugun 4 million oylik oldim\""
        ),
        "qoshilmadi_tuzatish": (
            "Xabaringizdan moliyaviy ma'lumot topa olmadim 🤔 "
            "Qaytadan yozing yoki /tuzatish_bekor bilan bekor qiling."
        ),
        "daromad_belgi": "🟢 Daromad",
        "harajat_belgi": "🔴 Harajat",
        "qoshildi": "qo'shildi ✅",
        "summa_lbl": "Summa",
        "kategoriya_lbl": "Kategoriya",
        "izoh_lbl": "Izoh",
        "tuzatildi": "✏️ Yozuv tuzatildi ✅",
        "eksport_tayyorlanmoqda": "⏳ Ma'lumotlar tayyorlanmoqda...",
        "eksport_bosh": "📭 Hozircha hech qanday yozuv yo'q.",
        "eksport_topildi": "📦 {n} ta yozuv topildi — fayl yuborilmoqda...",
        "eksport_caption": "📄 Barcha ma'lumotlaringiz ({n} ta yozuv)\nExcel yoki boshqa dasturda ochishingiz mumkin.",
        "eksport_xato": "❌ Fayl tayyorlashda xatolik yuz berdi. Birozdan so'ng qaytadan urinib ko'ring.",
        "tozalash_ogohlantirish": (
            "⚠️ DIQQAT!\n\nBu amal SIZNING BARCHA yozuvlaringizni "
            "o'chiradi va QAYTARIB BO'LMAYDI.\n\nIshonchingiz komilmi?"
        ),
        "tozalash_ha": "✅ Ha, o'chirish",
        "bekor_tugma": "❌ Bekor qilish",
        "tozalash_bekor": "❌ Bekor qilindi — hech narsa o'chirilmadi.",
        "tozalash_ochilmoqda": "⏳ Yozuvlar o'chirilmoqda...",
        "tozalash_ok": "🧹 {n} ta yozuv o'chirildi ✅",
        "oxirgi_bosh": "📭 Hozircha yozuv yo'q.",
        "ochirish_tugma": "🗑 O'chirish",
        "tuzatish_tugma": "✏️ Tuzatish",
        "oxirgi_hint": "👆 Yuqoridagi yozuvlardan birini o'chirish yoki tuzatish mumkin.",
        "oxirgi_xato": "❌ Yozuvlarni o'qishda xatolik yuz berdi.",
        "topilmadi_qayta": "❌ Yozuv topilmadi — /oxirgi ni qayta ishga tushiring.",
        "ochirish_soraladi": "⚠️ Bu yozuvni o'chirishga ishonchingiz komilmi?",
        "ochirildi": "🗑 Yozuv o'chirildi ✅",
        "ochirish_xato": "❌ O'chirishda xatolik yuz berdi.",
        "ochirish_bekor_ok": "❌ Bekor qilindi — yozuv joyida qoldi.",
        "tuzatish_soraladi": (
            "✏️ Tuzatish: endi to'g'ri xabarni oddiy tilda yozib yuboring.\n"
            "Masalan: \"Bozorga 200 ming sarfladim\"\n\n"
            "Bot uni yangi yozuv sifatida tahlil qilib, shu yozuvni almashtiradi.\n"
            "(Bekor qilish uchun: /tuzatish_bekor)"
        ),
        "tuzatish_bekor_ok": "❌ Tuzatish bekor qilindi.",
        "tuzatish_xato": "❌ Tuzatishda xatolik yuz berdi. Qaytadan urinib ko'ring yoki /tuzatish_bekor.",
        "sahifa_xabar": (
            "📊 Sizning shaxsiy moliya ilovangiz — balans, tahlil va "
            "barcha yozuvlar bir joyda:"
        ),
        "sahifa_tugma": "📊 Ilovani ochish",
        "hisobot_tugma": "📊 Hisobotni ko'rish",
        "menyu_balans": "📊 Balansni ko'rish",
        "menyu_oxirgi": "🕓 Oxirgi yozuvlar",
        "menyu_fayl": "📥 Ma'lumotlarni faylda olish",
        "menyu_tozalash": "🧹 Barcha yozuvlarni tozalash",
        "menyu_app": "📊 Moliya ilovasi",
        "menyu_placeholder": "Yozing yoki tugmani tanlang...",
        "ovoz_xato": "❌ Ovozli xabarni qayta ishlashda xatolik yuz berdi. Birozdan so'ng qaytadan urinib ko'ring.",
        "matn_xato": "❌ Xabaringizni qayta ishlashda xatolik yuz berdi. Birozdan so'ng qaytadan urinib ko'ring.",
        "eshitdim": "🎙 Eshitdim: \"{matn}\"",
        "til_cmd_xabar": "🌐 Tilni tanlang / Выберите язык:",
        "hisobot_sarlavha": "📊 Hisobot: {davr}",
        "hisobot_bosh": "📭 Bu davr uchun yozuv topilmadi.",
        "davr_bugun": "Bugun", "davr_hafta": "Oxirgi 7 kun",
        "davr_oy": "Shu oy", "davr_yil": "Shu yil", "davr_hammasi": "Barcha davr",
        "his_daromad": "🟢 Daromad", "his_harajat": "🔴 Xarajat",
        "his_balans": "💼 Balans", "his_soni": "🔢 Yozuvlar soni: {n} ta",
        "his_kat": "📂 Kategoriyalar bo'yicha:",
        "his_takror": "⚠️ Xuddi shunday yozuv hozirgina qo'shilgan — takroriy xabar saqlanmadi.",
        "id_mening": "🆔 Sizning ID raqamingiz:",
        "id_username": "👤 Username:",
        "fo_sarlavha": "👥 Ro'yxatdan o'tgan foydalanuvchilar ({n} ta):",
        "fo_faqt": "⛔ Bu buyruq faqat bot egasi uchun.",
        "fo_yozuvlar": "🧾",
        "fo_birinchi": "📅",
    },
    "ru": {
        "salom_tanlash": "Ассалому алайкум! 👋\nПожалуйста, выберите язык 👇",
        "salom_tanlash_ru": "Assalomu alaykum! 👋\nIltimos, tilni tanlang 👇",
        "til_uz_tugma": "🇺🇿 O'zbekcha",
        "til_ru_tugma": "🇷🇺 Русский",
        "til_saqlandi": "✅ Язык сохранён: русский",
        "menu_tanlangan": (
    "🎉 Бот готов к работе!\n\n"
    "📝 Просто напишите или отправьте 🎤 голосовое сообщение:\n"
    "• “Сегодня получил зарплату 4 миллиона”\n"
    "• “Потратил 150 тысяч на базаре”\n\n"
    "Бот сам определит сумму, категорию и тип операции.\n\n"
    "📊 /balans — отчёт\n"
    "🕓 /oxirgi — последние записи\n"
    "📥 /eksport — Excel-файл\n"
    "🧹 /tozalash — удалить все записи\n"
    "🔗 /sahifa — финансовое приложение\n"
    "🌐 /til — изменить язык\n\n"
    "💡 Все функции также доступны в меню ниже."
),
        "balans_sarlavha": "📊 Ваш отчёт:",
        "balans_xato": "❌ Ошибка при получении отчёта. Попробуйте позже.",
        "umumiy_daromad": "🟢 Общий доход",
        "umumiy_harajat": "🔴 Общий расход",
        "joriy_balans": "💼 Текущий баланс",
        "oy_daromad": "📅 Доход за этот месяц",
        "oy_harajat": "📅 Расход за этот месяц",
        "hafta_balans": "🗓 Баланс за эту неделю",
        "kat_sarlavha": "📊 По категориям за этот месяц:",
        "som": "сум",
        "qoshilmadi": (
            "Не нашёл финансовой информации в вашем сообщении 🤔\n"
            "Например, напишите так: \"Сегодня получил 4 миллиона зарплаты\""
        ),
        "qoshilmadi_tuzatish": (
            "Не нашёл финансовой информации в вашем сообщении 🤔 "
            "Напишите заново или отмените командой /tuzatish_bekor."
        ),
        "daromad_belgi": "🟢 Доход",
        "harajat_belgi": "🔴 Расход",
        "qoshildi": "добавлено ✅",
        "summa_lbl": "Сумма",
        "kategoriya_lbl": "Категория",
        "izoh_lbl": "Комментарий",
        "tuzatildi": "✏️ Запись исправлена ✅",
        "eksport_tayyorlanmoqda": "⏳ Готовим данные...",
        "eksport_bosh": "📭 Пока нет ни одной записи.",
        "eksport_topildi": "📦 Найдено записей: {n} — отправляю файл...",
        "eksport_caption": "📄 Все ваши данные ({n} записей)\nМожно открыть в Excel или другой программе.",
        "eksport_xato": "❌ Ошибка при создании файла. Попробуйте позже.",
        "tozalash_ogohlantirish": (
            "⚠️ ВНИМАНИЕ!\n\nЭто действие удалит ВСЕ ваши записи, "
            "и их НЕЛЬЗЯ БУДЕТ ВОССТАНОВИТЬ.\n\nВы уверены?"
        ),
        "tozalash_ha": "✅ Да, удалить",
        "bekor_tugma": "❌ Отмена",
        "tozalash_bekor": "❌ Отменено — ничего не удалено.",
        "tozalash_ochilmoqda": "⏳ Удаляем записи...",
        "tozalash_ok": "🧹 Удалено записей: {n} ✅",
        "oxirgi_bosh": "📭 Пока нет ни одной записи.",
        "ochirish_tugma": "🗑 Удалить",
        "tuzatish_tugma": "✏️ Исправить",
        "oxirgi_hint": "👆 Одну из записей выше можно удалить или исправить.",
        "oxirgi_xato": "❌ Ошибка при чтении записей.",
        "topilmadi_qayta": "❌ Запись не найдена — запустите /oxirgi заново.",
        "ochirish_soraladi": "⚠️ Вы уверены, что хотите удалить эту запись?",
        "ochirildi": "🗑 Запись удалена ✅",
        "ochirish_xato": "❌ Ошибка при удалении.",
        "ochirish_bekor_ok": "❌ Отменено — запись осталась на месте.",
        "tuzatish_soraladi": (
            "✏️ Исправление: теперь напишите правильное сообщение обычным языком.\n"
            "Например: \"Потратил 200 тысяч на рынок\"\n\n"
            "Бот проанализирует его и заменит эту запись.\n"
            "(Отмена: /tuzatish_bekor)"
        ),
        "tuzatish_bekor_ok": "❌ Исправление отменено.",
        "tuzatish_xato": "❌ Ошибка при исправлении. Попробуйте снова или /tuzatish_bekor.",
        "sahifa_xabar": (
            "📊 Ваше личное приложение — баланс, аналитика и все записи "
            "в одном месте:"
        ),
        "sahifa_tugma": "📊 Открыть приложение",
        "hisobot_tugma": "📊 Посмотреть отчёт",
        "menyu_balans": "📊 Баланс",
        "menyu_oxirgi": "🕓 Последние записи",
        "menyu_fayl": "📥 Скачать данные файлом",
        "menyu_tozalash": "🧹 Очистить все записи",
        "menyu_app": "📊 Финансы",
        "menyu_placeholder": "Напишите или выберите кнопку...",
        "ovoz_xato": "❌ Ошибка при обработке голосового сообщения. Попробуйте позже.",
        "matn_xato": "❌ Ошибка при обработке сообщения. Попробуйте позже.",
        "eshitdim": "🎙 Я услышал: \"{matn}\"",
        "til_cmd_xabar": "🌐 Tilni tanlang / Выберите язык:",
        "hisobot_sarlavha": "📊 Отчёт: {davr}",
        "hisobot_bosh": "📭 Записей за этот период нет.",
        "davr_bugun": "Сегодня", "davr_hafta": "Последние 7 дней",
        "davr_oy": "Этот месяц", "davr_yil": "Этот год", "davr_hammasi": "За всё время",
        "his_daromad": "🟢 Доход", "his_harajat": "🔴 Расход",
        "his_balans": "💼 Баланс", "his_soni": "🔢 Кол-во записей: {n}",
        "his_kat": "📂 По категориям:",
        "his_takror": "⚠️ Такая же запись только что добавлена — повторное сообщение не сохранено.",
        "id_mening": "🆔 Ваш ID:",
        "id_username": "👤 Имя пользователя:",
        "fo_sarlavha": "👥 Зарегистрированные пользователи ({n}):",
        "fo_faqt": "⛔ Эта команда доступна только владельцу бота.",
        "fo_yozuvlar": "🧾",
        "fo_birinchi": "📅",
    },
}

# ============================ YORDAMCHILAR ============================

MENYU_KALITLARI = ("menyu_balans", "menyu_oxirgi", "menyu_fayl", "menyu_tozalash", "menyu_app")

# Ikkala tilning barcha tugma matnlari (routing uchun)
MENYU_TUGMALARI = {T[til][k] for til in T for k in MENYU_KALITLARI}


def _til(update) -> str:
    # Har bir user har qanday muloqotda registratsiya/yangilash (bir kunda 1 marta yozadi)
    try:
        u = update.effective_user
        chat_id = update.effective_chat.id
        profil, yangi_user = data_store.user_faollik(
            chat_id,
            " ".join(x for x in (u.first_name, u.last_name) if x).strip(),
            u.username or "",
        )
        # Yangi user ro'yxatdan o'tsa — bot egasiga xabar yuboramiz
        if yangi_user and str(chat_id) != OWNER_ID:
            try:
                username = f" @{profil['username']}" if profil.get("username") else ""
                update.get_bot().send_message(
                    int(OWNER_ID),
                    f"🎉 Botga yangi foydalanuvchi qo'shildi!\n"
                    f"👤 {profil.get('ism') or '—'}{username}\n"
                    f"🆔 {chat_id}\n📅 {profil.get('birinchi', '')[:10]}",
                )
            except Exception:
                pass
    except Exception:
        pass
    return data_store.til_olish(update.effective_chat.id)


def _menyu(til: str) -> ReplyKeyboardMarkup:
    """Faqat Moliya ilovasi tugmasi — qolgan amallar ilova ichida."""
    t = T[til]
    kb = [[KeyboardButton(t["menyu_app"], web_app=WebAppInfo(url=MINIAPP_URL))]]
    return ReplyKeyboardMarkup(
        kb, resize_keyboard=True, input_field_placeholder=t["menyu_placeholder"]
    )


def _belgi(til: str, turi: str) -> str:
    return T[til]["daromad_belgi"] if turi == "daromad" else T[til]["harajat_belgi"]


def _summa_fmt(summa) -> str:
    return data_store.fmt(summa)


def _yozuv_qisqa(y, til: str) -> str:
    """Yozuvni Telegramda ko'rsatish uchun qisqa matn (dict)."""
    belgi = "🟢" if y["turi"] == "Daromad" else "🔴"
    return (
        f"{belgi} {y['sana']} {y['vaqt']} | {y['kategoriya']}\n"
        f"   💵 {_summa_fmt(y['summa'])} {T[til]['som']}\n"
        f"   📝 {y['izoh'] or '-'}"
    )


def _balans_matni(chat_id, til: str) -> str:
    stat = data_store.stat_olish(chat_id)
    t = T[til]
    som = t["som"]
    qatorlar = [
        f"{t['umumiy_daromad']}: {_summa_fmt(stat['umumiy_daromad'])} {som}",
        f"{t['umumiy_harajat']}: {_summa_fmt(stat['umumiy_harajat'])} {som}",
        f"{t['joriy_balans']}: {_summa_fmt(stat['umumiy_daromad'] - stat['umumiy_harajat'])} {som}",
        "",
        f"{t['oy_daromad']}: {_summa_fmt(stat['oy_daromad'])} {som}",
        f"{t['oy_harajat']}: {_summa_fmt(stat['oy_harajat'])} {som}",
        f"{t['hafta_balans']}: {_summa_fmt(stat['hafta_balans'])} {som}",
    ]
    kat = []
    for nom, v in stat["kategoriyalar"].items():
        if v["daromad"]:
            kat.append(f"  🟢 {nom}: {_summa_fmt(v['daromad'])} {som}")
        if v["harajat"]:
            kat.append(f"  🔴 {nom}: {_summa_fmt(v['harajat'])} {som}")
    if kat:
        qatorlar.append("")
        qatorlar.append(t["kat_sarlavha"])
        qatorlar.extend(kat)
    return "\n".join(qatorlar)


def _davr_oraligi(davr: str) -> str:
    """Davr boshlanish sanasi ('hammasi' uchun bo'sh satr)."""
    bugun = datetime.date.today()
    if davr == "bugun":
        return bugun.isoformat()
    if davr == "hafta":
        return (bugun - datetime.timedelta(days=6)).isoformat()
    if davr == "oy":
        return bugun.replace(day=1).isoformat()
    if davr == "yil":
        return bugun.replace(month=1, day=1).isoformat()
    return ""


def _hisobot_matni(chat_id, til: str, davr: str, nima: str) -> str:
    """AI 'hisobot' deganda — davr va tur bo'yicha hisobot matni."""
    t = T[til]
    som = t["som"]
    yozuvlar = data_store.barchasi(chat_id)
    bosh = _davr_oraligi(davr)
    if bosh:
        yozuvlar = [y for y in yozuvlar if str(y.get("sana", ""))[:10] >= bosh]
    filtr = {"daromad": ("Daromad",), "harajat": ("Harajat",)}.get(nima, ("Daromad", "Harajat"))
    tanlangan = [y for y in yozuvlar if y.get("turi") in filtr]
    if not tanlangan:
        return t["hisobot_bosh"]

    dar = sum(data_store._son_qil(y.get("summa", 0)) for y in tanlangan if y.get("turi") == "Daromad")
    har = sum(data_store._son_qil(y.get("summa", 0)) for y in tanlangan if y.get("turi") == "Harajat")
    kat = {}
    for y in tanlangan:
        nom = y.get("kategoriya", "-")
        kat[nom] = kat.get(nom, 0) + data_store._son_qil(y.get("summa", 0))

    davr_kalit = davr if davr in ("bugun", "hafta", "oy", "yil", "hammasi") else "hammasi"
    q = [t["hisobot_sarlavha"].format(davr=t["davr_" + davr_kalit]), ""]
    if nima in ("daromad", "hammasi"):
        q.append(f"{t['his_daromad']}: {_summa_fmt(dar)} {som}")
    if nima in ("harajat", "hammasi"):
        q.append(f"{t['his_harajat']}: {_summa_fmt(har)} {som}")
    if nima == "hammasi":
        q.append(f"{t['his_balans']}: {_summa_fmt(dar - har)} {som}")
    q.append(t["his_soni"].format(n=len(tanlangan)))

    top = sorted(kat.items(), key=lambda x: -x[1])[:7]
    if top:
        q.append("")
        q.append(t["his_kat"])
        if nima == "hammasi":
            q.extend(f"  • {nom}: {_summa_fmt(v)} {som}" for nom, v in top)
        else:
            belgi = "🟢" if nima == "daromad" else "🔴"
            q.extend(f"  {belgi} {nom}: {_summa_fmt(v)} {som}" for nom, v in top)
    return "\n".join(q)


# Takroriy xabarlardan himoya: oxirgi qo'shilgan yozuv kaliti
_oxirgi_qoshilgan = {}  # chat_id -> (kalit, vaqt)
_DUPL_VAQT = 300  # soniya


async def _natijani_saqla_va_javob_ber(update, context, natija: dict, til: str):
    t = T[til]

    # Hisobot so'rovi — yozuv EMAS, hisobot matnini qaytaramiz
    if natija.get("turi") == "hisobot":
        await update.message.reply_text(
            _hisobot_matni(
                update.effective_chat.id, til,
                natija.get("davr", "hammasi"),
                natija.get("nima", "hammasi"),
            )
        )
        return

    if natija.get("turi") not in ("daromad", "harajat"):
        await update.message.reply_text(t["qoshilmadi"])
        return

    # Takroriy xabarlardan himoya: bir xil yozuv 5 daqiqada 2 marta qo'shilmasin
    # (AI javobi kechikkanda foydalanuvchi xabarni qayta yuborishi mumkin)
    chat_id = update.effective_chat.id
    kalit = (
        natija.get("turi"),
        data_store._son_qil(natija.get("summa", 0)),
        natija.get("kategoriya", ""),
        natija.get("izoh", ""),
    )
    oxirgi = _oxirgi_qoshilgan.get(chat_id)
    if oxirgi and oxirgi[0] == kalit and time.time() - oxirgi[1] < _DUPL_VAQT:
        logger.info("Takroriy xabar tushirib qoldirildi (chat %s)", chat_id)
        await update.message.reply_text(t["his_takror"])
        return
    _oxirgi_qoshilgan[chat_id] = (kalit, time.time())

    data_store.yozuv_qosh(chat_id, natija)

    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(t["hisobot_tugma"], web_app=WebAppInfo(url=MINIAPP_URL))]]
    )
    await update.message.reply_text(
        f"{_belgi(til, natija['turi'])} {t['qoshildi']}\n\n"
        f"{t['summa_lbl']}: {_summa_fmt(natija['summa'])} {t['som']}\n"
        f"{t['kategoriya_lbl']}: {natija['kategoriya']}\n"
        f"{t['izoh_lbl']}: {natija.get('izoh', '-')}",
        reply_markup=kb,
    )


# ============================ HANDLERLAR ============================

async def mening_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/id — foydalanuvchi ID va username (zaxira/tiklash uchun)."""
    til = _til(update)
    u = update.effective_user
    await update.message.reply_text(
        f"{T[til]['id_mening']} {update.effective_chat.id}\n"
        f"{T[til]['id_username']} @{u.username or '—'}"
    )


async def foydalanuvchilar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/foydalanuvchilar — bot egasi barcha ro'yxatdan o'tgan userlarni
    to'liq ma'lumotlari bilan ko'radi (ID, ism, til, yozuvlar, balans)."""
    til = _til(update)
    t = T[til]
    if str(update.effective_chat.id) != OWNER_ID:
        await update.message.reply_text(t["fo_faqt"])
        return
    royxat = data_store.foydalanuvchilar_royxati()
    q = [t["fo_sarlavha"].format(n=len(royxat))]
    for i, x in enumerate(royxat, 1):
        username = f" @{x['username']}" if x["username"] else ""
        q.append(
            f"\n{i}) {x['ism'] or '—'}{username}\n"
            f"   🆔 {x['chat_id']} · 🌐 {x['til']} · 📡 {x['manba'] or 'bot'}\n"
            f"   🧾 {x['yozuvlar']} · 🟢 {data_store.fmt(x['daromad'])} · "
            f"🔴 {data_store.fmt(x['harajat'])} · 💼 {data_store.fmt(x['balans'])} {t['som']}\n"
            f"   {t['fo_birinchi']} {x['birinchi'][:10] or '—'} → {x['oxirgi'][:10] or '—'}"
        )
    await update.message.reply_text("\n".join(q))


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    u = update.effective_user
    u = update.effective_user
    data_store.user_faollik(
        chat_id,
        " ".join(x for x in (u.first_name, u.last_name) if x).strip(),
        u.username or "",
    )
    users = data_store._users_yukla()
    if str(chat_id) not in users:
        # Til hali tanlanmagan — so'raymiz
        await _til_soraladi(update, context)
        return
    til = data_store.til_olish(chat_id)
    await update.message.reply_text(T[til]["menyu_tanlangan"], reply_markup=_menyu(til))


async def _til_soraladi(update, context):
    til = data_store.til_olish(update.effective_chat.id)
    kb = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🇺🇿 O'zbekcha", callback_data="til:uz"),
                InlineKeyboardButton("🇷🇺 Русский", callback_data="til:ru"),
            ]
        ]
    )
    await update.message.reply_text(
        T[til]["salom_tanlash"] + "\n\n" + T["ru"]["salom_tanlash"], reply_markup=kb
    )


async def til_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/til — tilni o'zgartirish."""
    await _til_soraladi(update, context)


async def til_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    til = query.data.split(":")[1]
    chat_id = update.effective_chat.id
    data_store.til_saqla(chat_id, til)
    await query.edit_message_text(T[til]["til_saqlandi"])
    await query.message.reply_text(T[til]["menyu_tanlangan"], reply_markup=_menyu(til))


async def _sahifa_yubor(update, context, til: str):
    """Mini App'ni ochish — link yuborilmaydi."""
    kb = InlineKeyboardMarkup(
        [[InlineKeyboardButton(T[til]["sahifa_tugma"], web_app=WebAppInfo(url=MINIAPP_URL))]]
    )
    await update.message.reply_text(T[til]["sahifa_xabar"], reply_markup=kb)


async def jadval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/sahifa — foydalanuvchining shaxsiy sahifa linkini yuboradi."""
    til = _til(update)
    await _sahifa_yubor(update, context, til)


async def balans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    til = _til(update)
    try:
        matn = _balans_matni(update.effective_chat.id, til)
        await update.message.reply_text(
            f"{T[til]['balans_sarlavha']}\n\n{matn}", reply_markup=_menyu(til)
        )
    except Exception:
        logger.exception("Balansni olishda xatolik")
        await update.message.reply_text(T[til]["balans_xato"])


async def eksport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha ma'lumotlarni chiroyli Excel (.xlsx) fayl qilib yuboradi."""
    til = _til(update)
    t = T[til]
    xabar = await update.message.reply_text(t["eksport_tayyorlanmoqda"])
    try:
        yozuvlar = data_store.barchasi(update.effective_chat.id)
        if not yozuvlar:
            await xabar.edit_text(t["eksport_bosh"])
            return

        yozuvlar.sort(key=lambda y: (str(y.get("sana", "")), str(y.get("vaqt", ""))))
        qatorlar = [
            [y.get("sana", ""), y.get("vaqt", ""), y.get("turi", ""),
             y.get("kategoriya", ""), data_store._son_qil(y.get("summa", 0)),
             y.get("izoh", "")]
            for y in yozuvlar
        ]
        bugun = datetime.date.today().isoformat()
        fayl_bytes = xlsx_yoz.yarat(
            f"Moliya hisoboti — {bugun} ({len(yozuvlar)} ta yozuv)",
            ["Sana", "Vaqt", "Turi", "Kategoriya", "Summa (so'm)", "Izoh"],
            qatorlar,
        )

        await xabar.edit_text(t["eksport_topildi"].format(n=len(yozuvlar)))
        await update.message.reply_document(
            document=io.BytesIO(fayl_bytes),
            filename=f"moliya_{bugun}.xlsx",
            caption=t["eksport_caption"].format(n=len(yozuvlar)),
        )
        await xabar.delete()
    except Exception:
        logger.exception("Eksportda xatolik")
        await xabar.edit_text(t["eksport_xato"])


async def tozalash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha yozuvlarni o'chirishdan oldin tasdiq so'raydi."""
    til = _til(update)
    t = T[til]
    tasdiq_tugmalari = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(t["tozalash_ha"], callback_data="tozalash_ha"),
                InlineKeyboardButton(t["bekor_tugma"], callback_data="tozalash_yoq"),
            ]
        ]
    )
    await update.message.reply_text(t["tozalash_ogohlantirish"], reply_markup=tasdiq_tugmalari)


async def tozalash_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tozalash tasdiq tugmalari bosilganda ishlaydi."""
    query = update.callback_query
    await query.answer()
    til = _til(update)
    t = T[til]

    if query.data == "tozalash_yoq":
        await query.edit_message_text(t["tozalash_bekor"])
        return

    await query.edit_message_text(t["tozalash_ochilmoqda"])
    try:
        soni = data_store.tozalash(update.effective_chat.id)
        await query.edit_message_text(t["tozalash_ok"].format(n=soni))
    except Exception:
        logger.exception("Tozalashda xatolik")
        await query.edit_message_text(t["balans_xato"])


async def oxirgi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oxirgi 5 yozuvni har biri uchun o'chirish/tuzatish tugmalari bilan ko'rsatadi."""
    til = _til(update)
    t = T[til]
    try:
        yozuvlar = data_store.oxirgi_yozuvlar(update.effective_chat.id, 5)
        if not yozuvlar:
            await update.message.reply_text(t["oxirgi_bosh"], reply_markup=_menyu(til))
            return

        # List indekslarini context'ga saqlaymiz (callback ichida kerak bo'ladi)
        context.user_data["oxirgi_yozuvlar"] = {
            i: indeks for i, (indeks, _) in enumerate(yozuvlar)
        }

        for i, (_, yozuv) in enumerate(yozuvlar):
            tugmalar = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(t["ochirish_tugma"], callback_data=f"ochirish:{i}"),
                        InlineKeyboardButton(t["tuzatish_tugma"], callback_data=f"tuzatish:{i}"),
                    ]
                ]
            )
            await update.message.reply_text(
                _yozuv_qisqa(yozuv, til), reply_markup=tugmalar
            )
        await update.message.reply_text(t["oxirgi_hint"])
    except Exception:
        logger.exception("Oxirgi yozuvlarni ko'rsatishda xatolik")
        await update.message.reply_text(t["oxirgi_xato"])


async def yozuv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'chirish / tuzatish tugmalari bosilganda ishlaydi."""
    query = update.callback_query
    await query.answer()
    data = query.data
    til = _til(update)
    t = T[til]

    yozuvlar_map = context.user_data.get("oxirgi_yozuvlar", {})
    indeks = int(data.split(":")[1])
    qator_raqami = yozuvlar_map.get(indeks)
    if qator_raqami is None:
        await query.edit_message_text(t["topilmadi_qayta"])
        return

    if data.startswith("ochirish:"):
        tugmalar = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(t["tozalash_ha"], callback_data=f"ochirish_tasdiq:{indeks}"),
                    InlineKeyboardButton(t["bekor_tugma"], callback_data="ochirish_bekor"),
                ]
            ]
        )
        await query.edit_message_text(t["ochirish_soraladi"], reply_markup=tugmalar)

    elif data.startswith("ochirish_tasdiq:"):
        try:
            data_store.yozuvni_ochirish(update.effective_chat.id, qator_raqami)
            await query.edit_message_text(t["ochirildi"])
        except Exception:
            logger.exception("Yozuv o'chirishda xatolik")
            await query.edit_message_text(t["ochirish_xato"])

    elif data == "ochirish_bekor":
        await query.edit_message_text(t["ochirish_bekor_ok"])

    elif data.startswith("tuzatish:"):
        context.user_data["tuzatilayotgan_qator"] = qator_raqami
        await query.edit_message_text(t["tuzatish_soraladi"])


async def tuzatish_bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tuzatish rejimini bekor qiladi."""
    til = _til(update)
    context.user_data.pop("tuzatilayotgan_qator", None)
    await update.message.reply_text(T[til]["tuzatish_bekor_ok"])


async def matn_kelganda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    til = _til(update)
    t = T[til]

    # Himoya: agar menyu tugmasi bu yerga yetib kelsa — tegishli amalga yonaltiramiz
    if update.message.text in MENYU_TUGMALARI:
        await menyu_tugmasi(update, context)
        return

    # Tuzatish rejimi faol bo'lsa — yangi xabarni shu yozuvga yozamiz
    tuzatilayotgan_qator = context.user_data.pop("tuzatilayotgan_qator", None)
    if tuzatilayotgan_qator is not None:
        try:
            natija = matnni_tahlil_qil(update.message.text, til=til)
            if natija.get("turi") not in ("daromad", "harajat"):
                await update.message.reply_text(t["qoshilmadi_tuzatish"])
                context.user_data["tuzatilayotgan_qator"] = tuzatilayotgan_qator
                return
            data_store.yozuvni_yangilash(update.effective_chat.id, tuzatilayotgan_qator, natija)
            await update.message.reply_text(
                f"{t['tuzatildi']}\n\n"
                f"{_belgi(til, natija['turi'])}\n"
                f"{t['summa_lbl']}: {_summa_fmt(natija['summa'])} {t['som']}\n"
                f"{t['kategoriya_lbl']}: {natija['kategoriya']}\n"
                f"{t['izoh_lbl']}: {natija.get('izoh', '-')}"
            )
        except Exception:
            logger.exception("Yozuvni tuzatishda xatolik")
            await update.message.reply_text(t["tuzatish_xato"])
        return

    try:
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        except Exception:
            pass
        natija = matnni_tahlil_qil(update.message.text, til=til)
        await _natijani_saqla_va_javob_ber(update, context, natija, til)
    except Exception:
        logger.exception("Matnni qayta ishlashda xatolik")
        await update.message.reply_text(t["matn_xato"])


async def ovoz_kelganda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    til = _til(update)
    t = T[til]
    try:
        try:
            await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
        except Exception:
            pass
        voice = update.message.voice or update.message.audio
        fayl = await voice.get_file()

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await fayl.download_to_drive(tmp.name)
            tmp_yuli = tmp.name

        natija = ovozni_tahlil_qil(tmp_yuli, til=til)
        os.remove(tmp_yuli)

        if natija.get("original_matn"):
            await update.message.reply_text(t["eshitdim"].format(matn=natija["original_matn"]))

        await _natijani_saqla_va_javob_ber(update, context, natija, til)
    except Exception:
        logger.exception("Ovozni qayta ishlashda xatolik")
        await update.message.reply_text(t["ovoz_xato"])


async def menyu_tugmasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pastdagi menyu tugmalari bosilganda tegishli buyruqni ishga tushiradi."""
    matn = update.message.text
    til = _til(update)
    t = T[til]
    if matn == t["menyu_balans"]:
        await balans(update, context)
    elif matn == t["menyu_oxirgi"]:
        await oxirgi(update, context)
    elif matn == t["menyu_fayl"]:
        await eksport(update, context)
    elif matn == t["menyu_tozalash"]:
        await tozalash(update, context)



def asosiy():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN .env faylida topilmadi!")

    app = Application.builder().token(token).build()

    async def _miniapp_menyu(app_):
        """Telegram pastdagi menyuga Mini App tugmasini o'rnatadi."""
        try:
            await app_.bot.set_chat_menu_button(
                menu_button=MenuButtonWebApp(text="📊 Moliya", web_app=WebAppInfo(url=MINIAPP_URL))
            )
        except Exception:
            logger.exception("Mini App menyu tugmasini o'rnatib bo'lmadi")

    app.post_init = _miniapp_menyu

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("til", til_cmd))
    app.add_handler(CommandHandler("balans", balans))
    app.add_handler(CommandHandler("eksport", eksport))
    app.add_handler(CommandHandler("tozalash", tozalash))
    app.add_handler(CommandHandler("oxirgi", oxirgi))
    app.add_handler(CommandHandler("tuzatish_bekor", tuzatish_bekor))
    app.add_handler(CommandHandler("sahifa", jadval))
    app.add_handler(CommandHandler("jadval", jadval))  # eski buyruq ham ishlaydi
    app.add_handler(CommandHandler("id", mening_id))
    app.add_handler(CommandHandler("foydalanuvchilar", foydalanuvchilar))
    app.add_handler(CommandHandler("users", foydalanuvchilar))  # inglizcha alias
    app.add_handler(CallbackQueryHandler(til_callback, pattern="^til:"))
    app.add_handler(CallbackQueryHandler(tozalash_callback, pattern="^tozalash_"))
    app.add_handler(CallbackQueryHandler(yozuv_callback, pattern="^(ochirish|tuzatish)"))

    menyu_regex = "|".join(re.escape(x) for x in sorted(MENYU_TUGMALARI))
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(f"^({menyu_regex})$"),
            menyu_tugmasi,
        )
    )
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, ovoz_kelganda))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, matn_kelganda))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    asosiy()
