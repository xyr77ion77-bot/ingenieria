# ingenieria

Workspace de ingeniería estructural (normativa COVENIN, Venezuela).

## Contenido

| Carpeta | Descripción |
|---------|-------------|
| **`analisis-2d/`** | 🏗️ **Software de análisis estructural 2D** — motor Python (método de rigideces) + interfaz web interactiva. Ver [`analisis-2d/README.md`](analisis-2d/README.md). |
| `ACERO/` | Calculadoras HTML (sismo COVENIN 1756-1:2019, acero), normas en PDF (COVENIN 1756-1, 1618, 2003), hoja de cálculo de diseño y el proyecto modular `calculadora-sismica/`. |
| `OBRAS-HIDRAULICAS/` | 💧 **U.C. Obras Hidráulicas (Tema 4)** — Informe de investigación, **Caso 5 · Municipio Páez · Piedemonte y terrazas de El Guapo**: `Informe_Caso5_Municipio_Paez_ElGuapo.docx` (Word, listo para entregar). Incluye fuentes en `report_text.py`, generador `build_docx.py` y figuras. |

## Arranque rápido del software

```bash
cd analisis-2d && ./run.sh   # → http://localhost:8000
```

## Regenerar el informe de Obras Hidráulicas

```bash
cd OBRAS-HIDRAULICAS
python3 build_figs.py && python3 build_docx.py   # → Informe_Caso5_Municipio_Paez_ElGuapo.docx
```
