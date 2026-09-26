# BD de perfiles de acero (ArcelorMittal → JSON)

Fuente única de verdad para el diseño (lo que consume el motor cuando el
usuario pide «perfil»: **Sx = Wel,eje fuerte** es el campo crítico).

## Estado — 874 perfiles · 874 validados (100 %)

| Serie | Archivo | Perfiles | Validados |
|---|---|---:|---:|
| IPN | `json/IPN.json` | 21 | 21 |
| IPE (+AA/A/O/V) | `json/IPE.json` | 68 | 68 |
| HE (AA/A/B/C/M) | `json/HE.json` | 124 | 124 |
| HD | `json/HD.json` | 42 | 42 |
| HP | `json/HP.json` | 31 | 31 |
| UPN | `json/UPN.json` | 18 | 18 |
| UPE | `json/UPE.json` | 14 | 14 |
| U (americano) | `json/U.json` | 5 | 5 |
| L lados iguales | `json/L-lados-iguales.json` | 183 | 183 |
| L lados desiguales | `json/L-lados-desiguales.json` | 31 | 31 |
| FL (planas) | `json/FL.json` | 253 | 253 |
| R (redondos) | `json/R.json` | 26 | 26 |
| SQ (cuadrados) | `json/SQ.json` | 21 | 21 |
| HLZ/HL | `json/HLZ-HL-1.json` | 37 | 37 |

Total: **874 perfiles**. Nota: la versión anterior (posicional) extraía
114 HE y 14 HD; el mapeo por cabeceras reveló que las tablas reales tienen
124 HE (faltaban HE650x343…HE1000x584), 42 HD (HD400x216…HD400x1299) y las
variantes IPE AA/A/O/V (~40 perfiles más).

## Campos de la ficha

`nombre, alias, serie, G (kg/m), h, b, tw, tf, r/r1/r2(/r3), A (cm²),
d (h−2tf), hi (d−2r, solo IPE), P/pmin/pmax (detallado), emin/emax (canales),
orificio (M12/M20/M24/M27), z0/y0/v (angulares), u1/u2, AL (m²/m),
AG (m²/t), Ix, Sx, Zx, rx, Avz, Iy, Sy, Zy, ry, y_c/e_sc (canales),
Iu/ru/Iv/rv/yz (angulares), It, Iw`

Unidades: dims mm · A cm² · I cm⁴ · W/S cm³ · r cm · G kg/m.
Serie L-iguales: `h = b` (una sola columna de lado en la tabla).
R/SQ/FL se **generan por fórmulas exactas** (EN 10056/58/59), no se parsean:
R 26 diámetros · SQ 21 lados · FL 253 pares b×t (t ≤ b/2); G = 0,785·A.

## Pipeline (2 fases)

1. **`extraer_catalogos.py`** — PDF → render 200 dpi → RapidOCR →
   `raw/{serie}_p{n}.json` (celdas con coordenadas x/y). Idempotente.
2. **`convertir_catalogos.py`** — raw → `json/{serie}.json`:

   - **Columnas por cabecera**: la fila que contiene `G kg/m` define los
     centros de columna (clusters de X, eps 9). Se excluye la columna de
     designación y las cabeceras sin datos debajo (fragmentos `mm` del OCR).
   - **Clasificación de página** `dims`/`props` por el texto de su cabecera
     (`tw|tf|h mm` vs `Wel|Wpl`). **Join global por alias** dentro de la
     serie (las páginas de props se desbordan respecto a las de dims).
   - **Layouts por familia** en `FAMILIAS` (IPN 13 · IPE 13 · HE 13 · HE_P 12
     para HL/HLZ · UPN 13 · UPE 13 · U 11 · LIG 11 · LIG_BIG 13 · LDE 15);
     la familia angular se elige por nº de columnas.
   - **Designaciones tolerantes**: pies de nota `+/*`, `·/+`, `-74/*k`, `x`
     final; variantes intermedias `IPE AA/A/O/V`.
   - **Recuperación por G**: filas de dims cuya designación se perdió se
     emparejan (±0,5 %, único) con registros props-only.
   - **Fusión de alias con dígitos basura** (`L70x70x91` = `L70x70x9`)
     cuando son complementarios (uno con dims, otro con props) y el G cuadra.

## Validación automática (±3 %)

- `rx ≈ √(Ix/A)` (todas),
- `Sx ≈ 2Ix/h·10` (no aplica a angulares ni planas FL),
- `G ≈ 0,785·A` (γ = 7 850 kg/m³),
- campos mínimos presentes (G, A, h, Ix, Sx).

## Correcciones manuales (`correcciones_manuales.json`)

| Alias | Problema | Corrección |
|---|---|---|
| HEB160 | OCR perdió tw en p1 | tw=8, A=54,3, Sx=311,5 (fila p2 completa) |
| HEB800 | OCR perdió r | r=30 (p7/p8 completas) |
| L250x250x34 | designación p11 ilegible | h=b=250, tw=34, A=158=G/0,785 |
| IPEV450 | PDF imprime G=107 con A=132 (γ imposible 8,11) | G=103,6=0,785·A |

## Cruces de comprobación

- IPE300: A=53,8 · Sx=557 (coincide con el catálogo «auditado» viejo).
- IPN80: A=7,57 · Sx=19,5 — el catálogo nuevo GANA sobre el viejo (8,03).
- UPN200: Sx=191, Iy=148, y_c=2,01 · UPE200: Sx=191, e_sc=3,94.
- L100x65x7: Iy=37,58 · Sx=16,61 · yz=−37,7 (negativo ✓).
- HLZ1100A: G=393,1 · Ix=983 100 · rx=44,30 · R10: A=0,785 · G=0,617.
