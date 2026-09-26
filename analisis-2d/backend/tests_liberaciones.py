# ==================================================================
#  tests_liberaciones.py — Rótulas (liberaciones de momento M=0)
#  ------------------------------------------------------------------
#  Casos dorados de la teoría con la convención del motor:
#    · Viga empotrada-rótula con UDL↓:  M_emp = −wL²/8 · R_emp = 5wL/8
#    · Viga biapoyada con ambos extremos articulados:  M_vano = +wL²/8
#    · Pórtico con viga articulada + carga lateral:  columnas en voladizo
#      Δ = H·h³/(3·ΣEI) · M_base = H·h/2 (por columna, H/2 c/u)
# ==================================================================

import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.modelo import Barra, CargaNodal, ERROR, Apoyo, Modelo, Nudo
from engine.solver import analizar

FALLOS = []

# sección ficticia en unidades del motor
E, A_, I_ = 2_100_000.0, 100.0, 20_000.0   # kg/cm², cm², cm⁴


def viga(L=6.0, rel_i=False, rel_j=False, w=0.0, apoyos="pasadores"):
    m = Modelo(titulo="test")
    m.nudos = [Nudo("N1", 0.0, 0.0), Nudo("N2", L, 0.0)]
    m.barras = [Barra("V1", "N1", "N2", E, A_, I_, q_perp=w,
                      rel_i=rel_i, rel_j=rel_j)]
    if apoyos == "pasadores":
        m.apoyos = [Apoyo("N1", ux=True, uy=True), Apoyo("N2", uy=True)]
    elif apoyos == "empotrado_pasador":
        m.apoyos = [Apoyo("N1", ux=True, uy=True, rz=True), Apoyo("N2", uy=True)]
    elif apoyos == "pasador_empotrado":
        m.apoyos = [Apoyo("N1", ux=True, uy=True), Apoyo("N2", uy=True, rz=True)]
    return m


def chequear(nombre, condicion, detalle=""):
    ok = bool(condicion)
    print(("✓" if ok else "✗"), nombre, detalle)
    if not ok:
        FALLOS.append(nombre)


# ------------------------------------------------------------------
# T1 · Viga empotrada (i) — rótula (j) con UDL↓
#     M_i = −wL²/8 · M_j = 0 · V_i = 5wL/8 · V_j = −3wL/8
# ------------------------------------------------------------------
w, L = 1000.0, 6.0
r = analizar(viga(rel_j=True, w=-w, apoyos="empotrado_pasador"))
b = r["barras"][0]
R = {x["nudo"] + x["comp"]: x["valor"] for x in r["reacciones"]}
chequear("T1a Mi = −wL²/8", abs(b["Mi"] - (-w * L**2 / 8)) < 1e-6,
         f"Mi={b['Mi']:.2f}")
chequear("T1b M_j = 0 (rótula)", abs(b["Mj"]) < 1e-9, f"Mj={b['Mj']:.2e}")
chequear("T1c V_i = 5wL/8", abs(b["Vi"] - 5 * w * L / 8) < 1e-6,
         f"Vi={b['Vi']:.2f}")
chequear("T1d V_j = −3wL/8", abs(b["Vj"] - (-3 * w * L / 8)) < 1e-6,
         f"Vj={b['Vj']:.2f}")
chequear("T1e Reacciones 5wL/8 y 3wL/8",
         abs(R.get("N1Fy", 0) - 5 * w * L / 8) < 1e-6
         and abs(R.get("N2Fy", 0) - 3 * w * L / 8) < 1e-6,
         f"R1={R.get('N1Fy'):.2f} R2={R.get('N2Fy'):.2f}")
chequear("T1f M vano máx = 9wL²/128",
         abs(b["maxM_pos"] - 9 * w * L**2 / 128) < 1e-6,
         f"maxM+={b['maxM_pos']:.2f}")

# ------------------------------------------------------------------
# T2 · Viga rótula (i) — empotrada (j) con UDL↓ (simétrico)
#     M_i = 0 · M_j = −wL²/8 · R_i = 3wL/8 · R_j = 5wL/8
# ------------------------------------------------------------------
r = analizar(viga(rel_i=True, w=-w, apoyos="pasador_empotrado"))
b = r["barras"][0]
R = {x["nudo"] + x["comp"]: x["valor"] for x in r["reacciones"]}
chequear("T2a Mi = 0 (rótula)", abs(b["Mi"]) < 1e-9, f"Mi={b['Mi']:.2e}")
chequear("T2b Mj = −wL²/8", abs(b["Mj"] - (-w * L**2 / 8)) < 1e-6,
         f"Mj={b['Mj']:.2f}")
chequear("T2c Reacciones 3wL/8 y 5wL/8",
         abs(R.get("N1Fy", 0) - 3 * w * L / 8) < 1e-6
         and abs(R.get("N2Fy", 0) - 5 * w * L / 8) < 1e-6,
         f"R1={R.get('N1Fy'):.2f} R2={R.get('N2Fy'):.2f}")

# ------------------------------------------------------------------
# T3 · Viga biapoyada con AMBOS extremos articulados (= apoyos simples)
#     M_i = M_j = 0 · M_vano = +wL²/8 · V = ±wL/2
# ------------------------------------------------------------------
r = analizar(viga(rel_i=True, rel_j=True, w=-w))
b = r["barras"][0]
R = {x["nudo"] + x["comp"]: x["valor"] for x in r["reacciones"]}
chequear("T3a Mi = Mj = 0", abs(b["Mi"]) < 1e-9 and abs(b["Mj"]) < 1e-9,
         f"Mi={b['Mi']:.2e} Mj={b['Mj']:.2e}")
chequear("T3b M vano = +wL²/8",
         abs(b["maxM_pos"] - w * L**2 / 8) < 1e-6,
         f"maxM+={b['maxM_pos']:.2f}")
chequear("T3c V = ±wL/2",
         abs(b["Vi"] - w * L / 2) < 1e-6 and abs(b["Vj"] - (-w * L / 2)) < 1e-6,
         f"Vi={b['Vi']:.2f} Vj={b['Vj']:.2f}")
chequear("T3d Reacciones wL/2 c/u",
         abs(R.get("N1Fy", 0) - w * L / 2) < 1e-6
         and abs(R.get("N2Fy", 0) - w * L / 2) < 1e-6,
         f"R1={R.get('N1Fy'):.2f} R2={R.get('N2Fy'):.2f}")

# ------------------------------------------------------------------
# T4 · Pórtico 1 nivel con viga articulada + carga lateral H
#     Columnas en voladizo: Δ = H·h³/(3·2EI) · M_base = H·h/2 c/u
#     La viga articulada no toma momento (Mi = Mj = 0 en V1).
# ------------------------------------------------------------------
h, H = 4.0, 2000.0        # m, kg
m = Modelo(titulo="pórtico articulado")
m.nudos = [Nudo("A1", 0, 0), Nudo("A2", 6, 0),
           Nudo("B1", 0, h), Nudo("B2", 6, h)]
m.barras = [
    Barra("C1", "A1", "B1", E, A_, I_),                      # columna izq
    Barra("C2", "A2", "B2", E, A_, I_),                      # columna der
    Barra("V1", "B1", "B2", E, A_, I_, rel_i=True, rel_j=True),
]
m.apoyos = [Apoyo("A1", ux=True, uy=True, rz=True),
            Apoyo("A2", ux=True, uy=True, rz=True)]
m.cargas_nodales = [CargaNodal("B1", Fx=H)]
r = analizar(m)
bs = {x["id"]: x for x in r["barras"]}
# Solución cerrada EXACTA (viga elástica axialmente, no rígida):
#   columna = voladizo k_c = 3EI/h³ · viga = muelle axial k_v = EA/L
#   H = (k_c+k_v)u1 − k_v u2 ; 0 = −k_v u1 + (k_c+k_v)u2
EI_int = E * 1.0e4 * I_ * 1.0e-8          # EI en unidades internas (kg·m²)
EA_int = E * A_                            # EA interno (kg)
k_c = 3.0 * EI_int / h**3
k_v = EA_int / 6.0
u1 = H * (k_c + k_v) / (k_c * (k_c + 2.0 * k_v))
H1 = k_c * u1                              # carga que toma la columna 1
nd = {n["id"]: n for n in r["nudos"]}
chequear("T4a Δ exacta (sistema 2 GDL)",
         abs(nd["B1"]["ux"] - u1) / u1 < 1e-9,
         f"ux={nd['B1']['ux']:.6f} vs {u1:.6f}")
chequear("T4b M_base columna = H1·h",
         abs(abs(bs["C1"]["maxM"]) - H1 * h) < 1e-3,
         f"M={bs['C1']['maxM']:.2f} vs {H1 * h:.2f}")
chequear("T4c Viga articulada: Mi = Mj = 0",
         abs(bs["V1"]["Mi"]) < 1e-9 and abs(bs["V1"]["Mj"]) < 1e-9,
         f"Mi={bs['V1']['Mi']:.2e} Mj={bs['V1']['Mj']:.2e}")
chequear("T4d Viga articulada: N = −(H − H1)",
         abs(abs(bs["V1"]["Ni"]) - (H - H1)) < 1e-3,
         f"N={bs['V1']['Ni']:.2f} vs {-(H - H1):.2f}")

# ------------------------------------------------------------------
# T5 · Momento aplicado a un nudo sin rigidez rotacional → ERROR amable
# ------------------------------------------------------------------
m = viga(rel_i=True, rel_j=True, w=0.0)
m.cargas_nodales = [CargaNodal("N1", Mz=500.0)]
try:
    analizar(m)
    chequear("T5 Mecanismo con Mz en nudo articulado detectado", False)
except ERROR as e:
    chequear("T5 Mecanismo con Mz en nudo articulado detectado",
             "mecanismo" in str(e).lower(), str(e)[:60])

# ------------------------------------------------------------------
# T6 · Serialización ida y vuelta conserva las liberaciones
# ------------------------------------------------------------------
m = viga(rel_i=True, rel_j=True, w=-w)
d = m.a_dict()
m2 = Modelo.desde_dict(d)
chequear("T6 a_dict/desde_dict conserva rel_i/rel_j",
         m2.barras[0].rel_i and m2.barras[0].rel_j)

print()
if FALLOS:
    print(f"═══ {len(FALLOS)} TESTS DE LIBERACIONES FALLARON ═══")
    for f in FALLOS:
        print("   ✗", f)
    sys.exit(1)
print("═══ TODOS LOS TESTS DE LIBERACIONES PASARON ═══")

