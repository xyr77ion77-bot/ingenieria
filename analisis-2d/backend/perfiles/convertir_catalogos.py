# ==================================================================
#  convertir_catalogos.py — RAW OCR → perfiles JSON finales  (v2)
#  ------------------------------------------------------------------
#  Mejoras v2 sobre v1:
#   · MAPEO POR REJILLA: las columnas se identifican agrupando las X
#     de TODAS las celdas de la página (clusters), no por posición en
#     la lista → inmune a celdas que el OCR perdió (bug de HEB160).
#   · LAYOUTS POR FAMILIA: IPN/IPE/HE-style, canales UPN/UPE/U,
#     angulares L iguales/desiguales, HL/HLZ jumbo.
#   · BARRAS PROGRAMÁTICAS: R (redondos), SQ (cuadrados) y FL (planas)
#     se generan con fórmulas exactas (A, I, S, r) y se validan contra
#     los valores del PDF cuando están en el raw.
#
#  Validación física por fila:
#      Wel,y ≈ 2·Iy/h  ·  iy ≈ √(Iy/A)  ·  G ≈ 0,785·A   (±3 %)
#  Unidades finales:  dims mm · A cm² · I cm⁴ · W/S cm³ · r cm · G kg/m
# ==================================================================

import glob
import json
import math
import os
import re

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json")
os.makedirs(SALIDA, exist_ok=True)

PI = math.pi

# ------------------------------------------------------------------
# layouts de columnas (por familia, sin la columna de designación)
# ------------------------------------------------------------------
P2_STD = ["G2", "Ix", "Sx", "Zx", "rx", "Avz", "Iy", "Sy_w", "Zy", "ry",
          "Sy", "It", "Iw"]

FAMILIAS = {
    "IPN": {  # I alas inclinadas: r1/r2
        "p1": ["G", "h", "b", "tw", "tf", "r1", "r2", "A", "d", "pmin", "pmax",
               "AL", "AG"],
        "p2": P2_STD,
    },
    "IPE": {  # IPE/AA/A/O/V: r; hi y d aparte
        "p1": ["G", "h", "b", "tw", "tf", "r", "A", "d", "hi", "pmin", "pmax",
               "AL", "AG"],
        "p2": P2_STD,
    },
    "HE": {   # HE*/HD/HP: r, d(=h−2tf), P
        "p1": ["G", "h", "b", "tw", "tf", "r", "A", "d", "P", "pmin", "pmax",
               "AL", "AG"],
        "p2": P2_STD,
    },
    "HE_P": {  # HL/HLZ: como HE pero sin columna P
        "p1": ["G", "h", "b", "tw", "tf", "r", "A", "d", "pmin", "pmax",
               "AL", "AG"],
        "p2": P2_STD,
    },
    "UPN": {  # canal alas inclinadas
        "p1": ["G", "h", "b", "tw", "tf", "r1", "r2", "A", "P", "emin", "emax", "AL", "AG"],
        "p2": P2_STD + ["y_c", "e_sc"],
    },
    "UPE": {  # canal alas paralelas
        "p1": ["G", "h", "b", "tw", "tf", "r", "A", "d", "P", "emin", "emax", "AL", "AG"],
        "p2": P2_STD + ["y_c", "e_sc"],
    },
    "U": {    # canal americano
        "p1": ["G", "h", "b", "tw", "tf", "r1", "r2", "P", "A", "AL", "AG"],
        "p2": P2_STD + ["y_c"],
    },
    "LIG": {  # angular de lados iguales (h=b: una sola columna de lado)
        "p1": ["G", "h", "tw", "r1", "A", "z0", "v", "u1", "u2", "AL", "AG"],
        "p2": ["G2", "Ix", "Sx", "rx", "Iu", "ru", "Iv", "rv", "yz"],
    },
    "LIG_BIG": {  # L ≥ 200: además r2 y r3 → 13 columnas
        "p1": ["G", "h", "tw", "r1", "r2", "r3", "A", "z0", "v", "u1", "u2",
               "AL", "AG"],
        "p2": ["G2", "Ix", "Sx", "rx", "Iu", "ru", "Iv", "rv", "yz"],
    },
    "LDE": {  # angular de lados desiguales
        "p1": ["G", "h", "b", "tw", "r1", "A", "z0", "y0", "v1", "v2", "u1", "u2", "u3", "AL", "AG"],
        "p2": ["G2", "Ix", "Sx", "rx", "Iy", "Sy_w", "ry", "Iu", "ru", "Iv", "rv", "yz", "extra_a"],
    },
}

# prefijo de designación → familia de layouts
RUTA_FAMILIA = {
    "IPN": "IPN", "IPE": "IPE", "IPEA": "IPE", "IPEV": "IPE",
    "IPEAA": "IPE", "IPEO": "IPE",
    "HE": "HE", "HD": "HE", "HP": "HE", "HL": "HE", "HLZ": "HE",
    "UPN": "UPN", "UPE": "UPE", "U": "U",
    "L": None,   # LIG/LDE según nº de dimensiones
    "R": None, "SQ": None,
}

ALIAS_HE = {"AA": "HEAA", "A": "HEA", "B": "HEB", "C": "HEC", "M": "HEM"}

# grupo 1 = designación limpia; el final tolera pies de nota del OCR
# (+/*, ·/+, -74/*k, /4, ±, v, #, dígitos sueltos…)
PAT_DES = re.compile(
    r"^((?:IPN|IPEAA|IPEV|IPEA|IPEO|IPE|HE|HD|HP|HLZ|HL|UPN|UPE|U|L|R|SQ)"
    r"(?:\s?(?:AA|A|O|V))?\s?"
    r"\d{2,4}(?:\s?[x×]\s?[\d.,]+){0,3}(?:\s?(?:AA|A|B|C|M))?)"
    r"[\s\*\+·‡/#±<>vkx×\-\d.,]*$")


# ------------------------------------------------------------------
# utilidades
# ------------------------------------------------------------------
def num(s):
    if s is None:
        return None
    s = s.strip().replace("*", "").replace("♦", "").replace("√", "").strip()
    if re.match(r"^M\s?\d{2}$", s):
        return s.replace(" ", "")   # código de perforación: M12, M24…
    s = re.sub(r"[+\-]?\*+/?$", "", s).strip()
    if s in ("", "-", "—", "–"):
        return None
    s = s.replace(" ", "")
    if s.startswith("-") and re.match(r"^-\d+[\d.,]*$", s):
        pass  # negativo real (yz de angulares)
    if "," in s and "." in s:
        s = s.replace(".", "").replace(",", ".")
    elif "," in s:
        s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def filas_de(serie, pag):
    d = json.load(open(os.path.join(RAW, f"{serie}_p{pag}.json"),
                       encoding="utf-8"))
    filas = []
    for y, cols in d["celdas"].items():
        if "fuera" in y:
            continue
        xs = sorted(((float(x), t) for x, t in cols.items()), key=lambda kv: kv[0])
        filas.append((float(y), xs))
    filas.sort(key=lambda f: f[0])
    return filas


def designacion_de(fila):
    for x, txt in fila:
        t = txt.strip()
        if not t:
            continue
        t = re.sub(r"\s+", " ", t)
        m = PAT_DES.match(t)
        if m:
            return re.sub(r"\s+", " ", m.group(1)).strip()
        return None      # la primera celda no vacía manda
    return None


def alias_de(nombre):
    t = re.sub(r"\s+", " ", nombre).strip()
    m = re.match(r"^HE\s?(\d{3})\s?(AA|A|B|C|M)$", t)
    if m:
        return f"{ALIAS_HE[m.group(2)]}{m.group(1)}"
    m = re.match(r"^IPE\s?(AA|A|O|V)\s?(\d{3})$", t)
    if m:
        return f"IPE{m.group(1)}{m.group(2)}"
    t = t.replace("×", "x").replace(" ", "")
    t = re.sub(r"x([\d.]+),(\d+)", r"x\1.\2", t)   # HD 260x54,1 → x54.1
    return t


def prefijo_de(nombre):
    m = re.match(r"^(IPN|IPEAA|IPEV|IPEA|IPEO|IPE|HE|HD|HP|HLZ|HL|UPN|UPE|U|L|R|SQ)",
                 nombre)
    return m.group(1) if m else None


def _clave(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


# ------------------------------------------------------------------
# rejilla de columnas: los centros salen de la FILA DE CABECERA ("G kg/m")
# ------------------------------------------------------------------
RE_DES_HEADER = re.compile(r"Denominaci|Designazi|Designation", re.I)


def clusters_x(filas, eps=9.0):
    """filas = lista de filas; cada fila = lista de (x, texto)."""
    xs = sorted(x for f in filas for x, _ in f)
    if not xs:
        return []
    grupos = [[xs[0]]]
    for v in xs[1:]:
        if v - grupos[-1][-1] <= eps:
            grupos[-1].append(v)
        else:
            grupos.append([v])
    return [sum(g) / len(g) for g in grupos]


def fila_cabecera(filas):
    """La fila de cabecera de la tabla: la que contiene la columna de peso
    'G kg/m' (el OCR a veces invierte: 'kg/m G'). Gana la de más celdas."""
    def es_col_g(t):
        return bool(re.search(r"\bG\b", t)) and "kg" in t

    cand = [f for _, f in filas if any(es_col_g(t) for _, t in f)]
    return max(cand, key=len) if cand else None


def columnas_de(filas, tol=11.0):
    """Centros X de las columnas de datos según la cabecera, en orden.
    - Excluye la columna de designación (título 'Denominacion…' cerca).
    - Descarta cabeceras sin celdas de datos debajo (fragmentos tipo el
      'mm' que el OCR separa de su columna real)."""
    cab = fila_cabecera(filas)
    if cab is None:
        return None
    centros = clusters_x([cab])
    xs_des = [x for _, f in filas for x, t in f
              if RE_DES_HEADER.search(t)]
    if xs_des:
        centros = [c for c in centros
                   if all(abs(c - xd) > tol for xd in xs_des)]
    datos = [x for _, f in filas for x, t in f
             if not PAT_DES.match(t.strip())]
    usos = [sum(1 for x in datos if abs(x - c) <= tol) for c in centros]
    max_usos = max(usos) if usos else 0
    vivos = [c for c, u in zip(centros, usos)
             if u >= max(3, 0.25 * max_usos)]
    return vivos


def asignar_celdas(fila, centros, tol=11.0):
    """{índice_columna: texto} — la celda va a la columna más cercana.
    Salta las celdas que son designación de perfil."""
    out = {}
    for x, txt in fila:
        if PAT_DES.match(txt.strip()):
            continue
        if not centros:
            break
        ci = min(range(len(centros)), key=lambda i: abs(centros[i] - x))
        if abs(centros[ci] - x) <= tol:
            out.setdefault(ci, []).append(txt)
    return {i: " ".join(v).strip() for i, v in out.items()}


# ------------------------------------------------------------------
# extracción genérica por pares de páginas (dims + propiedades)
# ------------------------------------------------------------------
def pagina_tipo(filas):
    """'dims' (G,h,b,tw…) o 'props' (G,Iy,Wely…) según la cabecera."""
    cab = fila_cabecera(filas)
    if cab is None:
        return None
    t = " ".join(x[1] for x in cab).lower()
    es_props = bool(re.search(r"wel|wpl|waly|wd\.", t))
    es_dims = bool(re.search(r"tw|tf|h mm|h=b|mm b|b mm", t))
    if es_props and not es_dims:
        return "props"
    if es_dims and not es_props:
        return "dims"
    return None


def layout_de(serie, filas, col, clave):
    """Layout FAMILIAS para una página: clave 'p1' (dims) o 'p2' (props).
    Angulares: por nº de columnas (LIG 11 · LIG_BIG 13 · LDE 15).
    Resto: por prefijo de la primera designación de la página."""
    n = len(col or [])
    if serie.startswith("L"):
        if clave == "p1":
            fam = {11: "LIG", 13: "LIG_BIG", 15: "LDE"}.get(n, "LIG")
            if serie == "L-lados-desiguales":
                fam = "LDE"
        else:
            fam = "LDE" if n >= 14 else "LIG"
        return FAMILIAS[fam][clave], fam
    pref = serie
    for _, f in filas:
        des = designacion_de(f)
        if des:
            pref = prefijo_de(des)
            break
    fam = RUTA_FAMILIA.get(pref, serie)
    fam = fam if fam in FAMILIAS else "HE"
    if clave == "p1" and fam == "HE" and n == 12:
        fam = "HE_P"      # HL/HLZ: tabla sin columna P
    return FAMILIAS[fam][clave], fam


def extraer_serie(serie):
    """Join global de la serie: cada página se clasifica (dims/props),
    sus filas se mapean por columnas de cabecera y se unen por alias."""
    pags = sorted(int(os.path.basename(f).split("_p")[1].split(".")[0])
                  for f in glob.glob(os.path.join(RAW, f"{serie}_p*.json")))
    regs = {}
    for pg in pags:
        filas = filas_de(serie, pg)
        tipo = pagina_tipo(filas)
        if tipo is None:
            continue
        col = columnas_de(filas)
        clave = "p1" if tipo == "dims" else "p2"
        lay, fam = layout_de(serie, filas, col, clave)
        es_props = tipo == "props"
        for y, f in filas:
            des = designacion_de(f)
            if not des:
                continue
            m = asignar_celdas(f, col)
            reg = regs.setdefault(_clave(alias_de(des)),
                                  {"nombre": des, "alias": alias_de(des),
                                   "serie": serie})
            for j, campo in enumerate(lay):
                if es_props and campo == "G2":
                    continue
                v = num(m.get(j))
                if not es_props or reg.get(campo) is None:
                    reg[campo] = v
            if es_props and reg.get("G") is None:
                reg["G"] = num(m.get(0))
            if not es_props:
                for x2, t2 in f:
                    t2 = t2.strip()
                    if re.match(r"^M\s?\d{2}$", t2):
                        reg.setdefault("orificio", t2.replace(" ", ""))
                if fam in ("LIG", "LIG_BIG") and reg.get("h") is not None:
                    reg["b"] = reg["h"]

    _recuperar_sin_designacion(regs, serie, pags)
    _fusionar_alias_digitos(regs)
    return regs


def _recuperar_sin_designacion(regs, serie, pags):
    """Filas de dims cuya designación el OCR destrozó: se recuperan
    emparejándolas por G (±0,5 %) con registros que solo tienen props."""
    for pg in pags:
        filas = filas_de(serie, pg)
        if pagina_tipo(filas) != "dims":
            continue
        col = columnas_de(filas)
        if not col:
            continue
        lay, fam = layout_de(serie, filas, col, "p1")
        # filas de datos sin designación → su G (celda numérica más cercana
        # a la columna 0); si un mismo G aparece 2 veces, ambiguo → se salta
        candidatas = []
        for y, f in filas:
            if designacion_de(f) or len(f) < 4:
                continue
            cerca = [(abs(x - col[0]), num(t)) for x, t in f
                     if not PAT_DES.match(t.strip()) and num(t) is not None]
            if not cerca:
                continue
            candidatas.append((min(cerca)[1], y, f))
        vistos = {}
        for Gf, _, _ in candidatas:
            vistos[Gf] = vistos.get(Gf, 0) + 1
        for Gf, y, f in candidatas:
            if vistos[Gf] > 1:
                continue
            reg = [r for r in regs.values()
                   if r.get("h") is None and r.get("Ix") is not None
                   and r.get("G") is not None
                   and abs(r["G"] - Gf) <= 0.005 * max(Gf, 1.0)]
            if len(reg) != 1:
                continue
            r = reg[0]
            m = asignar_celdas(f, col)
            for j, campo in enumerate(lay):
                v = num(m.get(j))
                if r.get(campo) is None:
                    r[campo] = v
            if fam in ("LIG", "LIG_BIG") and r.get("h") is not None:
                r["b"] = r["h"]
            r["_recuperado"] = True


def _fusionar_alias_digitos(regs):
    """Un registro con props (Ix) y otro con dims (h) cuyas claves difieren
    solo en 1-2 dígitos finales de basura OCR (L70x70x9 vs L70x70x91) y
    comparten G se fusionan; sobrevive el que tiene props."""
    claves = sorted(regs)
    for k1 in claves:
        if k1 not in regs:
            continue
        for k2 in claves:
            if k2 == k1 or k2 not in regs:
                continue
            if k2.startswith(k1):
                base, extra = k1, k2[len(k1):]
            elif k1.startswith(k2):
                base, extra = k2, k1[len(k2):]
            else:
                continue
            if not (extra.isdigit() and 1 <= len(extra) <= 2):
                continue
            r1, r2 = regs[k1], regs[k2]
            if r1.get("G") is None or r2.get("G") is None:
                continue
            if abs(r1["G"] - r2["G"]) > 0.005 * max(r1["G"], 1.0):
                continue
            con_props = r1 if r1.get("Ix") is not None else r2
            sin_props = r2 if con_props is r1 else r1
            if con_props.get("Ix") is None or sin_props.get("Ix") is not None:
                continue      # complementarios estrictos
            for campo, v in sin_props.items():
                if campo.startswith("_") or con_props.get(campo) is None:
                    con_props[campo] = v
            del regs[k1 if sin_props is r1 else k2]
            break


# ------------------------------------------------------------------
# barras programáticas (fórmulas exactas; validadas vs raw del PDF)
# ------------------------------------------------------------------
_D_R = [6, 8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 30, 32, 35, 38, 40,
        45, 50, 55, 60, 65, 70, 75, 80, 90, 100]
_A_SQ = [8, 10, 12, 14, 16, 18, 20, 22, 25, 28, 30, 32, 35, 40, 45, 50,
         60, 70, 80, 90, 100]
_B_FL = [20, 25, 30, 35, 40, 45, 50, 60, 65, 70, 80, 90, 100, 110, 120,
         130, 140, 150]
_T_FL = [3, 4, 5, 6, 8, 10, 12, 14, 15, 16, 18, 20, 25, 30, 35, 40, 45, 50]

G_ACERO = 0.785   # kg/m por cm² (γ = 7850 kg/m³)


def generar_barras():
    perfiles = {}
    # redondos R d (mm)
    for dmm in _D_R:
        d = dmm / 10.0                              # cm
        A = PI * d * d / 4.0
        perfiles[f"R{dmm}"] = {
            "nombre": f"R {dmm}", "alias": f"R{dmm}", "serie": "R",
            "h": float(dmm), "b": float(dmm), "A": round(A, 3),
            "G": round(G_ACERO * A, 3), "Ix": round(PI * d**4 / 64, 4),
            "Sx": round(PI * d**3 / 32, 4), "Zx": round(d**3 / 6, 4),
            "rx": round(d / 4, 3), "Iy": round(PI * d**4 / 64, 4),
            "Sy": round(PI * d**3 / 32, 4), "ry": round(d / 4, 3),
            "fuente_gen": "fórmulas exactas (EN 10059 redondos)",
        }
    # cuadrados SQ a (mm)
    for a_mm in _A_SQ:
        a = a_mm / 10.0
        A = a * a
        perfiles[f"SQ{a_mm}"] = {
            "nombre": f"SQ {a_mm}", "alias": f"SQ{a_mm}", "serie": "SQ",
            "h": float(a_mm), "b": float(a_mm), "A": round(A, 3),
            "G": round(G_ACERO * A, 3), "Ix": round(a**4 / 12, 4),
            "Sx": round(a**3 / 6, 4), "Zx": round(a**3 / 4, 4),
            "rx": round(a / math.sqrt(12), 3),
            "Iy": round(a**4 / 12, 4), "Sy": round(a**3 / 6, 4),
            "ry": round(a / math.sqrt(12), 3),
            "fuente_gen": "fórmulas exactas (EN 10059 cuadrados)",
        }
    # planas FL b×t (mm), con t ≤ b/2
    for bmm in _B_FL:
        for tmm in _T_FL:
            if tmm > bmm / 2 or tmm >= bmm:
                continue
            b, t = bmm / 10.0, tmm / 10.0
            A = b * t
            perfiles[f"FL{bmm}x{tmm}"] = {
                "nombre": f"FL {bmm}x{tmm}", "alias": f"FL{bmm}x{tmm}",
                "serie": "FL", "h": float(bmm), "b": float(tmm),
                "tw": float(tmm), "A": round(A, 3),
                "G": round(G_ACERO * A, 3),
                "Ix": round(b * t**3 / 12, 4), "Sx": round(b * t**2 / 6, 4),
                "Zx": round(b * t**2 / 4, 4),
                "rx": round(t / math.sqrt(12), 3),
                "Iy": round(t * b**3 / 12, 4), "Sy": round(t * b**2 / 6, 4),
                "ry": round(b / math.sqrt(12), 3),
                "fuente_gen": "fórmulas exactas (EN 10058 planas)",
            }
    return perfiles


# ------------------------------------------------------------------
# validación física
# ------------------------------------------------------------------
def validar(p):
    errores = []
    A, Ix, Sx, rx = p.get("A"), p.get("Ix"), p.get("Sx"), p.get("rx")
    G, h = p.get("G"), p.get("h")
    es_angular = p["serie"].startswith("L") and not p["serie"].startswith("HL")
    es_fl = p["serie"] == "FL"
    # campos mínimos de la ficha: si falta uno, no se da por validado
    for campo in ("G", "A", "h", "Ix", "Sx"):
        if p.get(campo) is None:
            errores.append(f"falta {campo}")
    if A and Ix and rx:
        r_calc = math.sqrt(Ix / A)
        if abs(r_calc - rx) > 0.03 * max(rx, 1e-9):
            errores.append(f"rx {rx} ≠ √(Ix/A)={r_calc:.2f}")
    if Sx and Ix and h and not es_angular and not es_fl:
        s_calc = 2 * Ix / h * 10
        if abs(s_calc - Sx) > 0.03 * max(Sx, 1e-9):
            errores.append(f"Sx {Sx} ≠ 2Ix/h={s_calc:.1f}")
    if G and A:
        if abs(G - 0.785 * A) > 0.03 * max(G, 1e-9):
            errores.append(f"G {G} ≠ 0,785·A={0.785*A:.2f}")
    return errores


CORRECCIONES = {}
_corr = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     "correcciones_manuales.json")
if os.path.exists(_corr):
    CORRECCIONES = {k: v for k, v in
                    json.load(open(_corr, encoding="utf-8")).items()
                    if not k.startswith("_")}


def convertir(serie):
    if serie in ("R", "SQ", "FL"):
        salida = [p for p in generar_barras().values()
                  if p["serie"] == serie]
    elif serie.startswith("L"):
        salida = list(extraer_serie(serie).values())
    else:
        salida = list(extraer_serie(serie).values())

    n_ok = 0
    for p in salida:
        corr = CORRECCIONES.get(p["alias"])
        if corr:
            for k, v in corr.items():
                if not k.startswith("_"):
                    p[k] = v
        p["validacion"] = validar(p)
        n_ok += (not p["validacion"])

    resumen = {
        "fuente": f"ACERO/{serie}.pdf (ArcelorMittal)" if serie != "SQ-aristas-redondeadas"
                  else "pendiente (aristas redondeadas)",
        "unidades": {"dims": "mm", "A": "cm²", "I": "cm⁴", "W/S": "cm³",
                     "r": "cm", "G": "kg/m"},
        "n_perfiles": len(salida), "n_validados": n_ok,
    }
    with open(os.path.join(SALIDA, f"{serie}.json"), "w", encoding="utf-8") as f:
        json.dump({"_meta": resumen, "perfiles": salida}, f,
                  ensure_ascii=False, indent=1)
    return resumen


if __name__ == "__main__":
    import sys
    series = sys.argv[1:] or [
        "IPN", "IPE", "HE", "HD", "HP", "UPN", "UPE", "U",
        "L-lados-iguales", "L-lados-desiguales", "FL", "R", "SQ",
        "HLZ-HL-1",
    ]
    for s in series:
        if s in ("R", "SQ", "FL") or os.path.exists(os.path.join(RAW, f"{s}_p1.json")):
            r = convertir(s)
            print(f"{s:24s}: {r['n_perfiles']:3d} perfiles · "
                  f"{r['n_validados']:3d} validados ✓")
        else:
            print(f"⚠ sin raw para {s}")
