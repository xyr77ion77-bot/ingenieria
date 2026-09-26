# 📊 Base de datos de perfiles de acero

Fuente: catálogos **ArcelorMittal** en `ACERO/*.pdf` (subidos por el usuario)
+ `ACERO/HEB.jpg` (formato SIDOR, cm).

## Estado de la ingesta

| Serie | Perfiles | Validados | Estado |
|---|---|---|---|
| IPN | 21 | 21 ✓ | **convertida** |
| IPE (+IPEA/IPEV) | 28 | 28 ✓ | **convertida** |
| HE (HEAA/HEA/HEB/HEC/HEM) | 114 | 114 ✓ | **convertida** |
| HD | 14 | 14 ✓ | **convertida** |
| HP | 21 | 21 ✓ | **convertida** |
| UPN / UPE / U | — | — | raw extraído, conversión pendiente |
| L iguales/desiguales | — | — | raw extraído, conversión pendiente |
| FL / R / SQ / SQ-r | — | — | raw extraído, conversión pendiente |
| HLZ / HL | — | — | raw extraído, conversión pendiente |

## Pipeline (2 fases)

1. `extraer_catalogos.py` — PDF → `raw/<serie>_p<n>.json`
   Reconstruye la retícula de la tabla desde las **líneas vectoriales**
   (pymupdf `get_drawings`) y asigna a cada celda el texto detectado por
   **RapidOCR** (los PDFs tienen el texto vectorizado con codificación
   corrupta; no hay texto extraíble directo).
2. `convertir_catalogos.py` — raw → `json/<serie>.json`
   Mapea columnas por serie (layouts distintos: IPN tiene r1/r2, IPE lleva
   r + d2, HE/HD/HP otro orden), normaliza designaciones
   (HE 100 B → **HEB100**, HD 260×54,1 → **HD260x54.1**) y **valida
   físicamente cada fila**:
   - `Wel,y ≈ 2·Iy/h` (±3 %)
   - `iy ≈ √(Iy/A)` (±3 %)
   - `G ≈ 0,785·A` (±3 %)
   Las filas con celdas perdidas por OCR se corrigen a mano en
   `correcciones_manuales.json` (documentadas; hoy: HEB160, HEB800).

## Esquema final (unidades técnicas)

`dims en mm · A cm² · I cm⁴ · S/W cm³ · r cm · G kg/m`

Campos: `nombre, alias, serie, G, h, b, tw, tf, r1/r, r2, A, d, orificio,
pmin, pmax, Ix, Sx (Wel,y), Zx (Wpl,y), rx, Avz, Iy, Zy, ry, Sy (dist.
centro cortante), It, Iw, validacion[]`

## Notas de validación cruzada

- **IPN 80**: A=7,57 cm² (DIN 1025-1) — *reemplaza* el A=8,03 del catálogo
  viejo "auditado" de `calculadora-sismica` (decisión del usuario).
- IPE 300: A=53,8 / Sx=557 → idéntico al catálogo auditado del repo ✓
- HEB 160: A=54,3 ✓ / Sx=311,5 (EN 10365; el repo viejo traía 276, valor
  de otra edición de tabla).
