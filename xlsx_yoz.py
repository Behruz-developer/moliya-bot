"""
Chiroyli Excel (.xlsx) fayl yaratuvchi — faqat stdlib (zipfile + xml).
openpyxl kerak emas. Xlsx — zip ichidagi bir nechta XML fayl.
"""
import zipfile
import io

_XML_ESC = {
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&apos;",
}


def _esc(s) -> str:
    return "".join(_XML_ESC.get(c, c) for c in str(s if s is not None else ""))


_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>
</Types>"""

_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>"""

_WORKBOOK = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"
 xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Yozuvlar" sheetId="1" r:id="rId1"/></sheets>
</workbook>"""

_WORKBOOK_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>"""

_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">
<numFmts count="1"><numFmt numFmtId="164" formatCode="#\\ ##0"/></numFmts>
<fonts count="7">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FF3D34A0"/><name val="Calibri"/></font>
<font><b/><sz val="14"/><color rgb="FF1F1F2E"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FF1E9E5B"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FFE74C3C"/><name val="Calibri"/></font>
<font><sz val="10.5"/><color rgb="FF8A8FA3"/><name val="Calibri"/></font>
</fonts>
<fills count="7">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF6C5CE7"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFEFECFF"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFE9F9EF"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFFDECEC"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFF4F4F8"/></patternFill></fill>
</fills>
<borders count="2">
<border><left/><right/><top/><bottom/><diagonal/></border>
<border>
<left style="thin"><color rgb="FFD9D6F2"/></left>
<right style="thin"><color rgb="FFD9D6F2"/></right>
<top style="thin"><color rgb="FFD9D6F2"/></top>
<bottom style="thin"><color rgb="FFD9D6F2"/></bottom>
<diagonal/>
</border>
</borders>
<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>
<cellXfs count="12">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
<xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="164" fontId="2" fillId="3" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="164" fontId="4" fillId="4" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="164" fontId="5" fillId="5" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="6" fillId="0" borderId="0" xfId="0" applyFont="1"/>
<xf numFmtId="0" fontId="2" fillId="6" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center"/></xf>
<xf numFmtId="164" fontId="2" fillId="6" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""

# cellXfs indekslari: 0=default 1=sarlavha 2=matn 3=raqam 4=jami-matn 5=jami-raqam 6=title
# 7=daromad raqam (yashil) 8=harajat raqam (qizil) 9=subtitle matni (kulrang)
# 10=balans-sarlavha (lavanda) 11=balans-raqam (lavanda)


def yarat(sarlavha: str, sarlavha_qator: list, qatorlar: list,
          summa_ustun: int = 4, kengliklar: list = None) -> bytes:
    """Stil berilgan .xlsx faylni baytlar shaklida qaytaradi."""
    ustunlar = len(sarlavha_qator)
    if not kengliklar:
        kengliklar = [12, 8, 11, 24, 15, 32][:ustunlar] + [14] * max(0, ustunlar - 6)
    kengliklar = kengliklar[:ustunlar]

    harflar = [chr(65 + i) for i in range(ustunlar)]
    cols = "<cols>" + "".join(
        f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(kengliklar)
    ) + "</cols>"

    satr = []

    # 1-qator: birlashtirilgan sarlavha
    oxirgi = harflar[-1]
    satr.append(
        f'<row r="1" ht="24" customHeight="1"><c r="A1" s="6" t="inlineStr">'
        f"<is><t>{_esc(sarlavha)}</t></is></c></row>"
    )
    # 2-qator: ustun sarlavhalari
    h = '<row r="2">'
    for i, m in enumerate(sarlavha_qator):
        h += f'<c r="{harflar[i]}2" s="1" t="inlineStr"><is><t>{_esc(m)}</t></is></c>'
    satr.append(h + "</row>")

    # Ma'lumot qatorlari
    for i, q in enumerate(qatorlar):
        r = i + 3
        h = f'<row r="{r}">'
        for j, qiymat in enumerate(q):
            ref = f"{harflar[j]}{r}"
            if isinstance(qiymat, (int, float)) and not isinstance(qiymat, bool):
                s = "3" if j == summa_ustun else "2"
                h += f'<c r="{ref}" s="{s}"><v>{qiymat}</v></c>'
            else:
                h += f'<c r="{ref}" s="2" t="inlineStr"><is><t>{_esc(qiymat)}</t></is></c>'
        satr.append(h + "</row>")

    # Jami qatori
    if qatorlar:
        jami_r = len(qatorlar) + 3
        jami = sum(
            q[summa_ustun] for q in qatorlar
            if isinstance(q[summa_ustun], (int, float)) and not isinstance(q[summa_ustun], bool)
        )
        h = f'<row r="{jami_r}">'
        h += f'<c r="A{jami_r}" s="4" t="inlineStr"><is><t>JAMI</t></is></c>'
        for j in range(1, ustunlar):
            ref = f"{harflar[j]}{jami_r}"
            if j == summa_ustun:
                h += f'<c r="{ref}" s="5"><v>{jami}</v></c>'
            else:
                h += f'<c r="{ref}" s="4"/>'
        satr.append(h + "</row>")
        merges = f'<mergeCells count="2"><mergeCell ref="A1:{oxirgi}1"/><mergeCell ref="A{jami_r}:B{jami_r}"/></mergeCells>'
    else:
        merges = '<mergeCells count="1"><mergeCell ref="A1:%s1"/></mergeCells>' % oxirgi

    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + cols
        + '<sheetData>' + "".join(satr) + "</sheetData>"
        + merges
        + "</worksheet>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("xl/workbook.xml", _WORKBOOK)
        z.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        z.writestr("xl/styles.xml", _STYLES)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


# ============================ CHIROYLI HISOBOT (davr bo'yicha) ============================
# Sarlavha + egasi/valyuta/sana + daromad-harajat-balans kartalari +
# tranzaksiyalar jadvali (ketma-ket balans bilan) + kategoriyalar taqsimoti.

_T_UZ = {
    "sarlavha": "Hisobot — tranzaksiyalar",
    "subtitle": "Tanlangan davrdagi barcha kirim va chiqimlar",
    "egasi": "Egasi", "valyuta": "Valyuta", "som": "so'm", "tuzildi": "Tuzildi",
    "daromad": "Daromad", "harajat": "Harajat", "ozgarish": "Balans o'zgarishi",
    "jami_yozuv": "Jami yozuvlar",
    "th_no": "№", "th_sana": "Sana", "th_tavsif": "Tavsif", "th_kat": "Kategoriya",
    "th_kirim": "Kirim", "th_chiqim": "Chiqim", "th_balans": "Balans",
    "jami": "JAMI", "bosh_qator": "Bo'sh — bu davr uchun yozuv topilmadi.",
    "kat_sarlavha": "Kategoriyalar bo'yicha taqsimot",
    "kat_th_nom": "Kategoriya", "kat_th_soni": "Soni", "kat_th_summa": "Summa",
}
_T_RU = {
    "sarlavha": "Отчёт — транзакции",
    "subtitle": "Все поступления и расходы за выбранный период",
    "egasi": "Владелец", "valyuta": "Валюта", "som": "сум", "tuzildi": "Сформирован",
    "daromad": "Доходы", "harajat": "Расходы", "ozgarish": "Изменение баланса",
    "jami_yozuv": "Всего транзакций",
    "th_no": "№", "th_sana": "Дата", "th_tavsif": "Описание", "th_kat": "Категория",
    "th_kirim": "Доход", "th_chiqim": "Расход", "th_balans": "Баланс",
    "jami": "ИТОГО", "bosh_qator": "Пусто — за этот период записей нет.",
    "kat_sarlavha": "Расходы по категориям",
    "kat_th_nom": "Категория", "kat_th_soni": "Кол-во", "kat_th_summa": "Сумма",
}


def hisobot_yarat(yozuvlar: list, davr_matni: str, egasi: str = "", til: str = "uz",
                   boshlangich_balans: int = 0) -> bytes:
    """Chiroyli dizaynli .xlsx hisobot: sarlavha, davr, egasi, daromad/harajat/balans
    kartalari, tranzaksiyalar jadvali (ketma-ket balans bilan) va kategoriya taqsimoti.
    yozuvlar: [{"sana", "turi": "Daromad"/"Harajat", "kategoriya", "summa", "izoh"}, ...]
    """
    tr = _T_RU if til == "ru" else _T_UZ
    harflar = [chr(65 + i) for i in range(7)]
    oxirgi = harflar[-1]
    kengliklar = [6, 12, 30, 20, 15, 15, 15]
    cols = "<cols>" + "".join(
        f'<col min="{i+1}" max="{i+1}" width="{w}" customWidth="1"/>'
        for i, w in enumerate(kengliklar)
    ) + "</cols>"

    yozuvlar = sorted(yozuvlar, key=lambda y: (str(y.get("sana", "")), str(y.get("vaqt", ""))))
    dar_jami = sum(int(y.get("summa", 0) or 0) for y in yozuvlar if y.get("turi") == "Daromad")
    har_jami = sum(int(y.get("summa", 0) or 0) for y in yozuvlar if y.get("turi") == "Harajat")

    satr, merges = [], []

    def txt(ref, s, text):
        return f'<c r="{ref}" s="{s}" t="inlineStr"><is><t>{_esc(text)}</t></is></c>'

    r = 1
    satr.append(f'<row r="{r}" ht="26" customHeight="1">{txt(f"A{r}", 6, tr["sarlavha"])}</row>')
    merges.append(f'A{r}:{oxirgi}{r}')
    r += 1
    satr.append(f'<row r="{r}">{txt(f"A{r}", 9, tr["subtitle"])}</row>')
    merges.append(f'A{r}:{oxirgi}{r}')
    r += 2  # bo'sh qator

    meta = f'{tr["egasi"]}: {egasi or "-"}    ·    {tr["valyuta"]}: UZS    ·    {tr["tuzildi"]}: {davr_matni}'
    satr.append(f'<row r="{r}">{txt(f"A{r}", 9, meta)}</row>')
    merges.append(f'A{r}:{oxirgi}{r}')
    r += 2  # bo'sh qator

    k1, k2 = r, r + 1
    satr.append(
        f'<row r="{k1}">{txt(f"A{k1}", 10, tr["daromad"])}{txt(f"C{k1}", 10, tr["harajat"])}'
        f'{txt(f"E{k1}", 10, tr["ozgarish"])}{txt(f"G{k1}", 10, tr["jami_yozuv"])}</row>'
    )
    satr.append(
        f'<row r="{k2}" ht="20">'
        f'<c r="A{k2}" s="7"><v>{dar_jami}</v></c>'
        f'<c r="C{k2}" s="8"><v>{har_jami}</v></c>'
        f'<c r="E{k2}" s="11"><v>{dar_jami - har_jami}</v></c>'
        f'<c r="G{k2}" s="11"><v>{len(yozuvlar)}</v></c></row>'
    )
    merges.extend([f'A{k1}:B{k1}', f'A{k2}:B{k2}', f'C{k1}:D{k1}', f'C{k2}:D{k2}',
                   f'E{k1}:F{k1}', f'E{k2}:F{k2}'])
    r += 3  # 2 karta qator + bo'sh qator

    th_r = r
    sarlavha_qator = [tr["th_no"], tr["th_sana"], tr["th_tavsif"], tr["th_kat"],
                       tr["th_kirim"], tr["th_chiqim"], tr["th_balans"]]
    h = f'<row r="{th_r}">'
    for i, m in enumerate(sarlavha_qator):
        h += txt(f"{harflar[i]}{th_r}", 1, m)
    satr.append(h + "</row>")
    r += 1

    balans = boshlangich_balans
    for i, y in enumerate(yozuvlar):
        summa = int(y.get("summa", 0) or 0)
        is_daromad = y.get("turi") == "Daromad"
        balans += summa if is_daromad else -summa
        row_r = r
        tavsif = (y.get("izoh") or "").strip() or y.get("kategoriya", "")
        h = f'<row r="{row_r}">'
        h += f'<c r="A{row_r}" s="2"><v>{i + 1}</v></c>'
        h += txt(f"B{row_r}", 2, y.get("sana", ""))
        h += txt(f"C{row_r}", 2, tavsif)
        h += txt(f"D{row_r}", 2, y.get("kategoriya", ""))
        h += f'<c r="E{row_r}" s="7"><v>{summa}</v></c>' if is_daromad else f'<c r="E{row_r}" s="3"/>'
        h += f'<c r="F{row_r}" s="8"><v>{summa}</v></c>' if not is_daromad else f'<c r="F{row_r}" s="3"/>'
        h += f'<c r="G{row_r}" s="3"><v>{balans}</v></c>'
        satr.append(h + "</row>")
        r += 1

    if not yozuvlar:
        satr.append(f'<row r="{r}">{txt(f"A{r}", 9, tr["bosh_qator"])}</row>')
        merges.append(f'A{r}:{oxirgi}{r}')
        r += 1
    else:
        jami_r = r
        h = f'<row r="{jami_r}">'
        h += txt(f"A{jami_r}", 4, tr["jami"])
        h += f'<c r="B{jami_r}" s="4"/><c r="C{jami_r}" s="4"/><c r="D{jami_r}" s="4"/>'
        h += f'<c r="E{jami_r}" s="5"><v>{dar_jami}</v></c>'
        h += f'<c r="F{jami_r}" s="5"><v>{har_jami}</v></c>'
        h += f'<c r="G{jami_r}" s="5"><v>{balans}</v></c>'
        satr.append(h + "</row>")
        merges.append(f'A{jami_r}:D{jami_r}')
        r += 1

    r += 1  # bo'sh qator

    kat_jami, kat_soni = {}, {}
    for y in yozuvlar:
        if y.get("turi") != "Harajat":
            continue
        nom = y.get("kategoriya", "-")
        kat_jami[nom] = kat_jami.get(nom, 0) + int(y.get("summa", 0) or 0)
        kat_soni[nom] = kat_soni.get(nom, 0) + 1

    if kat_jami:
        satr.append(f'<row r="{r}">{txt(f"A{r}", 9, tr["kat_sarlavha"])}</row>')
        merges.append(f'A{r}:{oxirgi}{r}')
        r += 1
        kat_th_r = r
        satr.append(
            f'<row r="{kat_th_r}">'
            + txt(f"A{kat_th_r}", 1, tr["kat_th_nom"])
            + txt(f"B{kat_th_r}", 1, tr["kat_th_soni"])
            + txt(f"C{kat_th_r}", 1, tr["kat_th_summa"])
            + "</row>"
        )
        r += 1
        for nom, summa in sorted(kat_jami.items(), key=lambda x: -x[1]):
            kr = r
            satr.append(
                f'<row r="{kr}">'
                + txt(f"A{kr}", 2, nom)
                + f'<c r="B{kr}" s="2"><v>{kat_soni[nom]}</v></c>'
                + f'<c r="C{kr}" s="8"><v>{summa}</v></c>'
                + "</row>"
            )
            r += 1

    merge_tags = "".join(f'<mergeCell ref="{m}"/>' for m in merges)
    merges_xml = f'<mergeCells count="{len(merges)}">{merge_tags}</mergeCells>' if merges else ""

    sheet = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        + cols
        + '<sheetData>' + "".join(satr) + "</sheetData>"
        + merges_xml
        + "</worksheet>"
    )

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _CONTENT_TYPES)
        z.writestr("_rels/.rels", _RELS)
        z.writestr("xl/workbook.xml", _WORKBOOK)
        z.writestr("xl/_rels/workbook.xml.rels", _WORKBOOK_RELS)
        z.writestr("xl/styles.xml", _STYLES)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buf.getvalue()


