# -*- coding: utf-8 -*-
"""Generador del Informe de Investigación — Caso 5 (Municipio Páez · El Guapo).
Produce OBRAS-HIDRAULICAS/Informe_Caso5_Municipio_Paez_ElGuapo.docx
Uso:  python3 build_docx.py
"""
import os, re, copy
from docx import Document

from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

BASE = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE)

TEAL   = "0E4D64"; TEAL2 = "1D6E8C"; SAND = "E76F51"; GOLD = "C9A227"
INK    = "1F2A33"; GRAY  = "5B6770"; LIGHT = "EAF2F6"; ZEBRA = "F5FAFC"

def rgb(hexstr): return RGBColor.from_string(hexstr)

# ---------------------------------------------------------------- documento base
doc = Document()

# propiedades
cp = doc.core_properties
cp.title = "Informe de Investigación — Caso 5 · Municipio Páez (El Guapo) — Fuentes subterráneas"
cp.author = "Equipo de investigación — Caso 5"
cp.subject = "U.C. Obras Hidráulicas · Tema 4 · PNFCC Trayecto IV Sección 01"
cp.company = "PNFCC — U.C. Obras Hidráulicas"

# estilo Normal y encabezados
st = doc.styles["Normal"]
st.font.name = "Georgia"; st.font.size = Pt(10); st.font.color.rgb = rgb(INK)
st.paragraph_format.space_before = Pt(0); st.paragraph_format.space_after = Pt(7)
st.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE; st.paragraph_format.line_spacing = 1.12
st.paragraph_format.alignment = 3  # justified

def style_heading(name, size, color, bold=True, before=14, after=6, border=False):
    s = doc.styles[name]
    s.font.name = "Georgia"; s.font.bold = bold; s.font.size = Pt(size); s.font.color.rgb = rgb(color)
    s.paragraph_format.space_before = Pt(before); s.paragraph_format.space_after = Pt(after)
    s.paragraph_format.keep_with_next = True; s.paragraph_format.line_spacing = 1.15
    s.paragraph_format.alignment = 0
    # bottom border para H1
    if border:
        ppr = s.element.get_or_add_pPr()
        pbdr = ppr.find(qn("w:pBdr"))
        if pbdr is None:
            pbdr = OxmlElement("w:pBdr"); ppr.append(pbdr)
        bottom = OxmlElement("w:bottom")
        bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "8")
        bottom.set(qn("w:space"), "2"); bottom.set(qn("w:color"), TEAL2)
        pbdr.append(bottom)

style_heading("Heading 1", 15.5, TEAL, True, 16, 8, border=True)
style_heading("Heading 2", 11.5, TEAL2, True, 12, 5)
style_heading("Heading 3", 10, INK, True, 8, 4)

# sección 1 = portada (sin encabezado/pie), sección 2 = contenido
sec1 = doc.sections[0]
sec1.page_width, sec1.page_height = Cm(21.59), Cm(27.94)   # carta
for s in doc.sections:
    s.left_margin = s.right_margin = Cm(2.3)
    s.top_margin = s.bottom_margin = Cm(2.1)
    s.header_distance, s.footer_distance = Cm(1.0), Cm(0.9)

# ---------------------------------------------------------------- helpers OXML
def set_cell_bg(cell, hexfill):
    shd = cell._tc.get_or_add_tcPr().find(qn("w:shd"))
    if shd is None:
        shd = OxmlElement("w:shd"); cell._tc.get_or_add_tcPr().append(shd)
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hexfill)

def set_cell_margins(cell, top=60, bottom=60, left=80, right=80):
    mar = cell._tc.get_or_add_tcPr().find(qn("w:tcMar"))
    if mar is not None: cell._tc.get_or_add_tcPr().remove(mar)
    mar = OxmlElement("w:tcMar")
    for tag, val in (("top",top),("bottom",bottom),("start",left),("end",right)):
        el = OxmlElement(f"w:{tag}")
        el.set(qn("w:w"), str(val)); el.set(qn("w:type"), "dxa"); mar.append(el)
    cell._tc.get_or_add_tcPr().append(mar)

def set_table_borders(table, color=TEAL2, sz=10, inside=True):
    tbl = table._tbl
    borders = tbl.tblPr.find(qn("w:tblBorders"))
    if borders is not None: tbl.tblPr.remove(borders)
    borders = OxmlElement("w:tblBorders")
    def edge(name):
        el = OxmlElement(f"w:{name}")
        el.set(qn("w:val"),"single"); el.set(qn("w:sz"),str(sz))
        el.set(qn("w:space"),"0"); el.set(qn("w:color"),color)
        borders.append(el)
    for e in ("top","bottom","start","end"): edge(e)
    if inside:
        for e in ("insideH","insideV"): edge(e)
    tbl.tblPr.append(borders)

def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr()
    el = OxmlElement("w:tblHeader"); trPr.append(el)

def add_field_run(paragraph, fieldcode):
    r1 = paragraph.add_run(); f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"),"begin"); r1._r.append(f1)
    r2 = paragraph.add_run(); it = OxmlElement("w:instrText"); it.set(qn("xml:space"),"preserve"); it.text = fieldcode; r2._r.append(it)
    r3 = paragraph.add_run(); f2 = OxmlElement("w:fldChar"); f2.set(qn("w:fldCharType"),"end"); r3._r.append(f2)

def add_bottom_border(paragraph, color=TEAL2, sz=10, space=2):
    pPr = paragraph._p.get_or_add_pPr()
    pbdr = pPr.find(qn("w:pBdr"))
    if pbdr is None:
        pbdr = OxmlElement("w:pBdr"); pPr.append(pbdr)
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"),"single"); bottom.set(qn("w:sz"),str(sz)); bottom.set(qn("w:space"),str(space)); bottom.set(qn("w:color"),color)
    pbdr.append(bottom)

TOKEN = re.compile(r"(\*\*.+?\*\*|\*.+?\*)", re.S)
def add_runs(paragraph, text, size=None, color=None, base_bold=False, base_italic=False, font=None):
    for part in TOKEN.split(text):
        if not part: continue
        bold, italic, chunk = base_bold, base_italic, part
        if part.startswith("**") and part.endswith("**"): bold, chunk = True, part[2:-2]
        elif part.startswith("*") and part.endswith("*"): italic, chunk = True, part[1:-1]
        r = paragraph.add_run(chunk)
        r.bold, r.italic = bold, italic
        if size: r.font.size = Pt(size)
        if color: r.font.color.rgb = rgb(color)
        if font: r.font.name = font

def para_border_box(doc):
    t = doc.add_table(rows=1, cols=1); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = True
    cell = t.cell(0,0)
    set_cell_bg(cell, LIGHT); set_cell_margins(cell, 120, 120, 160, 160)
    set_table_borders(t, color=TEAL2, sz=12, inside=False)
    cell.paragraphs[0].paragraph_format.space_after = Pt(0)
    return t

# ---------------------------------------------------------------- portada
def cover():
    # franja superior institucional
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(2)
    add_runs(p, "R E P Ú B L I C A   B O L I V A R I A N A   D E   V E N E Z U E L A", size=8.5, color=GRAY)
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(0)
    add_runs(p, "P N F C C   ·   T R A Y E C T O   I V   ·   S E C C I Ó N   0 1", size=9.5, color=TEAL2, base_bold=True)
    add_bottom_border(p, color=TEAL2, sz=10, space=6)

    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_before = Pt(16); p.paragraph_format.space_after = Pt(0)
    add_runs(p, "U.C.:  O B R A S   H I D R Á U L I C A S", size=11, color=INK, base_bold=True)
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(10)
    add_runs(p, "Tema 4 · Obras hidráulicas relacionadas con fuentes subterráneas", size=9.5, color=GRAY, base_italic=True)
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(10)
    add_runs(p, "Prof.: María Nieves", size=10, color=INK)

    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(2)
    add_runs(p, "I N F O R M E   D E   I N V E S T I G A C I Ó N", size=26, color=TEAL, base_bold=True, font="Georgia")
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(4)
    add_runs(p, "Caso 5 · Piedemonte y terrazas de El Guapo", size=17.5, color=TEAL2, base_bold=True)
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(12)
    add_runs(p, "Municipio Páez, Estado Miranda — Prospección geofísica, construcción y recarga del acuífero de piedemonte de la cuenca del río Guapo", size=10.5, color=INK)

    # imagen de portada
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(os.path.join(BASE, "figs", "cover.jpg"), width=Cm(16.4))
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(10)
    add_runs(p, "Ilustración referencial del piedemonte barloventeño (imagen generada con fines ilustrativos)", size=7.5, color=GRAY, base_italic=True)

    # ficha de datos
    t = doc.add_table(rows=4, cols=2); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    t.columns[0].width = Cm(5.2); t.columns[1].width = Cm(11.0)
    data = [("Actividad", "Actividad evaluativa — Informe de investigación · Valor: 20 pts."),
            ("Autores", "Equipo de investigación — Caso 5 (nombres según listado del equipo)"),
            ("Lugar y fecha", "Carrizal, estado Miranda, Venezuela — 22 de noviembre de 2026"),
            ("Bibliografía", "Normas APA (7.ª ed.) · Fuentes detalladas en la sección 7 del informe")]
    for i, (k, v) in enumerate(data):
        c0, c1 = t.cell(i,0), t.cell(i,1)
        c0.width = Cm(5.2); c1.width = Cm(11.0)
        set_cell_bg(c0, LIGHT); set_cell_margins(c0, 60,60,100,100); set_cell_margins(c1, 60,60,140,60)
        p0 = c0.paragraphs[0]; p0.paragraph_format.space_after = Pt(0)
        add_runs(p0, k.upper(), size=8, color=TEAL2, base_bold=True)
        p1 = c1.paragraphs[0]; p1.paragraph_format.space_after = Pt(0)
        add_runs(p1, v, size=9, color=INK)
    set_table_borders(t, color="D4E0E7", sz=8, inside=True)

    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_before = Pt(10)
    add_bottom_border(p, color=TEAL2, sz=8, space=2)
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_before = Pt(2)
    add_runs(p, "Documento de entrega académica · Todos los datos técnicos provienen de las fuentes citadas en la sección 7", size=7.5, color=GRAY, base_italic=True)

cover()

# nueva sección para el cuerpo (con encabezado/pie)
sec2 = doc.add_section(2)  # WD_SECTION_START.NEW_PAGE == 2
sec2.header.is_linked_to_previous = False; sec2.footer.is_linked_to_previous = False
sec1.header.is_linked_to_previous = False; sec1.footer.is_linked_to_previous = False
# portada sin encabezado/pie
sec1.header.paragraphs[0].text = ""; sec1.footer.paragraphs[0].text = ""

# encabezado sección 2
hp = sec2.header.paragraphs[0]; hp.alignment = 3
hp.paragraph_format.space_after = Pt(2)
add_runs(hp, "U.C. OBRAS HIDRÁULICAS  ·  TEMA 4  ", size=7, color=GRAY, base_bold=True)
add_runs(hp, "|  CASO 5 · MUNICIPIO PÁEZ — EL GUAPO", size=7, color=TEAL2, base_bold=True)
add_bottom_border(hp, color=TEAL2, sz=8, space=3)

# pie sección 2
fp = sec2.footer.paragraphs[0]; fp.alignment = 3
fp.paragraph_format.space_before = Pt(2)
add_runs(fp, "Informe de investigación — Fuentes subterráneas  |  PNFCC · Trayecto IV · Sección 01  |  Página ", size=7, color=GRAY)
add_field_run(fp, "PAGE")
add_runs(fp, " de ", size=7, color=GRAY)
add_field_run(fp, "NUMPAGES")
# estilo runs de campo
for r in fp.runs:
    r.font.size = Pt(7); r.font.color.rgb = rgb(GRAY)

# línea superior del pie
pPr = fp._p.get_or_add_pPr()
pbdr = OxmlElement("w:pBdr"); top = OxmlElement("w:top")
top.set(qn("w:val"),"single"); top.set(qn("w:sz"),"8"); top.set(qn("w:space"),"3"); top.set(qn("w:color"),TEAL2)
pbdr.append(top); pPr.append(pbdr)

# ---------------------------------------------------------------- bloques
from report_text import CONTENT

def render_idx():
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(4); p.paragraph_format.space_after = Pt(6)
    add_runs(p, "Contenido del informe (sin numeración de página; los títulos corresponden a las secciones del cuerpo).", size=8.5, color=GRAY, base_italic=True)
    entries = []
    for blk in CONTENT:
        if blk[0] == "h1": entries.append((1, blk[1]))
        elif blk[0] == "h2": entries.append((2, blk[1]))
    for level, text in entries:
        if text == "Índice": continue
        p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(3 if level == 1 else 1)
        p.paragraph_format.left_indent = Cm(0 if level == 1 else 0.55)
        p.paragraph_format.alignment = 0
        if level == 1:
            add_runs(p, text.upper(), size=9.5, color=TEAL2, base_bold=True)
        else:
            add_runs(p, text, size=9, color=INK)

def render_table(spec):
    # rótulo de tabla (estilo APA)
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(8); p.paragraph_format.space_after = Pt(0)
    add_runs(p, spec["num"], size=9, color=TEAL2, base_bold=True)
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(3)
    add_runs(p, spec["title"], size=9.5, color=INK, base_italic=True)
    headers, rows = spec["headers"], spec["rows"]
    widths = spec.get("widths")
    t = doc.add_table(rows=len(rows)+1, cols=len(headers)); t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for i, w in enumerate(widths): t.columns[i].width = Cm(w)
    for i, htext in enumerate(headers):
        cell = t.cell(0, i); cell.width = Cm(widths[i])
        set_cell_bg(cell, TEAL); set_cell_margins(cell, 70, 70, 90, 90)
        p0 = cell.paragraphs[0]; p0.paragraph_format.space_after = Pt(0); p0.alignment = 0
        add_runs(p0, "**" + htext + "**", size=8, color="FFFFFF")
    set_repeat_table_header(t.rows[0])
    for r_i, row in enumerate(rows):
        for c_i, celltext in enumerate(row):
            cell = t.cell(r_i+1, c_i); cell.width = Cm(widths[c_i])
            if r_i % 2 == 1: set_cell_bg(cell, ZEBRA)
            set_cell_margins(cell, 55, 55, 90, 90)
            p0 = cell.paragraphs[0]; p0.paragraph_format.space_after = Pt(0); p0.paragraph_format.line_spacing = 1.05
            add_runs(p0, celltext, size=8, color=INK)
    set_table_borders(t, color="C4D6DE", sz=6, inside=True)
    if spec.get("note"):
        p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(8)
        add_runs(p, "Nota. ", size=7.5, color=GRAY, base_bold=True, base_italic=True)
        add_runs(p, spec["note"], size=7.5, color=GRAY, base_italic=True)

def render_figure(spec):
    p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_before = Pt(10); p.paragraph_format.space_after = Pt(2)
    p.add_run().add_picture(os.path.join(BASE, spec["path"]), width=Cm(spec["width"]))
    cap = doc.add_paragraph(); cap.alignment = 3; cap.paragraph_format.space_after = Pt(10)
    m = re.match(r"(Figura \d+\.)\s*(.*)", spec["caption"])
    if m:
        add_runs(cap, m.group(1) + " ", size=8, color=TEAL2, base_bold=True)
        add_runs(cap, m.group(2), size=8, color=GRAY, base_italic=True)
    else:
        add_runs(cap, spec["caption"], size=8, color=GRAY, base_italic=True)

def render_bullets(items, ordered=False):
    for i, item in enumerate(items, 1):
        p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(0.55)
        p.paragraph_format.first_line_indent = Cm(-0.32); p.paragraph_format.space_after = Pt(3)
        marker = f"{i}." if ordered else "•"
        add_runs(p, marker + "  ", size=9.5, color=TEAL2, base_bold=True)
        add_runs(p, item, size=10)

def render_refs(items):
    for ref in items:
        p = doc.add_paragraph(); p.paragraph_format.left_indent = Cm(0.75)
        p.paragraph_format.first_line_indent = Cm(-0.75); p.paragraph_format.space_after = Pt(5)
        p.paragraph_format.line_spacing = 1.1
        p.alignment = 0
        add_runs(p, ref, size=9)

def render_callout(text):
    t = para_border_box(doc)
    cell = t.cell(0, 0)
    p0 = cell.paragraphs[0]; p0.paragraph_format.space_after = Pt(0); p0.paragraph_format.line_spacing = 1.15
    add_runs(p0, "◆  ", size=10, color=SAND, base_bold=True)
    add_runs(p0, text, size=8.7, color=TEAL)
    doc.add_paragraph().paragraph_format.space_after = Pt(4)

for blk in CONTENT:
    kind = blk[0]
    if kind == "h1":
        doc.add_paragraph(blk[1], style="Heading 1")
    elif kind == "h2":
        doc.add_paragraph(blk[1], style="Heading 2")
    elif kind == "h3":
        doc.add_paragraph(blk[1], style="Heading 3")
    elif kind == "p":
        p = doc.add_paragraph(); add_runs(p, blk[1])
    elif kind == "bullets":
        render_bullets(blk[1], ordered=False)
    elif kind == "steps":
        render_bullets(blk[1], ordered=True)
    elif kind == "refs":
        render_refs(blk[1])
    elif kind == "table":
        render_table(blk[1])
    elif kind == "figure":
        render_figure(blk[1])
    elif kind == "callout":
        render_callout(blk[1])
    elif kind == "idx":
        render_idx()

out = os.path.join(BASE, "Informe_Caso5_Municipio_Paez_ElGuapo.docx")
doc.save(out)
print("OK ->", out, f"{os.path.getsize(out)/1024:.0f} KB")
