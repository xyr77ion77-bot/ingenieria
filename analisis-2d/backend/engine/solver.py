# ==================================================================
#  solver.py — Motor de análisis: método matricial de rigideces
#  ------------------------------------------------------------------
#  Pórtico plano · 3 GDL por nudo (ux, uy, θz) · análisis elástico
#  de primer orden (lineal, sin P-Δ).
#
#  PROCEDIMIENTO
#    1. K_local 6×6 de elemento marco (axial + flexión).
#    2. Transformación T(α) → K_global del elemento = Tᵀ·k·T.
#    3. Ensamblaje K(3N×3N) y vector F:
#         F = cargas nodales + cargas equivalentes de las barras (−Tᵀ·FEF)
#           + peso propio (si está activo, como q_perp y q_axial).
#    4. Partición por GDL libres/restringidos → U_libres = K_ff⁻¹·F_f.
#    5. Reacciones R = K_cf·U_f − F_c.
#    6. Fuerzas de extremo por barra: f = k·T·U_e + FEF.
#    7. Diagramas internos N(x), V(x), M(x) por equilibrio del cuerpo
#       libre [0, x] (ver convención más abajo).
#
#  CONVENCIÓN DE RESULTADOS INTERNOS (la que dibuja la UI):
#    · N(x)  positivo = TRACCIÓN.
#    · V(x)  positivo = par horario (convención clásica). En viga
#              horizontal con carga de gravedad ↓: V(0) = +wL/2,
#              V(L) = −wL/2.
#    · M(x)  positivo = FLEXIÓN SIMPLE (tracción en la fibra −y
#              local para viga horizontal = fibra inferior).
#              Carga de gravedad ↓ en viga biapoyada: M ≈ +wL²/8.
#
#  VERIFICACIONES AUTOMÁTICAS (tests_engine.py):
#    viga simple, voladizo, viga continua de 2 tramos, pórtico con
#    carga lateral — contra fórmulas cerradas de la teoría.
# ==================================================================

import math
import numpy as np

from .modelo import ERROR, Modelo

# Conversiones de unidades hacia el sistema interno coherente
# (kg, m): E[kg/cm²]→kg/m² ·10⁴ | A[cm²]→m² ·10⁻⁴ | I[cm⁴]→m⁴ ·10⁻⁸
_K_E = 1.0e4
_K_A = 1.0e-4
_K_I = 1.0e-8
_GAMMA_ACERO = 7850.0   # kg/m³ (peso propio de perfiles de acero)

N_PUNTOS_DIAGRAMA = 25   # puntos por barra para los diagramas


# ------------------------------------------------------------------
# Elemento
# ------------------------------------------------------------------
def _matriz_rigidez_local(EA, EI, L):
    """k local 6×6. GDL: [ux1, uy1, rz1, ux2, uy2, rz2] (ejes locales)."""
    k = np.zeros((6, 6))
    k[0, 0] = k[3, 3] = EA / L
    k[0, 3] = k[3, 0] = -EA / L

    c1 = 12.0 * EI / L ** 3
    c2 = 6.0 * EI / L ** 2
    c3 = 4.0 * EI / L
    c4 = 2.0 * EI / L

    k[1, 1] = k[4, 4] = c1
    k[1, 4] = k[4, 1] = -c1
    k[1, 2] = k[2, 1] = k[1, 5] = k[5, 1] = c2
    k[2, 4] = k[4, 2] = k[4, 5] = k[5, 4] = -c2
    k[2, 2] = k[5, 5] = c3
    k[2, 5] = k[5, 2] = c4
    return k


def _matriz_transformacion(c, s):
    """T 6×6: u_local = T·u_global (dos nudos, 3 GDL c/u)."""
    T = np.zeros((6, 6))
    T[0, 0] = T[1, 1] = T[3, 3] = T[4, 4] = c
    T[0, 1] = T[3, 4] = s
    T[1, 0] = T[4, 3] = -s
    T[2, 2] = T[5, 5] = 1.0
    return T


def _fuerzas_fijacion(w_perp, w_ax, L):
    """
    FEF (local): fuerzas de empotramiento que los apoyos aplican a la
    barra fija en ambos extremos, para cargas uniformes.
      w_perp en +y local, w_ax en +x local.
    FEF = [fx1, fy1, m1, fx2, fy2, m2]
    """
    FEF = np.zeros(6)
    FEF[0] = FEF[3] = -w_ax * L / 2.0
    FEF[1] = FEF[4] = -w_perp * L / 2.0
    FEF[2] = -w_perp * L ** 2 / 12.0
    FEF[5] = +w_perp * L ** 2 / 12.0
    return FEF


# ------------------------------------------------------------------
# Diagramas internos por equilibrio de cuerpo libre [0, x]
# ------------------------------------------------------------------
def _diagramas_barra(f_local, w_perp, w_ax, L, n_puntos=N_PUNTOS_DIAGRAMA):
    """
    f_local = k·u_local + FEF  → fuerzas que el NUDO aplica sobre el
    EXTREMO de la barra (componentes locales [fx1, fy1, m1, fx2, fy2, m2]).

    Equilibrio del cuerpo libre [0, x] (extremo i incluido).
    f_local son las fuerzas que el NUDO aplica sobre el EXTREMO de la
    barra (componentes locales [fx1, fy1, m1, fx2, fy2, m2]).

    · Cortante (convención clásica: positivo = par horario):
        ΣF⊥ del segmento  →  V(x) = fy1 + w_perp·x
    · Momento flector (positivo = FLEXIÓN SIMPLE, tracción en la
      fibra +y local) — momento de las cargas del segmento respecto
      al corte, M(x) = −m1 + fy1·x + w_perp·x²/2
        (viga biapoyada con carga ↓: M(vano) = +wL²/8 ✓)
    · Axial (positivo = TRACCIÓN): N(x) = −(fx1 + w_ax·x)
        (voladizo con compresión en la punta: N = −P ✓)
    """
    fx1, fy1, m1 = f_local[0], f_local[1], f_local[2]
    xs = [L * i / (n_puntos - 1) for i in range(n_puntos)]
    N, V, M = [], [], []
    for x in xs:
        N.append(-(fx1 + w_ax * x))
        V.append(fy1 + w_perp * x)
        M.append(-m1 + fy1 * x + w_perp * x * x / 2.0)
    return xs, N, V, M


# ------------------------------------------------------------------
# Solver principal
# ------------------------------------------------------------------
def analizar(modelo: Modelo) -> dict:
    """
    Ejecuta el análisis elástico completo. Devuelve el diccionario de
    resultados listo para la API/UI. Lanza ERROR con mensajes amables.
    """
    modelo.validar()

    # ---------- índices de GDL ----------
    ids_nudos = [n.id for n in modelo.nudos]
    idx = {nid: i for i, nid in enumerate(ids_nudos)}
    NG = 3 * len(ids_nudos)

    def gdl(nid):
        i = idx[nid]
        return (3 * i, 3 * i + 1, 3 * i + 2)

    # ---------- ensamblaje ----------
    K = np.zeros((NG, NG))
    Feq = np.zeros(NG)          # cargas nodales + equivalentes
    F_nodal_puro = np.zeros(NG) # solo cargas nodales (para desglose)
    elems = []                  # datos por barra para post-proceso

    for b in modelo.barras:
        ni, nj = modelo.nudo(b.ni), modelo.nudo(b.nj)
        L = math.hypot(nj.x - ni.x, nj.y - ni.y)
        if L < 1e-9:
            raise ERROR(f"La barra '{b.id}' tiene longitud nula.")
        c = (nj.x - ni.x) / L
        s = (nj.y - ni.y) / L

        E = b.E * _K_E
        A = b.A * _K_A
        I = b.I * _K_I
        EA, EI = E * A, E * I

        # cargas de barra (incluye peso propio si procede)
        # El peso propio apunta en −ŷ global (pp = γ·A, kg/m).
        # Ejecutores locales: t = (c, s) a lo largo de i→j, n = (−s, c) ⊥.
        # Descomponiendo −pp·ĵ:  w_ax = −pp·s ,  w_perp = −pp·c
        w_perp = b.q_perp
        w_ax = b.q_axial
        if b.peso_propio:
            pp = A * _GAMMA_ACERO          # kg/m
            w_ax += -pp * s
            w_perp += -pp * c

        k_loc = _matriz_rigidez_local(EA, EI, L)
        T = _matriz_transformacion(c, s)
        k_glob = T.T @ k_loc @ T

        gi = gdl(b.ni)
        gj = gdl(b.nj)
        g = list(gi) + list(gj)

        for a_ in range(6):
            for b_ in range(6):
                K[g[a_], g[b_]] += k_glob[a_, b_]

        FEF = _fuerzas_fijacion(w_perp, w_ax, L)
        Feq_eq = -(T.T @ FEF)          # cargas equivalentes en nudos
        for a_ in range(6):
            Feq[g[a_]] += Feq_eq[a_]

        elems.append({
            "barra": b, "L": L, "c": c, "s": s, "T": T,
            "k_loc": k_loc, "FEF": FEF,
            "w_perp": w_perp, "w_ax": w_ax,
        })

    # cargas nodales del usuario
    for cn in modelo.cargas_nodales:
        g = gdl(cn.nudo)
        Feq[g[0]] += cn.Fx
        Feq[g[1]] += cn.Fy
        Feq[g[2]] += cn.Mz
        F_nodal_puro[g[0]] += cn.Fx
        F_nodal_puro[g[1]] += cn.Fy
        F_nodal_puro[g[2]] += cn.Mz

    # ---------- partición libres / restringidos ----------
    libres, restringidos = [], []
    for n in modelo.nudos:
        a = modelo.apoyo_de(n.id)
        for j, restringido in enumerate(
            (a.ux if a else False, a.uy if a else False, a.rz if a else False)
        ):
            (restringidos if restringido else libres).append(gdl(n.id)[j])

    if not restringidos:
        raise ERROR("La estructura no tiene restricciones: es un mecanismo "
                    "(modelo flotante). Coloca al menos un apoyo.")
    if not libres:
        raise ERROR("Todos los grados de libertad están restringidos.")

    libres = np.array(libres, dtype=int)
    restringidos = np.array(restringidos, dtype=int)

    Kff = K[np.ix_(libres, libres)]
    Ff = Feq[libres]

    # ---------- resolver ----------
    try:
        Uf = np.linalg.solve(Kff, Ff)
    except np.linalg.LinAlgError:
        raise ERROR("El sistema de ecuaciones es singular: la estructura es "
                    "inestable o hipostática (faltan apoyos o hay un mecanismo). "
                    "Revisa apoyos, uniones y rigideces.")

    if not np.all(np.isfinite(Uf)):
        raise ERROR("El sistema produjo desplazamientos no finitos: revisa "
                    "rigideces nulas o un mecanismo parcial.")

    # Detección de mecanismos: un sistema singular (numerical) puede
    # devolver valores finitos pero con residuo grande o desplazamientos
    # absurdos → estructura inestable.
    norma_F = max(float(np.linalg.norm(Ff)), 1e-12)
    residuo = float(np.linalg.norm(Kff @ Uf - Ff)) / norma_F
    if residuo > 1e-6:
        raise ERROR("La estructura es inestable o hipostática: el sistema no "
                    "tiene solución única (mecanismo, falta de apoyos o unión "
                    "suelta). Residuo relativo ≈ %.1e." % residuo)
    if float(np.max(np.abs(Uf))) > 1e6:
        raise ERROR("La estructura se deforma desproporcionadamente (mecanismo "
                    "cuasi-singular). Revisa apoyos y rigideces de barras.")

    # Aviso preventivo: modo rígido aunque no haya carga que lo active
    if len(libres) <= 1500:
        try:
            w = np.linalg.eigvalsh(Kff)
            if w[0] <= 1e-12 * max(w[-1], 1e-12):
                avisos.append("Se detectó un posible modo rígido (mecanismo "
                              "descargado): la estructura es inestable ante "
                              "cargas en cierta dirección.")
        except Exception:
            pass

    U = np.zeros(NG)
    U[libres] = Uf

    # condición de la matriz (aviso de semirrigidez numérica)
    avisos = []
    try:
        cond = np.linalg.cond(Kff)
        if cond > 1e10:
            avisos.append(
                f"La estructura es numéricamente semirrígida (cond ≈ {cond:.1e}): "
                "revisa nudos sin conectar o barras muy rígidas frente a otras."
            )
    except Exception:
        pass

    # ---------- reacciones ----------
    if len(restringidos):
        Kcf = K[np.ix_(restringidos, libres)]
        Fc = Feq[restringidos]
        R = Kcf @ Uf - Fc
    else:
        R = np.zeros(0)

    reacciones = []
    for k_, g in enumerate(restringidos):
        nudo_id = ids_nudos[g // 3]
        comp = g % 3
        val = float(R[k_])
        if abs(val) < 1e-9:
            val = 0.0
        reacciones.append({
            "nudo": nudo_id,
            "comp": ("Fx", "Fy", "Mz")[comp],
            "valor": val,
        })

    # ---------- fuerzas de extremo y diagramas ----------
    barras_res = []
    diagramas = {}
    for e in elems:
        b = e["barra"]
        gi = gdl(b.ni)
        gj = gdl(b.nj)
        Ue = np.array([U[gi[0]], U[gi[1]], U[gi[2]],
                       U[gj[0]], U[gj[1]], U[gj[2]]])
        u_loc = e["T"] @ Ue
        f_loc = e["k_loc"] @ u_loc + e["FEF"]

        xs, Ns, Vs, Ms = _diagramas_barra(f_loc, e["w_perp"], e["w_ax"], e["L"])

        barras_res.append({
            "id": b.id,
            "ni": b.ni, "nj": b.nj,
            # fuerzas en extremos (convención interna: ver _diagramas_barra)
            "Ni": float(Ns[0]), "Vi": float(Vs[0]), "Mi": float(Ms[0]),
            "Nj": float(Ns[-1]), "Vj": float(Vs[-1]), "Mj": float(Ms[-1]),
            "maxN": float(max(Ns, key=abs)), "maxV": float(max(Vs, key=abs)),
            "maxM": float(max(Ms, key=abs)),
            "minM": float(min(Ms)), "maxM_pos": float(max(Ms)),
        })
        diagramas[b.id] = {"x": xs, "N": Ns, "V": Vs, "M": Ms}

    # ---------- desplazamientos nodales ----------
    nudos_res = []
    for n in modelo.nudos:
        g = gdl(n.id)
        nudos_res.append({
            "id": n.id,
            "ux": float(U[g[0]]), "uy": float(U[g[1]]), "rz": float(U[g[2]]),
        })

    # ---------- KPIs y verificación de equilibrio ----------
    # Equilibrio global: ΣR + ΣF_aplicadas = 0
    gdl_fy = [gdl(n.id)[1] for n in modelo.nudos]
    gdl_fx = [gdl(n.id)[0] for n in modelo.nudos]
    suma_Fy_cargas = float(Feq[gdl_fy].sum())   # cargas verticales aplicadas (+ arriba)
    suma_Ry = sum(r["valor"] for r in reacciones if r["comp"] == "Fy")
    suma_Fx_cargas = float(Feq[gdl_fx].sum())
    suma_Rx = sum(r["valor"] for r in reacciones if r["comp"] == "Fx")

    eq_Fy_ok = abs(suma_Ry + suma_Fy_cargas) <= max(1e-6, 1e-8 * abs(suma_Fy_cargas))
    eq_Fx_ok = abs(suma_Rx + suma_Fx_cargas) <= max(1e-6, 1e-8 * abs(suma_Fx_cargas))

    dmax = max((abs(nd["uy"]) for nd in nudos_res), default=0.0)
    mmax = max((max(abs(br["maxM"]), abs(br["minM"])) for br in barras_res), default=0.0)

    if not eq_Fy_ok:
        avisos.append("⚠ La suma de reacciones verticales no cierra con las "
                      "cargas: verifica el modelo.")

    return {
        "ok": True,
        "titulo": modelo.titulo,
        "nudos": nudos_res,
        "reacciones": reacciones,
        "barras": barras_res,
        "diagramas": diagramas,
        "kpi": {
            "delta_max": dmax,
            "M_max": mmax,
            "suma_Fy_cargas": suma_Fy_cargas,
            "suma_Ry": suma_Ry,
            "suma_Fx_cargas": suma_Fx_cargas,
            "suma_Rx": suma_Rx,
            "equilibrio_ok": eq_Fx_ok and eq_Fy_ok,
            "cond_K": float(np.linalg.cond(Kff)) if len(libres) else None,
        },
        "avisos": avisos,
    }
