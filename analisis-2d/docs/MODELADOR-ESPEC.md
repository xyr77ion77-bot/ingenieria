# 📐 Especificación — Pestaña «Modelador» (Planta + Corte)

> Estado: **diseño aprobado por el usuario, pendiente de programación.**
> Principio: la geometría del edificio se define UNA vez (planta + cortes) y
> alimenta Análisis 2D, Acero y Concreto. Ninguna otra pestaña dibuja geometría.

---

## 1. Decisiones aprobadas

| # | Decisión | Elección |
|---|----------|----------|
| 1 | Ubicación | **Pestaña nueva «Modelador»** — fuente de geometría del proyecto |
| 2 | Pórticos | **Marcar ejes resistentes** X/Y en la planta (clic) |
| 3 | Corte editable | **Geometría + uniones** (secciones se asignan en Acero/Concreto) |
| 4 | Conexión con el motor | **Botón «Generar modelo 2D»** (sin sincronización automática) |
| 5 | Layout | **Split: planta izquierda · corte derecha**, siempre visibles |
| 6 | Niveles | **Globales del edificio** (una lista compartida; un pórtico puede tener menos) |
| 7 | Columnas en corte | **Activables/desactivables** (vano salteado con viga de luz completa) |
| 8 | Uniones | **Patrón global + excepción por nudo**; bases empotrada/articulada por columna |

Reutiliza el patrón de `ACERO/calculadora-sismica/js/canvas_planta.js`:
`estado → coordenadas → dibujo → hitBoxes → pointer events`, ejes numerados
(1,2,3… en X / A,B,C… en Y), ± vanos, área tributaria, «perfil real» y
exportar PNG para la memoria de cálculo.

---

## 2. Layout de la pestaña

```
┌────────────────────────────────────────────────────────────────────────────┐
│ ⚙️ Modelador      [Estructura: Nave 4 ejes × 3 ejes]   [💾] [PNG] [⤢]      │
│ ┌───────────────────────────────┐  ┌─────────────────────────────────────┐ │
│ │ PLANTA                        │  │ CORTE · Eje 2 (X)  ▾ [1][2][3][A]…  │ │
│ │     1    2    3    4          │  │  N3 ───┌──┐───┌──┐───┌──┐─── h=3.20  │ │
│ │  A ▓────▓────▓────▓           │  │     ───┤R ├───┤R ├───┤R ├───          │ │
│ │    5.0  5.0  5.0              │  │  N2 ───┌──┐───┌──┐───┌──┐─── h=3.20  │ │
│ │  B ▓────▓────▓────▓           │  │     ───┤R ├───┤R ├───┤R ├───          │ │
│ │  C ▓────▓────▓────▓  ▓=pórtico│  │  N1 ───┌──┐───┌──┐───┌──┐─── h=4.00  │ │
│ │  D ▓────▓────▓────▓           │  │     ───┤E ├───┤E ├───┤E ├───          │ │
│ │                               │  │  ═╧═══ ═╧══ ═╧═══ ═╧══  bases        │ │
│ │ [± vanos X] [± vanos Y]       │  │                                     │ │
│ │ Resist. X: 1,3   Y: A,C       │  │ [± nivel] [patrón uniones ▾]        │ │
│ └───────────────────────────────┘  └─────────────────────────────────────┘ │
│                    [ ⚡ Generar modelo 2D de este pórtico ]                 │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Vista PLANTA (izquierda)

### Dibujo
- Retícula de ejes: verticales `1..n` (vanos X = `lx[]`) y horizontales `A..`
  (vanos Y = `ly[]`) — igual que `canvas_planta.js`.
- **Ejes resistentes**: los ejes marcados se dibujan gruesos con sombreado ▓
  y color por dirección (X = rojo, Y = azul).
- Nudos de cruce: círculo pequeño (clic → seleccionar cruce, como hoy).
- Modo «perfil real» (heredado): vigas con peralte y columnas con huella
  cuando haya sección asignada.
- Área tributaria sombreada al pasar el cursor por un nudo (medios vanos;
  en bordes no sale del edificio).
- Etiquetas de vano con su longitud al centro de cada tramo.

### Interacciones
| Acción | Gesto |
|---|---|
| Añadir vano X / Y | botón «+» (o arrastrar el último eje) |
| Eliminar vano | botón «−» del último vano (con confirmación) |
| Editar luz de un vano | clic en el tramo → campo numérico (como hoy) |
| **Marcar/desmarcar pórtico resistente** | **clic en el eje (línea completa)** |
| Elegir pórtico para el corte | clic en el eje marcado → carga su corte a la derecha |
| Exportar PNG | botón (memoria de cálculo) |

### Reglas (COVENIN 1756-1)
- Aviso si hay **menos de 2 pórticos resistentes por dirección**: afecta el
  factor de redundancia ρ (§6.3, Tabla 13) — la UI muestra el conteo
  `Resist. X: n · Y: m` y sugiere ρ según los planos sismorresistentes.
- El corte solo puede abrirse en ejes **marcados como resistentes**.

---

## 4. Vista CORTE (derecha)

El corte es la **elevación de un pórtico** (un eje resistente): columnas en
los cruces con los ejes perpendiculares, vigas entre ellas, niveles apilados.

### Elementos dibujados
- **Niveles** como líneas horizontales etiquetadas `N1, N2…` con su altura
  acumulada (y h de piso al costado).
- **Columnas**: trazos verticales entre niveles en cada eje perpendicular
  activo; las **desactivadas** se dibujan punteadas/gris (vano salteado).
- **Vigas**: trazo horizontal entre columnas activas, con la luz del vano
  (heredada de la retícula de planta).
- **Uniones**: símbolo en cada nudo — ⌐ sólido = rígida, circulito = articulada.
- **Bases**: triángulo relleno (empotrada) / triángulo con ruedas (articulada).

### Interacciones
| Acción | Gesto |
|---|---|
| Cambiar de pórtico | selector de ejes arriba (o clic en la planta) |
| Añadir/quitar nivel | botones «± nivel» (edita la lista global) |
| Editar altura de piso | clic en la etiqueta h del nivel (global: aplica a todos) |
| Pórtico con menos niveles | botón «este pórtico termina aquí» (recorta hacia arriba) |
| Desactivar/reactivar columna | clic sobre la columna (vano salteado) |
| Patrón de uniones | select: «P-RM todo rígido» / «vigas articuladas» / «todo articulado» |
| Excepción de unión | clic en el nudo (alterna rígida/articulada, marca ⚡excepción) |
| Base de cada columna | clic en la base (alterna empotrada/articulada) |
| Exportar PNG | botón |

### Reglas
- Las luces de vano del corte **vienen de la planta** (no se editan aquí).
  Si desactivas la columna B del eje 2: la viga A→C queda de luz `la+lb`
  y el vano marcado como «salteado».
- Al cambiar el patrón de uniones se reemplazan las configuraciones **no
  marcadas como excepción**.
- Cada pórtico guarda su propia configuración (columnas activas, uniones,
  bases, niveles propios) — los niveles y luces son globales.

---

## 5. Modelo de datos (sección `modelador` del proyecto .json)

```json
{
  "modelador": {
    "geometria": {
      "lx": [5.0, 5.0, 5.0],
      "ly": [5.0, 5.0, 4.0, 4.0],
      "niveles": [ { "nombre": "N1", "h_piso": 4.0 },
                   { "nombre": "N2", "h_piso": 3.2 },
                   { "nombre": "N3", "h_piso": 3.2 } ]
    },
    "ejes_resistentes": { "X": [1, 3], "Y": ["A", "C"] },
    "cortes": {
      "X:1": {
        "niveles_propios": 3,
        "columnas": { "A": { "activa": true, "base": "empotrada" },
                      "B": { "activa": false },            // vano salteado
                      "C": { "activa": true, "base": "articulada" },
                      "D": { "activa": true, "base": "empotrada" } },
        "uniones": { "patron": "pr_momento",
                     "excepciones": { "N2|C": "articulada" } }
      }
    }
  }
}
```

Convención: `cortes["X:1"]` = pórtico del eje vertical 1 (corre en Y, columnas
en A..D). `cortes["Y:A"]` = pórtico del eje A (corre en X, columnas en 1..n).

---

## 6. Flujo «⚡ Generar modelo 2D» (mapa al motor)

Para el pórtico abierto en el corte:

1. **Nudos**: intersección de columnas activas × niveles propios.
2. **Barras**:
   - columna activa → elemento marco entre nivel k y k+1 (o desactivada: se omite);
   - viga entre columnas activas consecutivas en cada nivel;
     vano salteado → una sola barra con L = Σ luces.
3. **Apoyos**: base de cada columna → empotrada (ux,uy,rz) o articulada (ux,uy).
4. **Uniones**:
   - rígida → nada (elemento marco actual);
   - articulada → requiere **liberaciones de extremo** (M=0) en la barra.

> ⚠️ **Dependencia del motor**: hoy el solver NO tiene liberaciones de extremo.
> Para los patrones con vigas articuladas hace falta la extensión planificada
> del núcleo (M0: «liberaciones rótula»). Mientras no exista, la UI ofrece:
> (a) bloquear patrones articulados con nota, o (b) aproximación I≈10⁻⁴·I
> (no recomendada: condiciona la matriz). **Decisión sugerida: implementar
> liberaciones como primer paso de programación del Modelador.**

5. El modelo generado se abre en la pestaña **Análisis 2D** como modelo nuevo
   (título «Pórtico X:1») y de ahí fluye a Acciones → Acero/Concreto.
   No se sobreescribe ningún modelo existente (opción elegida: botón).

---

## 7. Cómo la usan las otras pestañas

| Pestaña | Uso del Modelador |
|---|---|
| Análisis 2D | recibe el modelo generado (botón) |
| Acciones | el peso sísmico por nivel podrá derivarse del área tributaria de la planta × CP/CV por m² (fase posterior) |
| Acero 1618 | lista de pórticos generados; asigna perfil por nivel/tipo y diseña con la envolvente |
| Concreto | igual que Acero con secciones rectangulares |
| Plantillas | pre-llena la retícula (nave a dos aguas, cerchas) — el Modelador es su lienzo |

---

## 8. Orden de programación propuesto (cuando des el visto bueno)

1. **Liberaciones de extremo en el motor** (rótula M=0) + tests — prerequisite.
2. Esqueleto de la pestaña Modelador + vista Planta (retícula, vanos, ejes
   resistentes) con el patrón de canvas_planta.js.
3. Vista Corte (niveles, columnas on/off, uniones, bases) + modelo de datos.
4. Botón «Generar modelo 2D» + mapping al motor + tests de mapping.
5. Pulido: perfil real, área tributaria, exportar PNG, avisos de ρ.
