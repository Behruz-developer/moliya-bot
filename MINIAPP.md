# Telegram Mini App (Web App) — Moliya

Botga to'liq Telegram Mini App qo'shildi: 4 ekranli SPA ( Главная / Аналитика / Транзакции / Профиль ),
Telegram initData HMAC autentifikatsiyasi bilan. Dizayn — binafsha gradient, och lavanda fon, Inter shrift.

## Yangi fayllar

| Fayl | Vazifasi |
|---|---|
| `miniapp.py` | `/app` sahifa + `/api/*` marshrutlar + initData HMAC tekshiruvi |
| `miniapp.html` | SPA interfeys (barcha 4 ekran, RU/UZ i18n, bottom sheet-lar) |

## O'zgargan fayllar

- **`bot.py`** — Telegram Web App tugmalari:
  - pastdagi Telegram menyuga `MenuButtonWebApp` (📊 Moliya) — `post_init` ichida o'rnatiladi;
  - reply-klaviaturada `menyu_sahifa` → `menyu_app` (`KeyboardButton` + `web_app`);
  - har bir yozuv saqlangach javob ostida inline `web_app` tugma «📊 Hisobotni ko'rish»;
  - `/sahifa` endi **link yubormaydi** — Mini App'ni ochadigan tugma yuboradi; `/start` link yubormaydi.
- **`categories.py`** — yagona kategoriya ro'yxati (`KATEGORIYALAR`: kalit → uz/ru nom, icon, rang, tur)
  + eski nomlarni yangi kalitga mapping (OLD_TO_NEW), yangi kategoriya «Kafe va restoranlar» qo'shildi.
- **`data_store.py`** — har bir yozuv endi `id` bilan (yangi yozuvlarda avtomatik; eskilarda birinchi
  API murojaatida lazy-migratsiya). Yangi funksiyalar: `yozuvlar_id_bilan`, `yozuvni_ochirish_id`,
  `yozuvni_yangilash_id`. Botning indekslarga asoslangan eski funksiyalari o'zgarmadi.
- **`keep_alive.py`** — faqat `import miniapp; miniapp.register(app)` qo'shildi (eski sahifalar ishlaydi).

## API

Barcha so'rovlar sarlavha bilan: `Authorization: tma <Telegram.WebApp.initData>`.
Server initData'ni bot tokeni bilan HMAC-SHA256 (secret = HMAC("WebAppData", token)) tekshiradi,
`auth_date` 24 soatdan eskirgan bo'lsa — 401. Foydalanuvchi faqat o'z yozuvlarini ko'radi/tuzatadi.

| Metod | Yo'l | Tavsif |
|---|---|---|
| POST | `/api/me` | Profil (ism, username, photo), til, barcha yozuvlar, kategoriya meta |
| POST | `/api/settings` | `{"til": "uz"|"ru"}` — tilni saqlash |
| POST | `/api/transactions` | Yangi yozuv: `{turi, kategoriya, summa, izoh, sana?}` |
| PATCH | `/api/transactions/<id>` | Tahrirlash (faqat yuborilgan maydonlar) |
| DELETE | `/api/transactions/<id>` | O'chirish |
| POST | `/api/export` | `{tur: "all"|"income"|"expense", dan?, gacha?}` (YYYY-MM-DD) — filtrlangan yozuvlar stil berilgan **.xlsx** bo'lib **bot chatiga** `sendDocument` orqali yuboriladi (`xlsx_yoz.py`, faqat stdlib) |

Yozuv JSON: `{id, sana, vaqt, turi: "income"|"expense", kategoriya: <kalit>, summa: <int>, izoh}`.
Status «Зачислено/Выполнено» turi bo'yicha frontda chiqariladi — bazada saqlanmaydi.

## Eksport va tez summalar

- **Eksport UI:** Profil → «Excel fayl qilib olish» — tur chiplari (Hammasi/Daromad/Xarajat) + davr presetlari (Bugun, 7 kun, Shu oy, O'tgan oy, Shu yil, Barchasi) yoki custom sana oralig'i (dan/gacha). Fayl bot chatiga keladi (Telegram WebApp'da brauzer yuklab olishi ishonchsiz).
- **Tez summalar:** forma Summa maydoni ostida foydalanuvchining o'z tarixidan shu kategoriya (bo'sh bo'lsa tur bo'yicha) eng ko'p kiritilgan 4 ta summa chip sifatida; bosilganda inputga formatlangan holda yoziladi (Payme/Click uslubi).
- **Bot takroriy xabardan himoya:** bir xil yozuv 5 daqiqada ikki marta qo'shilmaydi (`bot.py:_oxirgi_qoshilgan`). Forma tugmasida ham debounce bor.
- **Hisobot so'rovlari:** botga "oxirgi haftadagi xarajatlar qancha" kabi ovozli/matnli so'rov yuborilsa, AI `turi="hisobot"` (+ davr, nima) qaytaradi va bot hisobot matnini chiqaradi.
- **Pastki tugmalar:** reply keyboard'da faqat «Moliya ilovasi» tugmasi qoldi; qolgan amallar ilova ichida (/balans, /oxirgi, /eksport, /tozalash buyruqlari ham ishlayveradi).

## Kategoriyalar (kalit: ru nom / rang)

salary (Зарплата, #2FBF71), bonus (Бонус, #F5A623), freelance (Фриланс, #4D9FFF),
gift_income (Подарок, #FF6B81), other_income (Другой доход, #B8B5E3),
groceries (Продукты, #6C5CE7), transport (Транспорт, #F5A623), cafe (Кафе и рестораны, #4D9FFF),
shopping (Покупки, #FF6B81), fun (Развлечения, #F5A623), home (Дом и ЖКХ, #00B894),
health (Здоровье, #FF7675), education (Образование, #6C5CE7), debt (Долги, #A0A6B8),
other_expense (Другое, #B8B5E3).
Eski nomlar (`Одежда`, `Коммунальные услуги` va h.k.) avtomatik mapping qilinadi.

## Muhit o'zgaruvchilari (.env)

- `TELEGRAM_BOT_TOKEN` — majburiy (imzo va getMe uchun).
- `PUBLIC_URL` yoki `RENDER_EXTERNAL_URL` — Mini App URL (`{PUBLIC_URL}/app`). HTTPS bo'lishi shart!
- `SUPPORT_URL` (ixtiyoriy) — «Помощь и поддержка» havolasi; bo'lmasa `https://t.me/behruz_frontend` ochiladi.

## Ishga tushirish (lokal)

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # tokenlarni to'ldiring
python bot.py         # bot + Flask (PORT, default 10000) birga ishlaydi
```

Test: `Mini App`ni Telegram'da oching (bot menyusi 📊 Moliya).

## VPS deploy (Ubuntu, nginx + systemd + HTTPS)

1. Kod: `git clone` → `/opt/moliya-bot`, venv yaratib `pip install -r requirements.txt`.
2. `.env` to'ldiring, `PUBLIC_URL=https://moliya.sizdomen.uz` qo'ying.
3. systemd (`/etc/systemd/system/moliya.service`):

```ini
[Unit]
Description=Moliya bot + Mini App
After=network.target

[Service]
WorkingDirectory=/opt/moliya-bot
Environment=PYTHONUNBUFFERED=1
ExecStart=/opt/moliya-bot/venv/bin/python bot.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable --now moliya
```

4. nginx (`/etc/nginx/sites-available/moliya`):

```nginx
server {
    listen 80;
    server_name moliya.sizdomen.uz;

    location / {
        proxy_pass http://127.0.0.1:10000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/moliya /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
sudo certbot --nginx -d moliya.sizdomen.uz   # HTTPS (Mini App uchun majburiy)
```

5. BotFather: hech narsa o'zgartirish shart emas — bot `post_init`da menyuni o'zi yangilaydi
   (yoki `/setmenubutton` bilan tekshirib ko'ring).

## Xavfsizlik

- Avtorizatsiya faqat initData imzosi orqali; ID URL'da yo'q.
- Server har bir so'rovda `user.id` bo'yicha filtrlaydi (client ishonchsiz).
- Faqat HTTPS; tokenlar `.env`da (gitga kirmaydi).
- `auth_date` 24 soat amal qiladi — eski initData rad etiladi.
