"""
Dashboard serveri: har bir foydalanuvchi uchun zamonaviy, responsive
moliyaviy sahifa (dark/light, ikki til, grafiklar, sana filtri, pagination).
Flask lokalda o'rnatilmagan bo'lsa — import xatosiz o'tadi.
"""
import os
import csv
import io
import json
from threading import Thread
from flask import Flask, Response

import data_store

app = Flask(__name__)

# ============================ TARJIMALAR ============================

D = {
    "uz": {
        "app_name": "Moliya",
        "balans": "Balans",
        "umumiy_daromad": "Daromad",
        "umumiy_harajat": "Harajat",
        "oy_daromad": "Oy daromad",
        "oy_harajat": "Oy harajat",
        "oy_balans": "Oy balans",
        "som": "so'm",
        "trend_title": "Oxirgi 6 oy",
        "donut_title": "Harajat kategoriyalari",
        "donut_empty": "Harajat ma'lumoti yo'q",
        "kat_title": "Kategoriya reytingi",
        "rec_title": "Yozuvlar",
        "rec_empty": "Yozuv topilmadi",
        "hamma": "Hammasi",
        "daromad": "Daromad",
        "harajat": "Harajat",
        "bugun": "Bugun",
        "hafta": "Hafta",
        "oy": "Oy",
        "barchasi": "Barcha davr",
        "sanadan": "Sanadan",
        "sanagacha": "Sanagacha",
        "csv": "CSV",
        "yozuvlar_btn": "Yozuvlar",
        "orqaga": "Orqaga",
        "keyingi": "Keyingi",
        "oldingi": "Oldingi",
        "sahifa_lbl": "{p} / {j} sahifa",
        "kat_filtr": "Kategoriya",
        "hint_dash": "Yozuv qo'shish: botga matn yoki ovoz yuboring",
        "hint_rec": "Yozuv qo'shish: botga matn yoki ovoz yuboring",
    },
    "ru": {
        "app_name": "Финансы",
        "balans": "Баланс",
        "umumiy_daromad": "Доход",
        "umumiy_harajat": "Расход",
        "oy_daromad": "Доход за месяц",
        "oy_harajat": "Расход за месяц",
        "oy_balans": "Баланс за месяц",
        "som": "сум",
        "trend_title": "Последние 6 месяцев",
        "donut_title": "Категории расходов",
        "donut_empty": "Нет данных о расходах",
        "kat_title": "Рейтинг категорий",
        "rec_title": "Записи",
        "rec_empty": "Записи не найдены",
        "hamma": "Все",
        "daromad": "Доход",
        "harajat": "Расход",
        "bugun": "Сегодня",
        "hafta": "Неделя",
        "oy": "Месяц",
        "barchasi": "Всё время",
        "sanadan": "С даты",
        "sanagacha": "По дату",
        "csv": "CSV",
        "yozuvlar_btn": "Записи",
        "orqaga": "Назад",
        "keyingi": "Далее",
        "oldingi": "Назад",
        "sahifa_lbl": "Стр. {p} / {j}",
        "kat_filtr": "Категория",
        "hint_dash": "Добавить запись: напишите боту текст или голос",
        "hint_rec": "Добавить запись: напишите боту текст или голос",
    },
}

OYLAR = {
    "uz": ["Yan", "Fev", "Mar", "Apr", "May", "Iyn", "Iyl", "Avg", "Sen", "Okt", "Noy", "Dek"],
    "ru": ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"],
}


def _malumotlar_json(chat_id) -> str:
    yozuvlar = data_store.barchasi(chat_id)
    royxat = []
    for y in reversed(yozuvlar):
        try:
            summa = data_store._son_qil(y["summa"])
        except Exception:
            summa = 0
        royxat.append({
            "sana": str(y["sana"])[:10],
            "vaqt": str(y["vaqt"])[:5],
            "turi": y["turi"],
            "kategoriya": y["kategoriya"],
            "summa": summa,
            "izoh": y.get("izoh") or "",
        })
    return json.dumps(royxat, ensure_ascii=False)# ============================ UMUMIY CSS ============================

_CSS = """
:root{
  --bg:#f1f5f9; --card:#ffffff; --card2:#f1f5f9; --border:#e2e8f0;
  --text:#0f172a; --muted:#64748b; --accent:#6366f1;
  --pos:#059669; --neg:#dc2626; --shadow:0 8px 24px rgba(15,23,42,.08);
  --grad:linear-gradient(135deg,#6366f1,#8b5cf6);
}
[data-theme="dark"]{
  --bg:#0b1220; --card:#151e31; --card2:#1b2540; --border:#233047;
  --text:#e7edf7; --muted:#8b97ad;
  --pos:#34d399; --neg:#f87171; --shadow:0 10px 30px rgba(0,0,0,.35);
}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,sans-serif;background:var(--bg);color:var(--text);min-height:100vh;transition:background .3s,color .3s}
.wrap{max-width:1080px;margin:0 auto;padding:20px 16px 48px}
.top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:20px;flex-wrap:wrap}
.logo{display:flex;align-items:center;gap:12px}
.logo .mark{width:42px;height:42px;border-radius:13px;background:var(--grad);display:flex;align-items:center;justify-content:center;font-size:21px;box-shadow:var(--shadow)}
.logo h1{font-size:19px;font-weight:800;letter-spacing:-.3px}
.logo h1 span{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.top-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.iconbtn{min-width:40px;height:40px;padding:0 12px;border-radius:12px;background:var(--card);border:1px solid var(--border);color:var(--text);font-size:15px;cursor:pointer;display:flex;align-items:center;justify-content:center;gap:6px;transition:transform .15s,box-shadow .15s;text-decoration:none;font-weight:600;font-family:inherit}
.iconbtn:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
.abtn{display:inline-flex;align-items:center;gap:8px;background:var(--grad);color:#fff;text-decoration:none;font-weight:700;font-size:13px;padding:10px 15px;border-radius:12px;box-shadow:var(--shadow);transition:transform .15s,opacity .15s;border:none;cursor:pointer;font-family:inherit}
.abtn:hover{transform:translateY(-2px)}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:12px;margin-bottom:16px}
.card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:16px;box-shadow:var(--shadow)}
.kpi .lbl{font-size:11px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.5px;display:flex;align-items:center;gap:7px}
.kpi .ico{width:30px;height:30px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:14px;margin-left:auto;flex-shrink:0}
.kpi .val{font-size:22px;font-weight:800;margin-top:8px;letter-spacing:-.4px;font-variant-numeric:tabular-nums}
.ico.b{background:rgba(99,102,241,.14)} .ico.g{background:rgba(16,185,129,.14)} .ico.r{background:rgba(239,68,68,.14)}
.pos{color:var(--pos)} .neg{color:var(--neg)} .neu{color:var(--accent)}
.sec{margin-top:16px}
.sec h2{font-size:12px;font-weight:700;color:var(--muted);margin:0 2px 10px;display:flex;align-items:center;gap:7px;text-transform:uppercase;letter-spacing:.5px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}
.filters{display:flex;gap:8px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.chip{border:1px solid var(--border);background:var(--card);color:var(--text);font-size:12.5px;font-weight:600;padding:7px 13px;border-radius:99px;cursor:pointer;transition:all .15s;font-family:inherit}
.chip:hover{border-color:var(--accent)}
.chip.on{background:var(--grad);border-color:transparent;color:#fff}
select.chip,input.chip{appearance:none;padding-right:10px}
input.chip{color-scheme:light dark}
"""
_CSS += """
.bars{display:flex;align-items:flex-end;justify-content:space-around;gap:12px;height:170px;padding:6px 2px 0}
.bargrp{display:flex;flex-direction:column;align-items:center;gap:7px;flex:1;max-width:90px;height:100%;justify-content:flex-end}
.barcol{display:flex;align-items:flex-end;gap:4px;height:100%;width:100%;justify-content:center}
.bar{width:15px;border-radius:6px 6px 2px 2px;min-height:3px;transition:height 1s cubic-bezier(.22,1,.36,1)}
.bar.in{background:linear-gradient(180deg,#34d399,#059669)}
.bar.out{background:linear-gradient(180deg,#f87171,#dc2626)}
.bargrp .m{font-size:11px;color:var(--muted);font-weight:600}
.barleg{display:flex;gap:14px;justify-content:center;margin-top:10px;font-size:11.5px;color:var(--muted)}
.barleg span{display:flex;align-items:center;gap:6px}
.barleg i{width:10px;height:10px;border-radius:3px;display:inline-block}
.barleg .in{background:#34d399}.barleg .out{background:#f87171}
.donut-wrap{display:flex;align-items:center;gap:20px;flex-wrap:wrap;justify-content:center}
.legend{display:flex;flex-direction:column;gap:8px;min-width:160px}
.legend .li{display:flex;align-items:center;gap:8px;font-size:12.5px}
.legend .dot{width:10px;height:10px;border-radius:3px;flex-shrink:0}
.legend .nm{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:140px}
.legend .pc{color:var(--muted);font-variant-numeric:tabular-nums}
circle{transition:stroke-dashoffset 1s cubic-bezier(.22,1,.36,1)}
.katrow{display:grid;grid-template-columns:26px minmax(0,1fr) 100px 54px;gap:4px 10px;align-items:center;padding:9px 0;border-bottom:1px solid var(--border)}
.katrow:last-child{border-bottom:none}
.katrow .rn{width:24px;height:24px;border-radius:8px;background:var(--card2);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:10.5px;font-weight:700;color:var(--muted)}
.katrow .nm{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.katrow .barbg{grid-column:1/3;height:7px;background:var(--card2);border-radius:6px;overflow:hidden;margin-top:2px}
.katrow .barbg>div{height:100%;border-radius:6px;background:var(--grad);width:0;transition:width 1s cubic-bezier(.22,1,.36,1)}
.katrow .sm{font-weight:700;font-size:12px;text-align:right;font-variant-numeric:tabular-nums}
.katrow .pc{color:var(--muted);font-size:11.5px;text-align:right;font-variant-numeric:tabular-nums}
.rec{display:flex;align-items:center;gap:11px;padding:12px 2px;border-bottom:1px solid var(--border);animation:fadein .35s both}
.rec:last-child{border-bottom:none}
.rec .em{width:38px;height:38px;border-radius:11px;display:flex;align-items:center;justify-content:center;font-size:16px;flex-shrink:0}
.em.g{background:rgba(16,185,129,.13)} .em.r{background:rgba(239,68,68,.13)}
.rec .mid{flex:1;min-width:0}
.rec .t1{font-size:13.5px;font-weight:650;display:flex;gap:7px;align-items:center;flex-wrap:wrap}
.rec .badge{font-size:10px;padding:2px 7px;border-radius:6px;font-weight:700}
.badge.g{background:rgba(16,185,129,.15);color:var(--pos)} .badge.r{background:rgba(239,68,68,.15);color:var(--neg)}
.rec .t2{font-size:11.5px;color:var(--muted);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rec .amt{font-weight:800;font-size:14px;white-space:nowrap;font-variant-numeric:tabular-nums}
.dayhead{font-size:11px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin:14px 2px 2px}
.empty{text-align:center;padding:30px 10px;color:var(--muted)}
.empty .big{font-size:36px;margin-bottom:8px}
.pager{display:flex;gap:8px;align-items:center;justify-content:center;margin-top:16px}
.pager .pg-info{font-size:13px;color:var(--muted);font-weight:600;min-width:100px;text-align:center}
.footer{text-align:center;color:var(--muted);font-size:11.5px;margin-top:24px}
@keyframes fadein{from{opacity:0;transform:translateY(5px)}to{opacity:1;transform:none}}
@media(max-width:560px){
  .kpi .val{font-size:19px}
  .bar{width:11px}
  .katrow .sm{font-size:11px} .katrow .pc{font-size:10.5px}
}
"""# ============================ UMUMIY JS ============================

_JS_COMMON = """
const Y = @@JSON@@;
const T = {uz: @@TUZ@@, ru: @@TRU@@};
const OY = {uz: @@OYUZ@@, ru: @@OYRU@@};
let lang = localStorage.getItem('moliya_lang') || '@@DEFLANG@@';
if(!T[lang]) lang = 'uz';
let t = T[lang];
const el = id => document.getElementById(id);
const fmtS = n => String(n||0).replace(/\\B(?=(\\d{3})+(?!\\d))/g, ' ') + ' ' + t.som;

// --- Tema (default: light) ---
let theme = localStorage.getItem('moliya_theme') || 'light';
function temaQoy(){
  document.body.dataset.theme = theme;
  const b = el('themeBtn'); if(b) b.textContent = theme === 'dark' ? '☀️' : '🌙';
}
temaQoy();
if(el('themeBtn')) el('themeBtn').onclick = () => {
  theme = theme === 'dark' ? 'light' : 'dark';
  localStorage.setItem('moliya_theme', theme);
  temaQoy();
};

// --- Til ---
function tilQoy(){
  t = T[lang];
  document.querySelectorAll('[data-t]').forEach(e => { e.textContent = T[lang][e.dataset.t] || e.textContent; });
  const b = el('langBtn'); if(b) b.textContent = lang === 'uz' ? '🇺🇿' : '🇷🇺';
  renderAll();
}
if(el('langBtn')) el('langBtn').onclick = () => {
  lang = lang === 'uz' ? 'ru' : 'uz';
  localStorage.setItem('moliya_lang', lang);
  tilQoy();
};

// --- Sanalar ---
const NOW = new Date();
const OYBOSHI = NOW.toISOString().slice(0,7);
const bugunStr = NOW.toISOString().slice(0,10);
const HAFTA = new Date(NOW); HAFTA.setDate(NOW.getDate() - ((NOW.getDay()+6)%7));
const haftaStr = HAFTA.toISOString().slice(0,10);

// --- Umumiy filtr ---
let fDavr = 'barchasi', fFrom = null, fTo = null;
function filtrQil(y){
  if(fDavr === 'bugun' && y.sana !== bugunStr) return false;
  if(fDavr === 'hafta' && y.sana < haftaStr) return false;
  if(fDavr === 'oy' && y.sana < OYBOSHI) return false;
  if(fFrom && y.sana < fFrom) return false;
  if(fTo && y.sana > fTo) return false;
  return true;
}
function summa(f, turi){
  return Y.filter(y => f(y) && (turi ? y.turi === turi : true)).reduce((s,y)=>s+y.summa,0);
}
const KAT_RANGLAR = ['#6366f1','#8b5cf6','#ec4899','#f59e0b','#10b981','#06b6d4','#ef4444','#84cc16','#a855f7','#64748b'];
"""# ============================ DASHBOARD SAHIFASI ============================

DASH_HTML = """<!doctype html>
<html lang="@@LANG@@">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@APP_NAME@@</title>
<style>@@CSS@@</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="logo">
      <div class="mark">💰</div>
      <h1><span class="appName">@@APP_NAME@@</span> Dashboard</h1>
    </div>
    <div class="top-actions">
      <button class="iconbtn" id="langBtn">🇺🇿</button>
      <button class="iconbtn" id="themeBtn">🌙</button>
      <a class="iconbtn" href="/u/@@CHAT_ID@@/yozuvlar">📋 <span data-t="yozuvlar_btn"></span></a>
      <a class="abtn" href="/u/@@CHAT_ID@@/csv">⬇ <span data-t="csv"></span></a>
    </div>
  </div>

  <div class="card sec" style="margin-top:0">
    <div class="filters" id="filters" style="margin-bottom:0">
      <button class="chip on" data-davr="barchasi" data-t="barchasi"></button>
      <button class="chip" data-davr="oy" data-t="oy"></button>
      <button class="chip" data-davr="hafta" data-t="hafta"></button>
      <button class="chip" data-davr="bugun" data-t="bugun"></button>
      <input class="chip" type="date" id="fromD" title="@@SANADAN@@">
      <span style="color:var(--muted)">–</span>
      <input class="chip" type="date" id="toD" title="@@SANAGACHA@@">
    </div>
  </div>

  <div class="kpi" id="kpi" style="margin-top:14px"></div>

  <div class="grid2">
    <div class="card sec">
      <h2>📊 <span data-t="trend_title"></span></h2>
      <div class="bars" id="bars"></div>
      <div class="barleg">
        <span><i class="in"></i><span data-t="daromad"></span></span>
        <span><i class="out"></i><span data-t="harajat"></span></span>
      </div>
    </div>
    <div class="card sec">
      <h2>🍩 <span data-t="donut_title"></span></h2>
      <div class="donut-wrap" id="donutWrap"></div>
    </div>
  </div>

  <div class="card sec">
    <h2>🏆 <span data-t="kat_title"></span></h2>
    <div id="katList"></div>
  </div>

  <div class="footer" data-t="hint_dash"></div>
</div>

<script>@@JS_COMMON@@
@@JS_DASH@@
</script>
</body>
</html>"""# ============================ YOZUVLAR SAHIFASI ============================

REC_HTML = """<!doctype html>
<html lang="@@LANG@@">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@APP_NAME@@</title>
<style>@@CSS@@</style>
</head>
<body>
<div class="wrap">
  <div class="top">
    <div class="logo">
      <a class="iconbtn" href="/u/@@CHAT_ID@@">← <span data-t="orqaga"></span></a>
      <h1>📋 <span class="appName">@@APP_NAME@@</span></h1>
    </div>
    <div class="top-actions">
      <button class="iconbtn" id="langBtn">🇺🇿</button>
      <button class="iconbtn" id="themeBtn">🌙</button>
    </div>
  </div>

  <div class="card sec" style="margin-top:0">
    <div class="filters" id="filters" style="margin-bottom:0">
      <button class="chip on" data-davr="barchasi" data-t="barchasi"></button>
      <button class="chip" data-davr="oy" data-t="oy"></button>
      <button class="chip" data-davr="hafta" data-t="hafta"></button>
      <button class="chip" data-davr="bugun" data-t="bugun"></button>
      <input class="chip" type="date" id="fromD" title="@@SANADAN@@">
      <span style="color:var(--muted)">–</span>
      <input class="chip" type="date" id="toD" title="@@SANAGACHA@@">
      <button class="chip on" data-tur="hamma" data-t="hamma"></button>
      <button class="chip" data-tur="Daromad">🟢 <span data-t="daromad"></span></button>
      <button class="chip" data-tur="Harajat">🔴 <span data-t="harajat"></span></button>
      <select class="chip" id="selKat"></select>
    </div>
  </div>

  <div class="card sec" style="margin-top:14px">
    <h2>🧾 <span data-t="rec_title"></span> · <span id="recCount"></span></h2>
    <div id="recList"></div>
    <div class="pager" id="pager" style="display:none">
      <button class="chip" id="prevBtn">‹ <span data-t="oldingi"></span></button>
      <div class="pg-info" id="pgInfo"></div>
      <button class="chip" id="nextBtn"><span data-t="keyingi"></span> ›</button>
    </div>
  </div>

  <div class="footer" data-t="hint_rec"></div>
</div>

<script>@@JS_COMMON@@
@@JS_REC@@
</script>
</body>
</html>"""# ============================ DASHBOARD JS ============================

_JS_DASH = """
function kpiCard(lbl, val, cls, ico, icoCls){
  return `<div class="card"><div class="lbl">${lbl}<span class="ico ${icoCls}">${ico}</span></div><div class="val ${cls}">${val}</div></div>`;
}
function renderKPI(){
  const f = filtrQil;
  const d = summa(f,'Daromad'), h = summa(f,'Harajat');
  const fOy = y => f(y) && y.sana >= OYBOSHI;
  const oyD = summa(fOy,'Daromad'), oyH = summa(fOy,'Harajat');
  el('kpi').innerHTML =
    kpiCard(t.balans, fmtS(d-h), (d-h)>=0?'neu':'neg', '💼','b') +
    kpiCard(t.umumiy_daromad, fmtS(d), 'pos', '🟢','g') +
    kpiCard(t.umumiy_harajat, fmtS(h), 'neg', '🔴','r') +
    kpiCard(t.oy_daromad, fmtS(oyD), 'pos', '📅','g') +
    kpiCard(t.oy_harajat, fmtS(oyH), 'neg', '📅','r') +
    kpiCard(t.oy_balans, fmtS(oyD-oyH), (oyD-oyH)>=0?'neu':'neg', '🗓','b');
}
function renderTrend(){
  const oylarArr = [];
  for(let i=5;i>=0;i--){
    const d = new Date(NOW.getFullYear(), NOW.getMonth()-i, 1);
    const key = d.toISOString().slice(0,7);
    oylarArr.push({ nom: oy[d.getMonth()],
      daromad: summa(y=>y.sana.startsWith(key),'Daromad'),
      harajat: summa(y=>y.sana.startsWith(key),'Harajat') });
  }
  const maxBar = Math.max(...oylarArr.map(o=>Math.max(o.daromad,o.harajat)), 1);
  el('bars').innerHTML = oylarArr.map(o=>`
    <div class="bargrp">
      <div class="barcol">
        <div class="bar in" style="height:${Math.round(o.daromad/maxBar*100)}%" title="${t.daromad}: ${fmtS(o.daromad)}"></div>
        <div class="bar out" style="height:${Math.round(o.harajat/maxBar*100)}%" title="${t.harajat}: ${fmtS(o.harajat)}"></div>
      </div>
      <div class="m">${o.nom}</div>
    </div>`).join('');
}
function renderDonut(){
  const kat = {};
  Y.filter(y=>y.turi==='Harajat' && filtrQil(y)).forEach(y=>kat[y.kategoriya]=(kat[y.kategoriya]||0)+y.summa);
  const items = Object.entries(kat).sort((a,b)=>b[1]-a[1]);
  if(!items.length){
    el('donutWrap').innerHTML = `<div class="empty"><div class="big">🍩</div>${t.donut_empty}</div>`;
    return;
  }
  const jami = items.reduce((s,i)=>s+i[1],0);
  let acc = 0; const C = 2*Math.PI*54;
  const segs = items.slice(0,9).map((it,i)=>{
    const frac = it[1]/jami;
    const seg = `<circle r="54" cx="80" cy="80" fill="none" stroke="${KAT_RANGLAR[i%KAT_RANGLAR.length]}" stroke-width="26"
      stroke-dasharray="${(frac*C).toFixed(2)} ${C.toFixed(2)}" stroke-dashoffset="${(-acc*C).toFixed(2)}"></circle>`;
    acc += frac;
    return seg;
  }).join('');
  const legend = items.slice(0,9).map((it,i)=>`
    <div class="li"><span class="dot" style="background:${KAT_RANGLAR[i%KAT_RANGLAR.length]}"></span>
    <span class="nm">${it[0]}</span><span class="pc">${Math.round(it[1]/jami*100)}%</span></div>`).join('');
  el('donutWrap').innerHTML = `
    <svg width="150" height="150" viewBox="0 0 160 160" style="transform:rotate(-90deg)">
      <circle r="54" cx="80" cy="80" fill="none" stroke="var(--card2)" stroke-width="26"></circle>${segs}
    </svg>
    <div class="legend">${legend}</div>`;
}
function renderKat(){
  const kat = {};
  Y.filter(filtrQil).forEach(y=>{
    if(!kat[y.kategoriya]) kat[y.kategoriya]={d:0,h:0};
    if(y.turi==='Daromad') kat[y.kategoriya].d+=y.summa; else kat[y.kategoriya].h+=y.summa;
  });
  const items = Object.entries(kat).sort((a,b)=>(b[1].d+b[1].h)-(a[1].d+a[1].h));
  if(!items.length){ el('katList').innerHTML = `<div class="empty"><div class="big">📭</div>${t.rec_empty}</div>`; return; }
  const jami = items.reduce((s,i)=>s+i[1].d+i[1].h,0);
  const maxKat = items[0][1].d + items[0][1].h;
  el('katList').innerHTML = items.map((it,i)=>{
    const j = it[1].d+it[1].h;
    return `<div class="katrow">
      <div class="rn">${i+1}</div>
      <div class="nm">${it[0]}</div>
      <div class="sm">${fmtS(j)}</div>
      <div class="pc">${Math.round(j/jami*100)}%</div>
      <div class="barbg"><div data-w="${Math.round(j/maxKat*100)}"></div></div>
    </div>`;
  }).join('');
  requestAnimationFrame(()=>document.querySelectorAll('.barbg>div').forEach(d=>{ d.style.width = d.dataset.w + '%'; }));
}
function renderAll(){ tilQoyStatik(); renderKPI(); renderTrend(); renderDonut(); renderKat(); }
function tilQoyStatik(){}
el('filters').addEventListener('click', e=>{
  const b = e.target.closest('button.chip');
  if(!b) return;
  el('filters').querySelectorAll('button.chip[data-davr]').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  fDavr = b.dataset.davr; fFrom = null; fTo = null;
  el('fromD').value = ''; el('toD').value = '';
  renderAll();
});
el('fromD').onchange = e=>{ fFrom = e.target.value || null; el('filters').querySelectorAll('button.chip[data-davr]').forEach(x=>x.classList.remove('on')); renderAll(); };
el('toD').onchange = e=>{ fTo = e.target.value || null; el('filters').querySelectorAll('button.chip[data-davr]').forEach(x=>x.classList.remove('on')); renderAll(); };
renderAll();
"""# ============================ YOZUVLAR SAHIFASI JS ============================

_JS_REC = """
const HAR_BETDA = 12;
const kategoriyalar = [...new Set(Y.map(y=>y.kategoriya))];
let fTur = 'hamma', fKat = 'hamma', bet = 1;

function renderFiltrKat(){
  el('selKat').innerHTML = `<option value="hamma">${t.kat_filtr}: ${t.hamma}</option>` +
    kategoriyalar.map(k=>`<option value="${k}">${k}</option>`).join('');
  el('selKat').value = fKat;
}
function filtered(){
  return Y.filter(y=>{
    if(!filtrQil(y)) return false;
    if(fTur!=='hamma' && y.turi!==fTur) return false;
    if(fKat!=='hamma' && y.kategoriya!==fKat) return false;
    return true;
  });
}
function recHtml(y){
  const d = y.turi==='Daromad';
  return `<div class="rec">
    <div class="em ${d?'g':'r'}">${d?'🟢':'🔴'}</div>
    <div class="mid">
      <div class="t1">${y.kategoriya}<span class="badge ${d?'g':'r'}">${d?t.daromad:t.harajat}</span></div>
      <div class="t2">${y.sana} · ${y.vaqt}${y.izoh?' · '+y.izoh:''}</div>
    </div>
    <div class="amt ${d?'pos':'neg'}">${d?'+':'−'} ${fmtS(y.summa)}</div>
  </div>`;
}
function renderList(){
  const r = filtered();
  const jamiBet = Math.max(1, Math.ceil(r.length/HAR_BETDA));
  if(bet > jamiBet) bet = jamiBet;
  el('recCount').textContent = String(r.length);
  if(!r.length){
    el('recList').innerHTML = `<div class="empty"><div class="big">📭</div>${t.rec_empty}</div>`;
    el('pager').style.display = 'none';
    return;
  }
  const boshi = (bet-1)*HAR_BETDA;
  const betdagi = r.slice(boshi, boshi+HAR_BETDA);
  const guruh = {};
  betdagi.forEach(y=>{ (guruh[y.sana]=guruh[y.sana]||[]).push(y); });
  el('recList').innerHTML = Object.keys(guruh).sort().reverse().map(sana=>{
    const head = sana===bugunStr ? `☀️ ${t.bugun}` : sana;
    return `<div class="dayhead">${head}</div>` + guruh[sana].map(recHtml).join('');
  }).join('');
  el('pager').style.display = 'flex';
  el('pgInfo').textContent = t.sahifa_lbl.replace('{p}', bet).replace('{j}', jamiBet);
  el('prevBtn').style.visibility = bet > 1 ? 'visible' : 'hidden';
  el('nextBtn').style.visibility = bet < jamiBet ? 'visible' : 'hidden';
}
function renderAll(){ tilQoyStatik(); renderFiltrKat(); renderList(); }
function tilQoyStatik(){}
el('filters').addEventListener('click', e=>{
  const b = e.target.closest('button.chip');
  if(!b) return;
  if(b.dataset.davr !== undefined){
    el('filters').querySelectorAll('button.chip[data-davr]').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    fDavr = b.dataset.davr; fFrom = null; fTo = null;
    el('fromD').value = ''; el('toD').value = '';
  } else {
    el('filters').querySelectorAll('button.chip[data-tur]').forEach(x=>x.classList.remove('on'));
    b.classList.add('on');
    fTur = b.dataset.tur;
  }
  bet = 1; renderList();
});
el('fromD').onchange = e=>{ fFrom = e.target.value || null; el('filters').querySelectorAll('button.chip[data-davr]').forEach(x=>x.classList.remove('on')); bet = 1; renderList(); };
el('toD').onchange = e=>{ fTo = e.target.value || null; el('filters').querySelectorAll('button.chip[data-davr]').forEach(x=>x.classList.remove('on')); bet = 1; renderList(); };
el('selKat').onchange = e=>{ fKat = e.target.value; bet = 1; renderList(); };
el('prevBtn').onclick = ()=>{ if(bet>1){ bet--; renderList(); window.scrollTo({top:0,behavior:'smooth'}); } };
el('nextBtn').onclick = ()=>{ bet++; renderList(); window.scrollTo({top:0,behavior:'smooth'}); };
renderAll();
"""# ============================ ROUTELAR ============================

def _html_tayyorla(tmpl, chat_id, js_page) -> str:
    til = data_store.til_olish(chat_id)
    t = D.get(til, D["uz"])
    html = tmpl
    for k, v in {
        "@@CSS@@": _CSS,
        "@@JS_COMMON@@": _JS_COMMON,
        "@@JS_DASH@@": _JS_DASH if js_page == "dash" else "",
        "@@JS_REC@@": _JS_REC if js_page == "rec" else "",
        "@@LANG@@": til,
        "@@DEFLANG@@": til,
        "@@APP_NAME@@": t["app_name"],
        "@@CHAT_ID@@": str(chat_id),
        "@@JSON@@": _malumotlar_json(chat_id),
        "@@TUZ@@": json.dumps(D["uz"], ensure_ascii=False),
        "@@TRU@@": json.dumps(D["ru"], ensure_ascii=False),
        "@@OYUZ@@": json.dumps(OYLAR["uz"], ensure_ascii=False),
        "@@OYRU@@": json.dumps(OYLAR["ru"], ensure_ascii=False),
        "@@SANADAN@@": t["sanadan"],
        "@@SANAGACHA@@": t["sanagacha"],
    }.items():
        html = html.replace(k, v)
    return html


@app.route("/")
def home():
    return "Bot 24/7 faol! ✅"


@app.route("/u/<chat_id>")
def sahifa(chat_id):
    if not chat_id.isdigit():
        return "Topilmadi", 404
    return _html_tayyorla(DASH_HTML, chat_id, "dash")


@app.route("/u/<chat_id>/yozuvlar")
def yozuvlar_sahifa(chat_id):
    if not chat_id.isdigit():
        return "Topilmadi", 404
    return _html_tayyorla(REC_HTML, chat_id, "rec")


@app.route("/u/<chat_id>/csv")
def csv_yukla(chat_id):
    yozuvlar = data_store.barchasi(chat_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Sana", "Vaqt", "Turi", "Kategoriya", "Summa", "Izoh", "Asl matn"])
    for y in yozuvlar:
        w.writerow([y["sana"], y["vaqt"], y["turi"], y["kategoriya"],
                    y["summa"], y["izoh"], y["asl_matn"]])
    return Response(
        "\ufeff" + buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename=moliya_{chat_id}.csv"},
    )


def run():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()