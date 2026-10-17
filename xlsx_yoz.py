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
<fonts count="4">
<font><sz val="11"/><name val="Calibri"/></font>
<font><b/><color rgb="FFFFFFFF"/><sz val="11"/><name val="Calibri"/></font>
<font><b/><sz val="11"/><color rgb="FF3D34A0"/><name val="Calibri"/></font>
<font><b/><sz val="14"/><color rgb="FF1F1F2E"/><name val="Calibri"/></font>
</fonts>
<fills count="4">
<fill><patternFill patternType="none"/></fill>
<fill><patternFill patternType="gray125"/></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FF6C5CE7"/></patternFill></fill>
<fill><patternFill patternType="solid"><fgColor rgb="FFEFECFF"/></patternFill></fill>
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
<cellXfs count="7">
<xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/>
<xf numFmtId="0" fontId="1" fillId="2" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1" applyAlignment="1"><alignment horizontal="center" vertical="center"/></xf>
<xf numFmtId="0" fontId="0" fillId="0" borderId="1" xfId="0" applyBorder="1"/>
<xf numFmtId="164" fontId="0" fillId="0" borderId="1" xfId="0" applyNumberFormat="1" applyBorder="1"/>
<xf numFmtId="0" fontId="2" fillId="3" borderId="1" xfId="0" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="164" fontId="2" fillId="3" borderId="1" xfId="0" applyNumberFormat="1" applyFont="1" applyFill="1" applyBorder="1"/>
<xf numFmtId="0" fontId="3" fillId="0" borderId="0" xfId="0" applyFont="1"/>
</cellXfs>
<cellStyles count="1"><cellStyle name="Normal" xfId="0" builtinId="0"/></cellStyles>
</styleSheet>"""

# cellXfs indekslari: 0=default 1=sarlavha 2=matn 3=raqam 4=jami-matn 5=jami-raqam 6=title


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

