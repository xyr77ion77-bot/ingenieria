# ==================================================================
#  tests_engine.py — Verificación del motor contra fórmulas cerradas
#  ------------------------------------------------------------------
#  Ejecutar:  .venv/bin/python backend/tests_engine.py
#
#  Casos (unidades kg, m, kg/cm²). Las cargas de gravedad son
#  q_perp NEGATIVO (−y local de una barra horizontal = hacia abajo).
#
#   1. Viga simplemente apoyada + UDL↓     (wL²/8, 5wL⁴/384EI, ΣRy = wL)
#   2. Viga simplemente apoyada + P↓       (PL/4,  PL³/48EI)
#   3. Voladizo con P↓ en punta            (Mbase = −PL, PL³/3EI)
#   4. Viga continua 2 tramos + UDL↓       (R central = 1.25wL, M = −wL²/8)
#   5. Pórtico 1 nivel + empuje lateral    (Σ|Mb| = P·h, ΣRx = −P)
#   6. Triángulo isósceles cargado         (diagonales −P√2/2, base +P/2)
#   7. Peso propio                         (ΣRy = γ·A·L, Mmax = wL²/8)
#   8. Detección de estructura inestable
# ==================================================================

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from engine.modelo import Modelo, Nudo, Barra, Apoyo, CargaNodal, ERROR
from engine.solver import analizar

E = 2_100_000.0   # kg/cm² (acero)
A = 100.0         # cm²
I = 10_000.0      # cm⁴

TOL = 5e-4        # tolerancia relativa


def casi(a, b, tol=TOL, msg=""):
    assert abs(a - b) <= tol * max(1.0, abs(b)), f"esperado {b}, obtuvo {a:.6f}  {msg}"


def reaccion(r, nudo, comp):
    for rr in r["reacciones"]:
        if rr["nudo"] == nudo and rr["comp"] == comp:
            return rr["valor"]
    return 0.0


def viga_simple_udl():
    L, w = 6.0, 1000.0          # w ↓ (gravedad) → q_perp = −w
    m = Modelo("viga simple UDL",
               nudos=[Nudo("A", 0, 0), Nudo("C", L / 2, 0), Nudo("B", L, 0)],
               barras=[Barra("V1", "A", "C", E, A, I, q_perp=-w),
                       Barra("V2", "C", "B", E, A, I, q_perp=-w)],
               apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", uy=True)])
    r = analizar(m)
    v = r["barras"][0]
    casi(v["Vi"], +w * L / 2, msg="V(0) = +wL/2")
    casi(v["Vj"], 0.0, tol=1e-3, msg="V(L/2⁻) = 0")
    casi(v["maxM"], w * L ** 2 / 8, msg="Mmax = +wL²/8")
    casi(v["Mi"], 0.0, msg="M en apoyos = 0")
    d = [x for x in r["nudos"] if x["id"] == "C"][0]
    uy = -5 * w * L ** 4 / (384 * (E * 1e4) * (I * 1e-8))     # hacia abajo
    casi(d["uy"], uy, msg="deflexión 5wL⁴/384EI en el centro")
    casi(reaccion(r, "A", "Fy"), +w * L / 2, msg="R_A = +wL/2 (hacia arriba)")
    casi(r["kpi"]["suma_Ry"], w * L, msg="ΣRy = wL")
    print("✓ 1. Viga simple + UDL↓  (V, M, deflexión, reacciones)")


def viga_simple_puntual():
    L, P = 4.0, 5000.0
    m = Modelo("viga simple P al centro",
               nudos=[Nudo("A", 0, 0), Nudo("C", L / 2, 0), Nudo("B", L, 0)],
               barras=[Barra("V1", "A", "C", E, A, I), Barra("V2", "C", "B", E, A, I)],
               apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", uy=True)],
               cargas_nodales=[CargaNodal("C", Fy=-P)])
    r = analizar(m)
    v1 = r["barras"][0]
    casi(v1["Vi"], +P / 2, msg="V(0) = +P/2")
    casi(v1["Vj"], +P / 2, msg="V constante = P/2 en tramo 1")
    casi(v1["maxM"], P * L / 4, msg="Mmax = PL/4")
    d = [x for x in r["nudos"] if x["id"] == "C"][0]
    uy = -P * L ** 3 / (48 * (E * 1e4) * (I * 1e-8))
    casi(d["uy"], uy, msg="deflexión PL³/48EI")
    print("✓ 2. Viga simple + P↓ al centro  (V, M, deflexión)")


def voladizo():
    L, P = 3.0, 2000.0
    m = Modelo("voladizo",
               nudos=[Nudo("A", 0, 0), Nudo("B", L, 0)],
               barras=[Barra("V1", "A", "B", E, A, I)],
               apoyos=[Apoyo("A", ux=True, uy=True, rz=True)],
               cargas_nodales=[CargaNodal("B", Fy=-P)])
    r = analizar(m)
    v = r["barras"][0]
    casi(v["Mi"], -P * L, msg="M(0) = −PL (flexión negativa)")
    casi(abs(v["maxM"]), P * L, msg="|M|max = PL")
    casi(v["Vi"], +P, msg="V constante = +P")
    casi(v["Mj"], 0.0, msg="M en punta = 0")
    d = [x for x in r["nudos"] if x["id"] == "B"][0]
    uy = -P * L ** 3 / (3 * (E * 1e4) * (I * 1e-8))
    casi(d["uy"], uy, msg="deflexión PL³/3EI")
    casi(reaccion(r, "A", "Fy"), +P, msg="R_A = +P")
    print("✓ 3. Voladizo + P↓ en punta  (M = −PL, deflexión, reacciones)")


def viga_continua():
    L, w = 5.0, 800.0
    m = Modelo("viga continua 2 tramos",
               nudos=[Nudo("A", 0, 0), Nudo("B", L, 0), Nudo("C", 2 * L, 0)],
               barras=[Barra("V1", "A", "B", E, A, I, q_perp=-w),
                       Barra("V2", "B", "C", E, A, I, q_perp=-w)],
               apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", uy=True), Apoyo("C", uy=True)])
    r = analizar(m)
    casi(r["kpi"]["suma_Ry"], 2 * w * L, msg="ΣRy = 2wL")
    R_B = reaccion(r, "B", "Fy")
    casi(R_B, 1.25 * w * L, tol=2e-3, msg="R central = 1.25wL")
    mB = r["barras"][0]["Mj"]
    casi(mB, -w * L ** 2 / 8, tol=2e-3, msg="M apoyo central = −wL²/8")
    print("✓ 4. Viga continua 2 tramos  (R central 1.25wL, M apoyo −wL²/8)")


def momento_global(modelo, r):
    """ΣM respecto al origen de cargas (nodales + distribuidas) + reacciones."""
    nudos = {n.id: n for n in modelo.nudos}
    M = 0.0
    for c in modelo.cargas_nodales:
        n = nudos[c.nudo]
        M += n.x * c.Fy - n.y * c.Fx + c.Mz
    # cargas distribuidas (q_perp ⊥ al eje, q_axial along eje, peso propio)
    import math as _m
    for b in modelo.barras:
        ni, nj = nudos[b.ni], nudos[b.nj]
        L = _m.hypot(nj.x - ni.x, nj.y - ni.y)
        c_, s_ = (nj.x - ni.x) / L, (nj.y - ni.y) / L
        xc, yc = (ni.x + nj.x) / 2, (ni.y + nj.y) / 2
        q_ax, q_pp = b.q_axial, (-7850.0 * b.A * 1e-4 if b.peso_propio else 0.0)
        Fx = (b.q_perp * (-s_) + (q_ax + q_pp) * c_) * L
        Fy = (b.q_perp * (c_) + (q_ax + q_pp) * s_) * L
        M += xc * Fy - yc * Fx
    for rr in r["reacciones"]:
        n = nudos[rr["nudo"]]
        if rr["comp"] == "Fx":
            M += -n.y * rr["valor"]
        elif rr["comp"] == "Fy":
            M += n.x * rr["valor"]
        else:
            M += rr["valor"]
    return M


def portico_lateral():
    L, h, P = 6.0, 4.0, 2000.0
    Icol = 10_000.0

    # --- (a) PÓRTICO DE CORTANTE (viga rígida): solución exacta ---
    # V_columna = P/2 → M_base = V·h/2 = P·h/4, δ_tope = P·h³/(24EI)
    I_rigida = 1e12
    m = Modelo("pórtico de cortante",
               nudos=[Nudo("A", 0, 0), Nudo("B", L, 0), Nudo("C", 0, h), Nudo("D", L, h)],
               barras=[Barra("C1", "A", "C", E, A, Icol),
                       Barra("C2", "B", "D", E, A, Icol),
                       Barra("V1", "C", "D", E, A * 100, I_rigida)],
               apoyos=[Apoyo("A", ux=True, uy=True, rz=True),
                       Apoyo("B", ux=True, uy=True, rz=True)],
               cargas_nodales=[CargaNodal("C", Fx=P)])
    r = analizar(m)
    casi(reaccion(r, "A", "Fx"), -P / 2, msg="R_Ax = −P/2")
    casi(reaccion(r, "B", "Fx"), -P / 2, msg="R_Bx = −P/2")
    casi(abs(reaccion(r, "A", "Mz")), P * h / 4, tol=5e-3, msg="|M_base| = P·h/4")
    EI = (E * 1e4) * (Icol * 1e-8)
    dC = [x for x in r["nudos"] if x["id"] == "C"][0]
    casi(dC["ux"], P * h ** 3 / (24 * EI), tol=5e-3, msg="δ = P·h³/(24EI)")

    # --- (b) pórtico flexible + gravedad: equilibrio global ΣM = 0 ---
    w = 1000.0
    m2 = Modelo("pórtico flexible",
                nudos=[Nudo("A", 0, 0), Nudo("B", L, 0), Nudo("C", 0, h), Nudo("D", L, h)],
                barras=[Barra("C1", "A", "C", E, A, Icol),
                        Barra("C2", "B", "D", E, A, Icol),
                        Barra("V1", "C", "D", E, A, Icol, q_perp=-w)],
                apoyos=[Apoyo("A", ux=True, uy=True, rz=True),
                        Apoyo("B", ux=True, uy=True, rz=True)],
                cargas_nodales=[CargaNodal("C", Fx=P)])
    r2 = analizar(m2)
    casi(r2["kpi"]["suma_Rx"], -P, msg="ΣRx = −P")
    casi(r2["kpi"]["suma_Ry"], w * L, msg="ΣRy = wL")
    casi(momento_global(m2, r2), 0.0, tol=1e-6, msg="ΣM_origen = 0")
    print("✓ 5. Pórtico lateral  (cortante y P·h/4 exactos con viga rígida, ΣM = 0)")


def celosia_inclinada():
    L, P = 2.0, 1000.0
    I_bisagra = 1e-4   # inercia casi nula → comportamiento de barra articulada
    m = Modelo("triángulo",
               nudos=[Nudo("A", 0, 0), Nudo("B", 2 * L, 0), Nudo("C", L, L)],
               barras=[Barra("D1", "A", "C", E, A, I_bisagra),
                       Barra("D2", "B", "C", E, A, I_bisagra),
                       Barra("M1", "A", "B", E, A, I_bisagra)],
               apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", uy=True)],  # B deslizante
               cargas_nodales=[CargaNodal("C", Fy=-P)])
    r = analizar(m)
    diag = [b for b in r["barras"] if b["id"] == "D1"][0]
    casi(diag["Ni"], -P * math.sqrt(2) / 2, msg="diagonal comprimida −P√2/2")
    base = [b for b in r["barras"] if b["id"] == "M1"][0]
    casi(base["Ni"], +P / 2, msg="base en tracción +P/2 (tiro absorbed por la solera)")
    casi(r["kpi"]["suma_Ry"], P, msg="ΣRy = P")
    print("✓ 6. Triángulo inclinado  (diagonales −P√2/2, solera +P/2)")


def peso_propio():
    L = 4.0
    A2 = 100.0  # cm² → 78.5 kg/m
    m = Modelo("peso propio",
               nudos=[Nudo("A", 0, 0), Nudo("B", L, 0)],
               barras=[Barra("V1", "A", "B", E, A2, I, peso_propio=True)],
               apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", uy=True)])
    r = analizar(m)
    pp = (A2 * 1e-4) * 7850.0
    casi(r["kpi"]["suma_Ry"], pp * L, msg="ΣRy = γ·A·L")
    casi(r["barras"][0]["maxM"], pp * L ** 2 / 8, msg="Mmax por peso propio")
    print("✓ 7. Peso propio  (ΣRy = γAL, Mmax = wL²/8)")


def estructura_inestable():
    try:
        m2 = Modelo("voladizo sin apoyo de giro",
                    nudos=[Nudo("A", 0, 0), Nudo("B", 3, 0)],
                    barras=[Barra("B1", "A", "B", E, A, I)],
                    apoyos=[Apoyo("A", ux=True, uy=True)],  # sin rz → mecanismo
                    cargas_nodales=[CargaNodal("B", Fy=-100)])
        analizar(m2)
        raise AssertionError("debió lanzar ERROR por inestabilidad")
    except ERROR:
        print("✓ 8. Detecta estructura inestable (mensaje amable)")


if __name__ == "__main__":
    viga_simple_udl()
    viga_simple_puntual()
    voladizo()
    viga_continua()
    portico_lateral()
    celosia_inclinada()
    peso_propio()
    estructura_inestable()
    print("\n═══ TODOS LOS TESTS PASARON ═══")
