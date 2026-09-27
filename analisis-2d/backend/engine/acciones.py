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
# Memoria de cálculo (modo aprendizaje): cada paso = fórmula +
# sustitución con los valores reales + fuente + porqué
# ------------------------------------------------------------------
def _f(x, dec=2):
    """1234.5 → '1.234,5' (sin miles para no liar copiado: '1234,5')."""
    t = "%.*f" % (dec, float(x))
    if "." in t:
        t = t.rstrip("0").rstrip(".")
    return t.replace(".", ",")


def construir_memoria(modelo, acc, s, ys, W, gamma, csv_v, combos,
                      incluir_sismo):
    M = []

    def sec(nombre):
        d = {"seccion": nombre, "pasos": []}
        M.append(d)
        return d["pasos"]

    def paso(sc, formula, sustitucion="", resultado="", fuente="", porque=""):
        sc.append({"formula": formula, "sustitucion": sustitucion,
                   "resultado": str(resultado), "fuente": fuente,
                   "porque": porque})

    sz = acc.sismo

    # ── 1 · Peso sísmico W por nivel ──
    s1 = sec("1 · Peso sísmico W por nivel")
    fcv = sz.get("fraccion_cv", 0.25)
    paso(s1, "CV_sísmico = frac · CV",
         "frac = " + _f(fcv) + " (fracción de CV presente durante el sismo)",
         _f(fcv),
         "COVENIN 1756:2019 · Tabla 20",
         "No toda la carga variable está presente cuando ocurre el sismo; "
         "la norma la fracciona según el uso del edificio (oficinas 0,25).")
    _ys, _W, nivel_de = pesos_por_nivel(modelo, acc)
    aporte = {y: 0.0 for y in _ys}
    nb = {y: 0 for y in _ys}
    for b in modelo.barras:
        ni, nj = modelo.nudo(b.ni), modelo.nudo(b.nj)
        L = math.hypot(nj.x - ni.x, nj.y - ni.y)
        if L <= 0:
            continue
        w = (acc.barra_cp.get(b.id, 0.0)
             + acc.barra_cv.get(b.id, 0.0) * fcv
             + (b.A * 1e-4 * _GAMMA_ACERO if b.peso_propio else 0.0))
        wmed = w * L / 2.0
        aporte[nivel_de[ni.id]] += wmed
        aporte[nivel_de[nj.id]] += wmed
        nb[nivel_de[ni.id]] += 1
        nb[nivel_de[nj.id]] += 1
    for y, w in zip(_ys, _W):
        if w <= 1e-9:
            continue
        paso(s1, "W_i = Σ_b (CP + frac·CV + pp) · L / 2",
             "Nivel y=" + _f(y) + " m: " + str(nb[y]) + " barras aportando → W = "
             + _f(w) + " kg",
             _f(w) + " kg",
             "COVENIN 1756:2019 · §9.4",
             "El sismo estático equivalente usa el peso de cada nivel: 100% de "
             "la carga permanente + fracción de la variable. Cada barra reparte "
             "la mitad de su carga a cada extremo.")
    paso(s1, "W_total = Σ W_i", "Σ de " + str(len([w for w in W if w > 1e-9]))
         + " niveles con peso", _f(sum(W)) + " kg",
         "COVENIN 1756:2019 · §9.4",
         "El peso total entra en el cortante base de diseño V0 = C·W_total.")

    if incluir_sismo and s:
        # ── 2 · Parámetros del sismo ──
        s2 = sec("2 · Parámetros del sismo (COVENIN 1756:2019)")
        paso(s2, "R, Cd, Ω según sistema estructural",
             "nd = " + sz.get("nd", "ND3") + " (acero P-RM) → R = "
             + _f(s.get("R", 0), 0) + " · Cd = " + _f(s.get("Cd", 0))
             + " · Ω₀ = " + _f(s.get("Omega", 0), 0),
             "R = " + _f(s.get("R", 0), 0),
             "COVENIN 1756:2019 · Tablas 14–16",
             "R reduce el espectro elástico a inelástico: la estructura disipa "
             "energía mediante ductilidad.")
        paso(s2, "AA = FA · α · A0",
             "FA = " + _f(s.get("FA", 1)) + " (sitio " + sz.get("sitio", "CD")
             + ") · α = " + _f(s.get("alpha", 1)) + " (grupo "
             + sz.get("grupo", "B2") + ") · A0 = " + _f(sz.get("A0", 0)),
             "AA = " + _f(s.get("AA", 0), 3),
             "COVENIN 1756:2019 · §7.2, Tablas 4–11",
             "La aceleración horizontal de diseño parte del mapa de amenaza "
             "sísmica (zona) y se corrige por el tipo de suelo y la topografía.")
        hn = s.get("hn", 0.0)
        ct = sz.get("ct", 0.08)
        paso(s2, "Ta = ct · hn^0,75",
             "ct = " + _f(ct) + " (Tabla 24, acero P-RM) · hn = " + _f(hn)
             + " m",
             "Ta = " + _f(s.get("Ta", 0), 3) + " s  (límite σ·Ta = "
             + _f(s.get("Tmax", 0), 3) + " s)",
             "COVENIN 1756:2019 · §9.4.3.3 + Tabla 23–24",
             "Período fundamental estimado de la estructura; con el nivel de "
             "amenaza se limita (σ) para no sub-diseñar estructuras flexibles.")
        paso(s2, "C = μ · Ad(T)  ·  Cmín = AA / R",
             "μ = " + _f(s.get("mu", 0)) + " · Ad(T=" + _f(s.get("T", 0), 3)
             + " s) = " + _f(s.get("AdT", 0), 4) + " → C = " + _f(s.get("C", 0), 4)
             + " · Cmín = " + _f(s.get("Cmin", 0), 4)
             + ("  (escala ×" + _f(s.get("escala", 1), 3) if s.get("escala", 1) != 1.0 else ""),
             "V0 = C·W = " + _f(s.get("V0", 0)) + " kg → V0d = " + _f(s.get("V0d", 0)) + " kg",
             "COVENIN 1756:2019 · §9.2–9.4 (fórmulas 9.3–9.4)",
             "El coeficiente sísmico base C convierte el peso en cortante; si C "
             "queda por debajo del mínimo AA/R se escala el cortante (V0d).")
        paso(s2, "Ft = k · V0d,  k = 0,06·T/TC − 0,02 (4% ≤ k ≤ 10%)",
             "T = " + _f(s.get("T", 0), 3) + " s · TC = " + _f(s.get("TC", 0), 3)
             + " s → k = " + _f(s.get("coefFt", 0), 3),
             "Ft = " + _f(s.get("Ft", 0)) + " kg",
             "COVENIN 1756:2019 · (9.10)",
             "Fuerza de tope: compensa el efecto de los modos superiores que el "
             "modelo de un solo grado de libertad por nivel no captura.")
        wh = [(w, h) for w, h in zip(W, s.get("_niveles_filtrados", [])[:0] or _ys)
              if w > 1e-9]
        fis = s.get("Fis", [])
        ys_f = [y for y, w in zip(_ys, _W) if w > 1e-9]
        for y, w, fi in zip(ys_f, [w for w in W if w > 1e-9], fis):
            paso(s2, "F_i = (V0d − Ft) · W_i·h_i / Σ(W_j·h_j)",
                 "y=" + _f(y) + " m: (" + _f(s.get("V0d", 0)) + " − "
                 + _f(s.get("Ft", 0)) + ") × " + _f(w) + "×" + _f(y)
                 + " / Σ(W·h)",
                 "F" + _f(y, 1) + " = " + _f(fi) + " kg",
                 "COVENIN 1756:2019 · (9.11)",
                 "Distribución lineal del cortante: el nivel con más peso y más "
                 "altura recibe mayor fuerza (aceleración de primer modo).")
        if csv_v:
            paso(s2, "CSV = β · AA · γ_máx · E0",
                 "β = 2,3 · AA = " + _f(s.get("AA", 0), 3) + " · γ_máx = 3,0 · E0 = 1,0",
                 "CSV = " + _f(csv_v, 3) + "  →  SV = CSV·CP",
                 "COVENIN 1756:2019 · §8.3.1.4 (8.4–8.5)",
                 "El sismo vertical agita la masa en la dirección de gravedad; "
                 "se expresa como fracción del peso permanente (efecto elástico "
                 "sin ductilidad, por eso β=2,3).")

    # ── 3 · γ y combinaciones ──
    s3 = sec("3 · γ de la carga variable y combinaciones")
    if incluir_sismo:
        cvs = [v for v in acc.barra_cv.values() if v > 0]
        paso(s3, "γ = 0,5 si CV < 500 kgf/m² · γ = 1 en los demás casos",
             ("CV máx = " + _f(max(cvs), 2) + " kg/m " if cvs else "")
             + ("→ γ = " + _f(gamma, 1) if cvs else "sin CV → γ = " + _f(gamma, 1)),
             "γ = " + _f(gamma, 1),
             "COVENIN 1756:2019 · §8.3.2.b",
             "Cuando la carga variable es liviana (< 500 kgf/m², salvo reunión "
             "pública o estacionamiento), es improbable que esté completa "
             "justo cuando ocurre el sismo: se reduce al 50%.")
    porque_combo = {
        "8.6": "Gravedad mayorada con sismo horizontal y 30% del vertical: "
               "combinación de resistencia usual.",
        "8.7": "Con CP al 90% se verifica volteo y tracción en columnas: la "
               "permanente mínima es la desfavorable para esos efectos.",
        "8.9": "SH y SV se combinan por raíz de la suma de cuadrados (8.8) "
               "porque son efectos independientes entre sí.",
        "8.10": "Igual que 8.7 pero con el sismo combinado por SRSS (8.8).",
        "1,4": "Solo gravedad mayorada (sismo desactivado): combinación básica "
               "de resistencia.",
        "1,2": "Gravedad mayorada con carga variable a tope (γ según §8.3.2.b).",
    }
    for c in combos:
        clave = c["nombre"].split(" ")[0].replace(",", ",")
        pq = porque_combo.get(clave, "")
        paso(s3, c["formula"],
             "factores: CP×" + _f(c["fac"]["CP"], 1) + " · CV×"
             + _f(c["fac"]["CV"], 1) + " · SH×" + _f(c["fac"]["SH"], 1)
             + " · SV×" + _f(c["fac"]["SV"], 2),
             "", "COVENIN 1756:2019 · (" + c["nombre"] + ")", pq)

    # ── 4 · Evaluación ──
    s4 = sec("4 · Evaluación y envolvente")
    paso(s4, "U = Σ (factor × caso) por superposición",
         "los casos CP, CV, SH y SV se resuelven una vez con el solver de "
         "rigideces 2D y se combinan linealmente",
         "envolvente por barra/nudo/reacción",
         "Principio de superposición (comportamiento elástico lineal)",
         "La envolvente guarda, en cada extremo de barra, el peor efecto (M, "
         "V, N) y qué combinación lo gobierna: es lo que después dimensiona "
         "el acero o el concreto.")
    return M


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
    memoria = construir_memoria(modelo, acc, s, ys, W, gamma, csv_v,
                                combos, incluir_sismo)
    return {
        "ok": True,
        "memoria": memoria,
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
