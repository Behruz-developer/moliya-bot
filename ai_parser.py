"""
Matn va ovozli xabarlarni Google Gemini (bepul AI, yangi google-genai SDK)
yordamida moliyaviy yozuvga aylantirish. Gemini ovozni to'g'ridan-to'g'ri
tushunadi, shuning uchun alohida "ovozni matnga o'girish" bosqichi kerak emas.
"""
import os
import json
import logging
import datetime
from dotenv import load_dotenv
from google import genai
from categories import DAROMAD_KATEGORIYALARI, HARAJAT_KATEGORIYALARI

load_dotenv()  # .env qiymatlarini shu yerda ham yuklaymiz, import tartibiga bog'liq bo'lmasin

logger = logging.getLogger(__name__)

_API_KEY = os.getenv("GOOGLE_API_KEY")
if not _API_KEY:
    raise RuntimeError(
        "GOOGLE_API_KEY topilmadi! .env faylida GOOGLE_API_KEY=... qatorini "
        "to'g'ri to'ldirganingizga va faylni saqlaganingizga ishonch hosil qiling."
    )

_client = genai.Client(api_key=_API_KEY)

# Bepul tarifda tezroq/ko'proq so'rov yubormoqchi bo'lsangiz
# .env ichida GEMINI_MODEL=gemini-2.5-flash-lite deb qo'yishingiz mumkin.
MODEL_NOMI = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# Asosiy model 503 (yuk yuqori) yoki 404 qaytarsa, navbatma-navbat shularga urinamiz.
ZAXIRA_MODELLAR = ["gemini-3.8-flash", "gemini-3.5-flash-lite"]

SYSTEM_PROMPT = f"""Sen moliyaviy yordamchisan. Foydalanuvchi o'zbek tilida
(yozma yoki ovozli, so'zlashuv uslubida) yuborgan xabarni tahlil qilib,
FAQAT quyidagi JSON formatda javob ber, hech qanday qo'shimcha matn yozma:

{{
  "turi": "daromad" yoki "harajat" yoki "noaniq",
  "summa": <son, so'm hisobida, masalan 4000000>,
  "kategoriya": "<quyidagi ro'yxatdan biri>",
  "izoh": "<qisqa, 5-6 so'zdan oshmagan izoh>",
  "eshitilgan_matn": "<agar kirish ovozli xabar bo'lsa, eshitgan gapingizni shu yerga yoz; matnli xabar bo'lsa bo'sh qoldir>"
}}

Agar turi = daromad bo'lsa, kategoriya shulardan biri bo'lishi kerak: {", ".join(DAROMAD_KATEGORIYALARI)}
Agar turi = harajat bo'lsa, kategoriya shulardan biri bo'lishi kerak: {", ".join(HARAJAT_KATEGORIYALARI)}

Summalarni to'g'ri tushun: "4 million", "4mln", "4000000", "4 ming" (=4000) kabi
ifodalarni to'g'ri songa o'gir. Agar xabarda moliyaviy ma'lumot umuman
topilmasa, "turi" ni "noaniq" qilib qaytar.
"""

_GENERATION_CONFIG = {
    "system_instruction": SYSTEM_PROMPT,
    "response_mime_type": "application/json",
}


def _natijani_tayyorla(xom_javob_matni: str, original_matn: str = "") -> dict:
    natija = json.loads(xom_javob_matni)
    if not original_matn:
        original_matn = natija.get("eshitilgan_matn", "")
    natija["original_matn"] = original_matn
    natija["sana"] = datetime.date.today().isoformat()
    natija["vaqt"] = datetime.datetime.now().strftime("%H:%M")
    return natija


def _generate(contents):
    """Asosiy model ishlamasa (503/404), zaxira modellarda urinib ko'radi."""
    from google.genai import errors as genai_errors

    modellar = [MODEL_NOMI] + [m for m in ZAXIRA_MODELLAR if m != MODEL_NOMI]
    oxirgi_xato = None
    for model in modellar:
        try:
            javob = _client.models.generate_content(
                model=model,
                contents=contents,
                config=_GENERATION_CONFIG,
            )
            if not javob.text:
                raise ValueError("AI bo'sh javob qaytardi")
            return javob.text
        except (genai_errors.ServerError, genai_errors.ClientError, ValueError) as e:
            oxirgi_xato = e
            logger.warning("Model %s ishlamadi: %s — keyingisiga o'tamiz", model, e)
    raise oxirgi_xato


def matnni_tahlil_qil(matn: str) -> dict:
    """Yozma xabarni AI orqali tuzilgan moliyaviy yozuvga aylantiradi."""
    javob_matni = _generate(matn)
    return _natijani_tayyorla(javob_matni, original_matn=matn)


def ovozni_tahlil_qil(fayl_yuli: str) -> dict:
    """Ovozli xabar faylini (ogg) to'g'ridan-to'g'ri Gemini'ga yuborib,
    bir martada matnga o'giradi va moliyaviy yozuvga aylantiradi."""
    audio_fayl = _client.files.upload(file=fayl_yuli)
    javob_matni = _generate(["Bu ovozli xabarni tingla va tahlil qil.", audio_fayl])
    return _natijani_tayyorla(javob_matni)