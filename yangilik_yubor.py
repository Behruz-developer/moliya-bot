#!/usr/bin/env python3
"""Versiya 1.1.0 yangilanishi xabari — har userga o'z tilida (uz/ru) yuboriladi."""
import json
import time
from dotenv import load_dotenv
load_dotenv()

import httpx

TOKEN = None
import os
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

XABAR_UZ = """🆕 Versiya 1.1.0

🎉 Moliya bot yangilandi!

Botga bir nechta qulay funksiyalar qo'shildi:

🎙 Ovozli yozuv yanada osonlashdi

Ilovani oching, pastdagi 🎙 tugmasini bosing va gapiring. Aytganlaringiz avtomatik ravishda matnga aylanadi.

✓ tugmasini bossangiz, AI ma'lumotlarni o'zi aniqlab, tranzaksiyani qo'shadi. Hech narsa yozishingiz shart emas.

📊 Excel hisobot endi yanada qulay!

Hisobotni matn yoki ovozli xabar orqali so'rashingiz mumkin.

Masalan:
• «10-oktabrdan 15-oktabrgacha hisobotni yubor»
• Shu gapni ovozli xabar qilib yuboring.

Bot kerakli davr uchun Excel hisobot tayyorlab, chatga yuboradi.

📱 Barcha imkoniyatlar bitta ilovada!

Endi balans, statistika, analitika, tranzaksiyalarni tahrirlash va hisobotlarni yuklab olish — barchasi ilovaning o'zida.

📲 Ilovani ochish: pastdagi menyudan «📊 Moliya» tugmasini bosing."""

XABAR_RU = """🆕 Версия 1.1.0

🎉 Бот «Молия» обновился!

Добавили несколько удобных функций:

🎙 Голосовой ввод стал ещё проще

Откройте приложение, нажмите кнопку 🎙 внизу и говорите. Ваши слова автоматически появятся в виде текста.

Нажмите ✓, и AI сам определит данные и добавит транзакцию. Ничего вводить вручную не нужно.

📊 Отчёты в Excel

Запросить отчёт можно как текстом, так и голосовым сообщением.

Например:
• «Отправь отчёт с 10 по 15 октября»
• Или просто отправьте эту фразу голосом.

Бот подготовит Excel-файл за нужный период и отправит его прямо в чат.

📱 Все функции теперь в одном приложении!

Баланс, статистика, аналитика, редактирование транзакций и экспорт отчётов — всё доступно в приложении.

📲 Открыть приложение: нажмите кнопку «📊 Молия» в нижнем меню."""


def main():
    if not TOKEN:
        print("XATO: TELEGRAM_BOT_TOKEN yo'q")
        return
    with open("data/users.json", encoding="utf-8") as f:
        users = json.load(f)

    ok, fail = 0, []
    for chat_id_str, profil in users.items():
        til = profil.get("til") if isinstance(profil, dict) else "uz"
        til = til if til in ("uz", "ru") else "uz"
        matn = XABAR_UZ if til == "uz" else XABAR_RU
        try:
            r = httpx.post(
                f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                json={"chat_id": int(chat_id_str), "text": matn},
                timeout=20,
            )
            if r.status_code == 200:
                ok += 1
                print(f"OK   {chat_id_str} ({til})")
            else:
                fail.append(chat_id_str)
                print(f"XATO {chat_id_str}: {r.status_code} {r.text[:80]}")
        except Exception as e:
            fail.append(chat_id_str)
            print(f"XATO {chat_id_str}: {e}")
        time.sleep(0.4)

    print(f"\nYuborildi: {ok} | Xato: {len(fail)}")


if __name__ == "__main__":
    main()