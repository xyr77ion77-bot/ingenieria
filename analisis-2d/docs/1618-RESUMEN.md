# COVENIN 1618-1998 — Fórmulas usadas por `engine/diseno_acero.py`

La norma (PDF en `ACERO/`, 258 págs) trae los artículos normativos con las
ecuaciones como imagen; **el Comentario (C-x.x) cita cada fórmula y confirma
que corresponden a AISC LRFD** (referencias Galambos 1988, Kirby & Nethercot
1979, Basler 1961, Kanchanalai 1977). Unidades del motor: kg · m · kg/cm²
(los perfiles de la BD: A cm², I cm⁴, W/S cm³, r cm, G kg/m → se convierten).

## Factores de minoración (φ)
| Efecto | φ | Fuente |
|---|---|---|
| Flexión φb | 0,90 | 1618 cap. 16 (AISC LRFD) |
| Compresión φc | 0,85 | 1618 cap. 15 (AISC LRFD) |
| Corte φv | 1,00 | 1618 cap. 16.4 (webs I laminadas; C-16.4, kp=5,0) |
| Tracción (cedencia) | 0,90 | cap. 14 |

## Flexión (cap. 16) — vigas
- Compacta ala/alma (Tabla 4.1): λp_fl = 65/√Fy · λp_al = 640/√Fy
- Mp = Fy·Zx  ·  Mr = Fy·Sx
- **(16-8)**: Lp = 1,76·ry·√(E/Fy)
- **(16-7)**: Cb = 12,5·Mt / (2,5·Mt + 3MA + 4MB + 3MC) (Kirby & Nethercot;
  conservador por defecto: Cb = 1,0 si no se calculan los momentos a L/4)
- **(16-10)**: Lr — longitud donde Mcr = Mr; el motor la resuelve con el
  momento crítico elástico de doble simetría:
  Mcr = (π/Lb)·√(E·Iy·G·It)·√(1 + π²·E·Iw/(G·It·Lb²))  (It/Iw de la BD)
- **(16-6)**: zona inelástica Mn = Cb·[Mp − (Mp−Mr)(Lb−Lp)/(Lr−Lp)] ≤ Mp
- **(16-17)**: zona elástica Mn = Cb·Mcr ≤ Mp
- φMn = 0,90·Mn

## Corte (cap. 16.4) — alma de I
- Aw = d·tw · **Vn = 0,6·Fy·Aw·Cv**
- Cv = 1,0 si h/tw ≤ 2,45·√(E/Fy) · si no, Cv = 2,45√(E/Fy)/(h/tw)
- φVn = 1,00·Vn

## Compresión (cap. 15) — columnas
- λc = (KL/r)π⁻¹·√(Fy/E)
- **(15-2)**: Fcr = 0,658^λc²·Fy  (λc ≤ 1,5)
- **(15-3)**: Fcr = 0,877/λc²·Fy  (λc > 1,5)
- Nn = Fcr·A · φNn = 0,85·Nn · aviso si KL/r > 200

## Interacción (cap. 18) — flexocompresión
- **(18-1a)**: Nu/φNn + 8/9·Mu/φbMn ≤ 1,0  (si Nu/φNn ≥ 0,2)
- **(18-1b)**: Nu/φNn + Mu/φbMn ≤ 1,0  (si Nu/φNn < 0,2)
- Mu = B1·Mu,primer-orden · B1 = Cm/(1 − Nu/Ne1) ≥ 1 · Ne1 = π²·E·Ix/L²
- Cm = 0,85 (miembro con cargas transversales — vigas-columna de pórtico;
  C-9: fórmulas (9-2)/(9-4), límite Austin)
- **P-Δ (B2)**: amplificación por deriva de piso θ = ΣPu·Δ/(ΣVu·h)
  (efectos de segundo orden; C-9.4/Fig. C-9.5): Mu = Mu/(1−θ); aviso si θ>0,25

## Flechas (estados límites de servicio)
- Caso de servicio SERV = 1,0·CP + 1,0·CV (gravedad, sin sismo)
- Flecha al centro del vano (viga con w y momentos Mi, Mj):
  f = 5wL⁴/(384EI) + (Mi+Mj)·L²/(16EI)  (kg·cm; hogging negativo)
- Límites: f ≤ L/300 (normal) · L/360 (exigente) — formulario
  DISEÑO DE ESTRUCTURAS.pdf, pág. 3

## Optimizador
- Verifica todos los perfiles de las series pedidas y devuelve el de
  **menor peso G (kg/m)** que cumpla TODOS los estados límites de su tipo
  (viga: flexión+corte+flecha · columna: compresión+interacción).
