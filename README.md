# Moliya Bot — Telegram + AI + Google Sheets

Bu bot Telegram orqali kelgan matn yoki ovozli xabarlarni AI yordamida tahlil qilib,
avtomatik ravishda Google Sheets jadvalingizga daromad/harajat sifatida yozadi.
Jadval ichida balans, haftalik va oylik hisobotlar formulalar orqali o'z-o'zidan hisoblanadi.

## 1-qadam: Telegram bot yaratish

1. Telegramda **@BotFather** ga yozing.
2. `/newbot` buyrug'ini yuboring, botga nom bering.
3. Sizga beriladigan **tokenni** saqlab qo'ying — bu `TELEGRAM_BOT_TOKEN`.

## 2-qadam: OpenAI API kaliti olish

1. https://platform.openai.com/api-keys ga kiring.
2. Yangi API kalit yarating — bu `OPENAI_API_KEY`.
3. Hisobingizda balans (kamida $5) bo'lishi kerak, aks holda so'rovlar ishlamaydi.

## 3-qadam: Google Sheets + Service Account sozlash

1. https://console.cloud.google.com ga kiring, yangi loyiha yarating.
2. **APIs & Services → Library** dan quyidagilarni yoqing:
   - Google Sheets API
   - Google Drive API
3. **APIs & Services → Credentials → Create Credentials → Service Account** orqali
   yangi service account yarating.
4. Yaratilgan service account ichiga kirib, **Keys → Add Key → Create new key → JSON**
   tanlang. Yuklab olingan faylni `credentials.json` deb nomlab, bot papkasiga qo'ying.
5. JSON fayl ichidagi `client_email` qatorini nusxa oling (masalan
   `moliya-bot@loyiha-nomi.iam.gserviceaccount.com`).
6. Google Drive'da yangi bo'sh **Google Sheet** yarating.
7. Shu jadvalni oching → **Share** tugmasi → yuqoridagi `client_email` manzilini
   qo'shing va **Editor** huquqini bering.
8. Jadval linkidan Sheet ID'ni oling:
   `https://docs.google.com/spreadsheets/d/BU_YERDA_SHEET_ID/edit` — shu qismi
   `GOOGLE_SHEET_ID`.

## 4-qadam: Loyihani sozlash

```bash
cd moliya-bot
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# .env faylini ochib, TELEGRAM_BOT_TOKEN, OPENAI_API_KEY, GOOGLE_SHEET_ID ni to'ldiring
```

`credentials.json` faylini shu papkaga joylashtirganingizga ishonch hosil qiling.

## 5-qadam: Jadval strukturasini yaratish (FAQAT BIR MARTA)

```bash
python setup_sheet.py
```

Bu buyruq jadvalingizda avtomatik ravishda **"Tranzaksiyalar"** va **"Dashboard"**
varaqlarini, sarlavhalarni va hisob-kitob formulalarini yaratadi.

## 6-qadam: Botni ishga tushirish

```bash
python bot.py
```

Endi Telegramda botingizga yozing:
- "Bugun 4 million oylik oldim"
- "Bozorga 150 ming so'm sarfladim"
- yoki shunchaki ovozli xabar yuboring

Bot xabarni tahlil qilib, Google Sheets'ga yozadi va sizga tasdiq qaytaradi.
`/balans` buyrug'i orqali joriy hisobotni istalgan vaqtda ko'rishingiz mumkin.

## Botni doim ishlab turishi uchun (serveringizda)

Server qayta yoqilganda bot ham avtomatik ishga tushishi uchun `systemd` xizmati
sifatida sozlashni tavsiya qilaman — buni keyingi bosqichda (AI integratsiyalarini
kuchaytirishdan oldin yoki keyin) birga sozlab beraman, agar xohlasangiz.

## Keyingi bosqich

Bot va Sheets integratsiyasi tayyor bo'lgach, quyidagilarni qo'shishimiz mumkin:
- Xarajat limitlari va ogohlantirishlar ("bu oy oziq-ovqatga limitdan oshib ketdingiz")
- Har hafta/oy oxirida avtomatik hisobot yuborish
- Bir necha valyutada (USD/UZS) hisob yuritish
- Grafik/diagramma bilan vizual hisobotlar
