# ==================================================================
#  tests_generador.py — Modelador → modelo 2D (engine/generador.py)
#  Retícula de referencia: lx=[5,5,5] (ejes 1-4) · ly=[5,4] (A-C)
#  · Niveles: N1 h=4 · N2 h=3,2 · pórtico X:1 (corre en Y, A-B-C)
# ==================================================================

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.generador import generar_portico
from engine.modelo import ERROR

FALLOS = []


def chequear(nombre, condicion, detalle=""):
    ok = bool(condicion)
    print(("✓" if ok else "✗"), nombre, detalle)
    if not ok:
        FALLOS.append(nombre)


def proyecto_base():
    return {
        "geometria": {
            "lx": [5, 5, 5],
            "ly": [5, 4],
            "niveles": [
                {"nombre": "N1", "h_piso": 4.0},
                {"nombre": "N2", "h_piso": 3.2, "es_techo": True},
            ],
        },
        "cortes": {
            "X:1": {
                "niveles_propios": 2,
                "columnas": {
                    "A": {"activa": True, "base": "empotrada"},
                    "B": {"activa": True, "base": "empotrada"},
                    "C": {"activa": True, "base": "empotrada"},
                },
                "uniones": {"patron": "pr_momento", "excepciones": {}},
            },
        },
    }


def barras_por_id(modelo):
    return {b["id"]: b for b in modelo["barras"]}


def nudos_por_id(modelo):
    return {n["id"]: n for n in modelo["nudos"]}


# ---------- T1 · pórtico completo rígido ----------
m, r = generar_portico(proyecto_base(), "X:1")
chequear("T1a 9 nudos (3 columnas × 3 cotas)", r["n_nudos"] == 9)
chequear("T1b 10 barras (6 columnas + 4 vigas)",
         r["n_barras"] == 10 and r["n_columnas"] == 6 and r["n_vigas"] == 4)
n = nudos_por_id(m)
chequear("T1c posiciones: A x=0 · B x=5 · C x=9; N0 y=0 · N1 y=4 · N2 y=7,2",
         n["A_N0"]["x"] == 0 and n["B_N0"]["x"] == 5 and n["C_N0"]["x"] == 9
         and n["A_N0"]["y"] == 0 and n["A_N1"]["y"] == 4
         and n["C_N2"]["y"] == 7.2)
bs = barras_por_id(m)
chequear("T1d columnas C_A_1: A_N0→A_N1",
         bs["C_A_1"]["ni"] == "A_N0" and bs["C_A_1"]["nj"] == "A_N1")
chequear("T1e viga V1_2: B_N1→C_N1 (luz 4 m)",
         bs["V1_2"]["ni"] == "B_N1" and bs["V1_2"]["nj"] == "C_N1")
chequear("T1f todo rígido: sin liberaciones",
         not any(b["rel_i"] or b["rel_j"] for b in m["barras"]))
chequear("T1g 3 apoyos empotrados (rz=True)",
         len(m["apoyos"]) == 3 and all(a["rz"] for a in m["apoyos"]))
chequear("T1h título «Pórtico X:1»", m["titulo"] == "Pórtico X:1")

# ---------- T2 · columna B desactivada (vano salteado) ----------
p = proyecto_base()
p["cortes"]["X:1"]["columnas"]["B"]["activa"] = False
m, r = generar_portico(p, "X:1")
chequear("T2a 6 nudos · 6 barras (4 columnas + 2 vigas)",
         r["n_nudos"] == 6 and r["n_barras"] == 6
         and r["n_columnas"] == 4 and r["n_vigas"] == 2)
bs = barras_por_id(m)
chequear("T2b viga salteada A→C con L=9 m",
         "V1_1" in bs and bs["V1_1"]["ni"] == "A_N1"
         and bs["V1_1"]["nj"] == "C_N1"
         and abs(nudos_por_id(m)["C_N1"]["x"] - 9) < 1e-9)
chequear("T2c resumen reporta el salto",
         len(r["saltados"]) == 2 and "A→C" in r["saltados"][0]
         and "9 m" in r["saltados"][0])
chequear("T2d sin barras de la columna B",
         not any("_B_" in bid for bid in bs))

# ---------- T3 · base articulada ----------
p = proyecto_base()
p["cortes"]["X:1"]["columnas"]["C"]["base"] = "articulada"
m, r = generar_portico(p, "X:1")
ap = {a["nudo"]: a for a in m["apoyos"]}
chequear("T3a base C articulada: rz=False · A y B rz=True",
         ap["C_N0"]["rz"] is False and ap["A_N0"]["rz"] is True
         and ap["B_N0"]["rz"] is True)
chequear("T3b resumen lo reporta", r["bases_articuladas"] == ["C"])

# ---------- T4 · patrón vigas articuladas + excepción ----------
p = proyecto_base()
p["cortes"]["X:1"]["uniones"] = {
    "patron": "vigas_articuladas",
    "excepciones": {"N1|C": "rígida"},
}
m, r = generar_portico(p, "X:1")
bs = barras_por_id(m)
chequear("T4a vigas articuladas por patrón (V2_1 ambos extremos)",
         bs["V2_1"]["rel_i"] and bs["V2_1"]["rel_j"])
chequear("T4b excepción N1|C: la viga que llega a C en N1 queda rígida al final",
         bs["V1_2"]["rel_j"] is False)
chequear("T4c columnas siempre continuas (sin rel)",
         not any(b["id"].startswith("C_") and (b["rel_i"] or b["rel_j"])
                 for b in m["barras"]))

# ---------- T5 · niveles propios = 1 ----------
p = proyecto_base()
p["cortes"]["X:1"]["niveles_propios"] = 1
m, r = generar_portico(p, "X:1")
chequear("T5a 6 nudos · 5 barras (3 col + 2 vigas: 2 vanos)",
         r["n_nudos"] == 6 and r["n_columnas"] == 3 and r["n_vigas"] == 2
         and r["n_barras"] == 5)
chequear("T5b no existen nudos N2",
         not any(n["id"].endswith("_N2") for n in m["nudos"]))

# ---------- T6 · pórtico Y:A (corre en X) ----------
p = proyecto_base()
p["cortes"]["Y:A"] = {
    "niveles_propios": 2,
    "columnas": {str(i): {"activa": True, "base": "empotrada"}
                 for i in range(1, 5)},
    "uniones": {"patron": "pr_momento", "excepciones": {}},
}
m, r = generar_portico(p, "Y:A")
n = nudos_por_id(m)
chequear("T6a Y:A: 4 columnas en x=0,5,10,15",
         r["n_nudos"] == 12 and n["1_N0"]["x"] == 0 and n["2_N0"]["x"] == 5
         and n["4_N0"]["x"] == 15)

# ---------- T7 · errores amables ----------
try:
    p = proyecto_base()
    for c in "ABC":
        p["cortes"]["X:1"]["columnas"][c]["activa"] = False
    generar_portico(p, "X:1")
    chequear("T7a sin columnas activas → ERROR", False)
except ERROR as e:
    chequear("T7a sin columnas activas → ERROR", "columna" in str(e))
try:
    generar_portico(proyecto_base(), "X:9")
    chequear("T7b pórtico inexistente → ERROR", False)
except ERROR as e:
    chequear("T7b pórtico inexistente → ERROR", "no tiene corte" in str(e))
try:
    generar_portico(proyecto_base(), "Z:1")
    chequear("T7c dirección Z → ERROR", False)
except ERROR:
    chequear("T7c dirección Z → ERROR", True)

# ---------- T8 · el modelo pasa por el validador del motor ----------
from engine.modelo import Modelo
p8 = proyecto_base()
p8["cortes"]["Y:A"] = {
    "niveles_propios": 2,
    "columnas": {str(i): {"activa": True, "base": "empotrada"}
                 for i in range(1, 5)},
    "uniones": {"patron": "pr_momento", "excepciones": {}},
}
m, r = generar_portico(p8, "Y:A")
mok = Modelo.desde_dict(m)
chequear("T8 el modelo generado valida en engine.modelo (12 nudos · 14 barras)",
         len(mok.nudos) == 12 and len(mok.barras) == 14
         and len(mok.apoyos) == 4)

print()
if FALLOS:
    print(f"═══ {len(FALLOS)} TESTS DEL GENERADOR FALLARON ═══")
    sys.exit(1)
print("═══ TODOS LOS TESTS DEL GENERADOR PASARON ═══")
