# 📦 COVENIN-MINDUR 2002-88 — Criterios de cargas para el Modelador

> Fuente: `ACERO/Norma2002_8_CRITERIOS.pdf` («Criterios y Acciones Mínimas
> para el Proyecto de Edificaciones», 123 págs. — texto extraído y moduleado).
> **Módulo**: `backend/engine/cargas2002.py` · **Tests**:
> `backend/tests_cargas2002.py` (35 checks). El usuario ordenó: *«las cargas
> del Modelador serán como la de esta norma»*.

## 1. Cargas variables verticales — Tabla 5.1 (kgf/m²)

Matriz completa en `TIPOS_5_1`: **8 tipos de edificación** (1a viviendas,
1b hoteles, 2 educacional, 3 concentración pública, 4 institucional,
5 comercial, 6 transporte/depósitos, 7 industrial, 8 varias) × **15
ambientes** (A áreas públicas … O techos). Valores clave:

| Ambiente | Valor más frecuente |
|---|---|
| K Habitaciones (vivienda) | **175** |
| B Oficinas (comercial/institucional) | **250** (nota 1) |
| B Aulas/quirófanos/laboratorios | **300** (nota 1) |
| B Cocinas/servicios | **400** (nota 1) |
| A Áreas públicas | 300–500 según tipo |
| C/D Asientos fijos/móviles | 400 / 500 |
| H Escaleras | 300 (vivienda) · 500 (resto) |
| L/M Máquinas livianas/medianas | 600 / 1200 |
| E Azotea con uso | uso, **≥100** (§5.2.4.1) |
| J Estacionamientos | 250 autos + **900 kg** puntual en cuadrado de 15 cm · 1000 autobuses (§5.2.5) |
| O Techos | ver §5.2.4.2 abajo |

Celdas sin valor en la norma → `None` (nota GENERAL: asimilar a caso
semejante). La columna O (techos) no es de la matriz: se calcula.

## 2. Techos — §5.2.4.2 (`carga_techo()`)

| Caso | Carga (kgf/m² proyección horizontal) |
|---|---|
| Techo metálico liviano, pp < 50 | **40** (+ correas: 80 kg concentrados, no simultáneos) |
| pp ≥ 50, pendiente ≤ 15 % | **100** |
| pp ≥ 50, pendiente > 15 % | **50** |

## 3. Reducción de CV acumulada — §5.2.3 (`factor_reduccion_cv()`)

Columnas, muros y fundaciones que soportan **3+ pisos** (no depósitos/garajes):

| Pisos soportados | 3 | 4 | 5 | 6 | ≥7 |
|---|---|---|---|---|---|
| ΣCV acumulada | 0,9 | 0,8 | 0,7 | 0,6 | 0,5 |

## 4. Horizontales y especiales

- **Barandas** §5.3.4: 100 kgf/m (uso público) · 50 kgf/m (privado), en el
  borde superior (`baranda_kgf_m`).
- **Tribunas** §5.3.1: 5 % de la CV de la grada, horizontal.
- **Impacto** §5.4.1: ascensores +100 %, grúa cabina +25 % / colgantes +10 %,
  maquinaria liviana ≥+20 % / oscilante ≥+50 %, barras de suspensión 100/33 %.
- **Balcones** nota 4: carga lineal de 150 kgf/m en el extremo del volado.

## 5. Cargas permanentes — cap. 4

- **Tabiquería** §4.4 (`carga_tabiquería`): definida ≤900 kgf/m → peso total /
  área del panel; **no definida → 150 kgf/m²** (100 si liviana); >900 kgf/m →
  análisis preciso / carga lineal sobre viga.
- **Tabla 4.3** tabiques frisados: bloque arcilla 10/15/20 cm = 180/230/280;
  bloque concreto = 210/270/330; ladrillo macizo 12/25 cm = 280/520.
- **Tabla 4.1** materiales: **concreto armado ordinario 2500 kgf/m³** (el
  valor de la norma), concreto simple 2400, ladrillo macizo 1800, mortero de
  cemento 2150. Tabla 4.3: pavimentos 50–120, impermeabilización 60–80,
  cielo raso colgado 20.

## 6. Cómo lo usa el Modelador

1. **Por nivel** (vista Corte): se elige tipo de edificación (global) y
   ambiente de cada nivel → CP y tabiquería del nivel salen de la norma
   (editables como override).
2. **Peso sísmico**: nivel → (CP + tabiquería + PP losa) × área tributaria
   (de la planta) — alimenta la pestaña Acciones (COVENIN 1756-1).
3. **Reducción §5.2.3**: la aplica el diseñador de columnas (Acero/Concreto)
   con el conteo de pisos soportados por cada miembro.
4. El techo se modela como un nivel «azotea» con `carga_techo(pp, pendiente)`
   o como azotea de uso con `azotea_con_uso()`.
