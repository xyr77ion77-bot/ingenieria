# ==================================================================
#  tests_diseno_acero.py — dorados COVENIN 1618-1998 + E2E
# ==================================================================
import math
import sys

from engine.diseno_acero import (E_ACERO, buscar_perfil, mn_flexion, vn_corte,
                                 pn_compresion, b1_amplificacion,
                                 flecha_centro_cm, cargar_perfiles, disenar)
from engine.generador import generar_portico

FALLOS = []


def check(nombre, cond, detalle=''):
    if cond:
        print('  ✓', nombre)
    else:
        FALLOS.append(nombre)
        print('  ✗', nombre, detalle)


print('═══ 1 · BD de perfiles ═══')
p = buscar_perfil('IPE 300')
check('IPE 300: A=53,8 · Sx=557 · Zx=628 · It=20,1',
      abs(p['A'] - 53.8) < .01 and abs(p['Sx'] - 557) < 1
      and abs(p['Zx'] - 628) < 1 and abs(p['It'] - 20.1) < .1)
check('IPE 300: Iw = 126·10³ cm⁶', abs(p['Iw'] - 126000) < 500)
cat = cargar_perfiles(['IPE', 'HE'])
check('catálogo IPE+HE ordenado por peso', len(cat) > 150
      and cat[0]['G'] <= cat[len(cat) // 2]['G'] <= cat[-1]['G'])

print('═══ 2 · Flexión (cap. 16) ═══')
fl = mn_flexion(p, 2500, lb_cm=0)
check('Mp = Fy·Zx = 1.570.000 kg·cm', abs(fl['Mp'] - 1570000) < 1)
check('φMn = 0,9·Mp = 1.413.000 kg·cm', abs(fl['phiMn'] - 1413000) < 1)
check('Lp = 1,76·ry·√(E/Fy) = 171 cm', abs(fl['Lp'] - 170.9) < 2)
check('Lr (Mcr=Mr) ≈ 439 cm', fl['Lr'] and 400 < fl['Lr'] < 480,
      str(fl['Lr']))
fl2 = mn_flexion(p, 2500, lb_cm=300)
check('zona inelástica entre Lp y Lr: Mp > Mn > Mr',
      fl2['Mn'] < fl['Mp'] and fl2['Mn'] > fl['Mr'] * 0.99)
fl3 = mn_flexion(p, 2500, lb_cm=900)
check('zona elástica: Mn = Cb·Mcr ≤ Mp', fl3['Mn'] < fl['Mr'])
check('Cb=2 sube la inelástica sin pasar de Mp',
      mn_flexion(p, 2500, lb_cm=300, cb=2.0)['Mn']
      > mn_flexion(p, 2500, lb_cm=300, cb=1.0)['Mn'] - 1e-6)

print('═══ 3 · Corte (cap. 16.4) ═══')
co = vn_corte(p, 2500)
check('Aw = d·tw = 19,78 cm²', abs(co['Aw'] - 19.78) < .05)
check('φVn = 0,6·Fy·Aw·Cv = 29.671 kg (Cv=1)', abs(co['phiVn'] - 29671) < 30)

print('═══ 4 · Compresión (cap. 15) ═══')
fy = 2500.0
lamc = 1.0
lam = lamc * math.pi / math.sqrt(fy / E_ACERO)   # λ = KL/r
fcr1 = pn_compresion({'rx': 10, 'ry': 10, 'A': 1.0}, fy, lam * 10)['Fcr']
check('λc=1 → Fcr = 0,658·Fy = 1645 kg/cm²', abs(fcr1 - 0.658 * fy) < 1)
lamc15 = 1.5
lam15 = lamc15 * math.pi / math.sqrt(fy / E_ACERO)
a = pn_compresion({'rx': 10, 'ry': 10, 'A': 1.0}, fy, (lam15 - .01) * 10)['Fcr']
b = pn_compresion({'rx': 10, 'ry': 10, 'A': 1.0}, fy, (lam15 + .01) * 10)['Fcr']
check('continuidad de Fcr en λc=1,5 (<1%)', abs(a - b) / b < .01,
      '%.1f vs %.1f' % (a, b))
he = buscar_perfil('HE 200 B')
pc = pn_compresion(he, 2500, 350 * 1.5)
check('HE 200 B con KL=525 cm: φNn > 60 t', pc['phiNn'] > 60000,
      '%.0f kg' % pc['phiNn'])

print('═══ 5 · Interacción y B1 (cap. 18) ═══')
b1, ne1 = b1_amplificacion(0.0, 525.0, he['Ix'])
check('sin axil → B1 = 1', b1 == 1.0)
b1b, _ = b1_amplificacion(20000.0, 525.0, he['Ix'])
check('con axil → B1 ≥ 1', b1b >= 1.0, '%.2f' % b1b)

print('═══ 6 · Flechas (servicio) ═══')
f = flecha_centro_cm(10.0, 600.0, -4500.0, 0.0, 20000.0)
check('empotrado-articulado w=1000kg/m L=6m I=20000: f=0,1607 cm',
      abs(f - 0.1607) < 0.002, '%.4f' % f)
f2 = flecha_centro_cm(10.0, 600.0, -3000.0, -3000.0, 20000.0)
check('empotrada-empotrada: f = wL⁴/384EI = 0,0803 cm',
      abs(f2 - 0.0803) < 0.002, '%.4f' % f2)

print('═══ 7 · E2E: pórtico del generador → diseño + optimizador ═══')
corte_cfg = {'niveles_propios': [], 'columnas': {'activa': ['1', '3'], 'base': {}},
             'uniones': {'patron': 'continuo', 'excepciones': {}}}
modelador = {'titulo': 'E2E acero',
             'geometria': {'lx': [6, 6], 'ly': [5, 5],
                           'niveles': [{'nombre': 'N1', 'h_piso': 4.0},
                                       {'nombre': 'N2', 'h_piso': 3.2, 'techo': True}]},
             'resistentes': {'X': ['1', '3'], 'Y': ['A', 'C']},
             'cortes': {'X:1': corte_cfg}, 'seccion': {'perfil': 'IPE 300'}}
md, _res = generar_portico(modelador, 'X:1')
ys_n = sorted({n['y'] for n in md['nudos']})
vigas_ids = [bb['id'] for bb in md['barras']
             if abs(next(n['y'] for n in md['nudos'] if n['id'] == bb['ni'])
                    - next(n['y'] for n in md['nudos'] if n['id'] == bb['nj'])) < 1e-6
             and next(n['y'] for n in md['nudos'] if n['id'] == bb['ni']) > 0]
acc = {'sismo': {'tipo_edificacion': '2', 'zona': '4', 'suelo': 'II',
                 'fraccion_cv': 0.25, 'rho': 1.0, 'FI': 1.0, 'Qc': 0},
       'barra_cp': {i: 1590.0 for i in vigas_ids},
       'barra_cv': {i: 750.0 for i in vigas_ids},
       'nodo_cp': {}, 'nodo_cv': {}}
out = disenar(md, acc, {'fy': 2500, 'optimizar': True,
                        'perfil_viga': 'IPE 300', 'perfil_columna': 'HE 200 B'})
check('diseño ok', out['ok'])
check('todas las barras del pórtico tienen fila',
      len(out['filas']) == len(md['barras']),
      '%d de %d' % (len(out['filas']), len(md['barras'])))
check('hay vigas y columnas clasificadas',
      any(f['tipo'] == 'viga' for f in out['filas'])
      and any(f['tipo'] == 'columna' for f in out['filas']))
check('ratios entre 0 y 100 (cotas sanas)',
      all(0 <= f['gobierna'] <= 100 for f in out['filas']))
check('optimizador devolvió perfiles',
      'viga' in out['optimo'] and 'columna' in out['optimo'],
      str(out['optimo']))
check('memoria con sección 5 · Diseño en acero',
      any('Diseño en acero' in s['seccion'] for s in out['memoria'])
      and len(out['memoria'][-1]['pasos']) >= 3)

print()
if FALLOS:
    print('FALLOS: %d → %s' % (len(FALLOS), FALLOS))
    sys.exit(1)
print('═══ TODOS LOS TESTS DE DISEÑO EN ACERO PASARON ═══')
