# ==================================================================
#  covenin1756.py — Motor sísmico COVENIN 1756-1:2019 (PORT)
#  ------------------------------------------------------------------
#  Port fiel a Python del motor AUDITADO del repo
#  (ACERO/calculadora-sismica/js/covenin1756.js), verificado
#  numéricamente contra la norma:
#
#   · espectro inelástico Ad(T)      → fórmulas 7.18–7.23
#   · μ                              → fórmula 9.4
#   · V0 = C·W, Cdin vs Cmin         → ec. 9.1 y §9.2.2
#   · Ta = Ct·hn^0.75                → §9.4.3.3 + Tabla 24
#   · Ft = (0.06·T/TC − 0.02)·V0d    → fórmula 9.10, acotada [4 %, 10 %]
#   · Fi = (V0d−Ft)·Wi·hi/Σ(Wj·hj)   → fórmula 9.11
#   · σ (Tabla 23), q (Tabla 17), factores de sitio (Tablas 8–13),
#     α (Tabla 14), R/Cd/Ω0 (Tabla 15, pórticos de acero RM),
#     fracciones de CV (Tabla 20)
#   · Componente vertical: CSV = β·AA·γmáx·η0 → fórmulas 8.4–8.5
#     con Tabla 19 (β = 2,3 según texto de §11.4)
#
#  VERIFICACIÓN DEL PORT (tests_combinaciones.py):
#  los valores se comparan contra la salida del JS auditado para el
#  caso de referencia (A0=0.21, A1=0.18, TL=3.9, B2/ND3/CD, 2 niveles).
# ==================================================================

import math

# ---------------- Tablas normativas ----------------

CLASES = ["A", "AB", "B", "BC", "C", "CD", "D", "DE", "E"]
AXS = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5]     # eje de A0/A1 (Tabla 14 de mapa)

# Tabla 8 — Factor de sitio FA (fijo) vs α·A0
TAB8 = {
    "A":  [0.80, 0.80, 0.80, 0.80, 0.80, 0.80, 0.80],
    "AB": [0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85],
    "B":  [0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 0.90],
    "BC": [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
    "C":  [1.30, 1.30, 1.25, 1.25, 1.20, 1.20, 1.15],
    "CD": [1.60, 1.50, 1.45, 1.35, 1.25, 1.20, 1.15],
    "D":  [1.90, 1.75, 1.60, 1.40, 1.25, 1.15, 1.00],
    "DE": [2.40, 2.05, 1.75, 1.35, 1.10, 0.95, 0.80],
    "E":  [2.70, 2.20, 1.85, 1.35, 1.00, 0.85, 0.70],
}

# Tabla 9 — Factor de sitio FV (flexible) vs α·A1
TAB9 = {
    "A":  [0.80, 0.80, 0.80, 0.80, 0.80, 0.80, 0.80],
    "AB": [0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85],
    "B":  [0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 0.90],
    "BC": [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
    "C":  [1.40, 1.40, 1.40, 1.40, 1.40, 1.40, 1.40],
    "CD": [1.80, 1.75, 1.75, 1.70, 1.70, 1.65, 1.65],
    "D":  [2.30, 2.20, 2.10, 2.00, 1.95, 1.90, 1.85],
    "DE": [3.30, 3.00, 2.70, 2.50, 2.30, 2.15, 2.00],
    "E":  [4.00, 3.30, 3.00, 2.70, 2.45, 2.30, 2.15],
}

# Tabla 10 — Factor de sitio FD (desplazamiento)
TAB10 = {"A": 0.85, "AB": 0.90, "B": 0.95, "BC": 1.00, "C": 1.20,
         "CD": 1.40, "D": 1.70, "DE": 2.25, "E": 2.65}

# Tabla 11 — Factores topográficos [FAT, FVT, FDT]
TAB11 = {"leve": [1.00, 1.00, 1.00],
         "mod":  [1.20, 1.10, 1.05],
         "sev":  [1.40, 1.20, 1.10]}

# Tablas 12–13 — Factores de profundidad del basamento (H en m)
TAB12H = [0, 10, 30, 60, 100, 200, 300, 500, 750, 1000]
TAB12 = {
    "FAH": [1.00, 1.00, 1.00, 1.01, 1.02, 1.03, 1.05, 1.07, 1.10],
    "FVH": [0.98, 1.00, 1.00, 1.02, 1.05, 1.08, 1.10, 1.20, 1.30],
    "FDH": [0.93, 0.96, 1.00, 1.05, 1.10, 1.20, 1.30, 1.60, 2.10],
}

# Tabla 17 — Exponente q de la rama TD < T
TABQ = {"A": 1.5, "AB": 1.5, "B": 1.5, "BC": 1.7, "C": 1.7,
        "CD": 1.9, "D": 1.9, "DE": 2.0, "E": 2.0}

# Tabla 14 — Factor de importancia de uso α
ALFA = {"A1": 2.0, "A2": 1.5, "B1": 1.2, "B2": 1.0, "C": 0.7}

# Tabla 15 — Pórticos de acero Resistentes a Momento
R_ACERO = {"ND3": 6, "ND2": 3.5, "ND1": 2.5}
CD_ACERO = {"ND3": 4.25, "ND2": 3.25, "ND1": 2.25}
OMEGA_ACERO = {"ND3": 3, "ND2": 2.5, "ND1": 2}

# Tabla 19 — Parámetros del espectro vertical (verificada en el PDF, pág. 89)
#   clase → (γ0, γmáx, γmín, TCV[s], η0, ηc)  con η0/ηc funciones de α·A0
TAB19 = {
    "A":  (0.7, 1.0, 0.42, 0.2), "AB": (0.7, 1.0, 0.42, 0.2),
    "B":  (0.7, 1.0, 0.42, 0.2), "BC": (0.7, 1.0, 0.42, 0.2),
    "C":  (0.8, 1.3, 0.36, 0.3), "CD": (0.8, 1.3, 0.36, 0.3),
    "D":  (0.9, 1.6, 0.30, 0.4), "DE": (0.9, 1.6, 0.30, 0.4),
    "E":  (0.9, 1.6, 0.30, 0.4),
}

# Tabla 20 — Fracción de la carga variable para el peso sísmico
FRACC_CV = {"vivienda": 0.15, "oficina": 0.25, "comercio": 0.25,
            "agrupacion": 0.50, "estacionamiento": 0.50, "almacen": 0.80,
            "recipientes": 1.00, "ascensor": 1.00, "techo": 0.00}


def interp(ax, clase, tabla):
    """Interpolación lineal sobre el eje de α·A0 / α·A1 (Tablas 8–9)."""
    arr = tabla[clase]
    if ax <= AXS[0]:
        return arr[0]
    if ax >= AXS[-1]:
        return arr[-1]
    i = 0
    while i < len(AXS) - 2 and ax > AXS[i + 1]:
        i += 1
    t = (ax - AXS[i]) / (AXS[i + 1] - AXS[i])
    return arr[i] + t * (arr[i + 1] - arr[i])


def interp_h(x, col):
    """Interpolación sobre la profundidad H (Tablas 12–13)."""
    arr = TAB12[col]
    if x <= TAB12H[0]:
        return arr[0]
    for i in range(len(TAB12H) - 1):
        if TAB12H[i] <= x <= TAB12H[i + 1]:
            t = (x - TAB12H[i]) / (TAB12H[i + 1] - TAB12H[i])
            return arr[i] + t * (arr[i + 1] - arr[i])
    return arr[-1]


def tabla19(clase, a_a0):
    """Tabla 19 → (γmáx, η0, ηc, TCV) con η dependientes de α·A0."""
    g0, gmax, gmin, tcv = TAB19[clase]
    if clase in ("A", "AB", "B", "BC"):
        e0 = 0.85 + 0.5 * a_a0
        ec = 1.45 - 1.5 * a_a0
    elif clase in ("C", "CD"):
        e0 = 0.7 + a_a0
        ec = 1.36 - 1.2 * a_a0
    else:
        e0 = 0.55 + 1.5 * a_a0
        ec = 1.3 - a_a0
    return gmax, e0, ec, tcv


def csv_vertical(aa, clase, a_a0, beta=2.3):
    """CSV = β·AA·γmáx·η0  (fórmulas 8.4–8.5; β = 2,3 según §11.4)."""
    gmax, e0, _ec, _tcv = tabla19(clase, a_a0)
    return beta * aa * gmax * e0


# ------------------------------------------------------------------
# Motor sísmico (estático equivalente) — port de calcularSismo()
# ------------------------------------------------------------------
def calcular_sismo(p: dict) -> dict:
    """
    p = {
      A0, A1, TL,                # mapas 4.1–4.3
      grupo ('B2'…), nd ('ND3'…),
      sitio ('CD'…), topo ('leve'…), H, rho (amortiguamiento §7.3.4),
      FI (§6.4),
      N (nº de niveles), hs_abs ([altura acumulada por nivel, asc]),
      W ([peso sísmico por nivel, kg]),
      ct (Tabla 24, default 0.08 acero P-RM)
    }
    Devuelve dict con todos los parámetros intermedios (auditables) y
    la función Ad(T) para el gráfico del espectro.
    """
    R = R_ACERO.get(p.get("nd", "ND3"), 6)
    Cd = CD_ACERO.get(p.get("nd", "ND3"), 4.25)
    Omega = OMEGA_ACERO.get(p.get("nd", "ND3"), 3)
    alpha = ALFA.get(p.get("grupo", "B2"), 1.0)

    # Factores de sitio (Tablas 8–13)
    a_a0 = alpha * p["A0"]
    a_a1 = alpha * p["A1"]
    cl = p.get("sitio", "CD")
    fac = interp(a_a0, cl, TAB8)
    fvc = interp(a_a1, cl, TAB9)
    fdc = TAB10[cl]
    fat, fvt, fdt = TAB11.get(p.get("topo", "leve"), TAB11["leve"])
    fah = interp_h(p.get("H", 0), "FAH")
    fvh = interp_h(p.get("H", 0), "FVH")
    fdh = interp_h(p.get("H", 0), "FDH")
    fa = fac * fah * fat
    fv = fvc * fvh * fvt
    fd = fdc * fdh * fdt

    # Aceleraciones de diseño (§7.2)
    AA = fa * alpha * p["A0"]
    AV = fv * alpha * p["A1"]

    # Ramas del espectro: TA ≤ TB ≤ TC ≤ TD
    beta = 2.4
    beta_s = max(beta, AV / AA) if AA > 0 else beta
    TC = (1 / beta) * (AV / AA) if AA > 0 else 0.5
    TB = 0.25 * TC
    TA = min(0.05, max(0.02, 0.2 * TB))
    TD = p["TL"] * (fd / fv) if fv > 0 else p["TL"]
    q = TABQ[cl]

    # Período fundamental Ta (§9.4.3.3 + Tabla 24) y límite σ·Ta (Tabla 23)
    hn = p["hs_abs"][-1]
    ct = p.get("ct", 0.08)
    Ta = ct * hn ** 0.75
    T = Ta
    sigma = 1.7 if AA <= 0.10 else (1.55 if AA <= 0.20 else 1.4)
    Tmax = sigma * Ta

    # Punto de quiebre T⁺ de la meseta elástica (fórmula 7.23)
    Tp = 0.4 if R >= 5 else 0.1 * (R - 1)
    Tp = min(TC, max(0.25 * TC, Tp))

    rho_am = p.get("rho", 1.0)
    fi = p.get("FI", 1.0)

    # Espectro inelástico de pseudoaceleraciones Ad(T) (7.18–7.23)
    def Ad(tx):
        if tx <= TA:
            return rho_am * fi * AA / 1.5
        if tx <= Tp:
            return rho_am * fi * (AA / 1.5) * (
                1 + ((tx - TA) / (Tp - TA)) * ((beta_s / R) / (1 / 1.5) - 1))
        if tx <= TC:
            return rho_am * fi * (beta_s * AA) / R
        if tx <= TD:
            return rho_am * fi * (beta_s * AA / R) * (TC / tx)
        return rho_am * fi * (beta_s * AA / R) * (TC / TD) * (TD / tx) ** q

    ad_t = Ad(T)

    # Coeficiente sísmico C = μ·Ad (9.3–9.4)
    n_niv = p["N"]
    mu1 = 1.4 * (n_niv + 9) / (2 * n_niv + 12)
    mu2 = 0.80 + (1 / 20) * (T / TC - 1) if TC > 0 else 0.80
    mu = max(mu1, mu2)
    C = mu * ad_t

    # Coeficiente mínimo Cmin = AA/R (§9.2.2) y cortante de diseño
    Cmin = AA / R
    w_tot = sum(p["W"])
    V0 = C * w_tot
    escala = (Cmin / C) if (C < Cmin and C > 0) else 1.0
    V0d = V0 * escala

    # Fuerza de tope Ft (9.10): 4 % ≤ coef ≤ 10 % de V0d
    coef_ft = min(0.10, max(0.04, 0.06 * T / TC - 0.02)) if TC > 0 else 0.04
    Ft = coef_ft * V0d
    v_eff = V0d - Ft

    # Distribución de fuerzas por nivel (9.11): Fi = (V0d−Ft)·Wi·hi/Σ(Wj·hj)
    wh = [w * h for w, h in zip(p["W"], p["hs_abs"])]
    sum_wh = sum(wh)
    fis = [v_eff * w / sum_wh for w in wh] if sum_wh > 0 else [0.0] * n_niv

    # Cortante de entrepiso (el superior incluye Ft — corrección auditada)
    v_pisos = [0.0] * n_niv
    for i in range(n_niv - 1, -1, -1):
        v_pisos[i] = (Ft if i == n_niv - 1 else v_pisos[i + 1]) + fis[i]

    return {
        "R": R, "Cd": Cd, "Omega": Omega, "alpha": alpha, "aA0": a_a0, "aA1": a_a1,
        "FAC": fac, "FVC": fvc, "FDC": fdc, "FAH": fah, "FVH": fvh, "FDH": fdh,
        "FAT": fat, "FVT": fvt, "FDT": fdt, "FA": fa, "FV": fv, "FD": fd,
        "AA": AA, "AV": AV, "betaS": beta_s, "TA": TA, "TB": TB, "TC": TC,
        "TD": TD, "q": q, "hn": hn, "Ta": Ta, "T": T, "Tmax": Tmax,
        "sigma": sigma, "Tp": Tp, "AdT": ad_t, "mu": mu, "C": C, "Cmin": Cmin,
        "Wtot": w_tot, "V0": V0, "escala": escala, "V0d": V0d,
        "coefFt": coef_ft, "Ft": Ft, "Veff": v_eff, "Fis": fis,
        "Vpisos": v_pisos, "Ad": Ad,
    }


def curva_espectro(s: dict, n_pts=240):
    """Muestreo del espectro Ad(T) para el gráfico."""
    pts = []
    t_fin = max(s["TD"] * 1.05, s["TC"] * 3)
    for k in range(n_pts + 1):
        tx = t_fin * k / n_pts
        pts.append({"T": tx, "Ad": s["Ad"](tx)})
    return pts
