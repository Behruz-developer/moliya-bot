# Daromad va harajat kategoriyalari (o'zbekcha va ruscha).
# Mini App uchun yagona ro'yxat: kalit -> nom (uz/ru), ikonka, rang.
# Kerak bo'lsa bu ro'yxatlarni o'zgartirishingiz mumkin.

DAROMAD_KATEGORIYALARI = [
    "Oylik",
    "Bonus",
    "Frilans/qo'shimcha ish",
    "Sovg'a",
    "Boshqa daromad",
]

HARAJAT_KATEGORIYALARI = [
    "Oziq-ovqat",
    "Transport",
    "Kafe va restoranlar",
    "Kommunal to'lovlar",
    "Kiyim-kechak",
    "Ko'ngilochar/Dam olish",
    "Sog'liq",
    "Ta'lim",
    "Uy-ro'zg'or",
    "Qarz/Kredit",
    "Boshqa harajat",
]

# Ruscha versiyalar (AI shulardan tanlaydi, agar user rus tilida yozsa)

DAROMAD_KATEGORIYALARI_RU = [
    "Зарплата",
    "Бонус",
    "Фриланс/подработка",
    "Подарок",
    "Другой доход",
]

HARAJAT_KATEGORIYALARI_RU = [
    "Продукты",
    "Транспорт",
    "Кафе и рестораны",
    "Коммунальные услуги",
    "Одежда",
    "Развлечения/Отдых",
    "Здоровье",
    "Образование",
    "Дом/Быт",
    "Долг/Кредит",
    "Другие расходы",
]

# ============ Mini App uchun yagona kategoriyalar (kalit bo'yicha) ============
# icon — miniapp.html dagi SVG ikonka nomi; color — accent rang.

KATEGORIYALAR = {
    # --- daromadlar ---
    "salary":        {"uz": "Oylik",                  "ru": "Зарплата",        "icon": "briefcase", "color": "#2FBF71", "tur": "daromad"},
    "bonus":         {"uz": "Bonus",                  "ru": "Бонус",           "icon": "gift",      "color": "#F5A623", "tur": "daromad"},
    "freelance":     {"uz": "Frilans/qo'shimcha ish", "ru": "Фриланс",         "icon": "laptop",    "color": "#4D9FFF", "tur": "daromad"},
    "gift_income":   {"uz": "Sovg'a",                 "ru": "Подарок",         "icon": "gift",      "color": "#FF6B81", "tur": "daromad"},
    "other_income":  {"uz": "Boshqa daromad",         "ru": "Другой доход",    "icon": "dots",      "color": "#B8B5E3", "tur": "daromad"},
    # --- harajatlar ---
    "groceries":     {"uz": "Oziq-ovqat",             "ru": "Продукты",        "icon": "cart",      "color": "#6C5CE7", "tur": "harajat"},
    "transport":     {"uz": "Transport",              "ru": "Транспорт",       "icon": "car",       "color": "#F5A623", "tur": "harajat"},
    "cafe":          {"uz": "Kafe va restoranlar",    "ru": "Кафе и рестораны","icon": "cup",       "color": "#4D9FFF", "tur": "harajat"},
    "shopping":      {"uz": "Kiyim-kechak",           "ru": "Покупки",         "icon": "bag",       "color": "#FF6B81", "tur": "harajat"},
    "fun":           {"uz": "Ko'ngilochar",           "ru": "Развлечения",     "icon": "game",      "color": "#F5A623", "tur": "harajat"},
    "home":          {"uz": "Uy va kommunal",         "ru": "Дом и ЖКХ",       "icon": "home",      "color": "#00B894", "tur": "harajat"},
    "health":        {"uz": "Sog'liq",                "ru": "Здоровье",        "icon": "heart",     "color": "#FF7675", "tur": "harajat"},
    "education":     {"uz": "Ta'lim",                 "ru": "Образование",     "icon": "book",      "color": "#6C5CE7", "tur": "harajat"},
    "debt":          {"uz": "Qarz/Kredit",            "ru": "Долги",           "icon": "card",      "color": "#A0A6B8", "tur": "harajat"},
    "other_expense": {"uz": "Boshqa harajat",         "ru": "Другое",          "icon": "dots",      "color": "#B8B5E3", "tur": "harajat"},
}

# Eski (yozuvlarda saqlangan) nomlar -> yangi kalit. Har ikki tildagi nomlar.
OLD_TO_NEW = {
    # daromad
    "Oylik": "salary", "Зарплата": "salary",
    "Bonus": "bonus", "Бонус": "bonus",
    "Frilans/qo'shimcha ish": "freelance", "Frilans": "freelance", "Фриланс/подработка": "freelance", "Фриланс": "freelance",
    "Sovg'a": "gift_income", "Подарок": "gift_income",
    "Boshqa daromad": "other_income", "Другой доход": "other_income",
    # harajat
    "Oziq-ovqat": "groceries", "Продукты": "groceries",
    "Transport": "transport", "Транспорт": "transport",
    "Kafe va restoranlar": "cafe", "Кафе и рестораны": "cafe",
    "Kiyim-kechak": "shopping", "Одежда": "shopping", "Покупки": "shopping",
    "Ko'ngilochar/Dam olish": "fun", "Ko'ngilochar": "fun", "Развлечения/Отдых": "fun", "Развлечения": "fun",
    "Kommunal to'lovlar": "home", "Коммунальные услуги": "home",
    "Uy-ro'zg'or": "home", "Дом/Быт": "home", "Дом и ЖКХ": "home",
    "Sog'liq": "health", "Здоровье": "health",
    "Ta'lim": "education", "Образование": "education",
    "Qarz/Kredit": "debt", "Долг/Кредит": "debt", "Долги": "debt",
    "Boshqa harajat": "other_expense", "Другие расходы": "other_expense", "Другое": "other_expense",
}


def kat_kalit(nom) -> str:
    """Yozuvdagi kategoriya nomini (eski ham, yangi ham) kalitga aylantiradi."""
    return OLD_TO_NEW.get(str(nom).strip(), "other_expense")


def kat_turi(nom) -> str:
    """Kategoriya nomi bo'yicha turi: 'daromad' yoki 'harajat'."""
