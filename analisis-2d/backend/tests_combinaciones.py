# ==================================================================
#  tests_combinaciones.py — Fase 2: acciones y combinaciones §8.3
#  ------------------------------------------------------------------
#  Ejecutar:  .venv/bin/python backend/tests_combinaciones.py
#
#  T1. Port del motor sísmico = valores dorados del JS auditado
#  T2. Casos CP/CV/SH/SV bien construidos (ΣFx del caso SH = V0d − Ft)
#  T3. γ = 0,5 con CV < 500 kg/m²  (§8.3.2.b)
#  T4. Superposición lineal de combinaciones (8.6+ = Σ f·caso)
#  T5. SRSS: S = signo·√(SH²+SV²)
#  T6. Envolvente con sismo desactivado (1,4·CP gobierna)
# ==================================================================

import math
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from engine.modelo import Modelo, Nudo, Barra, Apoyo, CargaNodal, ERROR
from engine.solver import analizar
from engine import covenin1756 as cov
from engine.acciones import (Acciones, pesos_por_nivel, gamma_de,
                             construir_casos, generar_combinaciones,
                             evaluar_combo, envolvente,
                             analizar_con_combinaciones)

E, A, I = 2_100_000.0, 78.1, 5696.0   # HEB 200
TOL = 2e-3


def casi(a, b, tol=TOL, msg=""):
    assert abs(a - b) <= tol * max(1.0, abs(b)), f"esperado {b}, obtuvo {a:.6f}  {msg}"


# ------------------------------------------------------------- modelo de prueba
def portico_2_niveles():
    """2 niveles (3,5 y 7,0 m), 1 vano de 6 m. CP = 10 000 kg/m por viga
    → W = [60 000, 60 000] (caso de referencia del motor auditado)."""
    m = Modelo("portico prueba",
               nudos=[Nudo("A", 0, 0), Nudo("B", 6, 0),
                      Nudo("C", 0, 3.5), Nudo("D", 6, 3.5),
                      Nudo("E", 0, 7.0), Nudo("F", 6, 7.0)],
               barras=[Barra("C1", "A", "C", E, A, I),
                       Barra("C2", "B", "D", E, A, I),
                       Barra("C3", "C", "E", E, A, I),
                       Barra("C4", "D", "F", E, A, I),
                       Barra("V1", "C", "D", E, A, I),
                       Barra("V2", "E", "F", E, A, I)],
               apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", ux=True, uy=True)])
    return m


ACC_BASE = Acciones(
    barra_cp={"V1": 10000.0, "V2": 10000.0},
    barra_cv={"V1": 300.0, "V2": 300.0},
    sismo={"A0": 0.21, "A1": 0.18, "TL": 3.9, "grupo": "B2", "nd": "ND3",
           "sitio": "CD", "topo": "leve", "H": 0.0, "rho": 1.0, "FI": 1.0,
           "ct": 0.08, "fraccion_cv": 0.25, "fraccion_portico": 1.0,
           "incluir_sismo": True, "incluir_sv": True,
           "sobrerresistencia": False, "rho_redundancia": 1.0,
           "gamma_manual": None},
)


def t1_port_golden():
    m = portico_2_niveles()
    ys, W, _ = pesos_por_nivel(m, ACC_BASE)
    # el nivel base (y=0) no tiene peso → se excluye del cómputo sísmico
    p = {**ACC_BASE.sismo, "N": 2, "hs_abs": [3.5, 7.0], "W": [60000, 60000]}
    s = cov.calcular_sismo(p)
    # valores dorados del JS auditado (verificados con node)
    casi(s["AA"], 0.2814, 1e-6, "AA")
    casi(s["TC"], 0.446642, 1e-6, "TC")
    casi(s["Ta"], 0.344281, 1e-6, "Ta")
    casi(s["mu"], 0.9625, 1e-6, "μ")
    casi(s["C"], 0.118995, 1e-6, "C")
    casi(s["Cmin"], 0.0469, 1e-6, "Cmin")
    casi(s["V0d"], 14279.369761, 1e-6, "V0d")
    casi(s["Ft"], 571.17479, 1e-6, "Ft")
    casi(s["Fis"][0], 4569.398323, 1e-6, "Fi nivel 1")
    casi(s["Fis"][1], 9138.796647, 1e-6, "Fi nivel 2")
    casi(s["Ad"](0.5), 0.100548, 1e-6, "Ad(0,5)")
    # CSV vertical (Tabla 19: CD → γmáx=1,3; η0=0,7+α·A0=0,91; β=2,3)
    csv = cov.csv_vertical(s["AA"], "CD", s["aA0"])
    casi(csv, 2.3 * 0.2814 * 1.3 * (0.7 + 0.21), 1e-6, "CSV")
    print("✓ T1. Port del motor sísmico = valores dorados del JS auditado")


def t2_casos():
    m = portico_2_niveles()
    ys, W, _ = pesos_por_nivel(m, ACC_BASE)
    casi(W[0], 0.0, msg="W base = 0")
    # W = CP + f·CV por nivel (ambos niveles simétricos)
    casi(W[1], 60000.0 + 0.25 * 300 * 6, msg="W nivel 1 (CP 10 000×6 + f·CV)")
    casi(W[2], 60000.0 + 0.25 * 300 * 6, msg="W nivel 2 (CP 10 000×6 + f·CV)")

    p = {**ACC_BASE.sismo, "N": 2, "hs_abs": [3.5, 7.0], "W": [60000, 60000]}
    s = cov.calcular_sismo(p)
    s["_niveles_filtrados"] = [3.5, 7.0]
    s["_clase"] = "CD"
    casos, csv_v = construir_casos(m, ACC_BASE, s)

    r_cp = analizar(casos["CP"])
    casi(r_cp["kpi"]["suma_Ry"], 120000.0, msg="ΣRy CP = 2×60 000")
    r_cv = analizar(casos["CV"])
    casi(r_cv["kpi"]["suma_Ry"], 300 * 12, msg="ΣRy CV = cv·L total (sin fracción)")
    r_sh = analizar(casos["SH"])
    suma_fx_sh = r_sh["kpi"]["suma_Fx_cargas"]
    casi(suma_fx_sh, +(s["V0d"] - s["Ft"]), msg="ΣFx(SH) = +(V0d − Ft)")
    casi(r_sh["kpi"]["suma_Rx"], -(s["V0d"] - s["Ft"]), msg="ΣRx = −(V0d − Ft)")
    r_sv = analizar(casos["SV"])
    csv = cov.csv_vertical(s["AA"], "CD", s["aA0"])
    casi(r_sv["kpi"]["suma_Ry"], csv * 120000.0, msg="ΣRy(SV) = CSV·CP")
    print("✓ T2. Casos CP/CV/SH/SV correctos (ΣFx SH = −(V0d−Ft), ΣRy SV = CSV·CP)")


def t3_gamma():
    m = portico_2_niveles()
    acc = Acciones(barra_cv={"V1": 300.0, "V2": 300.0})
    casi(gamma_de(m, acc), 0.5, msg="γ=0,5 con CV<500")
    acc2 = Acciones(barra_cv={"V1": 300.0, "V2": 600.0})
    casi(gamma_de(m, acc2), 1.0, msg="γ=1 con CV≥500")
    acc3 = Acciones(barra_cv={})
    acc3.sismo["gamma_manual"] = 0.5
    casi(gamma_de(m, acc3), 0.5, msg="override manual")
    print("✓ T3. γ según §8.3.2.b (0,5 con CV<500; override manual)")


def t4_superposicion():
    m = portico_2_niveles()
    p = {**ACC_BASE.sismo, "N": 2, "hs_abs": [3.5, 7.0], "W": [60000, 60000]}
    s = cov.calcular_sismo(p)
    s["_niveles_filtrados"] = [3.5, 7.0]
    s["_clase"] = "CD"
    casos, _ = construir_casos(m, ACC_BASE, s)
    res = {k: analizar(v) for k, v in casos.items()}

    def mj(r):
        return [x for x in r["barras"] if x["id"] == "V2"][0]["Mj"]

    vals = {k: mj(r) for k, r in res.items()}
    val_casos = {k: {"barras": {"V2": {"Mj": v}}, "nudos": {}, "reacciones": {}}
                 for k, v in vals.items()}

    gamma = gamma_de(m, ACC_BASE)
    combos = generar_combinaciones(ACC_BASE, s, gamma)
    c86 = [c for c in combos if c["nombre"] == "8.6 (+)"][0]
    ev = evaluar_combo(val_casos, c86)
    esperado = (1.2 * vals["CP"] + gamma * vals["CV"]
                + 1.0 * vals["SH"] + 0.3 * vals["SV"])
    casi(ev["barras"]["V2"]["Mj"], esperado, 1e-9, "8.6(+) Mj por superposición")
    print("✓ T4. Superposición lineal de combinaciones exacta")


def t5_srss():
    sh, sv = 3000.0, -400.0
    combo = {"nombre": "8.9 (+)", "fac": {"CP": 1.2, "CV": 0.5, "SH": 1.0, "SV": 1.0},
             "srss": True}
    val = {"CP": {"barras": {"V1": {"Mj": 1000.0}}, "nudos": {}, "reacciones": {}},
           "CV": {"barras": {"V1": {"Mj": 200.0}}, "nudos": {}, "reacciones": {}},
           "SH": {"barras": {"V1": {"Mj": sh}}, "nudos": {}, "reacciones": {}},
           "SV": {"barras": {"V1": {"Mj": sv}}, "nudos": {}, "reacciones": {}}}
    ev = evaluar_combo(val, combo)
    esperado = 1.2 * 1000 + 0.5 * 200 + math.sqrt(3000 ** 2 + 400 ** 2)
    casi(ev["barras"]["V1"]["Mj"], esperado, 1e-12, "SRSS con signo dominante SH")
    # dominante SV negativo
    combo2 = dict(combo)
    val2 = {"CP": val["CP"], "CV": val["CV"],
            "SH": {"barras": {"V1": {"Mj": -100.0}}, "nudos": {}, "reacciones": {}},
            "SV": {"barras": {"V1": {"Mj": -400.0}}, "nudos": {}, "reacciones": {}}}
    ev2 = evaluar_combo(val2, combo2)
    esperado2 = 1200 + 100 - math.sqrt(100 ** 2 + 400 ** 2)
    casi(ev2["barras"]["V1"]["Mj"], esperado2, 1e-12, "SRSS con dominante SV<0")
    print("✓ T5. SRSS: S = signo·√(SH²+SV²)")


def t6_envolvente_sin_sismo():
    m = portico_2_niveles()
    acc = Acciones(barra_cp={"V1": 10000.0, "V2": 10000.0})
    acc.sismo["incluir_sismo"] = False
    r = analizar_con_combinaciones(m.a_dict(), acc.__dict__)
    env_v2 = r["envolvente"]["barras"]["V2"]
    # referencia: caso CP directo (el marco redistribuye → no es wL²/8)
    m_cp = Modelo("cp", list(m.nudos),
                  [Barra("C1", "A", "C", E, A, I), Barra("C2", "B", "D", E, A, I),
                   Barra("C3", "C", "E", E, A, I), Barra("C4", "D", "F", E, A, I),
                   Barra("V1", "C", "D", E, A, I, q_perp=-10000.0),
                   Barra("V2", "E", "F", E, A, I, q_perp=-10000.0)],
                  list(m.apoyos))
    r_cp = analizar(m_cp)
    mmax_cp = max(r_cp["diagramas"]["V2"]["M"])   # máximo con signo en el vano
    casi(env_v2["Mmax"]["max"], 1.4 * mmax_cp, msg="envolvente max = 1,4·CP")
    assert env_v2["Mmax"]["cmax"] == "1,4·CP"
    casi(env_v2["Mmax"]["min"], 1.2 * mmax_cp, msg="envolvente min = 1,2·CP")
    print("✓ T6. Envolvente sin sismo: 1,4·CP gobierna, 1,2·CP cierra")


if __name__ == "__main__":
    t1_port_golden()
    t2_casos()
    t3_gamma()
    t4_superposicion()
    t5_srss()
    t6_envolvente_sin_sismo()
    print("\n═══ TODOS LOS TESTS DE COMBINACIONES PASARON ═══")
