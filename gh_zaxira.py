"""
Foydalanuvchi ma'lumotlarini GitHub repoga zaxiralash.

Render'da ephemeral disk tufayli har deploy ma'lumotlarni tozalaydi —
shuning uchun har bir o'zgarishdan keyin data fayllari repoga commit
qilib boriladi. Repodan yangi deploy chiqsa ham ma'lumotlar saqlanadi.

Muhit o'zgaruvchilari (.env / Render Environment):
- GITHUB_TOKEN — fine-grained PAT (moliya-bot repo: Contents Read/Write)
- GITHUB_REPO  — "owner/repo", masalan "Behruz-developer/moliya-bot"
"""
import base64
import json
import logging
import os
import threading
import urllib.request

logger = logging.getLogger(__name__)

_qulf = threading.Lock()
_kesh = {"sozlangan": None}


def _sozlanganmi():
    """GITHUB_TOKEN va GITHUB_REPO mavjud bo'lsa (repo, token) qaytaradi.
    Har chaqiruvda env'ni qayta o'qiydi (env keyin ham qo'yilishi mumkin)."""
    repo = (os.getenv("GITHUB_REPO") or "").strip()
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if repo and token:
        _kesh["sozlangan"] = (repo, token)
        return repo, token
    return None


def _api(url: str, method: str = "GET", body: dict = None, token: str = None):
    sorov = urllib.request.Request(url, method=method)
    sorov.add_header("Authorization", f"Bearer {token}")
    sorov.add_header("Accept", "application/vnd.github+json")
    sorov.add_header("User-Agent", "moliya-bot")
    data = None
    if body is not None:
        data = json.dumps(body).encode()
        sorov.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(sorov, data=data, timeout=20) as javob:
        return json.loads(javob.read().decode())


def faylni_zaxiralash(rel_yul: str, kontent: bytes, izoh: str):
    """Bitta faylni repoga commit qilib boradi (repo ildiziga nisbatan yo'l)."""
    sozl = _sozlanganmi()
    if not sozl:
        logger.debug("GitHub zaxira sozlanmagan (GITHUB_TOKEN/GITHUB_REPO yo'q)")
        return False
    repo, token = sozl
    url = f"https://api.github.com/repos/{repo}/contents/{rel_yul}"
    try:
        sha = None
        try:
            sha = _api(url, token=token).get("sha")
        except Exception:
            sha = None
        body = {"message": izoh, "content": base64.b64encode(kontent).decode()}
        if sha:
            body["sha"] = sha
        _api(url, method="PUT", body=body, token=token)
        logger.info("GitHub zaxira: %s (%d bayt)", rel_yul, len(kontent))
        return True
    except Exception as e:
        logger.warning("GitHub zaxira ishlamadi (%s): %s", rel_yul, e)
        # 409 (sha o'zgargan) bo'lsa — bir marta qayta urinib ko'ramiz
        try:
            sha = _api(url, token=token).get("sha")
            body = {"message": izoh, "content": base64.b64encode(kontent).decode(), "sha": sha}
            _api(url, method="PUT", body=body, token=token)
            logger.info("GitHub zaxira (2-urinish): %s (%d bayt)", rel_yul, len(kontent))
            return True
        except Exception as e2:
            logger.warning("GitHub zaxira 2-urinish ham ishlamadi (%s): %s", rel_yul, e2)
            return False


def fon_zaxira(rel_yul: str, kontent: bytes, izoh: str):
    """Zaxirani fon oqimida bajaradi — asosiy so'rovni sekinlashtirmasin."""
    threading.Thread(
        target=faylni_zaxiralash, args=(rel_yul, kontent, izoh), daemon=True
    ).start()
