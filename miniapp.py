"""
Telegram Mini App (Web App) backend:
- /app — SPA sahifa (miniapp.html faylidan)
- /api/* — faqat Telegram initData (HMAC-SHA256) orqali autentifikatsiya.
Foydalanuvchi faqat o'z ma'lumotlarini ko'radi — filtr server tomonda.
"""
import hashlib
import hmac
import json
import logging
import os
import time
import urllib.parse
import urllib.request

from flask import Response, g, jsonify, request

import data_store
from categories import KATEGORIYALAR, kat_kalit

logger = logging.getLogger(__name__)

_AUTH_MAX_YOSH = 86400  # initData amal qilish muddati (24 soat)
_html_cache = None
_support_cache = {"url": None, "vaqt": 0.0}


def _bot_token() -> str:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


def _initdanni_tekshir(init_data: str):
    """Telegram initData HMAC imzosini tekshiradi. OK bo'lsa user dict qaytaradi."""
    if not init_data:
        logger.info("MiniApp auth: initData bo'sh (eski Telegram versiyasi?)")
        return None, "bosh"
    if not _bot_token():
        logger.info("MiniApp auth: TELEGRAM_BOT_TOKEN sozlanmagan")
        return None, "token"
    juftliklar = [p.split("=", 1) for p in init_data.split("&") if "=" in p]
    qiymatlar = {k: v for k, v in juftliklar if k != "hash"}
    hash_qs = next((v for k, v in juftliklar if k == "hash"), None)
    if not hash_qs:
        return None, "hash"
    data_check = "\n".join(f"{k}={qiymatlar[k]}" for k in sorted(qiymatlar))
    secret = hmac.new(b"WebAppData", _bot_token().encode(), hashlib.sha256).digest()
    hisob = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(hisob, hash_qs):
        logger.info("MiniApp auth: hash mos emas (server tokeni boshqacha?)")
        return None, "hash"
    try:
        auth_date = int(qiymatlar.get("auth_date", "0"))
    except ValueError:
        return None, "format"
    if auth_date < time.time() - _AUTH_MAX_YOSH:
        logger.info("MiniApp auth: auth_date eskirgan")
        return None, "eskirgan"
    try:
        user = json.loads(urllib.parse.unquote(qiymatlar.get("user", "{}")))
    except json.JSONDecodeError:
        return None, "user"
    if not user.get("id"):
        logger.info("MiniApp auth: user.id topilmadi")
        return None, "user"
    return user, ""


def _userdan():
    """So'rov sarlavhasini (Authorization: tma <initData>) tekshiradi yoki None."""
    auth = request.headers.get("Authorization", "")
    init_data = auth[4:] if auth.startswith("tma ") else ""
    user, sabab = _initdanni_tekshir(init_data)
    g.auth_sabab = sabab
    return user


def _auth_401():
    return jsonify({"ok": False, "xato": "auth", "sabab": getattr(g, "auth_sabab", "")}), 401


def _til(user) -> str:
    chat_id = user["id"]
    saqlangan = data_store._users_yukla().get(str(chat_id), {}).get("til")
    if saqlangan in ("uz", "ru"):
        return saqlangan
    lang = (user.get("language_code") or "").lower()
    return "ru" if lang.startswith("ru") else "uz"


def _yozuv_json(y: dict) -> dict:
    kalit = kat_kalit(y.get("kategoriya", ""))
    return {
        "id": y.get("id", ""),
        "sana": str(y.get("sana", ""))[:10],
        "vaqt": str(y.get("vaqt", ""))[:5],
        "turi": "income" if y.get("turi") == "Daromad" else "expense",
        "kategoriya": kalit,
        "summa": data_store._son_qil(y.get("summa", 0)),
        "izoh": (y.get("izoh") or "").strip(),
    }


def _profil(user) -> dict:
    chat_id = user["id"]
    til = _til(user)
    yozuvlar = data_store.yozuvlar_id_bilan(chat_id)
    ism = " ".join(x for x in (user.get("first_name", ""), user.get("last_name", "")) if x).strip()
    return {
        "ok": True,
        "lang": til,
        "user": {
            "id": chat_id,
            "ism": ism or "Foydalanuvchi",
            "username": user.get("username", ""),
            "photo": user.get("photo_url", ""),
        },
        "yozuvlar": [_yozuv_json(y) for y in reversed(yozuvlar)],
        "kategoriyalar": KATEGORIYALAR,
    }


def _support_url() -> str:
    url = os.getenv("SUPPORT_URL", "")
    if url:
        return url
    hozir = time.time()
    if _support_cache["url"] and hozir - _support_cache["vaqt"] < 3600:
        return _support_cache["url"]
    u = "https://t.me/telegram"
    try:
        sorov = urllib.request.Request(
            f"https://api.telegram.org/bot{_bot_token()}/getMe", timeout=5
        )
        javob = json.loads(urllib.request.urlopen(sorov).read())
        nom = javob.get("result", {}).get("username")
        if nom:
            u = f"https://t.me/{nom}"
    except Exception:
        logger.warning("getMe ishlamadi, default support url")
    _support_cache.update(url=u, vaqt=hozir)
    return u


def _html_olish() -> str:
    global _html_cache
    if _html_cache is None:
        yuli = os.path.join(os.path.dirname(os.path.abspath(__file__)), "miniapp.html")
        with open(yuli, encoding="utf-8") as f:
            _html_cache = f.read()
    return _html_cache.replace("@@SUPPORT_URL@@", _support_url())


def register(app):
    """Mini App marshrutlarini Flask ilovaga ulaydi."""

    @app.route("/app")
    def miniapp_sahifa():
        return Response(_html_olish(), mimetype="text/html")

    @app.route("/api/me", methods=["POST"])
    def api_me():
        user = _userdan()
        if not user:
            return _auth_401()
        return jsonify(_profil(user))

    @app.route("/api/settings", methods=["POST"])
    def api_settings():
        user = _userdan()
        if not user:
            return _auth_401()
        data = request.get_json(silent=True) or {}
        data_store.til_saqla(user["id"], data.get("til", ""))
        return jsonify({"ok": True, "lang": data_store.til_olish(user["id"])})

    def _kat_nomi(kalit) -> str:
        malumot = KATEGORIYALAR.get(kalit)
        return malumot["uz"] if malumot else "Boshqa harajat"

    def _summa_yaroqli(n) -> bool:
        try:
            return int(n) > 0
        except (ValueError, TypeError):
            return False

    @app.route("/api/transactions", methods=["POST"])
    def api_qosh():
        user = _userdan()
        if not user:
            return _auth_401()
        data = request.get_json(silent=True) or {}
        turi = data.get("turi")
        kalit = data.get("kategoriya")
        if turi not in ("income", "expense") or kalit not in KATEGORIYALAR:
            return jsonify({"ok": False, "xato": "maydon"}), 400
        if not _summa_yaroqli(data.get("summa")):
            return jsonify({"ok": False, "xato": "summa"}), 400
        natija = {
            "turi": "daromad" if turi == "income" else "harajat",
            "kategoriya": _kat_nomi(kalit),
            "summa": int(data["summa"]),
            "izoh": (data.get("izoh") or "").strip()[:60],
            "original_matn": "",
        }
        yozuv = data_store.yozuv_qosh(user["id"], natija)
        sana = str(data.get("sana") or "")[:10]
        if sana:
            data_store.yozuvni_yangilash_id(user["id"], yozuv["id"], {"sana": sana})
        yozuv = next(y for y in data_store.barchasi(user["id"]) if y.get("id") == yozuv["id"])
        return jsonify({"ok": True, "yozuv": _yozuv_json(yozuv)})

    @app.route("/api/transactions/<yozuv_id>", methods=["PATCH", "PUT"])
    def api_tuzatish(yozuv_id):
        user = _userdan()
        if not user:
            return _auth_401()
        data = request.get_json(silent=True) or {}
        o_zgarishlar = {}
        if data.get("turi") in ("income", "expense"):
            o_zgarishlar["turi"] = data["turi"]
        if data.get("kategoriya") in KATEGORIYALAR:
            o_zgarishlar["kategoriya"] = _kat_nomi(data["kategoriya"])
        if _summa_yaroqli(data.get("summa")):
            o_zgarishlar["summa"] = int(data["summa"])
        if data.get("izoh") is not None:
            o_zgarishlar["izoh"] = str(data["izoh"]).strip()[:60]
        if data.get("sana"):
            o_zgarishlar["sana"] = str(data["sana"])[:10]
        if not o_zgarishlar:
            return jsonify({"ok": False, "xato": "maydon"}), 400
        ok = data_store.yozuvni_yangilash_id(user["id"], yozuv_id, o_zgarishlar)
        if not ok:
            return jsonify({"ok": False, "xato": "topilmadi"}), 404
        yozuv = next(y for y in data_store.barchasi(user["id"]) if y.get("id") == yozuv_id)
        return jsonify({"ok": True, "yozuv": _yozuv_json(yozuv)})

    @app.route("/api/transactions/<yozuv_id>", methods=["DELETE"])
    def api_ochirish(yozuv_id):
        user = _userdan()
        if not user:
            return _auth_401()
        ok = data_store.yozuvni_ochirish_id(user["id"], yozuv_id)
        if not ok:
            return jsonify({"ok": False, "xato": "topilmadi"}), 404
        return jsonify({"ok": True})

    @app.errorhandler(404)
    def api_404(_e):
        if request.path.startswith("/api/"):
            return jsonify({"ok": False, "xato": "topilmadi"}), 404
        return "Topilmadi", 404
