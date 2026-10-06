"""
Moliya bot — Telegram orqali matn/ovozli xabarlarni qabul qilib,
AI bilan tahlil qiladi va Google Sheets'ga yozadi.
"""
# Render'da uxlamasligi uchun keep-alive server (lokalda flask bo'lmasa — o'tkazib yuboriladi)
try:
    from keep_alive import keep_alive
    keep_alive()
except ImportError:
    pass

import asyncio
import os
import csv
import re
import tempfile
import logging

from dotenv import load_dotenv
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup
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

load_dotenv()

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Asosiy menyu tugmalari (rasmdagidek pastda chiqadi)
MENYU_BALANS = "📊 Balansni ko'rish"
MENYU_OXIRGI = "🕓 Oxirgi yozuvlar (o'chirish/tuzatish)"
MENYU_FAYL = "📥 Ma'lumotlarni faylda olish"
MENYU_TOZALASH = "🧹 Barcha yozuvlarni tozalash"
MENYU_JADVAL = "🔗 Jadvalni o'zgartirish"

ASOSIY_MENYU = ReplyKeyboardMarkup(
    [[MENYU_BALANS], [MENYU_OXIRGI], [MENYU_FAYL], [MENYU_TOZALASH], [MENYU_JADVAL]],
    resize_keyboard=True,
    input_field_placeholder="Yozing yoki tugmani tanlang...",
)

# --- Har bir foydalanuvchiga alohida shaxsiy sahifa (Google Sheets kerak emas!) ---
BASE_URL = os.getenv("PUBLIC_URL", os.getenv("RENDER_EXTERNAL_URL", "http://localhost:10000")).rstrip("/")


def _sahifa_link(chat_id) -> str:
    return f"{BASE_URL}/u/{chat_id}"


def _jadval_id(update, context):
    """(Eski nom saqlandi) endi shunchaki chat ID qaytaradi."""
    return update.effective_chat.id


async def _ulanganmi_yoki_soraladi(update, context) -> bool:
    """Endi hech qanday sozlash kerak emas — doim True (nomi eski)."""
    return True


async def jadval(update, context):
    """Foydalanuvchining shaxsiy sahifa linkini yuboradi."""
    link = _sahifa_link(update.effective_chat.id)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📊 Sahifamni ochish", url=link)]])
    await update.message.reply_text(
        "📊 Sizning shaxsiy sahifangiz:\n"
        + link
        + "\n\nSahifada: balans, kategoriyalar, barcha yozuvlar va "
        "CSV yuklab olish tugmasi bor.\n\n"
        "🔗 Linkni saqlab qo'ying — istalgan qurilmada ochiladi.",
        reply_markup=kb,
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    link = _sahifa_link(update.effective_chat.id)
    kb = InlineKeyboardMarkup([[InlineKeyboardButton("📊 Sahifamni ochish", url=link)]])
    await update.message.reply_text(
        "👋 Salom! Men shaxsiy moliya botingizman.\n\n"
        "📝 SHUNDAKI ISHLAYDI — sozlashga ehtiyoj yo'q:\n"
        "Shunchaki yozing yoki 🎤 ovozli xabar yuboring:\n"
        "• \"Bugun 4 million oylik oldim\"\n"
        "• \"Bozorga 150 ming sarfladim\"\n"
        "Bot summa, kategoriya va turini o'zi aniqlaydi ✅\n\n"
        "📊 Sizning shaxsiy sahifangiz (balans, yozuvlar, grafiklar):\n"
        + link
        + "\n\n📋 Buyruqlar:\n"
        "📊 /balans — hisobot\n"
        "🕓 /oxirgi — oxirgi 5 yozuv (o'chirish/tuzatish)\n"
        "📥 /eksport — CSV fayl\n"
        "🧹 /tozalash — barcha yozuvlarni o'chirish\n"
        "🔗 /jadval — shaxsiy sahifa linki\n\n"
        "💡 Pastdagi menyudan ham xuddi shu amallarni bajarish mumkin. Yaxshi kuzatishlar! 💰",
        reply_markup=ASOSIY_MENYU,
    )


async def balans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _ulanganmi_yoki_soraladi(update, context):
        return
    try:
        matn = data_store.balans_matni(_jadval_id(update, context))
        await update.message.reply_text(f"📊 Hisobotingiz:\n\n{matn}")
    except Exception as e:
        logger.exception("Balansni olishda xatolik")
        await update.message.reply_text(
            "Hisobotni o'qishda xatolik yuz berdi. Sheets sozlamalarini tekshiring."
        )


async def _natijani_saqla_va_javob_ber(update: Update, context: ContextTypes.DEFAULT_TYPE, natija: dict):
    if natija.get("turi") not in ("daromad", "harajat"):
        await update.message.reply_text(
            "Xabaringizdan moliyaviy ma'lumot topa olmadim 🤔\n"
            "Masalan shunday yozib ko'ring: \"Bugun 4 million oylik oldim\""
        )
        return

    data_store.yozuv_qosh(_jadval_id(update, context), natija)

    belgi = "🟢 Daromad" if natija["turi"] == "daromad" else "🔴 Harajat"
    await update.message.reply_text(
        f"{belgi} qo'shildi ✅\n\n"
        f"Summa: {int(natija['summa']):,} so'm\n"
        f"Kategoriya: {natija['kategoriya']}\n"
        f"Izoh: {natija.get('izoh', '-')}"
    )


async def eksport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha ma'lumotlarni CSV fayl qilib yuboradi."""
    if not await _ulanganmi_yoki_soraladi(update, context):
        return
    xabar = await update.message.reply_text("⏳ Ma'lumotlar tayyorlanmoqda...")
    try:
        qatorlar = data_store.barchasi(_jadval_id(update, context))
        if len(qatorlar) <= 1:
            await xabar.edit_text("📭 Hozircha hech qanday yozuv yo'q.")
            return

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".csv", delete=False, encoding="utf-8-sig", newline=""
        ) as tmp:
            yozuvchi = csv.writer(tmp)
            yozuvchi.writerows(qatorlar)
            fayl_yuli = tmp.name

        await xabar.edit_text(
            f"📦 {len(qatorlar) - 1} ta yozuv topildi — fayl yuborilmoqda..."
        )
        with open(fayl_yuli, "rb") as f:
            await update.message.reply_document(
                document=f,
                filename="moliya_malumotlari.csv",
                caption=f"📄 Barcha ma'lumotlaringiz ({len(qatorlar) - 1} ta yozuv)\n"
                "Excel yoki boshqa dasturda ochishingiz mumkin.",
            )
        os.remove(fayl_yuli)
        await xabar.delete()
    except Exception:
        logger.exception("Eksportda xatolik")
        await xabar.edit_text(
            "❌ Fayl tayyorlashda xatolik yuz berdi. Birozdan so'ng qaytadan urinib ko'ring."
        )


async def tozalash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha yozuvlarni o'chirishdan oldin tasdiq so'raydi."""
    tasdiq_tugmalari = InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ Ha, o'chirish", callback_data="tozalash_ha"),
                InlineKeyboardButton("❌ Bekor qilish", callback_data="tozalash_yoq"),
            ]
        ]
    )
    await update.message.reply_text(
        "⚠️ DIQQAT!\n\nBu amal Sheets'dagi BARCHA tranzaksiya yozuvlarini "
        "o'chiradi va QAYTARIB BO'LMAYDI.\n\nIshonchingiz komilmi?",
        reply_markup=tasdiq_tugmalari,
    )


async def tozalash_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tozalash tasdiq tugmalari bosilganda ishlaydi."""
    query = update.callback_query
    await query.answer()

    if query.data == "tozalash_yoq":
        await query.edit_message_text("❌ Bekor qilindi — hech narsa o'chirilmadi.")
        return

    await query.edit_message_text("⏳ Yozuvlar o'chirilmoqda...")
    try:
        soni = data_store.tozalash(_jadval_id(update, context))
        await query.edit_message_text(
            f"🧹 Tozalandi! {soni} ta yozuv o'chirildi.\n"
            "Endi jadval yangi yozuvlarga tayyor ✅"
        )
    except Exception:
        logger.exception("Tozalashda xatolik")
        await query.edit_message_text(
            "❌ Tozalashda xatolik yuz berdi. Birozdan so'ng qaytadan urinib ko'ring."
        )


async def menyu_tugmasi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pastdagi menyu tugmalari bosilganda tegishli buyruqni ishga tushiradi."""
    matn = update.message.text
    if matn == MENYU_BALANS:
        await balans(update, context)
    elif matn == MENYU_OXIRGI:
        await oxirgi(update, context)
    elif matn == MENYU_FAYL:
        await eksport(update, context)
    elif matn == MENYU_TOZALASH:
        await tozalash(update, context)
    elif matn == MENYU_JADVAL:
        await jadval(update, context)


MENYU_TUGMALARI = {MENYU_BALANS, MENYU_OXIRGI, MENYU_FAYL, MENYU_TOZALASH, MENYU_JADVAL}


# Yozuvni tuzatish/o'chirish uchun callback pattern
CB_OCHIRISH = "ochirish:"
CB_TUZATISH = "tuzatish:"


def _yozuv_qisqa(y) -> str:
    """Yozuvni Telegramda ko'rsatish uchun qisqa matn shakllantiradi (dict)."""
    belgi = "🟢" if y["turi"] == "Daromad" else "🔴"
    try:
        summa_fmt = f"{int(float(str(y['summa']).replace(' ', ''))):,}".replace(",", " ") + " so'm"
    except (ValueError, TypeError):
        summa_fmt = str(y["summa"])
    return (
        f"{belgi} {y['sana']} {y['vaqt']} | {y['kategoriya']}\n"
        f"   💵 {summa_fmt}\n"
        f"   📝 {y['izoh'] or '-'}"
    )


async def oxirgi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oxirgi 5 yozuvni har biri uchun o'chirish/tuzatish tugmalari bilan ko'rsatadi."""
    if not await _ulanganmi_yoki_soraladi(update, context):
        return
    try:
        yozuvlar = data_store.oxirgi_yozuvlar(_jadval_id(update, context), 5)
        if not yozuvlar:
            await update.message.reply_text("📭 Hozircha yozuv yo'q.")
            return

        # Indexlarini context'ga saqlaymiz (callback ichida kerak bo'ladi)
        context.user_data["oxirgi_yozuvlar"] = {
            i: indeks for i, (indeks, _) in enumerate(yozuvlar)
        }

        for i, (_, yozuv) in enumerate(yozuvlar):
            tugmalar = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🗑 O'chirish", callback_data=f"{CB_OCHIRISH}{i}"),
                        InlineKeyboardButton("✏️ Tuzatish", callback_data=f"{CB_TUZATISH}{i}"),
                    ]
                ]
            )
            await update.message.reply_text(
                _yozuv_qisqa(yozuv), reply_markup=tugmalar
            )
        await update.message.reply_text(
            "👆 Yuqoridagi yozuvlardan birini o'chirish yoki tuzatish mumkin."
        )
    except Exception:
        logger.exception("Oxirgi yozuvlarni ko'rsatishda xatolik")
        await update.message.reply_text("❌ Yozuvlarni o'qishda xatolik yuz berdi.")


async def yozuv_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """O'chirish / tuzatish tugmalari bosilganda ishlaydi."""
    query = update.callback_query
    await query.answer()
    data = query.data

    yozuvlar_map = context.user_data.get("oxirgi_yozuvlar", {})
    indeks = int(data.split(":")[1])
    qator_raqami = yozuvlar_map.get(indeks)
    if qator_raqami is None:
        await query.edit_message_text("❌ Yozuv topilmadi — /oxirgi ni qayta ishga tushiring.")
        return

    if data.startswith(CB_OCHIRISH):
        tugmalar = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("✅ Ha, o'chirish", callback_data=f"ochirish_tasdiq:{indeks}"),
                    InlineKeyboardButton("❌ Bekor qilish", callback_data="ochirish_bekor"),
                ]
            ]
        )
        await query.edit_message_text(
            "⚠️ Bu yozuvni o'chirishga ishonchingiz komilmi?", reply_markup=tugmalar
        )

    elif data.startswith("ochirish_tasdiq:"):
        try:
            data_store.yozuvni_ochirish(_jadval_id(update, context), qator_raqami)
            await query.edit_message_text("🗑 Yozuv o'chirildi ✅")
        except Exception:
            logger.exception("Yozuv o'chirishda xatolik")
            await query.edit_message_text("❌ O'chirishda xatolik yuz berdi.")

    elif data == "ochirish_bekor":
        await query.edit_message_text("❌ Bekor qilindi — yozuv joyida qoldi.")

    elif data.startswith(CB_TUZATISH):
        # Tuzatish: yangi matn kutasimiz — user message'ni /tuzatish <qator> <matn> shaklida yozadi
        yangi_qator = qator_raqami  # saqlangan
        context.user_data["tuzatilayotgan_qator"] = qator_raqami
        await query.edit_message_text(
            "✏️ Tuzatish: endi to'g'ri xabarni oddiy tilda yozib yuboring.\n"
            "Masalan: \"Bozorga 200 ming sarfladim\"\n\n"
            "Bot uni yangi yozuv sifatida tahlil qilib, shu qatorni almashtiradi.\n"
            "(Bekor qilish uchun: /tuzatish_bekor)"
        )


async def tuzatish_bekor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tuzatish rejimini bekor qiladi."""
    context.user_data.pop("tuzatilayotgan_qator", None)
    context.user_data.pop("jadval_kutmoqda", None)
    await update.message.reply_text("❌ Tuzatish bekor qilindi.")


async def matn_kelganda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Himoya: agar menyu tugmasi bu yerga yetib kelsa — tegishli amalga yonaltiramiz
    if update.message.text in MENYU_TUGMALARI:
        await menyu_tugmasi(update, context)
        return

    if not await _ulanganmi_yoki_soraladi(update, context):
        return

    # Tuzatish rejimi faol bo'lsa — yangi xabarni shu qatorga yozamiz
    tuzatilayotgan_qator = context.user_data.pop("tuzatilayotgan_qator", None)
    if tuzatilayotgan_qator is not None:
        try:
            natija = matnni_tahlil_qil(update.message.text)
            if natija.get("turi") not in ("daromad", "harajat"):
                await update.message.reply_text(
                    "Xabaringizdan moliyaviy ma'lumot topa olmadim 🤔 "
                    "Qaytadan yozing yoki /tuzatish_bekor bilan bekor qiling."
                )
                context.user_data["tuzatilayotgan_qator"] = tuzatilayotgan_qator
                return
            data_store.yozuvni_yangilash(_jadval_id(update, context), tuzatilayotgan_qator, natija)
            belgi = "🟢 Daromad" if natija["turi"] == "daromad" else "🔴 Harajat"
            await update.message.reply_text(
                f"✏️ Yozuv tuzatildi ✅\n\n"
                f"{belgi}\n"
                f"Summa: {int(natija['summa']):,} so'm\n"
                f"Kategoriya: {natija['kategoriya']}\n"
                f"Izoh: {natija.get('izoh', '-')}"
            )
        except Exception:
            logger.exception("Yozuvni tuzatishda xatolik")
            await update.message.reply_text(
                "❌ Tuzatishda xatolik yuz berdi. Qaytadan urinib ko'ring yoki /tuzatish_bekor."
            )
        return

    try:
        natija = matnni_tahlil_qil(update.message.text)
        await _natijani_saqla_va_javob_ber(update, context, natija)
    except Exception as e:
        logger.exception("Matnni qayta ishlashda xatolik")
        await update.message.reply_text(
            "Xabaringizni qayta ishlashda xatolik yuz berdi. Birozdan so'ng qaytadan urinib ko'ring."
        )


async def ovoz_kelganda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await _ulanganmi_yoki_soraladi(update, context):
        return
    try:
        voice = update.message.voice or update.message.audio
        fayl = await voice.get_file()

        with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
            await fayl.download_to_drive(tmp.name)
            tmp_yuli = tmp.name

        natija = ovozni_tahlil_qil(tmp_yuli)
        os.remove(tmp_yuli)

        if natija.get("original_matn"):
            await update.message.reply_text(f"🎙 Eshitdim: \"{natija['original_matn']}\"")

        await _natijani_saqla_va_javob_ber(update, context, natija)
    except Exception as e:
        logger.exception("Ovozni qayta ishlashda xatolik")
        await update.message.reply_text(
            "Ovozli xabarni qayta ishlashda xatolik yuz berdi. Birozdan so'ng qaytadan urinib ko'ring."
        )


def asosiy():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN .env faylida topilmadi!")

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balans", balans))
    app.add_handler(CommandHandler("eksport", eksport))
    app.add_handler(CommandHandler("tozalash", tozalash))
    app.add_handler(CommandHandler("oxirgi", oxirgi))
    app.add_handler(CommandHandler("tuzatish_bekor", tuzatish_bekor))
    app.add_handler(CommandHandler("jadval", jadval))
    app.add_handler(CallbackQueryHandler(tozalash_callback, pattern="^tozalash_"))
    app.add_handler(CallbackQueryHandler(yozuv_callback, pattern="^(ochirish|tuzatish)"))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, ovoz_kelganda))
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(
                f"^({re.escape(MENYU_BALANS)}|{re.escape(MENYU_OXIRGI)}|{re.escape(MENYU_FAYL)}|{re.escape(MENYU_TOZALASH)}|{re.escape(MENYU_JADVAL)})$"
            ),
            menyu_tugmasi,
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, matn_kelganda))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    asosiy()