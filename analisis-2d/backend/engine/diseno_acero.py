# ==================================================================
#  diseno_acero.py — Diseño de pórticos COVENIN 1618-1998
#  (estados límites; las ecuaciones corresponden a AISC LRFD — el
#   Comentario de la norma las cita: (15-2/3), (16-6/8/10/17),
#   (18-1a/b) — ver analisis-2d/docs/1618-RESUMEN.md)
#  ------------------------------------------------------------------
#  · Solo pórticos: VIGAS (flexión + corte + flecha) y COLUMNAS
#    (compresión + interacción P-M con B1 y amplificación P-Δ θ).
#  · Perfiles de la BD (backend/perfiles/json, 874) con It/Iw para
#    pandeo lateral torsional exacto.
#  · Cada verificación entra a la memoria de cálculo (modo
#    aprendizaje): fórmula → sustitución → fuente → porqué.
#  Unidades internas: kg · cm · kg/cm² (la app trabaja kg · m).
# ==================================================================

import json
import math
import os
from dataclasses import replace

from .modelo import Modelo, ERROR, CargaNodal
from .solver import analizar
from . import acciones as acc_mod

E_ACERO = 2_100_000.0        # kg/cm²
G_ACERO = E_ACERO / 2.6      # módulo transversal
FY_DEF = 2500.0              # A36
PHI_B, PHI_C, PHI_V = 0.90, 0.85, 1.00

_RUTA_JSON = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), 'perfiles', 'json')

_SERIES_ARCHIVO = {
    'IPE': 'IPE.json', 'IPN': 'IPN.json', 'HE': 'HE.json', 'HD': 'HD.json',
    'HP': 'HP.json', 'UPN': 'UPN.json', 'UPE': 'UPE.json', 'U': 'U.json',
    'FL': 'FL.json', 'R': 'R.json', 'SQ': 'SQ.json', 'HLZ': 'HLZ-HL-1.json',
    'L': 'L-lados-iguales.json', 'LD': 'L-lados-desiguales.json',
}


# ------------------------------------------------------------------
# BD de perfiles
# ------------------------------------------------------------------
def cargar_perfiles(series=None):
    """→ [dict] normalizado a cm: h,b,tw,tf,d · A,Ix,Sx,Zx,rx,Iy,ry,It,Avz
    · Iw (×10³ cm⁶ en la BD) · G kg/m · serie. series=None → perfiles I."""
    series = series or ['IPE', 'IPN', 'HE', 'HD', 'HP']
    salida = []
    for s in series:
        arch = _SERIES_ARCHIVO.get(s)
        if not arch:
            continue
        d = json.load(open(os.path.join(_RUTA_JSON, arch), encoding='utf-8'))
        for p in d['perfiles']:
            if not p.get('Ix') or not p.get('Sx') or not p.get('A'):
                continue
            # las series L/SQ/R no traen todas las dimensiones de perfiles I
            h = p.get('h') or 0.0
            b = p.get('b') or 0.0
            tw = p.get('tw') or 0.0
            tf = p.get('tf') or 0.0
            salida.append({
                'nombre': p['nombre'], 'serie': s, 'G': p.get('G') or 0.0,
                'h': h / 10.0, 'b': b / 10.0,
                'tw': tw / 10.0, 'tf': tf / 10.0,
                'd': (p.get('d') or h - 2 * tf) / 10.0,
                'A': p['A'], 'Ix': p['Ix'], 'Sx': p['Sx'], 'Zx': p.get('Zx') or p['Sx'],
                'rx': p.get('rx') or 1.0, 'ry': p.get('ry') or 1.0,
                'Iy': p.get('Iy') or 0.0, 'It': p.get('It') or 0.0,
                'Iw': (p.get('Iw') or 0.0) * 1e3,   # ×10³ cm⁶ → cm⁶
                'Avz': p.get('Avz') or p['A'],
            })
    salida.sort(key=lambda x: x['G'])
    return salida


def buscar_perfil(nombre, series=None):
    for p in cargar_perfiles(series):
        if p['nombre'].lower() == str(nombre).strip().lower():
            return p
    raise ERROR('El perfil «%s» no está en la base de datos.' % nombre)


# ------------------------------------------------------------------
# Estados límites
# ------------------------------------------------------------------
def mn_flexion(p, fy, lb_cm=0.0, cb=1.0):
    """COVENIN 1618 cap. 16: Mp/Lp(16-8)/inelástica(16-6)/elástica(16-17)."""
    Mp = fy * p['Zx']
    Mr = fy * p['Sx']
    Lp = 1.76 * p['ry'] * math.sqrt(E_ACERO / fy)

    def mcr(lb):
        if lb <= 0 or p['Iy'] <= 0 or p['It'] <= 0 or p['Iw'] <= 0:
            return None
        m = (math.pi / lb) * math.sqrt(E_ACERO * p['Iy'] * G_ACERO * p['It'])
        m *= math.sqrt(1.0 + math.pi ** 2 * E_ACERO * p['Iw']
                       / (G_ACERO * p['It'] * lb * lb))
        return m

    # (16-10): Lr tal que Mcr(Lr) = Mr — bisección
    Lr = None
    if mcr(Lp) and mcr(Lp) > Mr:
        lo, hi = Lp, max(2.0 * Lp, 1.0)
        while mcr(hi) and mcr(hi) > Mr and hi < 1e6:
            hi *= 2.0
        for _ in range(60):
            mid = 0.5 * (lo + hi)
            if mcr(mid) > Mr:
                lo = mid
            else:
                hi = mid
        Lr = 0.5 * (lo + hi)

    lb = lb_cm or 0.0
    if lb <= Lp:
        Mn, zona = Mp, 'plástico (Lb ≤ Lp)'
    elif Lr and lb <= Lr:
        Mn = cb * (Mp - (Mp - Mr) * (lb - Lp) / (Lr - Lp))
        Mn = min(Mn, Mp)
        zona = 'pandeo lateral torsional inelástico'
    elif mcr(lb):
        Mn = min(cb * mcr(lb), Mp)
        zona = 'pandeo lateral torsional elástico'
    else:
        Mn, zona = Mr, 'sin datos de pandeo → Mr'
    lam_f = (p['b'] / 2.0) / p['tf']
    lam_w = p['d'] / p['tw']
    compacta = lam_f <= 65.0 / math.sqrt(fy) and lam_w <= 640.0 / math.sqrt(fy)
    return {'Mn': Mn, 'phiMn': PHI_B * Mn, 'Mp': Mp, 'Mr': Mr,
            'Lp': Lp, 'Lr': Lr, 'zona': zona, 'cb': cb,
            'lam_f': lam_f, 'lam_w': lam_w, 'compacta': compacta}


def vn_corte(p, fy):
    """COVENIN 1618 cap. 16.4: Vn = 0,6·Fy·Aw·Cv (alma de I)."""
    Aw = p['d'] * p['tw']
    htw = p['d'] / p['tw']
    lim = 2.45 * math.sqrt(E_ACERO / fy)
    Cv = 1.0 if htw <= lim else lim / htw
    Vn = 0.6 * fy * Aw * Cv
    return {'Vn': Vn, 'phiVn': PHI_V * Vn, 'Cv': Cv, 'h_tw': htw, 'Aw': Aw}


def pn_compresion(p, fy, kl_cm):
    """COVENIN 1618 cap. 15: (15-2)/(15-3), φc=0,85."""
    rmin = min(p['rx'], p['ry'])
    lam = kl_cm / rmin if rmin > 0 else 999.0
    lamc = lam / math.pi * math.sqrt(fy / E_ACERO)
    if lamc <= 1.5:
        Fcr = (0.658 ** (lamc ** 2)) * fy
        forma = '(15-2)'
    else:
        Fcr = (0.877 / lamc ** 2) * fy
        forma = '(15-3)'
    Nn = Fcr * p['A']
    return {'Nn': Nn, 'phiNn': PHI_C * Nn, 'Fcr': Fcr, 'lam': lam,
            'lamc': lamc, 'forma': forma}


def b1_amplificacion(nu, l_cm, ix, cm=0.85):
    """B1 = Cm/(1 − Nu/Ne1) ≥ 1 · Ne1 = π²·E·Ix/L² (C-9, fórm. 9-2/9-4)."""
    if nu <= 0 or l_cm <= 0 or ix <= 0:
        return 1.0, math.pi ** 2 * E_ACERO * ix / l_cm ** 2 if l_cm > 0 else 0.0
    ne1 = math.pi ** 2 * E_ACERO * ix / (l_cm ** 2)
    return max(1.0, cm / (1.0 - nu / ne1)), ne1


def flecha_centro_cm(w_kg_cm, L_cm, mi_kgcm, mj_kgcm, I_cm4):
    """f = 5wL⁴/384EI + (Mi+Mj)L²/16EI (hogging negativo) — kg·cm."""
    return (5.0 * w_kg_cm * L_cm ** 4 / (384.0 * E_ACERO * I_cm4)
            + (mi_kgcm + mj_kgcm) * 100.0 * L_cm ** 2
            / (16.0 * E_ACERO * I_cm4))


def _f(x, dec=2):
    t = '%.*f' % (dec, float(x))
    if '.' in t:
        t = t.rstrip('0').rstrip('.')
    return t.replace('.', ',')


# ------------------------------------------------------------------
# Orquestador: diseño de todas las barras del pórtico activo
# ------------------------------------------------------------------
def disenar(modelo_dict, acciones_dict, params=None):
    params = params or {}
    fy = float(params.get('fy') or FY_DEF)
    series = params.get('series') or ['IPE', 'IPN', 'HE', 'HD', 'HP']
    k_col = float(params.get('k_col') or 1.5)
    cb = float(params.get('cb') or 1.0)
    lb_viga_m = params.get('lb_viga_m')          # None → luz de cada viga
    limite_flecha = int(params.get('limite_flecha') or 300)
    optimizar = bool(params.get('optimizar'))
    p_viga = params.get('perfil_viga') or 'IPE 300'
    p_col = params.get('perfil_columna') or 'HE 200 B'

    # resistencia (envolvente + memoria del flujo)
    out = acc_mod.analizar_con_combinaciones(modelo_dict, acciones_dict)
    if not out.get('ok'):
        return out
    env = out['envolvente']
    modelo = Modelo.desde_dict(modelo_dict)
    acc = acc_mod.Acciones.desde_dict(acciones_dict)

    # caso de servicio SERV = CP + CV (flechas)
    barras_serv = []
    for b in modelo.barras:
        w = (acc.barra_cp.get(b.id, 0.0) + acc.barra_cv.get(b.id, 0.0)
             + (b.A * 1e-4 * acc_mod._GAMMA_ACERO if b.peso_propio else 0.0))
        barras_serv.append(replace(b, peso_propio=False, q_perp=-w))
    cargas_serv = []
    for nid in set(list(acc.nodo_cp) + list(acc.nodo_cv)):
        n = modelo.nudo(nid)
        if not n:
            continue
        c1 = acc.nodo_cp.get(nid, {})
        c2 = acc.nodo_cv.get(nid, {})
        cargas_serv.append(CargaNodal(
            nid, (c1.get('Fx') or 0) + (c2.get('Fx') or 0),
            (c1.get('Fy') or 0) + (c2.get('Fy') or 0),
            (c1.get('Mz') or 0) + (c2.get('Mz') or 0)))
    res_serv = analizar(Modelo(modelo.titulo + ' · SERV', list(modelo.nudos),
                               barras_serv, list(modelo.apoyos), cargas_serv))
    serv_barra = {b['id']: b for b in res_serv['barras']}

    # P-Δ por deriva (θ, C-9.4): una estimación por nivel con la envolvente
    ys = sorted({round(n.y, 4) for n in modelo.nudos})
    thetas = {}
    for i in range(1, len(ys)):
        y_sup, y_inf = ys[i], ys[i - 1]
        cols = [b for b in modelo.barras
                if abs(modelo.nudo(b.ni).y - y_sup) < 1e-6
                or abs(modelo.nudo(b.nj).y - y_sup) < 1e-6]
        cols = [b for b in cols
                if abs(modelo.nudo(b.ni).y - modelo.nudo(b.nj).y) > 1e-6
                and min(modelo.nudo(b.ni).y, modelo.nudo(b.nj).y) < y_sup - 1e-6
                < max(modelo.nudo(b.ni).y, modelo.nudo(b.nj).y) + 1e-6]
        if not cols:
            continue
        ids_sup = [n.id for n in modelo.nudos if abs(n.y - y_sup) < 1e-6]
        ids_inf = [n.id for n in modelo.nudos if abs(n.y - y_inf) < 1e-6]
        env_n = env.get('nudos', {})

        def _mag(ids):
            vals = [max(abs(env_n[i]['ux']['min']),
                        abs(env_n[i]['ux']['max']))
                    for i in ids if i in env_n]
            return max(vals) if vals else 0.0

        mag_sup = _mag(ids_sup)
        mag_inf = _mag(ids_inf)
        if mag_sup <= 0:
            continue
        delta = abs(mag_sup - mag_inf) * 100.0   # m → cm
        spu = 0.0
        svu = 0.0
        for b in cols:
            e = env['barras'].get(b.id, {})
            spu += max(abs(e.get('Ni', {}).get('min', 0.0)),
                       abs(e.get('Ni', {}).get('max', 0.0)))
            svu += max(abs(e.get('Vi', {}).get('min', 0.0)),
                       abs(e.get('Vi', {}).get('max', 0.0)),
                       abs(e.get('Vj', {}).get('min', 0.0)),
                       abs(e.get('Vj', {}).get('max', 0.0)))
        h_cm = (y_sup - y_inf) * 100.0
        if svu > 0 and delta > 0:
            thetas[y_sup] = spu * delta / (svu * h_cm)

    def theta_de(y):
        for nivel in sorted(thetas, reverse=True):
            if y <= nivel + 1e-6:
                return thetas[nivel]
        return 0.0

    # ── clasificar barras (solo pórticos) ──
    vigas, columnas = [], []
    for b in modelo.barras:
        ni, nj = modelo.nudo(b.ni), modelo.nudo(b.nj)
        e = env['barras'].get(b.id)
        if e is None:
            continue
        L_cm = math.hypot(nj.x - ni.x, nj.y - ni.y) * 100.0
        mu = max(e['Mmax']['max'], abs(e['Mmin']['min']),
                 abs(e['Mi']['min']), abs(e['Mi']['max']),
                 abs(e['Mj']['min']), abs(e['Mj']['max']))
        sol = {
            'Pu': max(abs(e['Ni']['min']), abs(e['Ni']['max']),
                      abs(e['Nj']['min']), abs(e['Nj']['max'])),
            'Vu': max(abs(e['Vi']['min']), abs(e['Vi']['max']),
                      abs(e['Vj']['min']), abs(e['Vj']['max'])),
            'Mu': mu * 100.0,                   # kg·m → kg·cm
            'c_gobierna': e['Mmax']['cmax'] if e['Mmax']['max']
                          >= abs(e['Mmin']['min']) else e['Mmin']['cmin'],
        }
        if abs(ni.y - nj.y) < 1e-6 and ni.y > 1e-6:
            s = serv_barra.get(b.id, {})
            sol.update({'tipo': 'viga', 'L_cm': L_cm,
                        'w_ser': (acc.barra_cp.get(b.id, 0.0)
                                  + acc.barra_cv.get(b.id, 0.0)) / 100.0,
                        'Mi_ser': s.get('Mi', 0.0), 'Mj_ser': s.get('Mj', 0.0),
                        'f_ser_cm': flecha_centro_cm(
                            (acc.barra_cp.get(b.id, 0.0)
                             + acc.barra_cv.get(b.id, 0.0)) / 100.0,
                            L_cm, s.get('Mi', 0.0), s.get('Mj', 0.0), b.I)})
            vigas.append({'id': b.id, 'sol': sol})
        elif abs(ni.y - nj.y) > 1e-6:
            sol.update({'tipo': 'columna', 'L_cm': L_cm,
                        'theta': theta_de(max(ni.y, nj.y))})
            columnas.append({'id': b.id, 'sol': sol})
        # barras horizontales a nivel de base o diagonales: fuera de alcance

    # ── verificación de un miembro con un perfil dado ──
    def verificar(tipo, per, sol):
        r = {'ratios': {}}
        if tipo == 'viga':
            lb = sol['L_cm'] if lb_viga_m is None else lb_viga_m * 100.0
            flex = mn_flexion(per, fy, lb_cm=lb, cb=cb)
            cor = vn_corte(per, fy)
            r['flex'] = flex
            r['corte'] = cor
            r['ratios']['flexión'] = sol['Mu'] / flex['phiMn'] if flex['phiMn'] else 99
            r['ratios']['corte'] = sol['Vu'] / cor['phiVn'] if cor['phiVn'] else 99
            if sol.get('L_cm'):
                f_lim = sol['L_cm'] / limite_flecha
                r['flecha_cm'] = sol['f_ser_cm']
                r['f_lim_cm'] = f_lim
                r['ratios']['flecha'] = sol['f_ser_cm'] / f_lim if f_lim else 99
        else:
            comp = pn_compresion(per, fy, k_col * sol['L_cm'])
            b1, ne1 = b1_amplificacion(sol['Pu'], k_col * sol['L_cm'], per['Ix'])
            th = sol.get('theta') or 0.0
            mu_amp = sol['Mu'] / (1.0 - th) if th < 0.25 else float('inf')
            flex = mn_flexion(per, fy, lb_cm=0.0, cb=cb)
            r['comp'] = comp
            r['b1'] = b1
            r['ne1'] = ne1
            r['theta'] = th
            r['Mu_amp'] = mu_amp
            r['flex'] = flex
            n01 = sol['Pu'] / comp['phiNn'] if comp['phiNn'] else 99
            r['n01'] = n01
            mm = mu_amp * b1 / flex['phiMn'] if flex['phiMn'] else 99
            if n01 >= 0.2:
                r['ratios']['interacción (18-1a)'] = n01 + 8.0 / 9.0 * mm
            else:
                r['ratios']['interacción (18-1b)'] = n01 + mm
            r['ratios']['esbeltez'] = comp['lam'] / 200.0
        r['gobierna'] = max(r['ratios'].values())
        r['pasa'] = r['gobierna'] <= 1.0
        return r

    per_v = buscar_perfil(p_viga, series)
    per_c = buscar_perfil(p_col, series)
    filas = []
    for grupo, per_asignado in ((vigas, per_v), (columnas, per_c)):
        for m in grupo:
            sol = m['sol']
            per = per_v if sol['tipo'] == 'viga' else per_c
            res_v = verificar(sol['tipo'], per, sol)
            fila = {'barra': m['id'], 'tipo': sol['tipo'],
                    'perfil': per['nombre'],
                    'Pu': _f(sol['Pu']), 'Vu': _f(sol['Vu']),
                    'Mu': _f(sol['Mu'] / 1e5),
                    'L_m': _f(sol['L_cm'] / 100.0),
                    'ratios': {k: round(v, 3) for k, v in res_v['ratios'].items()},
                    'gobierna': round(res_v['gobierna'], 3),
                    'pasa': res_v['pasa'],
                    'combo': sol['c_gobierna'], 'detalle': res_v}
            filas.append(fila)

    # ── optimizador (el más liviano que pasa, por tipo) ──
    optimo = {}
    if optimizar:
        catalogo = cargar_perfiles(series)
        for tipo, miembros in (('viga', vigas), ('columna', columnas)):
            if not miembros:
                continue
            elegido = None
            for cand in catalogo:
                if all(verificar(tipo, cand, m['sol'])['pasa'] for m in miembros):
                    elegido = cand
                    break
            if elegido:
                optimo[tipo] = {'nombre': elegido['nombre'], 'G': elegido['G']}
    # marca en las filas si el perfil óptimo es otro
    for fila in filas:
        op = optimo.get(fila['tipo'])
        fila['optimo'] = op['nombre'] if op else None

    # ── memoria (modo aprendizaje): gobernante de cada tipo ──
    memoria = out.setdefault('memoria', [])
    sec = {'seccion': '5 · Diseño en acero (COVENIN 1618-1998)', 'pasos': []}
    memoria.append(sec)
    for tipo, miembros, per in (('Viga', vigas, per_v), ('Columna', columnas, per_c)):
        if not miembros:
            continue
        gob = max(miembros, key=lambda m: verificar(tipo, per, m['sol'])['gobierna'])
        sol = gob['sol']
        r = verificar(tipo, per, sol)
        if tipo == 'Viga':
            fl = r['flex']
            sec['pasos'].append({
                'formula': 'Mp = Fy·Zx · Lp = 1,76·ry·√(E/Fy)  (16-8)',
                'sustitucion': per['nombre'] + ': Fy = ' + _f(fy, 0)
                    + ' · Zx = ' + _f(per['Zx']) + ' cm³ · ry = ' + _f(per['ry'])
                    + ' cm → Mp = ' + _f(fl['Mp'] / 1e5) + ' t·m · Lp = '
                    + _f(fl['Lp'] / 100.0) + ' m'
                    + (' · Lr = ' + _f(fl['Lr'] / 100.0) + ' m' if fl['Lr'] else ''),
                'resultado': _f(fl['phiMn'] / 1e5) + ' t·m (φMn, ' + fl['zona'] + ')',
                'fuente': 'COVENIN 1618-1998 · cap. 16',
                'porque': 'El momento nominal baja si la viga sin arriostramiento '
                          'lateral (Lb) pandea antes de ceder.'})
            sec['pasos'].append({
                'formula': 'demanda/capacidad: Mu/φMn · Vu/φVn · f/(L/' + str(limite_flecha) + ')',
                'sustitucion': gob['id'] + ': Mu = ' + _f(sol['Mu'] / 1e5)
                    + ' t·m · Vu = ' + _f(sol['Vu']) + ' kg · f = '
                    + _f(sol.get('f_ser_cm', 0.0)) + ' cm',
                'resultado': 'ratio = ' + _f(r['gobierna'], 2)
                    + ('  ✓' if r['pasa'] else '  ✗ NO CUMPLE'),
                'fuente': 'COVENIN 1618-1998 · caps. 16 y 8.2 (flechas L/'
                    + str(limite_flecha) + ', formulario pág. 3)',
                'porque': 'El estado límite de resistencia (φ<1) y el de servicio '
                          '(flecha) se verifican por separado.'})
        else:
            cp = r['comp']
            sec['pasos'].append({
                'formula': 'λ = KL/r · λc = λ/π·√(Fy/E) · Fcr (15-2)/(15-3)',
                'sustitucion': per['nombre'] + ': K = ' + _f(k_col) + ' · L = '
                    + _f(sol['L_cm'] / 100.0) + ' m · r = ' + _f(min(per['rx'], per['ry']))
                    + ' cm → λ = ' + _f(cp['lam'], 1) + ' · λc = ' + _f(cp['lamc'], 3)
                    + ' → Fcr = ' + _f(cp['Fcr'], 0) + ' kg/cm² (' + cp['forma'] + ')',
                'resultado': _f(cp['phiNn']) + ' kg (φNn)',
                'fuente': 'COVENIN 1618-1998 · cap. 15',
                'porque': 'La columna pandea (pandeo flexional) antes de ceder si '
                          'es esbelta: Fcr cae con λc.'})
            sec['pasos'].append({
                'formula': 'Nu/φNn + (8/9 o 1)·B1·Mu/(1−θ)·1/φbMn  (18-1a/b)',
                'sustitucion': gob['id'] + ': Nu/φNn = ' + _f(r['n01'], 3)
                    + ' · B1 = ' + _f(r['b1'], 2) + ' · θ = ' + _f(r['theta'], 3)
                    + ' → ratio = ' + _f(r['gobierna'], 2)
                    + ('  ✓' if r['pasa'] else '  ✗ NO CUMPLE'),
                'resultado': _f(r['gobierna'], 2),
                'fuente': 'COVENIN 1618-1998 · cap. 18 + P-Δ (C-9.4)',
                'porque': 'El axil de compresión amplifica la flexión (efectos de '
                          'segundo orden): B1 por curvatura y θ por deriva de piso.'})
    sec['pasos'].append({
        'formula': 'P-Δ: θ = ΣPu·Δ / (ΣVu·h)',
        'sustitucion': '; '.join('y=' + _f(k) + ' m → θ=' + _f(v, 3)
                                 for k, v in sorted(thetas.items()))
        or 'sin derivas (pórtico sin desplazamiento)',
        'resultado': '',
        'fuente': 'COVENIN 1618-1998 · C-9.4 (segundo orden)',
        'porque': 'Si θ > 0,25 la deriva de piso amplifica demasiado el momento: '
                  'conviene aumentar rigidez (avisar).'})

    optimo_s = {k: v['nombre'] for k, v in optimo.items()}
    return {'ok': True, 'fy': fy, 'filas': filas,
            'optimo': optimo_s, 'thetas': {str(k): v for k, v in thetas.items()},
            'memoria': memoria, 'gamma': out['gamma'], 'sismo': out['sismo'],
            'niveles': out['niveles'], 'combos': out['combos'],
            'envolvente': out['envolvente'], 'avisos': out.get('avisos', [])}
