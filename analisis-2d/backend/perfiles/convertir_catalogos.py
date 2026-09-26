# ==================================================================
#  convertir_catalogos.py — RAW OCR → perfiles JSON finales
#  ------------------------------------------------------------------
#  Fase 2 de la ingesta: mapea las celdas crudas (extraer_catalogos.py)
#  a un esquema único y VALIDA físicamente cada fila:
#      Wel,y ≈ 2·Iy/h  (±3 %)   ·  iy ≈ √(Iy/A)  (±3 %)
#      G ≈ 0,785·A     (±3 %)
#  Unidades finales:  dims mm · A cm² · I cm⁴ · W/S cm³ · r cm · G kg/m
#  (los encabezados Arcelor «x10⁴ mm⁴» ya imprimen el valor en cm)
#
#  Cubre la familia de perfiles I/H de ArcelorMittal (2 páginas por
#  grupo: dims / propiedades):
#    IPN  (2 págs) · IPE (p1-2, p3-4, p5-6 IPEA/IPEV)
#    HE   (p1-2..p7-8: variantes HEAA/HEA/HEB/HEC/HEM)
#    HD (4 págs) · HP (2 págs)
# ==================================================================

import glob
import json
import math
import os
import re

RAW = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "json")
os.makedirs(SALIDA, exist_ok=True)

# IPN lleva r1/r2 y un solo d; IPE lleva r y d+d2; HE/HD/HP llevan r y d
COLS_P1_POR_SERIE = {
    "IPN": ["G", "h", "b", "tw", "tf", "r1", "r2", "A", "d", "orificio", "pmin", "pmax"],
    "IPE": ["G", "h", "b", "tw", "tf", "r", "A", "d", "d2", "orificio", "pmin", "pmax"],
    "HE":  ["G", "h", "b", "tw", "tf", "r", "A", "d", "orificio", "pmin", "pmax"],
    "HD":  ["G", "h", "b", "tw", "tf", "r", "A", "d", "orificio", "pmin", "pmax"],
    "HP":  ["G", "h", "b", "tw", "tf", "r", "A", "d", "orificio", "pmin", "pmax"],
}
COLS_P2 = ["G2", "Ix", "Sx", "Zx", "rx", "Avz", "Iy", "Sy_w", "Zy", "ry",
           "Sy", "It", "Iw"]

ALIAS_HE = {"AA": "HEAA", "A": "HEA", "B": "HEB", "C": "HEC", "M": "HEM"}


# ------------------------------------------------------------------
# utilidades
# ------------------------------------------------------------------
def num(s):
    if s is None:
        return None
    s = s.strip().replace("*", "").replace("♦", "").strip()
    if s in ("", "-", "—", "–"):
        return None
    s = s.replace(" ", "")
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


PAT_DES = re.compile(
    r"^(IPN|IPEA?|IPEV|HE|HD|HP|UPN|UPE|HLZ?|HL)\s?\d{2,3}"
    r"(\s?(AA|A|B|C|M))?(\s?[x×]\s?[\d,]+)?$")


def designacion_de(fila):
    """Primera celda (x<130) SOLO si cumple el patrón de designación."""
    for x, txt in fila:
        if x < 130:
            t = txt.strip()
            if not t:
                continue
            t = re.sub(r"[\*\+·‡]+$", "", t).strip()
            t = re.sub(r"\s+", " ", t)
            if PAT_DES.match(t):
                return t
    return None


def alias_de(nombre):
    m = re.match(r"^HE\s?(\d{3})\s?(AA|A|B|C|M)$", nombre)
    if m:
        return f"{ALIAS_HE[m.group(2)]}{m.group(1)}"
    m = re.match(r"^(HD|HP)\s?(\d{3})\s?[x×]\s?([\d,]+)$", nombre)
    if m:
        return f"{m.group(1)}{m.group(2)}x{m.group(3).replace(',', '.')}"
    return re.sub(r"\s+", "", nombre)


def _clave(s):
    return re.sub(r"[^A-Z0-9]", "", s.upper())


def celda_mas_cercana(fila, x_obj, tol=14):
    mejor = None
    for x, txt in fila:
        if abs(x - x_obj) <= tol:
            if mejor is None or abs(x - x_obj) < abs(mejor[0] - x_obj):
                mejor = (x, txt)
    return mejor[1] if mejor else None


# ------------------------------------------------------------------
# extracción familia I/H
# ------------------------------------------------------------------
def extraer_familia_ih(serie, cols_p1):
    pags = sorted(int(os.path.basename(f).split("_p")[1].split(".")[0])
                  for f in glob.glob(os.path.join(RAW, f"{serie}_p*.json")))
    perfiles = {}

    def filas_datos(filas):
        out = []
        for y, f in filas:
            des = designacion_de(f)
            if des:
                out.append((y, f, des))
        return out

    for i in range(0, len(pags) - 1, 2):
        d1 = filas_datos(filas_de(serie, pags[i]))
        d2 = filas_datos(filas_de(serie, pags[i + 1]))
        idx2 = {_clave(alias_de(d)): (yy, ff) for yy, ff, d in d2}

        for (y1, f1, des) in d1:
            clave = _clave(alias_de(des))
            par = idx2.get(clave)
            f2 = par[1] if par else None

            x_des = min((x for x, _ in f1), default=108)
            x_min = x_des + 8

            def take(f, cols):
                vals = {}
                if not f:
                    return vals
                xs = [x for x, _ in f if x > x_min]
                for j, c in enumerate(cols):
                    if j < len(xs):
                        vals[c] = num(celda_mas_cercana(f, xs[j]))
                return vals

            v1 = take(f1, cols_p1)
            v2 = take(f2, COLS_P2)
            reg = {**v1, **v2, "nombre": des, "alias": alias_de(des),
                   "serie": serie}
            perfiles[alias_de(des)] = reg
    return list(perfiles.values())


# ------------------------------------------------------------------
# validación física
# ------------------------------------------------------------------
def validar(p):
    errores = []
    A, Ix, Sx, rx = p.get("A"), p.get("Ix"), p.get("Sx"), p.get("rx")
    G, h = p.get("G"), p.get("h")
    if A and Ix and rx:
        r_calc = math.sqrt(Ix / A)
        if abs(r_calc - rx) > 0.03 * rx:
            errores.append(f"rx {rx} ≠ √(Ix/A)={r_calc:.2f}")
    if Sx and Ix and h:
        s_calc = 2 * Ix / h * 10
        if abs(s_calc - Sx) > 0.03 * Sx:
            errores.append(f"Sx {Sx} ≠ 2Ix/h={s_calc:.1f}")
    if G and A:
        if abs(G - 0.785 * A) > 0.03 * G:
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
    base = re.match(r"^(IPN|IPE|HE|HD|HP)", serie).group(1)
    perfiles = extraer_familia_ih(serie, COLS_P1_POR_SERIE[base])
    salida = []
    n_ok = 0
    for p in perfiles:
        corr = CORRECCIONES.get(p["alias"])
        if corr:
            for k, v in corr.items():
                if not k.startswith("_"):
                    p[k] = v
        errs = validar(p)
        p["validacion"] = errs
        n_ok += (not errs)
        salida.append(p)
    resumen = {
        "fuente": f"ACERO/{serie}.pdf (ArcelorMittal)",
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
    for s in (sys.argv[1:] or ["IPN", "IPE", "HE", "HD", "HP"]):
        if not os.path.exists(os.path.join(RAW, f"{s}_p1.json")):
            print(f"⚠ sin raw para {s}")
            continue
        r = convertir(s)
        print(f"{s}: {r['n_perfiles']} perfiles · {r['n_validados']} validados ✓")
