import os
import csv
import io
from threading import Thread
from flask import Flask, Response

import data_store

app = Flask(__name__)


def _yozuvlar_html(chat_id):
    yozuvlar = data_store.barchasi(chat_id)
    if not yozuvlar:
        return '<div class="empty">📭 Hozircha yozuv yo\'q. Botga yozing!</div>'
    qatorlar = []
    for y in reversed(yozuvlar):
        d = "daromad" if y["turi"] == "Daromad" else "harajat"
        summa_cls = "pos" if d == "daromad" else "neg"
        belgi = "+" if d == "daromad" else "−"
        qatorlar.append(f"""
        <div class="row">
          <div class="row-left">
            <div class="row-top">
              <span class="badge {d}">{y['turi']}</span>
              <span class="kat">{y['kategoriya']}</span>
            </div>
            <div class="row-sub">{y['sana']} · {y['vaqt']} · {y['izoh'] or '—'}</div>
          </div>
          <div class="summa {summa_cls}">{belgi} {data_store.fmt(y['summa'])}</div>
        </div>""")
    return "".join(qatorlar)


def _kat_html(chat_id):
    stat = data_store.stat_olish(chat_id)
    max_s = max([v["daromad"] + v["harajat"] for v in stat["kategoriyalar"].values()] + [1])
    bloklar = []
    for nom, v in stat["kategoriyalar"].items():
        jami = v["daromad"] + v["harajat"]
        d_cls = "daromad" if v["daromad"] else "harajat"
        bloklar.append(f"""
        <div class="kat-row">
          <div class="kat-name">{nom}</div>
          <div class="kat-bar-wrap"><div class="kat-bar {d_cls}" style="width:{int(jami / max_s * 100)}%"></div></div>
          <div class="kat-sum">{data_store.fmt(jami)}</div>
        </div>""")
    return "".join(bloklar)

def _sahifa(chat_id):
    stat = data_store.stat_olish(chat_id)
    balans = stat["umumiy_daromad"] - stat["umumiy_harajat"]
    return f"""<!doctype html>
<html lang="uz">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Moliya Dashboard</title>
<style>
* {{ margin: 0; padding: 0; box-sizing: border-box; }}
body {{ font-family: -apple-system, 'Segoe UI', Roboto, sans-serif; background: #0f172a; color: #e2e8f0; padding: 16px; max-width: 768px; margin: 0 auto; }}
h1 {{ font-size: 22px; margin: 0 0 16px; }}
h1 span {{ color: #38bdf8; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 10px; }}
.card {{ background: #1e293b; border-radius: 14px; padding: 14px 16px; }}
.card .label {{ font-size: 12px; color: #94a3b8; text-transform: uppercase; letter-spacing: .5px; }}
.card .value {{ font-size: 20px; font-weight: 700; margin-top: 6px; }}
.pos {{ color: #22c55e; }}
.neg {{ color: #ef4444; }}
.neu {{ color: #38bdf8; }}
.section {{ background: #1e293b; border-radius: 14px; padding: 16px; margin-top: 14px; }}
.section h2 {{ font-size: 15px; color: #94a3b8; margin-bottom: 10px; }}
.row {{ display: flex; justify-content: space-between; align-items: center; padding: 10px 0; border-bottom: 1px solid #334155; gap: 10px; }}
.row:last-child {{ border-bottom: none; }}
.row-top {{ display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }}
.badge {{ font-size: 11px; padding: 2px 8px; border-radius: 8px; font-weight: 600; }}
.badge.daromad {{ background: rgba(34, 197, 94, .15); color: #22c55e; }}
.badge.harajat {{ background: rgba(239, 68, 68, .15); color: #ef4444; }}
.kat {{ font-weight: 600; font-size: 14px; }}
.row-sub {{ font-size: 12px; color: #94a3b8; margin-top: 3px; }}
.summa {{ font-weight: 700; white-space: nowrap; }}
.empty {{ text-align: center; padding: 30px 10px; color: #94a3b8; }}
.kat-row {{ display: grid; grid-template-columns: 110px 1fr auto; align-items: center; gap: 10px; padding: 6px 0; }}
.kat-name {{ font-size: 13px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
.kat-bar-wrap {{ background: #334155; border-radius: 6px; height: 14px; overflow: hidden; }}
.kat-bar {{ height: 100%; border-radius: 6px; }}
.kat-bar.daromad {{ background: #22c55e; }}
.kat-bar.harajat {{ background: #ef4444; }}
.kat-sum {{ font-size: 13px; font-weight: 600; }}
.actions {{ margin-top: 16px; display: flex; gap: 10px; flex-wrap: wrap; }}
.btn {{ display: inline-block; background: #38bdf8; color: #fff; text-decoration: none; font-weight: 600; padding: 10px 18px; border-radius: 10px; font-size: 14px; }}
.btn:active {{ opacity: .8; }}
.footer {{ text-align: center; color: #64748b; font-size: 12px; margin: 20px 0 10px; }}
</style>
</head>
<body>
<h1><span>Moliya</span> Dashboard</h1>

<div class="cards">
  <div class="card"><div class="label">Joriy balans</div><div class="value neu">{data_store.fmt(balans)} so'm</div></div>
  <div class="card"><div class="label">Umumiy daromad</div><div class="value pos">{data_store.fmt(stat['umumiy_daromad'])}</div></div>
  <div class="card"><div class="label">Umumiy harajat</div><div class="value neg">{data_store.fmt(stat['umumiy_harajat'])}</div></div>
</div>

<div class="cards" style="margin-top:10px">
  <div class="card"><div class="label">Shu oy daromad</div><div class="value pos">{data_store.fmt(stat['oy_daromad'])}</div></div>
  <div class="card"><div class="label">Shu oy harajat</div><div class="value neg">{data_store.fmt(stat['oy_harajat'])}</div></div>
  <div class="card"><div class="label">Shu hafta balans</div><div class="value neu">{data_store.fmt(stat['hafta_balans'])}</div></div>
</div>

<div class="section">
  <h2>Kategoriyalar (shu oy)</h2>
  {_kat_html(chat_id) or '<div class="empty">Ma\'lumot yo\'q</div>'}
</div>

<div class="section">
  <h2>Barcha yozuvlar ({stat['jami_yozuvlar']})</h2>
  {_yozuvlar_html(chat_id)}
</div>

<div class="actions">
  <a class="btn" href="/u/{chat_id}/csv">CSV yuklab olish</a>
</div>

<div class="footer">Yangi yozuvlar bilan yangilash uchun sahifani qayta oching (refresh)</div>
</body>
</html>"""


@app.route("/")
def home():
    return "Bot 24/7 faol! ✅"


@app.route("/u/<chat_id>")
def sahifa(chat_id):
    if not chat_id.isdigit():
        return "Topilmadi", 404
    return _sahifa(chat_id)


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
  port = int(os.environ.get('PORT', 10000))
  app.run(host='0.0.0.0', port=port)


def keep_alive():
  t = Thread(target=run)
  t.daemon = True
  t.start()