# 🏗️ Análisis Estructural 2D

Software de **análisis estructural elástico de pórticos planos** con:

- **Motor de cálculo en Python** (método matricial de rigideces, NumPy)
- **Interfaz web interactiva** con la misma estética de las calculadoras del repo
- **Unidades técnicas**: kg · m · kg/cm² (convención venezolana)

```
┌────────────────────────────────────────────────────────────┐
│  Navegador (frontend)          Servidor local (backend)    │
│  ┌──────────────────┐   JSON   ┌─────────────────────┐     │
│  │ index.html       │ ───────► │ FastAPI  api.py     │     │
│  │ canvas.js (HTML5)│ ◄─────── │ engine/solver.py    │     │
│  │ estado.js        │          │ engine/modelo.py    │     │
│  └──────────────────┘          └─────────────────────┘     │
└────────────────────────────────────────────────────────────┘
```

## ▶️ Cómo usarlo

```bash
cd analisis-2d
./run.sh                      # crea .venv si falta y sirve en :8000
# abre http://localhost:8000
```

## 🧮 Motor de cálculo (`backend/engine/`)

Elemento de **marco plano** (3 GDL por nudo: ux, uy, θz), análisis elástico
lineal de primer orden:

| Archivo        | Contenido |
|----------------|-----------|
| `modelo.py`    | Entidades (Nudo, Barra, Apoyo, CargaNodal) + validaciones con mensajes amables |
| `solver.py`    | Rigidez local 6×6, transformación, ensamblaje, cargas equivalentes (FEF), partición libres/restringidos, reacciones, fuerzas de extremo, diagramas N(x) V(x) M(x), detección de mecanismos |
| `ejemplos.py`  | 7 estructuras de ejemplo (viga simple, voladizo, continua, pórticos, marco con cumbrera) |
| `covenin1756.py` | Motor sísmico COVENIN 1756-1:2019 (port del JS auditado del repo): espectro Ad(T) 7.18–7.23, μ, C/Cmín, Ta, Ft, Fi, Tablas 8–24, CSV vertical (8.4–8.5 + Tabla 19) |
| `acciones.py` | Fase 2: casos CP/CV/SH/SV, combinaciones §8.3.2 (8.6–8.15 con Ω₀ρ opcional), γ auto, envolvente con combinación gobernante |

**Convención de resultados internos**

- `N` → positivo en **tracción**
- `V` → positivo en **par horario** (viga con gravedad: V(0) = +wL/2)
- `M` → positivo en **flexión simple** (gravedad: M_vano = +wL²/8);
  el diagrama se dibuja en el lado de las fibras traccionadas
- Cargas de barra en el motor: `q_perp` y `q_axial` en ejes locales (+y local);
  la UI convierte la carga gravitacional ↓ global con
  `q_perp = −w·c`, `q_axial = −w·s`

**Verificación contra fórmulas cerradas** (`backend/tests_engine.py`, 8 casos):

1. Viga simple + UDL → wL²/8, 5wL⁴/384EI, ΣRy = wL ✓
2. Viga simple + P al centro → PL/4, PL³/48EI ✓
3. Voladizo → M = −PL, PL³/3EI ✓
4. Viga continua 2 tramos → R central = 1.25wL, M_apoyo = −wL²/8 ✓
5. Pórtico de cortante (viga rígida) → V = P/2, M_base = P·h/4, δ = P·h³/24EI ✓
6. Celosía articulada → diagonales −P√2/2, solera +P/2 ✓
7. Peso propio → ΣRy = γAL ✓
8. Detección de estructura inestable ✓

**Verificación de la Fase 2** (`backend/tests_combinaciones.py`, 6 tests): el port
del motor sísmico se compara contra los valores dorados del JS auditado (T1),
casos CP/CV/SH/SV (T2), γ §8.3.2.b (T3), superposición lineal (T4), SRSS (T5)
y envolvente gravitacional (T6).

```bash
.venv/bin/python backend/tests_engine.py          # motor (8 tests)
.venv/bin/python backend/tests_combinaciones.py   # acciones y combinaciones (6 tests)
```

El solver además autoverifica en cada corrida: ΣFx/ΣFy de reacciones contra
cargas, residuo del sistema (mecanismos), número de condición y modo rígido
descargado (avisos).

## 🖥️ Interfaz (`frontend/`) — pestañas de aplicación

**Pestaña «⚖️ Acciones y Combinaciones»** (`/acciones.html`, Fase 2):

- CP/CV por barra y por nudo (kg/m, kg) con aplicación rápida a todas
- Parámetros del sismo: A₀, A₁, T'L, grupo α, ND (R/Cd/Ω₀), sitio, topografía,
  H basamento, ρ, FI, Ct, fracción de CV (Tabla 20) y % de V₀ que toma el pórtico
- Combinaciones §8.3.2 automáticas (8.6–8.10, con 8.11–8.15 opcional por Ω₀ρ),
  γ auto (0,5 si CV < 500 kg/m²) o forzado
- Resultados: KPIs (AA, TC, Ta, μ, C, Cmín, V₀d, Ft, CSV, γ), gráfico del
  espectro Ad(T), tabla W/Fi por nivel, lista de combinaciones y **envolvente**
  N/V/M por barra, reacciones y desplazamientos con la combinación que gobierna

**Pestaña «🏗️ Análisis 2D»**:

- **Lienzo interactivo**: rejilla magnética 0,25 m, zoom con rueda, paneo,
  nudos/barras/apoyos/cargas con clic, barras encadenadas, arrastre de nudos.
- **Herramientas**: Seleccionar (S) · Nudo (N) · Barra (B) · Apoyo (A) ·
  Puntual (P) · Repartida (D).
- **Secciones**: catálogo auditado del repo (IPN SIDOR, IPE, HEB, HEA),
  rectangular b×h o A/I personalizados; materiales predefinidos (A36,
  concreto GC 210/280, madera).
- **Resultados**: diagramas M/V/N sobre el modelo, deformada, KPIs
  (δmáx, |M|máx, ΣRy, equilibrio), tablas de reacciones, fuerzas de barra
  y desplazamientos nodales.
- **Persistencia**: autosave en `localStorage`, guardar/abrir `.json`,
  7 ejemplos precargados.

## 📡 API

| Endpoint              | Descripción                        |
|-----------------------|------------------------------------|
| `POST /api/analizar`  | Análisis completo del modelo       |
| `POST /api/validar`   | Validación sin análisis            |
| `POST /api/combinaciones` | Casos CP/CV/SH/SV + combinaciones §8.3.2 + envolvente |
| `GET  /api/ejemplos`  | Lista de ejemplos                  |
| `GET  /api/ejemplos/{id}` | Modelo de ejemplo              |
| `GET  /api/salud`     | Ping                               |

## 🗺️ Ruta de crecimiento sugerida

1. **Fase 2 — Acciones y Combinaciones** ✅ HECHA: CP/CV + sismo estático
   equivalente + combinaciones §8.3.2 + envolvente (pestaña «Acciones»).
2. **Fase 3 — Diseño Acero COVENIN 1618-98**: tensión/compresión/flexión/
   interacción con las fuerzas de la envolvente (pestaña «Acero 1618»).
3. **Fase 4 — Plantillas**: pórtico simple, nave a dos aguas, cerchas planas
   y curvas (pestaña «Plantillas»).
4. **Fase 5 — Concreto y Madera** + rótulas, cargas sobre vanos, P-Δ.
