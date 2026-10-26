# 🔄 Yangi kompyuterga ko'chish qo'llanmasi

Ma'lumotlar **GitHub'da** saqlanadi (kompyuterda faqat nusxa bor). Yangi kompyuterdagi
qadam-qadama yo'riqnoma:

## 1. Kerakli dasturlarni o'rnating
- **Git** — https://git-scm.com (yoki macOS: `brew install git`)
- **Python 3.11+** — https://python.org (yoki macOS: `brew install python3`)

## 2. Repodan ma'lumotlarni yuklab oling
```bash
git clone https://github.com/Behruz-developer/moliya-bot.git
cd moliya-bot
```
*(Private repo — GitHub'dan kirish uchun username + Personal Access Token so'raydi.
Token yangi kompyuterda ham kerak bo'ladi — avvalgisini saqlab qo'ying:
GitHub → Settings → Developer settings → Personal access tokens.)*

## 3. .env faylini ko'chiring
Eski kompyuterdagi `.env` faylni yangi papkaga nusxalang. Qo'lda yozishingiz ham mumkin —
barcha qiymatlar **Render → Environment** bo'limida bor:
```
TELEGRAM_BOT_TOKEN=...
GOOGLE_API_KEY=...
GITHUB_TOKEN=...
GITHUB_REPO=...
OWNER_ID=1144941995
```

## 4. Kutubxonalarni o'rnating
```bash
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

## 5. Ishga tushiring
**`Dashboard.command`** fayliga ikki marta bosing — dashboard ochiladi.
Data avtomatik GitHub'dan yangilanadi.

---

## ❓ FAQ

**Kompyuter hozir o'lib ketsa, nima yo'qoladi?**
Hech narsa yo'qolmaydi — GitHub'da barcha userlar va yozuvlar saqlangan.

**Botning Telegram tomondagi ma'lumotlari?**
Bot Render'da ishlaydi va deployda repodan ko'tariladi — kompyuteringizga bog'liq emas.

**Repoda kod bilan data birga ekan, adashib o'chirsam?**
GitHub'da har bir o'zgarish tarixi saqlanadi — eski holatni tiklash mumkin.
Xavotir bo'lsa, data'ni alohida private repoga ko'chirish mumkin (15 daqiqa ish).
