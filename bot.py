"""
Moliya bot — Telegram orqali matn/ovozli xabarlarni qabul qilib,
AI bilan tahlil qiladi va Google Sheets'ga yozadi.
"""
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
from sheets_helper import (
    tranzaksiya_qoshish,
    dashboard_matnini_olish,
    barcha_yozuvlarni_olish,
    tranzaksiyalarni_tozalash,
    oxirgi_yozuvlarni_olish,
    yozuvni_ochirish,
    yozuvni_yangilash,
)

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

ASOSIY_MENYU = ReplyKeyboardMarkup(
    [[MENYU_BALANS], [MENYU_OXIRGI], [MENYU_FAYL], [MENYU_TOZALASH]],
    resize_keyboard=True,
    input_field_placeholder="Yozing yoki tugmani tanlang...",
)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Salom! Men shaxsiy moliya botingizman.\n\n"
        "📜 FOYDALANISH QO'LLANMASI\n\n"
        "1️⃣ Xarajat/daromad yozish:\n"
        "Shunchaki oddiy tilda yozing yoki 🎤 ovozli xabar yuboring:\n"
        "• \"Bugun 4 million oylik oldim\"\n"
        "• \"Bozorga 150 ming sarfladim\"\n"
        "Bot summa, kategoriya va turini o'zi aniqlab Sheets'ga yozadi ✅\n\n"
        "2️⃣ Buyruqlar:\n"
        "📊 /balans — hisobot (davr, oy, hafta, kategoriyalar)\n"
        "🕓 /oxirgi — oxirgi 5 yozuv (o'chirish yoki tuzatish mumkin)\n"
        "📥 /eksport — barcha ma'lumotlarni CSV faylda olish\n"
        "🧹 /tozalash — barcha yozuvlarni o'chirish (tasdiq so'raydi)\n"
        "🔄 /start — shu yo'riqnomani qayta ko'rish\n\n"
        "3️⃣ Google Sheets:\n"
        "📄 Tranzaksiyalar — barcha yozuvlar (ustunlardan filtrlab ko'rishingiz mumkin)\n"
        "📈 Dashboard — grafiklar va ko'rsatkichlar. \"Dan/Gacha\" sanalarni o'zgartirib "
        "istalgan davrni hisoblab ko'rishingiz mumkin.\n\n"
        "💡 Pastdagi menyudan ham xuddi shu amallarni bajarishingiz mumkin. "
        "Yaxshi kuzatishlar! 💰",
        reply_markup=ASOSIY_MENYU,
    )


async def balans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        matn = dashboard_matnini_olish()
        await update.message.reply_text(f"📊 Hisobotingiz:\n\n{matn}")
    except Exception as e:
        logger.exception("Balansni olishda xatolik")
        await update.message.reply_text(
            "Hisobotni o'qishda xatolik yuz berdi. Sheets sozlamalarini tekshiring."
        )


async def _natijani_saqla_va_javob_ber(update: Update, natija: dict):
    if natija.get("turi") not in ("daromad", "harajat"):
        await update.message.reply_text(
            "Xabaringizdan moliyaviy ma'lumot topa olmadim 🤔\n"
            "Masalan shunday yozib ko'ring: \"Bugun 4 million oylik oldim\""
        )
        return

    tranzaksiya_qoshish(natija)

    belgi = "🟢 Daromad" if natija["turi"] == "daromad" else "🔴 Harajat"
    await update.message.reply_text(
        f"{belgi} qo'shildi ✅\n\n"
        f"Summa: {int(natija['summa']):,} so'm\n"
        f"Kategoriya: {natija['kategoriya']}\n"
        f"Izoh: {natija.get('izoh', '-')}"
    )


async def eksport(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Barcha ma'lumotlarni CSV fayl qilib yuboradi."""
    xabar = await update.message.reply_text("⏳ Ma'lumotlar tayyorlanmoqda...")
    try:
        qatorlar = barcha_yozuvlarni_olish()
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
        soni = tranzaksiyalarni_tozalash()
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


MENYU_TUGMALARI = {MENYU_BALANS, MENYU_OXIRGI, MENYU_FAYL, MENYU_TOZALASH}


# Yozuvni tuzatish/o'chirish uchun callback pattern
CB_OCHIRISH = "ochirish:"
CB_TUZATISH = "tuzatish:"


def _yozuv_qisqa(qiymatlar: list) -> str:
    """Yozuvni Telegramda ko'rsatish uchun qisqa matn shakllantiradi."""
    sana, vaqt, turi, kat, summa, izoh = qiymatlar[:6]
    belgi = "🟢" if str(turi).lower() == "daromad" else "🔴"
    summa_son = str(summa).replace("\xa0", "").replace(",", "").replace(" so'm", "").replace("so'm", "").strip()
    try:
        summa_fmt = f"{int(float(summa_son)):,}".replace(",", " ") + " so'm"
    except (ValueError, TypeError):
        summa_fmt = str(summa)
    return f"{belgi} {sana} {vaqt} | {kat}\n   💵 {summa_fmt}\n   📝 {izoh or '-'}"


async def oxirgi(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Oxirgi 5 yozuvni har biri uchun o'chirish/tuzatish tugmalari bilan ko'rsatadi."""
    try:
        yozuvlar = oxirgi_yozuvlarni_olish(5)
        if not yozuvlar:
            await update.message.reply_text("📭 Hozircha yozuv yo'q.")
            return

        # Qator raqamlarini context'ga saqlaymiz (callback ichida kerak bo'ladi)
        context.user_data["oxirgi_yozuvlar"] = {
            i: qator_raqami for i, (qator_raqami, _) in enumerate(yozuvlar)
        }

        for i, (_, qiymatlar) in enumerate(yozuvlar):
            tugmalar = InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton("🗑 O'chirish", callback_data=f"{CB_OCHIRISH}{i}"),
                        InlineKeyboardButton("✏️ Tuzatish", callback_data=f"{CB_TUZATISH}{i}"),
                    ]
                ]
            )
            await update.message.reply_text(
                _yozuv_qisqa(qiymatlar), reply_markup=tugmalar
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
            yozuvni_ochirish(qator_raqami)
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
    await update.message.reply_text("❌ Tuzatish bekor qilindi.")


async def matn_kelganda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Himoya: agar menyu tugmasi bu yerga yetib kelsa — tegishli amalga yonaltiramiz
    if update.message.text in MENYU_TUGMALARI:
        await menyu_tugmasi(update, context)
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
            qiymatlar = [
                natija["sana"],
                natija["vaqt"],
                "Daromad" if natija["turi"] == "daromad" else "Harajat",
                natija["kategoriya"],
                natija["summa"],
                natija.get("izoh", ""),
                natija.get("original_matn", ""),
            ]
            yozuvni_yangilash(tuzatilayotgan_qator, qiymatlar)
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
        await _natijani_saqla_va_javob_ber(update, natija)
    except Exception as e:
        logger.exception("Matnni qayta ishlashda xatolik")
        await update.message.reply_text(
            "Xabaringizni qayta ishlashda xatolik yuz berdi. Birozdan so'ng qaytadan urinib ko'ring."
        )


async def ovoz_kelganda(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        await _natijani_saqla_va_javob_ber(update, natija)
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
    app.add_handler(CallbackQueryHandler(tozalash_callback, pattern="^tozalash_"))
    app.add_handler(CallbackQueryHandler(yozuv_callback, pattern="^(ochirish|tuzatish)"))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, ovoz_kelganda))
    app.add_handler(
        MessageHandler(
            filters.TEXT & filters.Regex(
                f"^({re.escape(MENYU_BALANS)}|{re.escape(MENYU_OXIRGI)}|{re.escape(MENYU_FAYL)}|{re.escape(MENYU_TOZALASH)})$"
            ),
            menyu_tugmasi,
        )
    )
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, matn_kelganda))

    logger.info("Bot ishga tushdi...")
    app.run_polling()


if __name__ == "__main__":
    asosiy()