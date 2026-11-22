# -*- coding: utf-8 -*-
import datetime
from docx import Document
from docx.shared import Pt, RGBColor, Cm
from docx.enum.text import WD_LINE_SPACING
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
import copy

NAVY   = RGBColor(0x0F, 0x2A, 0x43)
GOLD   = RGBColor(0xB8, 0x86, 0x0B)
RED    = RGBColor(0xB3, 0x20, 0x2C)
GREY   = RGBColor(0x59, 0x59, 0x59)
NAVY_HEX, SOFT_HEX, GOLD_HEX = "0F2A43", "EAF1F8", "E8A020"
YELLOW_HEX, BLUE_HEX, RED_HEX = "FFCC00", "00247D", "CF142B"

doc = Document()

# ---------- Page setup ----------
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)  # carta vertical (A4-ish)
sec.top_margin, sec.bottom_margin = Cm(2.2), Cm(2.2)
sec.left_margin, sec.right_margin = Cm(2.4), Cm(2.4)
sec.header_distance, sec.footer_distance = Cm(1.1), Cm(1.1)

# ---------- Base styles ----------
styles = doc.styles
normal = styles["Normal"]
normal.font.name = "Georgia"
normal.font.size = Pt(11)
normal.font.color.rgb = RGBColor(0x1A, 0x1A, 0x1A)
normal.paragraph_format.space_before = Pt(0)
normal.paragraph_format.space_after = Pt(8)
normal.paragraph_format.line_spacing = 1.32

def style_heading(name, size, color, before, after, bold=True, caps=False):
    s = styles[name]
    s.font.name = "Georgia"; s.font.bold = bold; s.font.size = Pt(size); s.font.color.rgb = color
    s.paragraph_format.space_before = Pt(before); s.paragraph_format.space_after = Pt(after)
    s.paragraph_format.line_spacing = 1.15; s.paragraph_format.keep_with_next = True
    s.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE

style_heading("Title", 22, NAVY, 6, 6)
style_heading("Heading 1", 17, NAVY, 18, 8)
style_heading("Heading 2", 13, GOLD, 14, 6)
style_heading("Heading 3", 11.5, NAVY, 10, 4)

# ---------- Helpers ----------
def set_cell_bg(cell, hex_fill):
    shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_fill)
    cell._tc.get_or_add_tcPr().append(shd)

def set_cell_margins(cell, top=90, bottom=90, left=110, right=110):
    mar = OxmlElement("w:tcMar")
    for tag, val in (("top", top), ("bottom", bottom), ("start", left), ("end", right)):
        el = OxmlElement(f"w:{tag}")
        el.set(qn("w:w"), str(val)); el.set(qn("w:type"), "dxa"); mar.append(el)
    cell._tc.get_or_add_tcPr().append(mar)

def set_repeat_table_header(row):
    trPr = row._tr.get_or_add_trPr(); trPr.append(OxmlElement("w:tblHeader"))

def set_col_widths(table, widths):
    table.autofit = False
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    grid = table._tbl.find(qn("w:tblGrid"))
    for gc, w in zip(grid.findall(qn("w:gridCol")), widths):
        gc.set(qn("w:w"), str(int(w * 567)))  # cm -> dxa
    for row in table.rows:
        for i, cell in enumerate(row.cells):
            cell.width = Cm(widths[i])

def add_field_run(paragraph, fieldcode):
    r1 = OxmlElement("w:r"); fc1 = OxmlElement("w:fldChar"); fc1.set(qn("w:fldCharType"), "begin"); r1.append(fc1)
    r2 = OxmlElement("w:r"); it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = fieldcode; r2.append(it)
    r3 = OxmlElement("w:r"); fc3 = OxmlElement("w:fldChar"); fc3.set(qn("w:fldCharType"), "end"); r3.append(fc3)
    for r in (r1, r2, r3): paragraph._p.append(r)

def h1(text):
    p = doc.add_heading(text, level=1)
    # bottom border for H1
    pPr = p._p.get_or_add_pPr()
    pbdr = OxmlElement("w:pBdr"); bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single"); bottom.set(qn("w:sz"), "8"); bottom.set(qn("w:space"), "2"); bottom.set(qn("w:color"), GOLD_HEX)
    pbdr.append(bottom); pPr.append(pbdr)
    return p

def h2(text): return doc.add_heading(text, level=2)
def h3(text): return doc.add_heading(text, level=3)

def body(text_runs, justify=True, size=11, space_after=8, space_before=0):
    """text_runs: str OR list of (text, bold, italic)"""
    p = doc.add_paragraph()
    p.paragraph_format.space_after = Pt(space_after); p.paragraph_format.space_before = Pt(space_before)
    if justify: p.alignment = 3  # WD_ALIGN_PARAGRAPH.JUSTIFY
    if isinstance(text_runs, str):
        text_runs = [(text_runs, False, False)]
    for t, b, i in text_runs:
        r = p.add_run(t); r.bold, r.italic = b, i; r.font.size = Pt(size)
    return p

def bullets(items):
    for item in items:
        p = doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.55); p.paragraph_format.first_line_indent = Cm(-0.3)
        p.paragraph_format.space_after = Pt(4)
        r = p.add_run("▸  "); r.font.color.rgb = GOLD; r.bold = True; r.font.size = Pt(10)
        if isinstance(item, str):
            item = [(item, False)]
        for t, b in item:
            rr = p.add_run(t); rr.bold = b; rr.font.size = Pt(11)

def caption(label, text, source=None):
    p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(2); p.alignment = 1
    r1 = p.add_run(label + ". "); r1.bold = True; r1.font.size = Pt(9); r1.font.color.rgb = NAVY
    r2 = p.add_run(text); r2.italic = True; r2.font.size = Pt(9); r2.font.color.rgb = GREY
    if source:
        p2 = doc.add_paragraph(); p2.alignment = 1; p2.paragraph_format.space_after = Pt(10)
        r = p2.add_run(source); r.font.size = Pt(8); r.font.color.rgb = GREY; r.italic = True

def make_table(headers, rows, widths, header_bg=NAVY_HEX, header_fg="FFFFFF", size=9.5):
    t = doc.add_table(rows=len(rows) + 1, cols=len(headers))
    for i, (htext, w) in enumerate(zip(headers, widths)):
        cell = t.cell(0, i); set_cell_bg(cell, header_bg); set_cell_margins(cell)
        p = cell.paragraphs[0]; p.paragraph_format.space_after = Pt(2); p.paragraph_format.line_spacing = 1.05
        r = p.add_run(htext); r.bold = True; r.font.size = Pt(size); r.font.color.rgb = RGBColor.from_string(header_fg)
    for ri, row in enumerate(rows):
        for i, val in enumerate(row):
            cell = t.cell(ri + 1, i); set_cell_margins(cell)
            if ri % 2 == 1: set_cell_bg(cell, SOFT_HEX)
            p = cell.paragraphs[0]; p.paragraph_format.space_after = Pt(2); p.paragraph_format.line_spacing = 1.15
            r = p.add_run(str(val)); r.font.size = Pt(size)
    set_col_widths(t, widths)
    set_repeat_table_header(t.rows[0])
    return t

def spacer(pts): 
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(pts); return p

IMG_DIR = "/home/user/ingenieria/informes/tema4-caso3-brion/"
LOGO = "/home/user/ingenieria/image-search/uptbal-cintillo-universidad-polit-cnica--1.png"

# =====================================================================
# PORTADA (sección 0 — sin encabezado/pie)
# =====================================================================
sec.header_distance = Cm(1.0)

# Logo
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(4)
p.add_run().add_picture(LOGO, width=Cm(2.35))

# Institución
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(0)
r = p.add_run("REPÚBLICA BOLIVARIANA DE VENEZUELA"); r.font.size = Pt(10.5); r.font.color.rgb = GREY; r.bold = True
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(0); p.paragraph_format.line_spacing = 1.15
r = p.add_run("UNIVERSIDAD POLITÉCNICA TERRITORIAL\nDE BARLOVENTO «ARGELIA LAYA»"); r.bold = True; r.font.size = Pt(15.5); r.font.color.rgb = NAVY
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(0)
r = p.add_run("UPTBAL  ·  Sede Higuerote, Municipio Brión  ·  Estado Bolivariano de Miranda"); r.font.size = Pt(9.5); r.font.color.rgb = GOLD; r.bold = True
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(2)
r = p.add_run("Decreto de creación N.º 7.568  ·  Gaceta Oficial N.º 5.987  ·  16 de julio de 2010"); r.font.size = Pt(7.5); r.font.color.rgb = GREY

# Tricolor cintillo bar
tri = doc.add_table(rows=1, cols=3)
tri.alignment = WD_TABLE_ALIGNMENT.CENTER
set_col_widths(tri, [5.4, 5.4, 5.4])
for i, colr in enumerate((YELLOW_HEX, BLUE_HEX, RED_HEX)):
    c = tri.cell(0, i); set_cell_bg(c, colr); set_cell_margins(c, top=30, bottom=30, left=10, right=10)
    c.paragraphs[0].paragraph_format.space_after = Pt(0); c.paragraphs[0].paragraph_format.line_spacing = 1.0
    c.paragraphs[0].add_run(" ").font.size = Pt(2)
spacer(6)

p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(0)
r = p.add_run("Programa Nacional de Formación en Construcción Civil (PNFCC)"); r.bold = True; r.font.size = Pt(11); r.font.color.rgb = NAVY
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(0)
r = p.add_run("Trayecto IV  ·  Sección 01"); r.font.size = Pt(10.5)
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(0)
r = p.add_run("Unidad Curricular: Obras Hidráulicas"); r.bold = True; r.font.size = Pt(12.5); r.font.color.rgb = NAVY
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(2)
r = p.add_run("Profesora: María Nieves"); r.font.size = Pt(10.5)

spacer(16)

p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(2)
r = p.add_run("INFORME DE INVESTIGACIÓN  ·  TEMA 4"); r.bold = True; r.font.size = Pt(10); r.font.color.rgb = RED

p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(4); p.paragraph_format.line_spacing = 1.12
r = p.add_run("OBRAS HIDRÁULICAS RELACIONADAS CON FUENTES SUBTERRÁNEAS"); r.bold = True; r.font.size = Pt(21); r.font.color.rgb = NAVY
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(2); p.paragraph_format.line_spacing = 1.25
r = p.add_run("Caso: Municipio Brión (Zona Costera e Insular de Higuerote)"); r.bold = True; r.font.size = Pt(13.5); r.font.color.rgb = GOLD
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(0)
r = p.add_run("El equilibrio hidrostático entre la lente de agua dulce y el agua salada del mar, la intrusión salina\ny las estrategias de gestión frente a la demanda turística estacional"); r.italic = True; r.font.size = Pt(10); r.font.color.rgb = GREY

spacer(14)

# Participantes
t = doc.add_table(rows=5, cols=2)
t.alignment = WD_TABLE_ALIGNMENT.CENTER
set_col_widths(t, [7.6, 6.4])
labels = [("PARTICIPANTES", "C.I.")] + [(f"[Nombre y Apellido {i}]", "[V-00.000.000]") for i in range(1, 5)]
for i, (a, b) in enumerate(labels):
    ca, cb = t.cell(i, 0), t.cell(i, 1)
    set_cell_margins(ca, top=60, bottom=60); set_cell_margins(cb, top=60, bottom=60)
    pa, pb = ca.paragraphs[0], cb.paragraphs[0]
    pa.alignment, pb.alignment = 1, 1
    pa.paragraph_format.space_after = Pt(0); pb.paragraph_format.space_after = Pt(0)
    pa.paragraph_format.line_spacing = 1.0; pb.paragraph_format.line_spacing = 1.0
    ra = pa.add_run(a); rb = pb.add_run(b)
    if i == 0:
        set_cell_bg(ca, NAVY_HEX); set_cell_bg(cb, NAVY_HEX)
        ra.bold = rb.bold = True; ra.font.color.rgb = rb.font.color.rgb = RGBColor.from_string("FFFFFF"); ra.font.size = rb.font.size = Pt(10)
    else:
        ra.font.size = rb.font.size = Pt(10); ra.font.color.rgb = RGBColor(0x7F, 0x7F, 0x7F); rb.font.color.rgb = RGBColor(0x7F, 0x7F, 0x7F)
        if i % 2 == 0: set_cell_bg(ca, SOFT_HEX); set_cell_bg(cb, SOFT_HEX)
spacer(10)

p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_after = Pt(0)
r = p.add_run("Higuerote, noviembre de 2026"); r.font.size = Pt(11); r.bold = True; r.font.color.rgb = NAVY
p = doc.add_paragraph(); p.alignment = 1
r = p.add_run("Fecha de entrega: 19 de noviembre de 2026   ·   Valoración: 20 puntos"); r.font.size = Pt(9.5); r.font.color.rgb = GREY

# =====================================================================
# Sección 2: contenido con encabezado y pie
# =====================================================================
new_sec = doc.add_section(2)  # WD_SECTION.NEW_PAGE
new_sec.page_height, new_sec.page_width = Cm(29.7), Cm(21.0)
new_sec.top_margin, new_sec.bottom_margin = Cm(2.2), Cm(2.2)
new_sec.left_margin, new_sec.right_margin = Cm(2.4), Cm(2.4)
new_sec.header_distance, new_sec.footer_distance = Cm(1.1), Cm(1.1)
new_sec.header.is_linked_to_previous = False
new_sec.footer.is_linked_to_previous = False
# Portada sin encabezado/pie
sec.header.is_linked_to_previous = False
sec.footer.is_linked_to_previous = False

hp = new_sec.header.paragraphs[0]; hp.alignment = 1; hp.paragraph_format.space_after = Pt(0)
hp.paragraph_format.line_spacing = 1.0
r = hp.add_run("OBRAS HIDRÁULICAS  ·  FUENTES SUBTERRÁNEAS"); r.font.size = Pt(7.5); r.bold = True; r.font.color.rgb = NAVY
r = hp.add_run("   |   Caso: Municipio Brión (Higuerote)"); r.font.size = Pt(7.5); r.font.color.rgb = GREY
pPr = hp._p.get_or_add_pPr(); pbdr = OxmlElement("w:pBdr"); bot = OxmlElement("w:bottom")
bot.set(qn("w:val"), "single"); bot.set(qn("w:sz"), "6"); bot.set(qn("w:space"), "2"); bot.set(qn("w:color"), GOLD_HEX); pbdr.append(bot); pPr.append(pbdr)

fp = new_sec.footer.paragraphs[0]; fp.alignment = 1; fp.paragraph_format.space_before = Pt(2)
r = fp.add_run("U.C. Obras Hidráulicas  ·  PNFCC  Trayecto IV, Sección 01  ·  UPTBAL        "); r.font.size = Pt(7.5); r.font.color.rgb = GREY
rr = fp.add_run("Página "); rr.font.size = Pt(7.5); rr.font.color.rgb = GREY
add_field_run(fp, "PAGE")
rr = fp.add_run(" de "); rr.font.size = Pt(7.5); rr.font.color.rgb = GREY
add_field_run(fp, "NUMPAGES")

print("Portada y secciones listas")

# =====================================================================
# ÍNDICE
# =====================================================================
h1("Contenido del informe")
toc_entries = [
    ("Resumen", "3"),
    ("1.  Introducción", "4"),
    ("2.  Contexto del caso: Municipio Brión (Zona Costera e Insular de Higuerote)", "5"),
    ("     2.1  Ubicación, población y vocación turística", "5"),
    ("     2.2  Hidrogeología local y antecedentes de estudio", "6"),
    ("3.  Dinámica costera: el equilibrio hidrostático entre la lente de agua dulce y el mar", "7"),
    ("     3.1  El modelo de Ghyben–Herzberg", "7"),
    ("     3.2  La zona de mezcla, la descarga al mar y las mareas", "8"),
    ("     3.3  Evidencias hidroquímicas en la parroquia Higuerote", "9"),
    ("4.  Impacto humano: la demanda turística estacional y la intrusión salina", "10"),
    ("     4.1  El turismo como forzante del bombeo estacional", "10"),
    ("     4.2  Mecanismo físico: del abatimiento a la cuña salina", "11"),
    ("     4.3  Consecuencias sanitarias, económicas y ambientales", "12"),
    ("5.  Mitigación: gestión y control del bombeo para frenar la cuña salina", "12"),
    ("     5.1  Medidas de control del bombeo y gestión de la demanda", "13"),
    ("     5.2  Monitoreo hidroquímico y piezométrico", "14"),
    ("     5.3  Protección de la recarga y del entorno", "15"),
    ("     5.4  Marco jurídico e institucional aplicable", "15"),
    ("     5.5  Participación comunitaria", "16"),
    ("6.  Conclusiones", "17"),
    ("Referencias", "18"),
]
for txt, _ in toc_entries:
    p = doc.add_paragraph(); p.paragraph_format.space_after = Pt(4); p.paragraph_format.line_spacing = 1.15
    indent = txt.startswith("     ")
    r = p.add_run(txt.strip())
    r.font.size = Pt(10 if indent else 11)
    r.font.color.rgb = GREY if indent else NAVY
    if not indent: r.bold = True
spacer(4)
p = doc.add_paragraph(); r = p.add_run("El índice lista las secciones del informe en su orden de lectura."); r.italic = True; r.font.size = Pt(8.5); r.font.color.rgb = GREY

# =====================================================================
# RESUMEN
# =====================================================================
h1("Resumen")
body([("El presente informe analiza las obras hidráulicas vinculadas a fuentes subterráneas en el Municipio Brión (Zona Costera e Insular de Higuerote, Estado Bolivariano de Miranda), con el propósito de responder tres interrogantes del caso asignado: (i) cómo se define el equilibrio hidrostático natural entre la lente de agua dulce y el agua salada del mar en un acuífero costero; (ii) por qué la alta demanda turística estacional acelera la intrusión salina en los pozos de la franja costera; y (iii) qué medidas de gestión o control de bombeo se recomiendan para frenar el avance de la cuña salina. Se aplicó una revisión documental e hidrogeológica de fuentes técnicas venezolanas (estudios del CIDIAT–IVIC en la parroquia Higuerote, antecedentes geológicos de la región de Barlovento y normativa nacional vigente), complementada con el modelo conceptual de Ghyben–Herzberg y con el inventario de pozos y manantiales existente. Los resultados evidencian que el acuífero aluvial costero es un sistema libre y vulnerable: la conductividad eléctrica registrada varía entre 370 y 1.885 µS/cm, con señales de incremento estacional en sitios bajo uso agrícola. Se concluye que la intrusión salina no es inevitable, sino una señal de gestión deficiente: ordenación del bombeo turístico, barreras y pozos de recarga, monitoreo sistemático y protección legal efectiva del acuífero son condiciones para la sostenibilidad del abastecimiento de Higuerote.", False, False)])
body([("Palabras clave: ", True, False), ("agua subterránea; acuífero costero; intrusión salina; Municipio Brión; gestión sostenible; Ghyben–Herzberg.", False, True)], space_after=4)

# =====================================================================
# 1. INTRODUCCIÓN
# =====================================================================
h1("1.  Introducción")
body([("El agua subterránea es aquella parte del agua procedente de la precipitación que se infiltra en el terreno hasta alcanzar la zona de saturación del subsuelo y constituye el mayor volumen de agua dulce disponible en el planeta (Nieves, s. f.). Frente a la variabilidad climática —sequías prolongadas asociadas a El Niño, lluvias extremas asociadas a La Niña y al rompimiento de presas como la de El Guapo en diciembre de 1999—, los acuíferos funcionan como un embalse natural estratégico: amortiguan los déficits estivales, sostienen a las comunidades dispersas y garantizan la continuidad del abastecimiento cuando las fuentes superficiales colapsan o se contaminan. En Venezuela, donde la distribución espacial y temporal de la lluvia es marcadamente irregular, el agua subterránea es, en la práctica, la reserva de contingencia de la costa caribeña.", False, False)])
body([("La región costera de Barlovento ilustra esta realidad con particular claridad. El Municipio Brión, cuya capital es Higuerote, depende en buena medida del acuífero aluvial de su planicie costera para el abastecimiento de la población permanente y —sobre todo— de la población flotante que, durante carnaval, Semana Santa, recesos escolares y diciembre, multiplica la demanda de agua potable y de servicio hotelero. Esta presión estacional se ejerce precisamente sobre el recurso más frágil del sistema: la lente de agua dulce que flota sobre la cuña de agua salada del mar Caribe (Custodio y Llamas, 1996; Todd y Mays, 2005).", False, False)])
body([("A diferencia de las fuentes superficiales, la contaminación subterránea —y en particular la salinización por intrusión marina— es de lenta detección y extremadamente difícil y costosa de revertir, debido al bajo flujo del agua en el subsuelo (Nieves, s. f.). Una vez que la cuña salina avanza tierra adentro y los pozos de captación se salinan, la recuperación puede tomar décadas. De allí que la gestión del acuífero de Higuerote no sea un asunto exclusivamente técnico, sino una decisión de política pública hídrica, sanitaria y territorial.", False, False)])
body([("Ante esta situación, el presente informe de investigación tiene como objetivo general ", False, False), ("analizar las obras hidráulicas relacionadas con fuentes subterráneas en el Municipio Brión, con énfasis en la dinámica hidrostático–hidrogeoquímica del acuífero costero de Higuerote y en las medidas de gestión que eviten su salinización", True, False), (". De este objetivo se derivan tres objetivos específicos, que estructuran el contenido del trabajo:", False, False)])
bullets([
    [("Definir el equilibrio hidrostático natural ", True), ("entre la lente de agua dulce subterránea y el agua salada del mar en un acuífero costero, aplicando el modelo de Ghyben–Herzberg y los antecedentes hidrogeológicos locales.", False)],
    [("Explicar por qué la alta demanda turística estacional acelera el fenómeno de la intrusión salina ", True), ("en los pozos de la franja costera de Higuerote, a partir del mecanismo de abatimiento y cono de depresión.", False)],
    [("Formular medidas de gestión y control de bombeo ", True), ("que permitan frenar el avance de la cuña salina, integrando monitoreo, recarga artificial, protección legal y participación comunitaria.", False)],
])
body([("Alcances y limitaciones. ", True, True), ("El estudio se circunscribe a la zona costera e insular de Higuerote (parroquia Higuerote, Municipio Brión), con énfasis en los sectores Oso Cotiza, Santa Ana–Valle Seco y el entorno de Carenero, donde existe información hidroquímica preliminar publicada por el IVIC, CIDIAT, ULA, USB e INAMEH (Silva et al., 2014). Se trata de una investigación de tipo documental y analítica: no incluye campañas de campo propias ni modelación numérica de flujo; las cifras hidroquímicas citadas corresponden a muestreos preliminares publicados y deben actualizarse con monitoreo sistemático antes de tomar decisiones de diseño definitivas.", False, False)])

# =====================================================================
# 2. CONTEXTO DEL CASO
# =====================================================================
h1("2.  Contexto del caso: Municipio Brión (Zona Costera e Insular de Higuerote)")

h2("2.1  Ubicación, población y vocación turística")
body([("El Municipio Brión está situado en el extremo oriental del Estado Bolivariano de Miranda, en plena subregión de Barlovento, y su capital es la ciudad de Higuerote. Limita con el mar Caribe al norte —franja de playas de alta afluencia como Higuerote y Carenero y áreas insulares asociadas— y con los valles y planicies aluviales del interior, irrigados por el río Curiepe, que desemboca en Higuerote, y por una red de caños y quebradas de régimen estacional (Pérez Zambrano y Gutiérrez Márquez, 2006). La economía local combina la agricultura de subsistencia, la pesca, el comercio y —de manera cada vez más determinante— el turismo de sol y playa.", False, False)])
body([("Esta vocación turística tiene una consecuencia hidráulica directa: la población se duplica o triplica en temporada alta (carnaval, Semana Santa, vacaciones escolares y diciembre), y con ella la demanda de agua para hospedaje, restaurantes, aseo y piscinas. Dado que el suministro superficial regional ha sido históricamente inestable —con episodios críticos como la destrucción de la presa El Guapo en diciembre de 1999—, buena parte de esa demanda adicional se cubre con bombeo de pozos y aljibes privados sobre el acuífero costero (Pérez Zambrano y Gutiérrez Márquez, 2006; Academia Nacional de la Ingeniería y el Hábitat [ANIH], 2025).", False, False)])

h2("2.2  Hidrogeología local y antecedentes de estudio")
body([("Desde el punto de vista hidrogeológico, la zona de Higuerote se asienta sobre la secuencia sedimentaria de la Cuenca del Bajo Tuy: formaciones Aramina, Caucagua y Mamporal, cubiertas por aluvión reciente —depósitos de abanicos aluviales y planicies de inundación de granulometría heterogénea, de alta porosidad y permeabilidad, que constituyen un acuífero libre (freático) costero de espesor moderado— (Pérez Zambrano y Gutiérrez Márquez, 2006). Estos sedimentos aluviales confieren al acuífero porosidades eficaces altas y transmisividades suficientes para captaciones domésticas y agropecuarias, pero con escasa protección natural frente a contaminantes superficiales y frente al avance del agua de mar.", False, False)])
body([("Los antecedentes técnicos disponibles son escasos pero consistentes. Alvarado (1982, citado en Pérez Zambrano y Gutiérrez Márquez, 2006) realizó el «Diagnóstico hidrogeológico de la región de Barlovento» y alertó sobre la «Salinización de acuíferos costeros de Venezuela por intrusión de agua de mar», proponiendo medidas de control para proteger la región. Más recientemente, un consorcio interinstitucional (IVIC, INAMEH, CIDIAT, ULA, USB y UCV) ejecutó el proyecto «Evaluación hidroquímica preliminar de un sistema acuífero de un sector costero del estado Miranda» en los sectores Oso Cotiza y Santa Ana–Valle Seco, al oeste de Carenero, en la parroquia Higuerote (Silva et al., 2014). El inventario de pozos y manantiales de ese estudio se reproduce en la Tabla 1.", False, False)])

caption("Tabla 1", "Inventario de pozos, aljibes y manantial de los sectores Oso Cotiza y Santa Ana–Valle Seco (parroquia Higuerote, Municipio Brión).", "Fuente: elaboración propia a partir de Silva et al. (2014), Tabla 1 y Figuras 1–2 del artículo. C = aljibe; P = pozo; M = manantial. N. e. = nivel estático; N. d. = nivel dinámico.")
make_table(
    ["Sitio", "Propietario / sitio", "Tipo", "CE (µS/cm)", "pH", "Nivel (m)"],
    [
        ["OCP1", "Fundo La Abuela (J. Molina)", "Aljibe", "1.540", "6,58", "N. d. 17,9"],
        ["OCP2", "Fundo Mi Futuro (I. Varoloche)", "Aljibe", "1.075", "6,41", "N. e. 3,2"],
        ["OCP3", "Fundo Agua Dulce (C. Echavarría)", "Pozo", "1.162", "6,58", "s/d"],
        ["OCP4", "Restaurant Doña Eva (J. De Lima)", "Aljibe", "1.885", "6,42", "N. e. 5,3"],
        ["OCP5", "Finca La Gorda (A. M. Roid)", "Manantial", "804", "6,53", "—"],
        ["SVP6", "Parcela / casa (C. Reyes)", "Aljibe", "370", "6,93", "N. e. 1,0"],
        ["SVP7", "Parcela (M. Arredondo)", "Aljibe", "999", "6,46", "N. e. 1,51"],
        ["SVP8", "Parcela (H. Vega)", "Aljibe", "976", "6,54", "N. e. 2,9"],
        ["SVM1", "Manantial, Qda. Valle Seco", "Manantial", "804", "6,53", "—"],
        ["SVP9", "Parque Aventura (M. Doscal)", "Aljibe", "442", "6,56", "N. e. 0,3"],
        ["OCP10", "Fundo El Milagro (H. López)", "Aljibe", "1.413", "6,82", "N. e. −0,08"],
        ["OCP11", "Parcela / casa (D. Reyes)", "Aljibe", "1.240", "6,59", "s/d"],
    ],
    [1.6, 6.3, 1.9, 2.2, 1.5, 2.6],
    size=8.5
)
spacer(6)

body([("Como se aprecia en la Figura 2, las conductividades eléctricas (CE) abarcan desde 370 µS/cm (SVP6, agua de mejor calidad) hasta 1.885 µS/cm (OCP4, sector cercano a la costa y de uso comercial). Cuatro sitios superan los 1.000 µS/cm y dos de ellos (OCP1 y OCP4) superan los 1.400 µS/cm, umbral a partir del cual el agua ya no se considera de excelente calidad para consumo directo sin tratamiento. Asimismo, los resultados temporales reportados muestran variaciones marcadas en sitios bajo uso agrícola y de cría (OCP11), donde los valores reportados en noviembre (3.000 mg/L) multiplicaron por 7,5 los de septiembre–octubre (400 mg/L) para la variable analizada, lo que sugiere tanto concentración estacional como aporte de origen antrópico (Silva et al., 2014).", False, False)])

doc.add_picture(IMG_DIR + "fig2_conductividad.png", width=Cm(15.6))
doc.paragraphs[-1].alignment = 1
caption("Figura 2", "Conductividad eléctrica por sitio de muestreo, sectores Oso Cotiza y Santa Ana–Valle Seco (2013–2014).", "Elaboración propia con datos de Silva et al. (2014).")

# =====================================================================
# 3. DINÁMICA COSTERA
# =====================================================================
h1("3.  Dinámica costera: equilibrio hidrostático entre la lente de agua dulce y el agua salada")

h2("3.1  El modelo de Ghyben–Herzberg")
body([("En un acuífero costero libre, el agua dulce —menos densa (ρf ≈ 1.000 kg/m³)— flota sobre el agua salada del mar (ρs ≈ 1.025 kg/m³). El equilibrio hidrostático puede estimarse con la relación clásica de Ghyben (1888) y Herzberg (1901), que vincula la altura del nivel freático sobre el nivel del mar (h) con la profundidad de la interfaz agua dulce–salada (z) medida bajo el nivel del mar:", False, False)])
p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_before = Pt(2); p.paragraph_format.space_after = Pt(10)
r = p.add_run("z  =  ( ρf / (ρs − ρf) ) · h   ≈   40 · h"); r.italic = True; r.bold = True; r.font.size = Pt(15); r.font.color.rgb = NAVY
body([("Es decir, por cada metro que el nivel freático se eleva sobre el mar, el agua dulce penetra unos 40 metros bajo el nivel del mar antes de encontrarse la interfaz con el agua salada (Custodio y Llamas, 1996; Todd y Mays, 2005). Esta relación explica la geometría de la «lente» de agua dulce representada en la Figura 1: máxima potencia en el interior de la planicie, adelgazamiento progresivo hacia la línea de costa y cuña salina que se insinúa por debajo de ella.", False, False)])

doc.add_picture(IMG_DIR + "fig1_ghyben_herzberg.png", width=Cm(16.0))
doc.paragraphs[-1].alignment = 1
caption("Figura 1", "Modelo conceptual del equilibrio hidrostático en el acuífero costero de Higuerote: lente de agua dulce, cuña salina, zona de mezcla, recarga y cono de depresión por bombeo.", "Elaboración propia.")

h2("3.2  La zona de mezcla, la descarga al mar y el efecto de las mareas")
body([("La interfaz real no es una superficie abrupta sino una ", False, False), ("zona de mezcla o interfaz difusa", True, False), (" de varios metros de espesor, donde el agua dulce y la salada se mezclan por dispersión mecánica y difusión molecular. Dentro de esta franja la conductividad y los cloruros aumentan gradualmente, por lo que un pozo que extraiga de la zona de transición entrega agua salobre aun cuando el cuerpo del acuífero siga siendo dulce. Esta es la razón práctica por la que la sola medición del nivel piezométrico no basta para evaluar la salinización: se requieren además indicadores hidroquímicos (CE, cloruros, sólidos totales disueltos, relación iones mayoritarios).", False, False)])
bullets([
    [("Descarga subterránea al mar (SGD). ", True), ("En condiciones naturales, el flujo neto se dirige del continente hacia el mar; ese gradiente hacia afuera es la barrera física que impide el avance de la cuña salina. Todo lo que reduzca ese gradiente (bombeo, sequía, menor recarga) la debilita.", False)],
    [("Efecto de marea y oleaje. ", True), ("La oscilación de la superficie del mar impone una dinámica de «respiración» de la interfaz (hasta décimas de metro) con cada pleamar; los acuíferos de franja insular son los más expuestos a este bombeo natural de agua salobre hacia los pozos playeros.", False)],
    [("Recarga estacional. ", True), ("La precipitación concentrada en los meses lluviosos (mayo–noviembre) recarga el acuífero y desplaza temporalmente la cuña mar adentro; en la estación seca (diciembre–abril) el nivel freático desciende y la cuña avanza tierra adentro, efecto que se suma al bombeo turístico de diciembre y Semana Santa.", False)],
])

h2("3.3  Evidencias hidroquímicas en la parroquia Higuerote")
body([("El avance reportado de Silva et al. (2014) documenta precisamente la vulnerabilidad de este sistema: conductividad entre 370 y 1.885 µS/cm, pH entre 6,4 y 6,9, alcalinidad entre 98 y 308 mg CaCO₃/L y una muestra (OCP11, sector agrícola–cría) con incremento anómalo en noviembre (3.000 mg/L frente a 400 mg/L). Los autores concluyen que existe ", False, False), ("variación temporal de las variables hidroquímicas", True, False), (" y advierten que la explotación del recurso sin control comprometería su calidad —la misma conclusión que alcanzan los estudios de acuíferos costeros de La Guaira (Osma y Oritapo) mediante tomografía eléctrica (Marín et al., 2020, citado en ANIH, 2025)—. En síntesis: el acuífero de Higuerote cumple el modelo de lente costera de Ghyben–Herzberg, está en equilibrio frágil y ya muestra señales medibles de estrés.", False, False)])

# =====================================================================
# 4. IMPACTO HUMANO
# =====================================================================
h1("4.  Impacto humano: la demanda turística estacional acelera la intrusión salina")

h2("4.1  El turismo como forzante del bombeo estacional")
body([("Higuerote y Carenero conforman uno de los corredores de sol y playa más concurridos de la costa central de Miranda: balnearios, posadas, restaurantes, clubes y segundas residencias concentran en carnaval, Semana Santa, vacaciones escolares (agosto y diciembre) y fines de semana largos una población flotante que puede multiplicar varias veces la población residente del municipio. Esa población flotante no dispone de redes públicas de agua suficientes, por lo que la oferta se resuelve, en gran medida, con captaciones subterráneas privadas: aljibes excavados someros (la mayoría de los 12 sitios inventariados por Silva et al. son aljibes), pozos perforados y camiones cisterna que también extraen del acuífero.", False, False)])
body([("El resultado es un patrón de bombeo fuertemente estacional e incontrolado: en temporada alta se extrae durante semanas un caudal muy superior a la recarga natural que el acuífero recibe incluso en el mes más lluvioso, y en temporada baja los niveles se recuperan solo parcialmente. Este desfase —bombeo máximo precisamente cuando la recarga es mínima o nula— es la condición óptima para la intrusión salina: el sistema nunca alcanza a reponer el volumen extraído antes del siguiente pico turístico.", False, False)])

h2("4.2  Mecanismo físico: del abatimiento a la cuña salina")
body([("El encadenamiento causa–efecto puede describirse en cinco pasos, directamente aplicables al caso de Higuerote:", False, False)])
bullets([
    [("1) Abatimiento. ", True), ("El bombeo continuo desciende el nivel dinámico respecto al nivel estático (abatimiento). En el inventario de la parroquia Higuerote ya se observa un nivel dinámico de 17,9 m en OCP1 frente a niveles estáticos de 0,3–5,3 m en los demás sitios (Silva et al., 2014).", False)],
    [("2) Cono de depresión. ", True), ("La depresión forma un cono alrededor del pozo; cuando varios conos se superponen (explotación concentrada en la franja playera), desciende el nivel general del acuífero y con él la carga hidráulica que empuja el agua dulce hacia el mar.", False)],
    [("3) Ruptura del equilibrio de Ghyben–Herzberg. ", True), ("Con h reducida, la ecuación z ≈ 40·h implica que la interfaz asciende hacia la superficie: por cada metro de abatimiento, la cuña salina sube ~40 m y avanza horizontalmente tierra adentro una distancia que depende de la pendiente piezométrica.", False)],
    [("4) Avance de la cuña y mezcla en los pozos. ", True), ("La cuña salina y la zona de mezcla difusa alcanzan la rejilla de los filtros de los pozos; el agua extraída se salobren progresivamente (conductividad en aumento, cloruros > 250 mg/L) antes de volverse inutilizable.", False)],
    [("5) Salinización prácticamente irreversible en escalas humanas. ", True), ("A diferencia de un contaminante orgánico, la sal no se degrada: una vez salinan los poros del acuífero, recuperar la calidad original exige cesar el bombeo durante años o décadas y, en la práctica, suele ser inviable.", False)],
])

h2("4.3  Consecuencias sanitarias, económicas y ambientales")
caption("Tabla 2", "Síntomas e indicadores tempranos de intrusión salina aplicables a los pozos de la franja costera de Brión.", "Elaboración propia con base en Silva et al. (2014), Nieves (s. f.) y OMS (2017).")
make_table(
    ["Indicador", "Comportamiento esperado", "Umbral / referencia", "Fuente útil"],
    [
        ["Conductividad eléctrica (CE)", "Tendencia ascendente estacional (época seca y temporada turística)", "> 1.000–1.500 µS/cm en alerta; potable suele ser < 1.000 µS/cm", "Silva et al. (2014): ya se registran 1.075–1.885 µS/cm en 4 sitios"],
        ["Cloruros (Cl⁻)", "Incremento abrupto en sitios bajo estrés", "≈ 250 mg/L (valor guía OMS para sabor/palatabilidad)", "Decreto 883 (1995); OMS (2017)"],
        ["Sólidos totales disueltos (TDS)", "Aumento proporcional a la salinización", "> 1.000 mg/L: agua de regular a mala calidad para bebida", "Silva et al. (2014): OCP11 pasó de 400 a 3.000 mg/L (nov.)"],
        ["Nivel estático / dinámico", "Descenso sostenido interanual", "Abatimiento > 30–40 % de la columna saturada = alarma", "Criterios de bombeo (Nieves, s. f.)"],
        ["Relación ión Cl/Na o % Na", "Desviación hacia signatura marina", "Diagnóstico hidrogeoquímico (diagramas de Piper)", "Custodio y Llamas (1996)"],
    ],
    [3.6, 4.4, 4.0, 4.2],
    size=8
)
spacer(4)
bullets([
    [("Sanitarias: ", True), ("el sodio y los cloruros elevados son de riesgo para personas hipertensas y con enfermedad renal; la mezcla salobre además favorece corrosión y arrastre de metales en tuberías antiguas.", False)],
    [("Económicas: ", True), ("los hoteles y posadas deben comprar agua embotellada o cisternas (costo recurrente); los agricultores pierden cosechas por riego con agua salina; el valor inmobiliario de la franja costera se deprecia.", False)],
    [("Ambientales: ", True), ("la intrusión reduce el flujo base de manantiales y caños (SVM1/Qda. Valle Seco) y puede afectar los manglares y la biota costera que dependen del balance de agua dulce.", False)],
    [("Sociales: ", True), ("los conflictos entre usuarios (hoteles vs. vecinos vs. agricultura) se intensifican en temporada alta si no existe un régimen de extracción acordado y fiscalizado.", False)],
])

# =====================================================================
# 5. MITIGACIÓN
# =====================================================================
h1("5.  Mitigación: gestión y control del bombeo para frenar la cuña salina")

h2("5.1  Medidas de control del bombeo y gestión de la demanda")
body([("La literatura y la experiencia venezolana (Alvarado, citado en Pérez Zambrano y Gutiérrez Márquez, 2006; ANIH, 2025) coinciden en que la única defensa eficaz es reducir y ordenar la extracción por debajo de la recarga natural a largo plazo, complementada con ingeniería de recarga. Las medidas se organizan en tres niveles:", False, False)])

caption("Tabla 3", "Medidas recomendadas de gestión y control de bombeo para la franja costera de Higuerote.", "Elaboración propia.")
make_table(
    ["Nivel", "Medida", "Descripción operativa"],
    [
        ["Preventiva — ordenación", "Censo y legalización de pozos y aljibes", "Registro georreferenciado obligatorio en la Oficina Municipal de Ambiente; concesión de aguas subterráneas según Ley de Aguas (2007); moratoria de nuevos pozos en la franja de 0–500 m de la línea de costa."],
        ["Preventiva — ordenación", "Distancia mínima y diseño constructivo", "Pozos nuevos solo tierra adentro de la isobaña de protección; revestimiento ciego ranurado frente al acuífero, empaque de grava seleccionada, filtros protegidos y sellos sanitarios de arcilla/cemento para evitar colapso y contaminación."],
        ["Gestión de la demanda", "Caudales máximos estacionales", "Licencia de extracción con tope por temporada alta; contadores volumétricos; corte rotativo en horas pico; recarga obligatoria en temporada baja (mantenimiento y descanso del acuífero)."],
        ["Gestión de la demanda", "Eficiencia hídrica turística", "Normas municipales: grifería ahorradora, reúso de aguas grises para riego de jardines, piscinas con circuito cerrado, auditorías hídricas a posadas y hoteles."],
        ["Ingeniería — recarga", "Recarga artificial del acuífero", "Balsas de infiltración y pozos de recarga con agua de lluvia captada en techos y calles, y excedentes de la cuenca de los ríos Curiepe y caños costeros, en época lluviosa."],
        ["Ingeniería — control", "Barrera hidráulica de inyección", "Línea de pozos de inyección de agua dulce a lo largo de la costa (o estratégica tierra adentro) para elevar la carga piezométrica y empujar la cuña hacia el mar."],
        ["Higiene y saneamiento", "Protección de fuentes frente a fosas sépticas", "Distancia mínima sanitaria pozo–fosa (> 30 m); alcantarillado o sistemas de saneamiento en los ejes turísticos; sustitución de letrinas por tanque séptico estándar."],
        ["Institucional", "Autoridad única del acuífero", "Comité técnico (alcaldía + MINEC + INAMEH + universidades) con capacidad sancionatoria y plan anual de extracción y monitoreo."],
    ],
    [3.1, 4.4, 8.6],
    size=8.5
)
spacer(4)

h2("5.2  Monitoreo hidroquímico y piezométrico")
body([("Sin medición no hay gestión. Se recomienda instaurar, como mínimo, un programa de monitoreo con la siguiente estructura:", False, False)])
bullets([
    [("Red de piezómetros ", True), ("a lo largo de un transepto costa–interior (por ejemplo, Oso Cotiza → Carenero → Valle Seco), con lectura mensual del nivel estático y trimestral del nivel dinámico en los pozos de producción.", False)],
    [("Muestreo hidroquímico estacional ", True), ("(lluvia, intermedia y seca) con determinación de CE, pH, TDS, cloruros, alcalinidad e iones mayoritarios, y comparación con los límites del Decreto 883 (1995) y los valores guía de la OMS (2017).", False)],
    [("Campañas geofísicas periódicas ", True), ("(sondeos eléctricos verticales y tomografía eléctrica, como las aplicadas en Osma y Oritapo, La Guaira) para mapear la posición del pie de la cuña salina cada 3–5 años.", False)],
    [("Registro histórico público ", True), ("de niveles y CE por pozo, accesible a la comunidad y a la alcaldía, replicando el esquema de inventario iniciado por Silva et al. (2014) y ampliándolo a los 10 pozos y 2 arroyos ya georreferenciados.", False)],
    [("Alerta temprana ", True), ("con umbrales escalonados (vigilancia → restricción de bombeo → veda temporal) vinculados a la evolución de la CE y del nivel estático antes del inicio de carnaval y Semana Santa.", False)],
])

h2("5.3  Protección de la recarga y del entorno")
bullets([
    [("Conservación de la cuenca de aporte: ", True), ("reforestación de las cabeceras del río Curiepe y de las quebradas de Valle Seco; control de quemas agrícolas y de la erosión en las zonas de terrazas aluviales.", False)],
    [("Ordenanza municipal de protección de cabeceras y de la franja costera ", True), ("que declare zona de no bombeo el primer kilómetro costero en períodos de estrés hídrico.", False)],
    [("Drenaje urbano y manejo de aguas pluviales ", True), ("para maximizar la infiltración en lugar de evacuar la lluvia al mar.", False)],
    [("Protección de manglares y lagunas costeras, ", True), ("ecosistemas indicadores y aliados del equilibrio agua dulce–salada.", False)],
])

h2("5.4  Marco jurídico e institucional aplicable")
caption("Tabla 4", "Marco jurídico venezolano aplicable a la protección de los acuíferos costeros.", "Elaboración propia.")
make_table(
    ["Instrumento", "Disposición relevante para el caso"],
    [
        ["Constitución de la República Bolivariana de Venezuela (1999), arts. 127 y 304", "Derecho y deber de cada generación de proteger el ambiente (art. 127); todas las aguas son bienes de dominio público de la Nación, insustituibles para la vida y el desarrollo (art. 304)."],
        ["Ley de Aguas (2007), Gaceta Oficial N.º 38.595", "Régimen de usos, concesiones y planes de gestión integral de cuencas; obligatoriedad del permiso para extracción de aguas subterráneas y de protección de zonas de recarga."],
        ["Decreto 883 — Normas para la Clasificación y el Control de la Calidad de los Cuerpos de Agua y Vertidos o Efluentes Líquidos (1995), Gaceta Oficial N.º 5.021", "Criterios de calidad y valores máximos permisibles para cuerpos de agua y efluentes; referencia para juzgar la potabilidad y el vertido en los sectores Oso Cotiza y Santa Ana–Valle Seco."],
        ["Ley Orgánica del Ambiente (2006)", "Principios de gestión ambiental, participación ciudadana y responsabilidad por daño ambiental (aplicable a vertidos de fosas sépticas y a sobreexplotación)."],
        ["Plan Nacional de Gestión Integral de las Aguas (2007), MinAmb", "Acción pendiente explícita: proyectos de recuperación de cuencas degradadas y gestión del agua en zonas de especial interés ambiental (citado por Silva et al., 2014)."],
        ["Normas técnicas del MPP de Ecosocialismo / MINEC e INAMEH", "Inventario nacional de pozos, red hidrometeorológica y asesoría técnica para permisos y monitoreo."],
    ],
    [6.4, 10.0],
    size=8.5
)
spacer(4)

h2("5.5  Participación comunitaria")
body([("La experiencia del proyecto interinstitucional en Higuerote demuestra que las comunidades organizadas de Oso Cotiza y Santa Ana–Valle Seco son aliadas naturales de la conservación: participaron en talleres, mesas de trabajo y programas de concienciación, y la Fundación Ecológica Brión (ECOBRIÓN) acompaña el proceso (Silva et al., 2014). Se propone: comité comunitario de agua con veedores por sector; campañas de educación en escuelas y posadas; jornadas semestrales de limpieza y medición comunitaria de CE con equipos portátiles; y ordenanzas municipales construidas con consulta pública. La gestión del acuífero no puede ser solo decretada desde Caracas: debe ser apropiada por quienes abren el grifo cada mañana en Higuerote.", False, False)])

# =====================================================================
# 6. CONCLUSIONES
# =====================================================================
h1("6.  Conclusiones")
body([("De la investigación realizada para el Caso 3 (Municipio Brión — Zona Costera e Insular de Higuerote) se derivan las siguientes conclusiones:", False, False)])
bullets([
    [("Primera. ", True), ("El acuífero costero de Higuerote es un acuífero libre aluvial de planicie, recargado por la precipitación de la cuenca del río Curiepe y de los caños costeros, y descargado naturalmente hacia el mar. Su equilibrio puede describirse con la relación de Ghyben–Herzberg (z ≈ 40·h): basta una reducción sostenida de 1 m en el nivel freático para que la interfaz ascienda ~40 m y la cuña salina avance tierra adentro. El equilibrio es, por tanto, real pero frágil, y su mantenimiento es una condición de ordenamiento territorial, no solo un parámetro técnico.", False)],
    [("Segunda. ", True), ("La demanda turística estacional reproduce el escenario clásico de intrusión salina: extracción máxima cuando la recarga es mínima (diciembre–abril), superposición de conos de depresión en la franja playera y salinización progresiva de los pozos. Los datos disponibles (CE entre 370 y 1.885 µS/cm; OCP11 con incremento anómalo en noviembre) confirman que el sistema ya opera bajo estrés, aunque aún no haya colapsado.", False)],
    [("Tercera. ", True), ("La intrusión salina es, en esencia, un fallo de gobernanza hídrica: existe normativa suficiente (Constitución arts. 127 y 304, Ley de Aguas de 2007, Decreto 883 de 1995, Ley Orgánica del Ambiente), existen diagnósticos técnicos desde Alvarado (1982) hasta Silva et al. (2014), y existe comunidad organizada receptiva; lo que falta es hacer cumplir los límites, disponer de monitoreo continuo y sancionar la extracción ilegal. La protección legal del acuífero sigue siendo más declarativa que efectiva.", False)],
    [("Cuarta. ", True), ("La estrategia de mitigación viable combina tres familias de medidas: (i) control administrativo y físico del bombeo (censo, concesiones, caudales topes por temporada, distancia a la costa, barrera hidráulica e infiltración artificial); (ii) monitoreo sistemático con alerta temprana (CE, cloruros, niveles estático y dinámico, geofísica periódica); y (iii) protección del entorno y participación comunitaria (conservación de la cuenca de recarga, comités de agua, educación hídrica turística). Ninguna medida aislada es suficiente; su secuencia y financiamiento deben quedar en un plan municipal hídrico de mediano plazo.", False)],
    [("Quinta. ", True), ("La sostenibilidad del abastecimiento de Higuerote exige tratar al acuífero como un bien de dominio público insustituible —no como un insumo privado disponible—, internalizar el costo hídrico en la tarifa turística, y actualizar el inventario hidroquímico antes de la temporada 2026–2027. Solo así el agua subterránea seguirá cumpliendo su papel estratégico frente a la variabilidad climática que la región ya experimenta.", False)],
    [("Reflexión final. ", True), ("Gestionar un acuífero costero es administrar una promesa con el futuro: el agua dulce que hoy se extrae de más pagará su factura mañana en forma de pozo salobre, cosecha perdida y conflicto social. La protección legal de los acuíferos no es un formalismo ecológico, sino la única garantía de que Barlovento seguirá disponiendo de su reserva natural de agua dulce cuando el mar y la sequía, inevitablemente, vuelvan a ponerlo a prueba.", False)],
])
body([("Recomendaciones finales del equipo investigador:", True, False)], space_after=2)
bullets([
    "Declarar el acuífero de la parroquia Higuerote zona de gestión hídrica especial mediante ordenanza municipal, con moratoria de pozos costeros.",
    "Ejecutar al menos una campaña hidroquímica completa (época seca 2026) validada por INAMEH y UCV/ULA antes de la temporada alta de diciembre.",
    "Instalar dos piezómetros de monitoreo continuo (telemetría) en Oso Cotiza y Carenero con reporte público en la alcaldía.",
    "Incorporar el tema «intrusión salina» en el pensum de la U.C. Obras Hidráulicas con práctica de campo en Higuerote.",
])

# =====================================================================
# REFERENCIAS (APA 7)
# =====================================================================
h1("Referencias")
refs = [
    "Academia Nacional de la Ingeniería y el Hábitat. (2025). Primer Simposio Venezolano sobre Calidad del Agua: El cambio climático y la calidad del agua [Memorias, Boletín ANIH, N.º 67, abril–junio 2025]. https://acading.org.ve/wp-content/uploads/2025/07/Memorias-del-Primer-Simposio-Venezolano-sobre-Calidad-del-Agua.pdf",
    "Custodio, E., y Llamas, M. R. (1996). Hidrología subterránea (2.ª ed., 2 tomos). Ediciones Omega.",
    "Nieves, M. (s. f.). Tema 4: Obras hidráulicas relacionadas con fuentes subterráneas [Diapositivas de clase, Unidad Curricular Obras Hidráulicas, PNFCC, Trayecto IV, Sección 01]. Universidad Politécnica Territorial de Barlovento «Argelia Laya».",
    "Pérez Zambrano, F. M., y Gutiérrez Márquez, L. A. (2006). Evaluación de las aguas subterráneas en la región de Barlovento, Estado Miranda [Trabajo final de grado, Universidad de Los Andes, Facultad de Ingeniería]. SERBIULA. http://bdigital.ula.ve/storage/pdftesis/pregrado/tde_arquivos/10/TDE-2012-11-03T22:26:40Z-1865/Publico/perezflor_parte1.pdf",
    "República Bolivariana de Venezuela. (1995). Normas para la clasificación y el control de la calidad de los cuerpos de agua y vertidos o efluentes líquidos (Decreto N.º 883). Gaceta Oficial N.º 5.021.",
    "República Bolivariana de Venezuela. (1999). Constitución de la República Bolivariana de Venezuela. Gaceta Oficial N.º 5.453 (Extraordinario), 24 de marzo de 2000.",
    "República Bolivariana de Venezuela. (2006). Ley Orgánica del Ambiente. Gaceta Oficial N.º 5.833 (Extraordinario).",
    "República Bolivariana de Venezuela. (2007). Ley de Aguas. Gaceta Oficial N.º 38.595, 2 de enero de 2007.",
    "Silva, S., Díaz, R., DeCarli, F., Jegat, H., Suárez, P., Prado, L., Barros, H., Sivira, D., y Ojeda, J. (2014, junio). Evaluación hidroquímica preliminar de un sistema acuífero de un sector costero del estado Miranda – avance. ODC, 172–178. https://revistaoc.oncti.gob.ve/index.php/ODC/article/download/394/457/808",
    "Todd, D. K., y Mays, L. W. (2005). Groundwater hydrology (3rd ed.). John Wiley & Sons.",
    "World Health Organization. (2017). Guidelines for drinking-water quality: Fourth edition incorporating the first addendum. WHO.",
]
for i, ref in enumerate(refs):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(1.15); p.paragraph_format.first_line_indent = Cm(-1.15)
    p.paragraph_format.space_after = Pt(7); p.paragraph_format.line_spacing = 1.15
    r = p.add_run(ref); r.font.size = Pt(10.5)

spacer(2)
p = doc.add_paragraph(); p.paragraph_format.space_before = Pt(6)
r = p.add_run("Nota sobre citación: "); r.bold = True; r.font.size = Pt(8.5); r.font.color.rgb = GREY
r = p.add_run("Las referencias siguen la 7.ª edición de las normas APA. Las fuentes institucionales (Gacetas Oficiales, boletines y tesis) se citan con el nombre de la entidad emisora como autor. Los antecedentes de Alvarado (1982) se citan en el texto como fuentes secundarias a través de Pérez Zambrano y Gutiérrez Márquez (2006), siguiendo la convención APA para obras no consultadas directamente. Los videos y enlaces complementarios del Tema 4 (aforo y pruebas de bombeo, radio de influencia) pueden consultarse en el material de clase de la Unidad Curricular."); r.font.size = Pt(8.5); r.font.color.rgb = GREY; r.italic = True

p = doc.add_paragraph(); p.alignment = 1; p.paragraph_format.space_before = Pt(18)
r = p.add_run("— Fin del informe —"); r.font.size = Pt(10); r.font.color.rgb = GOLD; r.bold = True

OUT = "/home/user/ingenieria/informes/tema4-caso3-brion/Informe_Tema4_Caso3_Brion_Higuerote_UPTBAL.docx"
doc.save(OUT)
print("Guardado:", OUT)
