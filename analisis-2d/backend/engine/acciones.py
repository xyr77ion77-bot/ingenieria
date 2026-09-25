# ==================================================================
#  acciones.py — Acciones y combinaciones COVENIN 1756-1:2019 §8.3
#  ------------------------------------------------------------------
#  FASE 2 (pestaña «Acciones» del software):
#
#   1. Construye los CASOS DE CARGA elementales a partir del modelo:
#        CP  — cargas permanentes (peso propio + q_cp + cargas nodales CP)
#        CV  — cargas variables   (q_cv + cargas nodales CV)
#        SH  — sismo horizontal estático equivalente (Fi por nivel, §9.4)
#        SV  — sismo vertical     (SV = CSV·CP, §8.3.1.4, fórmulas 8.4–8.5)
#
#   2. Genera las COMBINACIONES de §8.3.2 (verificadas contra el PDF):
#        U = 1,2·CP + γ·CV ± SH + 0,3·SV      (8.6)
#        U = 0,9·CP ± SH − 0,3·SV             (8.7)
#        S = (SH² + SV²)^(1/2)                (8.8)
#        U = 1,2·CP + γ·CV ± S                (8.9)
#        U = 0,9·CP ± S                       (8.10)
#      (opcionalmente con sobrerresistencia: SH → (Ω0·ρ)·SH, 8.11–8.15)
#
#   3. Resuelve cada caso con el motor y EVALÚA las combinaciones por
#      superposición (todas son lineales) → ENVOLVENTE por barra/nudo/
#      reacción con la combinación que gobierna cada extremo.
#
#  γ = 0,5 si la carga variable < 500 kgf/m² (salvo reunión pública o
#  estacionamiento) y 1 en los demás casos (§8.3.2.b). En esta versión
#  se deduce de las cargas CV por metro de barra y admite override
#  manual.
# ==================================================================

import math
from dataclasses import dataclass, field

from .modelo import Modelo, Nudo, Barra, Apoyo, CargaNodal, ERROR
from .solver import analizar
from . import covenin1756 as cov

_GAMMA_ACERO = 7850.0   # kg/m³


@dataclass
class Acciones:
    # cargas gravitacionales por barra (kg/m, hacia abajo global)
    barra_cp: dict = field(default_factory=dict)   # {id_barra: kg/m}
    barra_cv: dict = field(default_factory=dict)
    # cargas nodales por tipo (kg, kg·m)
    nodo_cp: dict = field(default_factory=dict)    # {id_nudo: {"Fx","Fy","Mz"}}
    nodo_cv: dict = field(default_factory=dict)
    # parámetros del sismo (COVENIN 1756-1:2019)
    sismo: dict = field(default_factory=lambda: {
        "A0": 0.21, "A1": 0.18, "TL": 3.9,
        "grupo": "B2", "nd": "ND3", "sitio": "CD", "topo": "leve",
        "H": 0.0, "rho": 1.0, "FI": 1.0,
        "ct": 0.08,                 # Tabla 24 (acero P-RM)
        "fraccion_cv": 0.25,        # Tabla 20 (oficinas)
        "fraccion_portico": 1.0,    # % del V0 que toma el plano modelado
        "incluir_sismo": True,
        "incluir_sv": True,
        "sobrerresistencia": False,
        "rho_redundancia": 1.0,     # §6.3 (Tabla 13)
        "gamma_manual": None,       # override de γ (§8.3.2.b)
    })

    @staticmethod
    def desde_dict(d):
        if not isinstance(d, dict):
            raise ERROR("Las acciones deben ser un objeto JSON.")
        acc = Acciones()
        acc.barra_cp = {str(k): float(v or 0) for k, v in (d.get("barra_cp") or {}).items()}
        acc.barra_cv = {str(k): float(v or 0) for k, v in (d.get("barra_cv") or {}).items()}
        acc.nodo_cp = {str(k): {"Fx": float((v or {}).get("Fx") or 0),
                                "Fy": float((v or {}).get("Fy") or 0),
                                "Mz": float((v or {}).get("Mz") or 0)}
                       for k, v in (d.get("nodo_cp") or {}).items()}
        acc.nodo_cv = {str(k): {"Fx": float((v or {}).get("Fx") or 0),
                                "Fy": float((v or {}).get("Fy") or 0),
                                "Mz": float((v or {}).get("Mz") or 0)}
                       for k, v in (d.get("nodo_cv") or {}).items()}
        s = d.get("sismo") or {}
        for k, v in s.items():
            if k in acc.sismo:
                acc.sismo[k] = v
        return acc


# ------------------------------------------------------------------
# Niveles y pesos sísmicos del modelo 2D
# ------------------------------------------------------------------
def niveles_del_modelo(modelo: Modelo):
    ys = sorted({round(n.y, 4) for n in modelo.nudos})
    return ys


def pesos_por_nivel(modelo: Modelo, acc: Acciones):
    """
    W por nivel (kg) a partir del modelo 2D:
      · cada barra aporta (CP + f·CV + pp)·L repartido la mitad a cada extremo
      · cada carga nodal aporta |Fy_cp| + f·|Fy_cv|
    Devuelve (ys, W, mapa_nivel_por_nudo).
    """
    f = acc.sismo.get("fraccion_cv", 0.25)
    ys = niveles_del_modelo(modelo)
    W = {y: 0.0 for y in ys}
    nivel_de = {n.id: min(ys, key=lambda y: abs(y - n.y)) for n in modelo.nudos}

    for b in modelo.barras:
        ni, nj = modelo.nudo(b.ni), modelo.nudo(b.nj)
        L = math.hypot(nj.x - ni.x, nj.y - ni.y)
        if L <= 0:
            continue
        cp = acc.barra_cp.get(b.id, 0.0)
        cv = acc.barra_cv.get(b.id, 0.0) * f
        pp = b.A * 1e-4 * _GAMMA_ACERO if b.peso_propio else 0.0
        w_medio = (cp + cv + pp) * L / 2.0
        W[nivel_de[ni.id]] += w_medio
        W[nivel_de[nj.id]] += w_medio

    for nid, c in acc.nodo_cp.items():
        n = modelo.nudo(nid)
        if n is None:
            continue
        W[nivel_de[nid]] += abs(c.get("Fy") or 0)
    for nid, c in acc.nodo_cv.items():
        n = modelo.nudo(nid)
        if n is None:
            continue
        W[nivel_de[nid]] += f * abs(c.get("Fy") or 0)

    return ys, [W[y] for y in ys], nivel_de


# ------------------------------------------------------------------
# γ según §8.3.2.b
# ------------------------------------------------------------------
def gamma_de(modelo: Modelo, acc: Acciones) -> float:
    if acc.sismo.get("gamma_manual") in (0.5, 1.0):
        return acc.sismo["gamma_manual"]
    cvs = [v for v in acc.barra_cv.values() if v > 0]
    if not cvs:
        return 1.0
    return 0.5 if max(cvs) < 500 else 1.0


# ------------------------------------------------------------------
# Casos de carga elementales
# ------------------------------------------------------------------
def construir_casos(modelo: Modelo, acc: Acciones, s: dict):
    """
    Devuelve (casos, csv) donde casos = {nombre: Modelo}.
    s = resultado de covenin1756.calcular_sismo (para Fi por nivel).
    """
    incluir_sismo = acc.sismo.get("incluir_sismo", True)
    incluir_sv = incluir_sismo and acc.sismo.get("incluir_sv", True)

    # --- CP (permanente) ---
    barras = []
    for b in modelo.barras:
        cp = acc.barra_cp.get(b.id, 0.0)
        pp = b.A * 1e-4 * _GAMMA_ACERO if b.peso_propio else 0.0
        barras.append(Barra(b.id, b.ni, b.nj, b.E, b.A, b.I,
                            nombre_seccion=b.nombre_seccion,
                            q_perp=-(cp + pp)))
    casos = {"CP": Modelo(modelo.titulo + " · CP", list(modelo.nudos), barras,
                          list(modelo.apoyos),
                          [CargaNodal(nid, c["Fx"], c["Fy"], c["Mz"])
                           for nid, c in acc.nodo_cp.items() if modelo.nudo(nid)])}

    # --- CV (variable) ---
    barras = [Barra(b.id, b.ni, b.nj, b.E, b.A, b.I,
                    nombre_seccion=b.nombre_seccion,
                    q_perp=-acc.barra_cv.get(b.id, 0.0))
              for b in modelo.barras]
    casos["CV"] = Modelo(modelo.titulo + " · CV", list(modelo.nudos), barras,
                         list(modelo.apoyos),
                         [CargaNodal(nid, c["Fx"], c["Fy"], c["Mz"])
                          for nid, c in acc.nodo_cv.items() if modelo.nudo(nid)])

    if incluir_sismo:
        # --- SH (sismo horizontal: Fi por nivel, §9.4) ---
        # los niveles con peso sísmico provienen del orquestador
        # (los niveles sin W — p. ej. la base — no reciben Fi)
        ys_f = s.get("_niveles_filtrados")
        if ys_f is None:
            ys_all, W_all, _ = pesos_por_nivel(modelo, acc)
            ys_f = [y for y, w in zip(ys_all, W_all) if w > 1e-9]
        frac = acc.sismo.get("fraccion_portico", 1.0)
        en_nivel = {y: [] for y in ys_f}
        _ys_all, _W_all, nivel_de = pesos_por_nivel(modelo, acc)
        for n in modelo.nudos:
            y_n = nivel_de[n.id]
            if y_n in en_nivel:
                en_nivel[y_n].append(n.id)
        cargas = []
        for y, fi_nivel in zip(ys_f, s["Fis"]):
            nodos = en_nivel.get(y) or []
            if not nodos or fi_nivel == 0:
                continue
            fx = fi_nivel * frac / len(nodos)
            for nid in nodos:
                cargas.append(CargaNodal(nid, Fx=fx))
        casos["SH"] = Modelo(modelo.titulo + " · SH", list(modelo.nudos),
                             [Barra(b.id, b.ni, b.nj, b.E, b.A, b.I)
                              for b in modelo.barras],
                             list(modelo.apoyos), cargas)

        # --- SV (sismo vertical: SV = CSV·CP, §8.3.1.4) ---
        if incluir_sv:
            csv_v = cov.csv_vertical(s["AA"], s.get("_clase", "CD"),
                                     s["aA0"])
            barras = []
            for b in modelo.barras:
                cp = acc.barra_cp.get(b.id, 0.0)
                pp = b.A * 1e-4 * _GAMMA_ACERO if b.peso_propio else 0.0
                barras.append(Barra(b.id, b.ni, b.nj, b.E, b.A, b.I,
                                    nombre_seccion=b.nombre_seccion,
                                    q_perp=-csv_v * (cp + pp)))
            cargas = [CargaNodal(nid, Fx=csv_v * c["Fx"], Fy=csv_v * c["Fy"],
                                 Mz=csv_v * c["Mz"])
                      for nid, c in acc.nodo_cp.items() if modelo.nudo(nid)]
            casos["SV"] = Modelo(modelo.titulo + " · SV", list(modelo.nudos),
                                 barras, list(modelo.apoyos), cargas)
        else:
            csv_v = 0.0
    else:
        csv_v = 0.0

    return casos, (csv_v if incluir_sismo else 0.0)


# ------------------------------------------------------------------
# Combinaciones §8.3.2
# ------------------------------------------------------------------
def generar_combinaciones(acc: Acciones, s: dict, gamma: float):
    """
    Lista de combinaciones. Cada una:
      {nombre, formula, fac:{CP,CV,SH,SV}, srss:bool}
    Con sobrerresistencia (§8.3.2.2): SH → (Ω0·ρ)·SH.
    """
    incluir_sismo = acc.sismo.get("incluir_sismo", True)
    incluir_sv = incluir_sismo and acc.sismo.get("incluir_sv", True)
    omega_r = 1.0
    etiqueta_sh = "SH"
    if incluir_sismo and acc.sismo.get("sobrerresistencia", False):
        omega_r = s["Omega"] * acc.sismo.get("rho_redundancia", 1.0)
        etiqueta_sh = f"(Ω₀ρ)·SH"

    fsh = omega_r if incluir_sismo else 0.0
    fsv = 1.0 if incluir_sv else 0.0

    combos = []
    if incluir_sismo:
        sv_p = " + 0,3·SV" if incluir_sv else ""
        sv_n = " − 0,3·SV" if incluir_sv else ""
        sh_srss = f"(Ω₀ρ)·SH" if omega_r != 1.0 else "SH"
        combos += [
            {"nombre": "8.6 (+)", "formula": f"U = 1,2·CP + {gamma:g}·CV + {etiqueta_sh}{sv_p}",
             "fac": {"CP": 1.2, "CV": gamma, "SH": +fsh, "SV": +0.3 * fsv}, "srss": False},
            {"nombre": "8.6 (−)", "formula": f"U = 1,2·CP + {gamma:g}·CV − {etiqueta_sh}{sv_p}",
             "fac": {"CP": 1.2, "CV": gamma, "SH": -fsh, "SV": +0.3 * fsv}, "srss": False},
            {"nombre": "8.7 (+)", "formula": f"U = 0,9·CP + {etiqueta_sh}{sv_n}",
             "fac": {"CP": 0.9, "CV": 0.0, "SH": +fsh, "SV": -0.3 * fsv}, "srss": False},
            {"nombre": "8.7 (−)", "formula": f"U = 0,9·CP − {etiqueta_sh}{sv_n}",
             "fac": {"CP": 0.9, "CV": 0.0, "SH": -fsh, "SV": -0.3 * fsv}, "srss": False},
            {"nombre": "8.9 (+)", "formula": f"U = 1,2·CP + {gamma:g}·CV + S   (S = √(SH²+SV²))",
             "fac": {"CP": 1.2, "CV": gamma, "SH": fsh, "SV": fsv}, "srss": True},
            {"nombre": "8.9 (−)", "formula": f"U = 1,2·CP + {gamma:g}·CV − S   (S = √(SH²+SV²))",
             "fac": {"CP": 1.2, "CV": gamma, "SH": -fsh, "SV": -fsv}, "srss": True},
            {"nombre": "8.10 (+)", "formula": f"U = 0,9·CP + S   (S = √(SH²+SV²))",
             "fac": {"CP": 0.9, "CV": 0.0, "SH": fsh, "SV": fsv}, "srss": True},
            {"nombre": "8.10 (−)", "formula": f"U = 0,9·CP − S   (S = √(SH²+SV²))",
             "fac": {"CP": 0.9, "CV": 0.0, "SH": -fsh, "SV": -fsv}, "srss": True},
        ]
    else:
        combos += [
            {"nombre": "1,4·CP", "formula": "U = 1,4·CP",
             "fac": {"CP": 1.4, "CV": 0.0, "SH": 0.0, "SV": 0.0}, "srss": False},
            {"nombre": "1,2·CP+γ·CV", "formula": f"U = 1,2·CP + {gamma:g}·CV",
             "fac": {"CP": 1.2, "CV": gamma, "SH": 0.0, "SV": 0.0}, "srss": False},
        ]
    return combos


# ------------------------------------------------------------------
# Evaluación y envolvente
# ------------------------------------------------------------------
def _valores_caso(res_caso: dict) -> dict:
    """Extrae los valores con signo por barra/nudo/reacción de un caso."""
    barras = {}
    for b in res_caso["barras"]:
        dg = res_caso["diagramas"].get(b["id"])
        m_arr = dg["M"] if dg else [0.0]
        barras[b["id"]] = {
            "Ni": b["Ni"], "Nj": b["Nj"],
            "Vi": b["Vi"], "Vj": b["Vj"],
            "Mi": b["Mi"], "Mj": b["Mj"],
            "Mmax": float(max(m_arr)), "Mmin": float(min(m_arr)),
        }
    nudos = {n["id"]: {"ux": n["ux"], "uy": n["uy"]} for n in res_caso["nudos"]}
    reacc = {f"{r['nudo']}:{r['comp']}": r["valor"] for r in res_caso["reacciones"]}
    return {"barras": barras, "nudos": nudos, "reacciones": reacc}


def evaluar_combo(val_casos: dict, combo: dict) -> dict:
    """
    Valores de la combinación por superposición:
      v = Σ f_caso · v_caso      (lineal)
      SRSS: v_sismo = signo·√(SH²+SV²) con el signo del efecto dominante
    """
    fac = combo["fac"]
    out = {"barras": {}, "nudos": {}, "reacciones": {}}
    if combo.get("srss"):
        def combinar(sh, sv):
            base = sh if abs(sh) >= abs(sv) else sv
            return 0.0 if (sh == 0 and sv == 0) else math.copysign(
                math.sqrt(sh * sh + sv * sv), base if base != 0 else 1.0)
    else:
        def combinar(sh, sv):
            return sh + sv

    claves_b = set()
    for c in val_casos.values():
        claves_b |= set(c["barras"].keys())
    for bid in claves_b:
        fila = {}
        for q in ("Ni", "Nj", "Vi", "Vj", "Mi", "Mj", "Mmax", "Mmin"):
            sh = fac.get("SH", 0.0) * val_casos.get("SH", {"barras": {}})["barras"].get(bid, {}).get(q, 0.0)
            sv = fac.get("SV", 0.0) * val_casos.get("SV", {"barras": {}})["barras"].get(bid, {}).get(q, 0.0)
            lin = (fac.get("CP", 0.0) * val_casos.get("CP", {"barras": {}})["barras"].get(bid, {}).get(q, 0.0)
                   + fac.get("CV", 0.0) * val_casos.get("CV", {"barras": {}})["barras"].get(bid, {}).get(q, 0.0))
            fila[q] = lin + combinar(sh, sv)
        out["barras"][bid] = fila

    claves_n = set()
    for c in val_casos.values():
        claves_n |= set(c["nudos"].keys())
    for nid in claves_n:
        fila = {}
        for q in ("ux", "uy"):
            sh = fac.get("SH", 0.0) * val_casos.get("SH", {"nudos": {}})["nudos"].get(nid, {}).get(q, 0.0)
            sv = fac.get("SV", 0.0) * val_casos.get("SV", {"nudos": {}})["nudos"].get(nid, {}).get(q, 0.0)
            lin = (fac.get("CP", 0.0) * val_casos.get("CP", {"nudos": {}})["nudos"].get(nid, {}).get(q, 0.0)
                   + fac.get("CV", 0.0) * val_casos.get("CV", {"nudos": {}})["nudos"].get(nid, {}).get(q, 0.0))
            fila[q] = lin + combinar(sh, sv)
        out["nudos"][nid] = fila

    claves_r = set()
    for c in val_casos.values():
        claves_r |= set(c["reacciones"].keys())
    for rk in claves_r:
        sh = fac.get("SH", 0.0) * val_casos.get("SH", {"reacciones": {}})["reacciones"].get(rk, 0.0)
        sv = fac.get("SV", 0.0) * val_casos.get("SV", {"reacciones": {}})["reacciones"].get(rk, 0.0)
        lin = (fac.get("CP", 0.0) * val_casos.get("CP", {"reacciones": {}})["reacciones"].get(rk, 0.0)
               + fac.get("CV", 0.0) * val_casos.get("CV", {"reacciones": {}})["reacciones"].get(rk, 0.0))
        out["reacciones"][rk] = lin + combinar(sh, sv)

    return out


def envolvente(evals: list) -> dict:
    """
    evals = [{nombre, barras, nudos, reacciones}, …]
    Devuelve min/max + combinación que gobierna cada extremo.
    """
    env = {"barras": {}, "nudos": {}, "reacciones": {}}

    def empujar(dic, clave, q, v, nombre):
        e = dic.setdefault(clave, {})
        e.setdefault(q, {"min": None, "max": None, "cmin": "", "cmax": ""})
        if e[q]["min"] is None or v < e[q]["min"]:
            e[q]["min"] = v; e[q]["cmin"] = nombre
        if e[q]["max"] is None or v > e[q]["max"]:
            e[q]["max"] = v; e[q]["cmax"] = nombre

    for ev in evals:
        for bid, fila in ev["barras"].items():
            for q, v in fila.items():
                empujar(env["barras"], bid, q, v, ev["nombre"])
        for nid, fila in ev["nudos"].items():
            for q, v in fila.items():
                empujar(env["nudos"], nid, q, v, ev["nombre"])
        for rk, v in ev["reacciones"].items():
            empujar(env["reacciones"], rk, "valor", v, ev["nombre"])
    return env


# ------------------------------------------------------------------
# Orquestador
# ------------------------------------------------------------------
def analizar_con_combinaciones(modelo_dict: dict, acciones_dict: dict) -> dict:
    modelo = Modelo.desde_dict(modelo_dict)
    acc = Acciones.desde_dict(acciones_dict)

    incluir_sismo = acc.sismo.get("incluir_sismo", True)
    s = {}
    ys, W, _nivel_de = pesos_por_nivel(modelo, acc)
    if incluir_sismo:
        if not ys or sum(W) <= 0:
            raise ERROR("El peso sísmico W es cero: define cargas CP por barra "
                        "o nodales antes de calcular el sismo.")
        # los niveles sin peso (p. ej. la base y=0) no cuentan para N/hi
        pares = [(y, w) for y, w in zip(ys, W) if w > 1e-9]
        ys_f = [y for y, _ in pares]
        W_f = [w for _, w in pares]
        p = {**acc.sismo, "N": len(ys_f), "hs_abs": ys_f, "W": W_f}
        s = cov.calcular_sismo(p)
        s["_clase"] = acc.sismo.get("sitio", "CD")
        s["_niveles_filtrados"] = ys_f

    # casos y resultados por caso
    casos, csv_v = construir_casos(modelo, acc, s)
    res_casos = {}
    for nombre, m in casos.items():
        res_casos[nombre] = analizar(m)

    gamma = gamma_de(modelo, acc)
    combos = generar_combinaciones(acc, s, gamma)

    val_casos = {k: _valores_caso(v) for k, v in res_casos.items()}
    evals = []
    for c in combos:
        ev = evaluar_combo(val_casos, c)
        ev["nombre"] = c["nombre"]
        evals.append(ev)
    env = envolvente(evals)

    fi_map = dict(zip(s.get("_niveles_filtrados", []), s.get("Fis", [])))
    return {
        "ok": True,
        "gamma": gamma,
        "csv": csv_v,
        "sismo": {k: v for k, v in s.items()
                  if k != "Ad" and not k.startswith("_")},
        "espectro": cov.curva_espectro(s) if incluir_sismo else [],
        "niveles": [{"y": y, "W": w, "Fi": fi_map.get(y, 0.0)}
                    for y, w in zip(ys, W)],
        "combos": combos,
        "envolvente": env,
        "casos_ok": {k: v["ok"] for k, v in res_casos.items()},
        "avisos": [a for v in res_casos.values() for a in v.get("avisos", [])],
    }
