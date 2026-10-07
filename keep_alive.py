"""
Dashboard serveri: har bir foydalanuvchi uchun zamonaviy, responsive
moliyaviy sahifa (dark/light mode, grafiklar, filtrlar).
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
        "balans": "Joriy balans",
        "umumiy_daromad": "Umumiy daromad",
        "umumiy_harajat": "Umumiy harajat",
        "oy_daromad": "Shu oy daromad",
        "oy_harajat": "Shu oy harajat",
        "oy_balans": "Shu oy balans",
        "som": "so'm",
        "trend_title": "Oxirgi 6 oy",
        "donut_title": "Harajat kategoriyalari",
        "donut_empty": "Harajat ma'lumoti yo'q",
        "kat_title": "Kategoriya reytingi",
        "rec_title": "Yozuvlar",
        "rec_empty": "Hozircha yozuv yo'q — botga yozing!",
        "filtr_davr": "Davr",
        "filtr_tur": "Tur",
        "filtr_kat": "Kategoriya",
        "hamma": "Hammasi",
        "daromad": "Daromad",
        "harajat": "Harajat",
        "bugun": "Bugun",
        "hafta": "Shu hafta",
        "oy": "Shu oy",
        "barchasi": "Barcha davr",
        "csv": "CSV yuklab olish",
        "toplam": "jami",
        "tushumlar_soni": "{n} ta yozuv",
        "izoh": "Izoh",
        "hint": "Yangi yozuvlar bot orqali qo'shiladi — ko'rish uchun sahifani yangilang (refresh)",
    },
    "ru": {
        "app_name": "Финансы",
        "balans": "Текущий баланс",
        "umumiy_daromad": "Общий доход",
        "umumiy_harajat": "Общий расход",
        "oy_daromad": "Доход за месяц",
        "oy_harajat": "Расход за месяц",
        "oy_balans": "Баланс за месяц",
        "som": "сум",
        "trend_title": "Последние 6 месяцев",
        "donut_title": "Категории расходов",
        "donut_empty": "Нет данных о расходах",
        "kat_title": "Рейтинг категорий",
        "rec_title": "Записи",
        "rec_empty": "Пока нет записей — напишите боту!",
        "filtr_davr": "Период",
        "filtr_tur": "Тип",
        "filtr_kat": "Категория",
        "hamma": "Все",
        "daromad": "Доход",
        "harajat": "Расход",
        "bugun": "Сегодня",
        "hafta": "Эта неделя",
        "oy": "Этот месяц",
        "barchasi": "Всё время",
        "csv": "Скачать CSV",
        "toplam": "всего",
        "tushumlar_soni": "{n} записей",
        "izoh": "Комментарий",
        "hint": "Новые записи добавляются через бота — обновите страницу, чтобы увидеть их",
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
    return json.dumps(royxat, ensure_ascii=False)# ============================ SAHIFA (HTML) ============================

_HTML = """<!doctype html>
<html lang="@@LANG@@">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>@@APP_NAME@@ Dashboard</title>
<style>
:root{
  --bg:#0b1220; --card:#151e31; --card2:#1b2540; --border:#233047;
  --text:#e7edf7; --muted:#8b97ad; --accent:#6366f1;
  --pos:#34d399; --neg:#f87171; --shadow:0 10px 30px rgba(0,0,0,.35);
  --grad:linear-gradient(135deg,#6366f1,#8b5cf6);
}
[data-theme="light"]{
  --bg:#f1f5f9; --card:#ffffff; --card2:#f1f5f9; --border:#e2e8f0;
  --text:#0f172a; --muted:#64748b; --pos:#059669; --neg:#dc2626;
  --shadow:0 10px 30px rgba(15,23,42,.08);
}
*{margin:0;padding:0;box-sizing:border-box}
body{
  font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Inter,sans-serif;
  background:var(--bg);color:var(--text);min-height:100vh;
  background-image:radial-gradient(1200px 500px at 80% -10%, rgba(99,102,241,.12), transparent),
                   radial-gradient(900px 400px at 0% 110%, rgba(139,92,246,.10), transparent);
  transition:background .3s,color .3s;
}
.wrap{max-width:1080px;margin:0 auto;padding:20px 16px 48px}
.top{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-bottom:22px}
.logo{display:flex;align-items:center;gap:12px}
.logo .mark{width:44px;height:44px;border-radius:14px;background:var(--grad);display:flex;align-items:center;justify-content:center;font-size:22px;box-shadow:var(--shadow)}
.logo h1{font-size:20px;font-weight:800;letter-spacing:-.3px}
.logo h1 span{background:var(--grad);-webkit-background-clip:text;background-clip:text;color:transparent}
.top-actions{display:flex;gap:8px;align-items:center}
.iconbtn{width:40px;height:40px;border-radius:12px;background:var(--card);border:1px solid var(--border);color:var(--text);font-size:17px;cursor:pointer;display:flex;align-items:center;justify-content:center;transition:transform .15s,box-shadow .15s}
.iconbtn:hover{transform:translateY(-2px);box-shadow:var(--shadow)}
.abtn{display:inline-flex;align-items:center;gap:8px;background:var(--grad);color:#fff;text-decoration:none;font-weight:700;font-size:13.5px;padding:10px 16px;border-radius:12px;box-shadow:var(--shadow);transition:transform .15s,opacity .15s}
.abtn:hover{transform:translateY(-2px)}
.abtn:active{opacity:.85}
.kpi{display:grid;grid-template-columns:repeat(auto-fit,minmax(210px,1fr));gap:14px;margin-bottom:18px}
.card{background:var(--card);border:1px solid var(--border);border-radius:18px;padding:18px;box-shadow:var(--shadow);transition:transform .2s,box-shadow .2s}
.card:hover{transform:translateY(-3px)}
.kpi .lbl{font-size:11.5px;color:var(--muted);font-weight:600;text-transform:uppercase;letter-spacing:.6px;display:flex;align-items:center;gap:8px}
.kpi .ico{width:34px;height:34px;border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:16px;margin-left:auto;flex-shrink:0}
.kpi .val{font-size:25px;font-weight:800;margin-top:10px;letter-spacing:-.5px;font-variant-numeric:tabular-nums}
.kpi .sub{font-size:12px;color:var(--muted);margin-top:4px}
.ico.b{background:rgba(99,102,241,.16)}
.ico.g{background:rgba(52,211,153,.16)}
.ico.r{background:rgba(248,113,113,.16)}
.pos{color:var(--pos)} .neg{color:var(--neg)} .neu{color:var(--accent)}
.sec{margin-top:18px}
.sec h2{font-size:12.5px;font-weight:700;color:var(--muted);margin:0 2px 12px;display:flex;align-items:center;gap:8px;text-transform:uppercase;letter-spacing:.6px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:14px}
@media(max-width:820px){.grid2{grid-template-columns:1fr}}.donut-wrap{display:flex;align-items:center;gap:22px;flex-wrap:wrap;justify-content:center}
.legend{display:flex;flex-direction:column;gap:9px;min-width:170px}
.legend .li{display:flex;align-items:center;gap:9px;font-size:13px}
.legend .dot{width:11px;height:11px;border-radius:4px;flex-shrink:0}
.legend .nm{flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:150px}
.legend .pc{color:var(--muted);font-variant-numeric:tabular-nums}
.bars{display:flex;align-items:flex-end;justify-content:space-around;gap:14px;height:190px;padding:6px 4px 0}
.bargrp{display:flex;flex-direction:column;align-items:center;gap:8px;flex:1;max-width:90px;height:100%;justify-content:flex-end}
.barcol{display:flex;align-items:flex-end;gap:5px;height:100%;width:100%;justify-content:center}
.bar{width:16px;border-radius:7px 7px 3px 3px;min-height:3px;transition:height 1s cubic-bezier(.22,1,.36,1)}
.bar.in{background:linear-gradient(180deg,#34d399,#059669)}
.bar.out{background:linear-gradient(180deg,#f87171,#dc2626)}
.bargrp .m{font-size:11.5px;color:var(--muted);font-weight:600}
.barleg{display:flex;gap:16px;justify-content:center;margin-top:12px;font-size:12px;color:var(--muted)}
.barleg span{display:flex;align-items:center;gap:6px}
.barleg i{width:11px;height:11px;border-radius:4px;display:inline-block}
.barleg .in{background:#34d399}.barleg .out{background:#f87171}
.katrow{display:grid;grid-template-columns:26px minmax(0,1fr) 110px 60px;gap:4px 10px;align-items:center;padding:10px 0;border-bottom:1px solid var(--border)}
.katrow:last-child{border-bottom:none}
.katrow .rn{width:26px;height:26px;border-radius:9px;background:var(--card2);border:1px solid var(--border);display:flex;align-items:center;justify-content:center;font-size:11px;font-weight:700;color:var(--muted)}
.katrow .nm{font-size:13.5px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.katrow .barbg{grid-column:1/3;height:8px;background:var(--card2);border-radius:6px;overflow:hidden;margin-top:2px}
.katrow .barbg>div{height:100%;border-radius:6px;background:var(--grad);width:0;transition:width 1s cubic-bezier(.22,1,.36,1)}
.katrow .sm{font-weight:700;font-size:12.5px;text-align:right;font-variant-numeric:tabular-nums}
.katrow .pc{color:var(--muted);font-size:12px;text-align:right;font-variant-numeric:tabular-nums}
.filters{display:flex;gap:10px;flex-wrap:wrap;align-items:center;margin-bottom:14px}
.chip{border:1px solid var(--border);background:var(--card2);color:var(--text);font-size:13px;font-weight:600;padding:8px 15px;border-radius:99px;cursor:pointer;transition:all .15s}
.chip:hover{border-color:var(--accent)}
.chip.on{background:var(--grad);border-color:transparent;color:#fff;box-shadow:var(--shadow)}
select.chip{appearance:none;padding-right:14px}
.rec{display:flex;align-items:center;gap:12px;padding:13px 2px;border-bottom:1px solid var(--border);animation:fadein .4s both}
.rec:last-child{border-bottom:none}
.rec .em{width:40px;height:40px;border-radius:12px;display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0}
.em.g{background:rgba(52,211,153,.14)} .em.r{background:rgba(248,113,113,.14)}
.rec .mid{flex:1;min-width:0}
.rec .t1{font-size:14px;font-weight:650;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.rec .badge{font-size:10.5px;padding:2px 8px;border-radius:7px;font-weight:700}
.badge.g{background:rgba(52,211,153,.16);color:var(--pos)} .badge.r{background:rgba(248,113,113,.16);color:var(--neg)}
.rec .t2{font-size:12px;color:var(--muted);margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.rec .amt{font-weight:800;font-size:14.5px;white-space:nowrap;font-variant-numeric:tabular-nums}
.dayhead{font-size:11.5px;color:var(--muted);font-weight:700;text-transform:uppercase;letter-spacing:.5px;margin:16px 2px 4px}
.empty{text-align:center;padding:34px 10px;color:var(--muted)}
.empty .big{font-size:40px;margin-bottom:10px}
.footer{text-align:center;color:var(--muted);font-size:12px;margin-top:26px}
.donutwrap{display:flex;justify-content:center;align-items:center}
circle{transition:stroke-dashoffset 1s cubic-bezier(.22,1,.36,1)}
@keyframes fadein{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:none}}
@media(max-width:560px){
  .kpi .val{font-size:21px}
  .bars{gap:6px}
  .bar{width:11px}
  .katrow .sm{font-size:11px} .katrow .pc{font-size:10.5px}
}
</style>
</head>
<body data-theme="dark">
<div class="wrap">
  <div class="top">
    <div class="logo">
      <div class="mark">💰</div>
      <h1><span>@@APP_NAME@@</span> Dashboard</h1>
    </div>
    <div class="top-actions">
      <button class="iconbtn" id="themeBtn" title="Dark/Light">🌙</button>
      <a class="abtn" href="/u/@@CHAT_ID@@/csv">⬇ @@CSV@@</a>
    </div>
  </div>

  <div class="kpi" id="kpi"></div>

  <div class="grid2">
    <div class="card sec">
      <h2>📊 @@TREND@@</h2>
      <div class="bars" id="bars"></div>
      <div class="barleg">
        <span><i class="in"></i>@@DAROMAD_L@@</span>
        <span><i class="out"></i>@@HARAJAT_L@@</span>
      </div>
    </div>
    <div class="card sec">
      <h2>🍩 @@DONUT@@</h2>
      <div class="donut-wrap" id="donutWrap"></div>
    </div>
  </div>

  <div class="card sec">
    <h2>🏆 @@KAT@@</h2>
    <div id="katList"></div>
  </div>

  <div class="card sec">
    <h2>🧾 @@REC@@ · <span id="recCount"></span></h2>
    <div class="filters" id="filters"></div>
    <div id="recList"></div>
  </div>

  <div class="footer">@@HINT@@</div>
</div><script>
const Y = @@JSON@@;
const T = @@TJSON@@;
const OY = @@OYLAR@@;

// ---- Tema ----
const savedTheme = localStorage.getItem('moliya_theme') || 'dark';
document.body.dataset.theme = savedTheme;
document.getElementById('themeBtn').textContent = savedTheme === 'dark' ? '🌙' : '☀️';
document.getElementById('themeBtn').onclick = () => {
  const t = document.body.dataset.theme === 'dark' ? 'light' : 'dark';
  document.body.dataset.theme = t;
  localStorage.setItem('moliya_theme', t);
  document.getElementById('themeBtn').textContent = t === 'dark' ? '🌙' : '☀️';
};

const fmtS = n => (n||0).toLocaleString('ru-RU').replace(/\u00a0/g,' ') + ' ' + T.som;
const el = id => document.getElementById(id);

// ---- KPI ----
const now = new Date();
const oyBoshi = now.toISOString().slice(0,7);
const hafta = new Date(now); hafta.setDate(now.getDate() - ((now.getDay()+6)%7));
const haftaStr = hafta.toISOString().slice(0,10);
const bugunStr = now.toISOString().slice(0,10);

function summa(f, turi){ return Y.filter(y=>f(y) && (turi?y.turi===turi:true)).reduce((s,y)=>s+y.summa,0); }
const umD = summa(()=>true,'Daromad'), umH = summa(()=>true,'Harajat');
const oyD = summa(y=>y.sana>=oyBoshi,'Daromad'), oyH = summa(y=>y.sana>=oyBoshi,'Harajat');
const hB = summa(y=>y.sana>=haftaStr,'Daromad') - summa(y=>y.sana>=haftaStr,'Harajat');
const balans = umD - umH;

function kpiCard(lbl, val, cls, ico, icoCls, sub){
  return `<div class="card kpi-card"><div class="lbl">${lbl}<span class="ico ${icoCls}">${ico}</span></div><div class="val ${cls}">${val}</div>${sub?`<div class="sub">${sub}</div>`:''}</div>`;
}
el('kpi').innerHTML =
  kpiCard(T.balans, fmtS(balans), balans>=0?'neu':'neg', '💼','b') +
  kpiCard(T.umumiy_daromad, fmtS(umD), 'pos', '🟢','g') +
  kpiCard(T.umumiy_harajat, fmtS(umH), 'neg', '🔴','r') +
  kpiCard(T.oy_daromad, fmtS(oyD), 'pos', '📅','g') +
  kpiCard(T.oy_harajat, fmtS(oyH), 'neg', '📅','r') +
  kpiCard(T.oy_balans, fmtS(oyD-oyH), (oyD-oyH)>=0?'neu':'neg', '🗓','b');

// ---- Trend: oxirgi 6 oy ----
const oylarArr = [];
for(let i=5;i>=0;i--){
  const d = new Date(now.getFullYear(), now.getMonth()-i, 1);
  const key = d.toISOString().slice(0,7);
  oylarArr.push({
    key,
    nom: OY[d.getMonth()],
    daromad: summa(y=>y.sana.startsWith(key),'Daromad'),
    harajat: summa(y=>y.sana.startsWith(key),'Harajat'),
  });
}
const maxBar = Math.max(...oylarArr.map(o=>Math.max(o.daromad,o.harajat)), 1);
el('bars').innerHTML = oylarArr.map(o=>`
  <div class="bargrp">
    <div class="barcol">
      <div class="bar in" style="height:${Math.round(o.daromad/maxBar*100)}%" title="${T.daromad}: ${fmtS(o.daromad)}"></div>
      <div class="bar out" style="height:${Math.round(o.harajat/maxBar*100)}%" title="${T.harajat}: ${fmtS(o.harajat)}"></div>
    </div>
    <div class="m">${o.nom}</div>
  </div>`).join('');

// ---- Donut: harajat kategoriyalari (shu oy) ----
const KAT_RANGLAR = ['#6366f1','#8b5cf6','#ec4899','#f59e0b','#10b981','#06b6d4','#ef4444','#84cc16','#a855f7','#64748b'];
function donutDraw(recs){
  const kat = {};
  recs.filter(y=>y.turi==='Harajat').forEach(y=>kat[y.kategoriya]=(kat[y.kategoriya]||0)+y.summa);
  const items = Object.entries(kat).sort((a,b)=>b[1]-a[1]);
  if(!items.length){
    el('donutWrap').innerHTML = `<div class="empty"><div class="big">🍩</div>${T.donut_empty}</div>`;
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
    <svg width="160" height="160" viewBox="0 0 160 160" style="transform:rotate(-90deg)">
      <circle r="54" cx="80" cy="80" fill="none" stroke="var(--card2)" stroke-width="26"></circle>${segs}
    </svg>
    <div class="legend">${legend}</div>`;
}
donutDraw(Y);

// ---- Kategoriya reytingi ----
function katDraw(recs){
  const kat = {};
  recs.forEach(y=>{
    if(!kat[y.kategoriya]) kat[y.kategoriya]={d:0,h:0};
    if(y.turi==='Daromad') kat[y.kategoriya].d+=y.summa; else kat[y.kategoriya].h+=y.summa;
  });
  const items = Object.entries(kat).sort((a,b)=>(b[1].d+b[1].h)-(a[1].d+a[1].h));
  if(!items.length){ el('katList').innerHTML = `<div class="empty"><div class="big">📭</div>${T.rec_empty}</div>`; return; }
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
  requestAnimationFrame(()=>document.querySelectorAll('.barbg>div').forEach(d=>{
    d.style.width = d.dataset.w + '%';
  }));
}
katDraw(Y);
</script>// ---- Filtrlar ----
<script>
// ---- Filtrlar ----
const kategoriyalar = [...new Set(Y.map(y=>y.kategoriya))];
let fDavr = 'barchasi', fTur = 'hamma', fKat = 'hamma';

el('filters').innerHTML = `
  <select class="chip" id="selDavr">
    <option value="barchasi">${T.barchasi}</option>
    <option value="oy">${T.oy}</option>
    <option value="hafta">${T.hafta}</option>
    <option value="bugun">${T.bugun}</option>
  </select>
  <button class="chip on" data-tur="hamma">${T.hamma}</button>
  <button class="chip" data-tur="Daromad">🟢 ${T.daromad}</button>
  <button class="chip" data-tur="Harajat">🔴 ${T.harajat}</button>
  <select class="chip" id="selKat">
    <option value="hamma">${T.filtr_kat}: ${T.hamma}</option>
    ${kategoriyalar.map(k=>`<option value="${k}">${k}</option>`).join('')}
  </select>`;

function filtrReqs(){
  let r = Y;
  if(fDavr==='bugun') r = r.filter(y=>y.sana===bugunStr);
  else if(fDavr==='hafta') r = r.filter(y=>y.sana>=haftaStr);
  else if(fDavr==='oy') r = r.filter(y=>y.sana>=oyBoshi);
  if(fTur!=='hamma') r = r.filter(y=>y.turi===fTur);
  if(fKat!=='hamma') r = r.filter(y=>y.kategoriya===fKat);
  return r;
}

el('filters').addEventListener('click', e=>{
  const b = e.target.closest('button.chip');
  if(!b) return;
  el('filters').querySelectorAll('button.chip').forEach(x=>x.classList.remove('on'));
  b.classList.add('on');
  fTur = b.dataset.tur;
  royxatChiz();
});
el('selDavr').onchange = e=>{ fDavr = e.target.value; royxatChiz(); };
el('selKat').onchange = e=>{ fKat = e.target.value; royxatChiz(); };

// ---- Yozuvlar ro'yxati ----
function recHtml(y){
  const d = y.turi==='Daromad';
  return `<div class="rec">
    <div class="em ${d?'g':'r'}">${d?'🟢':'🔴'}</div>
    <div class="mid">
      <div class="t1">${y.kategoriya}<span class="badge ${d?'g':'r'}">${d?T.daromad:T.harajat}</span></div>
      <div class="t2">${y.sana} · ${y.vaqt}${y.izoh?' · '+y.izoh:''}</div>
    </div>
    <div class="amt ${d?'pos':'neg'}">${d?'+':'−'} ${fmtS(y.summa)}</div>
  </div>`;
}
function royxatChiz(){
  const r = filtrReqs();
  el('recCount').textContent = String(r.length);
  if(!r.length){
    el('recList').innerHTML = `<div class="empty"><div class="big">📭</div>${T.rec_empty}</div>`;
    return;
  }
  const guruh = {};
  r.forEach(y=>{ (guruh[y.sana]=guruh[y.sana]||[]).push(y); });
  const kunlar = Object.keys(guruh).sort().reverse();
  el('recList').innerHTML = kunlar.map(sana=>{
    const head = sana===bugunStr ? `☀️ ${T.bugun}` : sana;
    return `<div class="dayhead">${head}</div>` + guruh[sana].map(recHtml).join('');
  }).join('');
}
royxatChiz();
</script>
</body>
</html>"""# ============================ ROUTELAR ============================

@app.route("/")
def home():
    return "Bot 24/7 faol! ✅"


def _sahifa_html(chat_id) -> str:
    til = data_store.til_olish(chat_id)
    t = D.get(til, D["uz"])
    html = _HTML
    almashtirishlar = {
        "@@LANG@@": til,
        "@@APP_NAME@@": t["app_name"],
        "@@CHAT_ID@@": str(chat_id),
        "@@JSON@@": _malumotlar_json(chat_id),
        "@@TJSON@@": json.dumps(t, ensure_ascii=False),
        "@@OYLAR@@": json.dumps(OYLAR[til], ensure_ascii=False),
        "@@CSV@@": t["csv"],
        "@@TREND@@": t["trend_title"],
        "@@DONUT@@": t["donut_title"],
        "@@KAT@@": t["kat_title"],
        "@@REC@@": t["rec_title"],
        "@@DAROMAD_L@@": t["daromad"],
        "@@HARAJAT_L@@": t["harajat"],
        "@@HINT@@": t["hint"],
    }
    for k, v in almashtirishlar.items():
        html = html.replace(k, v)
    return html


@app.route("/u/<chat_id>")
def sahifa(chat_id):
    if not chat_id.isdigit():
        return "Topilmadi", 404
    return _sahifa_html(chat_id)


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