# ==================================================================
#  extraer_catalogos.py — Ingesta de tablas de perfiles (PDF → JSON)
#  ------------------------------------------------------------------
#  Estrategia:
#   1. pymupdf: render + LÍNEAS VECTORIALES de la tabla → retícula
#      exacta (filas × columnas) por página.
#   2. RapidOCR (onnxruntime): texto de toda la página con coordenadas.
#   3. Cada texto se asigna a su celda por el punto medio.
#   4. Salida: raw/<serie>_p<n>.json  (celdas crudas con coordenadas).
#
#  Los encabezados trilingües se mapean a columnas semánticas en
#  convertir_catalogos.py (fase 2), con validación física por fila:
#     Wel,y ≈ 2·Iy/h ·  iy ≈ √(Iy/A) ·  G ≈ 0,785·A
# ==================================================================

import json
import os
import sys
from collections import defaultdict

import pymupdf

AC = "/home/user/ingenieria/ACERO"
SALIDA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
os.makedirs(SALIDA, exist_ok=True)

from rapidocr_onnxruntime import RapidOCR

OCR = RapidOCR()

# ------------------------------------------------------------------
# Retícula desde líneas vectoriales
# ------------------------------------------------------------------
def lineas_de_tabla(page):
    """Devuelve (ys, xs): coordenadas de líneas H y V largas de la tabla."""
    hs, vs = [], []
    for d in page.get_drawings():
        for item in d["items"]:
            if item[0] == "l":                     # línea
                p1, p2 = item[1], item[2]
                if abs(p1.y - p2.y) < 1.0 and abs(p1.x - p2.x) > 25:
                    hs.append((p1.y + p2.y) / 2)
                elif abs(p1.x - p2.x) < 1.0 and abs(p1.y - p2.y) > 8:
                    vs.append((p1.x + p2.x) / 2)
            elif item[0] == "re":                  # rectángulo (bordes de celda)
                r = item[1]
                if r.width > 25 and r.height < 2.5:
                    hs.append((r.y0 + r.y1) / 2)
                elif r.height > 8 and r.width < 2.5:
                    vs.append((r.x0 + r.x1) / 2)
    def cluster(vals, eps=2.5):
        vals = sorted(vals)
        out = []
        for v in vals:
            if out and v - out[-1][-1] <= eps:
                out[-1].append(v)
            else:
                out.append([v])
        return [sum(g) / len(g) for g in out]
    return cluster(hs), cluster(vs)


def celdas_de_page(page):
    """Construye la lista de celdas (x0, y0, x1, y1) de la retícula."""
    ys, xs = lineas_de_tabla(page)
    if len(ys) < 3 or len(xs) < 3:
        return []
    celdas = []
    for iy in range(len(ys) - 1):
        for ix in range(len(xs) - 1):
            celdas.append((xs[ix], ys[iy], xs[ix + 1], ys[iy + 1]))
    return celdas


def ocr_page(page, dpi=200):
    pix = page.get_pixmap(dpi=dpi)
    import numpy as np
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(
        pix.height, pix.width, pix.n)
    if pix.n == 4:
        img = img[:, :, :3]
    res, _ = OCR(img)
    zoom = dpi / 72.0
    out = []
    if not res:
        return out
    for box, txt, conf in res:
        xs = [p[0] for p in box]
        ysp = [p[1] for p in box]
        out.append({
            "txt": txt,
            "conf": float(conf),
            "cx": (min(xs) + max(xs)) / 2 / zoom,
            "cy": (min(ysp) + max(ysp)) / 2 / zoom,
        })
    return out


def extraer_pagina(pdf_path, npag):
    page = pymupdf.open(pdf_path)[npag]
    celdas = celdas_de_page(page)
    textos = ocr_page(page)
    grid = defaultdict(list)
    if celdas:
        for t in textos:
            for (x0, y0, x1, y1) in celdas:
                if x0 - 1 <= t["cx"] <= x1 + 1 and y0 - 1 <= t["cy"] <= y1 + 1:
                    grid[(round(y0, 1), round(x0, 1))].append(t)
                    break
            else:
                grid[("fuera", "fuera")].append(t)
    filas = defaultdict(dict)
    for (y0, x0), textos_c in grid.items():
        if y0 == "fuera":
            continue
        textos_c.sort(key=lambda t: t["cx"])
        filas[y0][x0] = " ".join(t["txt"] for t in textos_c).strip()
    return {"celdas": {str(k): v for k, v in sorted(filas.items())},
            "fuera": [t["txt"] for t in grid.get(("fuera", "fuera"), [])]}


if __name__ == "__main__":
    series = sys.argv[1:] or [
        "IPN", "IPE", "HE", "HD", "HP", "UPN", "UPE", "U",
        "L-lados-iguales", "L-lados-desiguales", "FL", "R",
        "SQ", "SQ-aristas-redondeadas", "HLZ-HL-1",
    ]
    for s in series:
        path = os.path.join(AC, f"{s}.pdf")
        if not os.path.exists(path):
            print(f"⚠ no existe {path}")
            continue
        doc = pymupdf.open(path)
        for i, _page in enumerate(doc):
            destino = os.path.join(SALIDA, f"{s}_p{i+1}.json")
            if os.path.exists(destino):      # idempotente
                continue
            data = extraer_pagina(path, i)
            with open(destino, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=1)
            nf = len(data["celdas"])
            print(f"  {s} p{i+1}: {nf} filas con celdas", flush=True)
        doc.close()
    print("RAW list →", SALIDA)
