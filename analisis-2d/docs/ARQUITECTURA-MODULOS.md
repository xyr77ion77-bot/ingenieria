# 📐 Arquitectura de módulos — Análisis Estructural 2D

> **Principio acordado:** cada módulo es un **espacio de trabajo (pestaña) independiente**,
> con su propia pantalla, su propio panel de entrada y sus propios reportes.
> Comparten el motor de cálculo y el archivo de proyecto, pero **nunca se mezclan
> en una sola vista**.

---

## 1. Mapa de módulos y anclaje normativo

Los anclajes citan secciones verificadas de los PDFs de norma del propio repo
(`ACERO/*.pdf`).

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NÚCLEO COMPARTIDO (no visible)                    │
│  engine/  ·  método de rigideces 2D  ·  modelo JSON  ·  resultados  │
└───────────────┬───────────────┬───────────────┬─────────────────────┘
                │               │               │
   ┌────────────▼───┐ ┌─────────▼──────┐ ┌──────▼───────────┐
   │ PESTAÑA 1      │ │ PESTAÑA 2      │ │ PESTAÑA 3        │
   │ ANÁLISIS 2D    │ │ ACCIONES Y     │ │ PLANTILLAS       │
   │ (pórticos)     │ │ COMBINACIONES  │ │ (asistente)      │
   │ ✓ YA EXISTE    │ │ COVENIN 1756   │ │ pórticos, naves, │
   │                │ │ 2002 · 2003-86 │ │ cerchas          │
   ├────────────────┤ ├────────────────┤ ├──────────────────┤
   │ PESTAÑA 4      │ │ PESTAÑA 5      │ │ PESTAÑA 6        │
   │ DISEÑO ACERO   │ │ DISEÑO CONCRETO│ │ DISEÑO MADERA    │
   │ COVENIN 1618-98│ │ ACI 318 (ref.) │ │ NDS (ref.)       │
   └────────────────┘ └────────────────┘ └──────────────────┘
```

### M0 · Núcleo de cálculo (transversal, sin pestaña)

| Elemento | Estado |
|---|---|
| Método de rigideces, elemento marco plano 3 GDL/nudo | ✅ hecho |
| Cargas uniformes ⊥ y axiales, peso propio, cargas nodales | ✅ hecho |
| Diagramas N/V/M, reacciones, deformada, envolventes | ✅ (envolvente llega con M2) |
| **Futuro:** liberaciones de extremo (rótulas), elemento celosía (2 GDL), cargas puntuales y trapezoidales sobre vano, temperatura, presfuerzo externo | 🔜 según módulos |

### M1 · Pestaña «Análisis 2D» — modelación y análisis de pórticos

- Lo ya construido: nudos/barras/apoyos/cargas, diagramas, tablas.
- Aquí vive el **cálculo matricial** en sí. Nada de normativa: el usuario modela
  y calcula casos de carga individuales.
- Mejoras propias de esta pestaña: casos de carga nombrados (G1, G2, W, S1…),
  visibilidad por caso, comparación de casos.

### M2 · Pestaña «Acciones y Combinaciones» — COVENIN 1756-1:2019 + 2003-86 + 2002

**M2.1 — Acciones gravitacionales** (COVENIN 2002: cargas permanentes y variables)

| Acción | Símbolo | Fuente en la norma |
|---|---|---|
| Carga permanente (peso propio, acabados, tabiques, equipos fijos) | CP | 1756-1 §8.2.2.1 |
| Carga variable de uso (tabla de valores mínimos por uso) | CV | 1756-1 §8.2.2.2 + COVENIN 2002 |

→ Editor por elemento/planta: CP, CV (kg/m²), fracción de CV para peso sísmico
(tabla 20 del 1756-1).

**M2.2 — Acción del viento** (COVENIN 2003-86, basada en ANSI A58.1-1982)

- Presión básica por velocidad regional y coeficientes de exposición.
- Presiones/succiones sobre **paredes y techos** → cargas laterales sobre columnas
  y perpendiculares sobre vigas/cerchas del pórtico 2D.
- Caso: edificios y **naves industriales** (empujes generales + locales).

**M2.3 — Acción sísmica** (COVENIN 1756-1:2019)

| Concepto | Sección |
|---|---|
| Espectro inelástico Ad(T), parámetros A₀/A₁/T'L, factores de sitio | §7.2–7.3 |
| Combinación de componentes horizontales: SH = SX ± 0,3·SY (método del 30 %) o SRSS | §8.3.1.1 (fórmulas 8.1–8.3) |
| Componente vertical: SV = CSV·CP | §8.3.1.4 (fórmulas 8.4–8.5) |
| Peso sísmico efectivo W = CP + fracción de CV | §8.2.2 (tabla 20) |
| Análisis estático equivalente: Ta, C, V₀, reparto Fi, torsión adicional 6 % | §9.4 (con Tablas 24, 17, 15…) |

> 💡 El motor sísmico de estas fórmulas **ya existe auditado** en el repo
> (`ACERO/calculadora-sismica/js/covenin1756.js`) — se porta a Python, no se
> reescribe desde cero.

**M2.4 — Generador de combinaciones** (§8.3.2 — verificado contra el PDF)

```
Sin sobrerresistencia                     Con sobrerresistencia Ω₀·ρ
U = 1,2·CP + γ·CV ± SH + 0,3·SV   (8.6)   U = 1,2·CP + γ·CV ± (Ω₀ρ)·SH + 0,3·SV  (8.11)
U = 0,9·CP ± SH − 0,3·SV          (8.7)   U = 0,9·CP ± (Ω₀ρ)·SH − 0,3·SV        (8.12)
S = (Sx²+Sy²+Sv²)^½               (8.8)   S = ((Ω₀ρ)²(Sx²+Sy²)+Sv²)^½           (8.13)
U = 1,2·CP + γ·CV ± S             (8.9)   U = 1,2·CP + γ·CV ± S                 (8.14)
U = 0,9·CP ± S                    (8.10)  U = 0,9·CP ± S                        (8.15)
```

- γ = 0,5 si CV < 500 kg/m² (salvo reunión pública o estacionamiento); 1 en otros casos.
- Voladizos: acción vertical neta hacia arriba de 0,3·SV.
- Salida del generador: **lista de casos combinados** → cada uno se resuelve con
  el motor → **envolventes** M⁺/M⁻, V, N por barra y tabla de la combinación que
  gobierna cada resultado (firma de la combinación).

### M3 · Pestaña «Plantillas» — asistente de estructuras tipo

Genera el **modelo 2D paramétrico** (un plano resistente) listo para M1/M2:

| Plantilla | Parámetros | Notas normativas |
|---|---|---|
| Viga / pórtico simple | luces, alturas | — |
| **Nave industrial a dos aguas** | luces, altura de columnas, pendiente de techo, pórticos cada X m | viento 2003-86 con coefficientes de techo a 2 aguas |
| Nave con **cerchas planas** (Pratt/Howe/Warren) | luz, altura, # paneles, tipo | barras biarticuladas (elemento celosía) |
| Nave con **cercha curva** (arco parabólico/circular) | luz, flecha, # segmentos | la curva se discretiza en elementos rectos; succiones de techo curvo (2003-86) |

### M4 · Pestaña «Diseño Acero» — COVENIN 1618-98 (LRFD)

Basada en AISC LRFD (1993 + Suplementos). Verificaciones por miembro con las
fuerzas de la **envolvente de M2**:

| Verificación | Capítulo C |
|---|---|
| Tensión (fluencia y rotura) | C-D1, C-D2 |
| Compresión (pandeo, esbeltez, series de columnas) | C-E |
| Flexión ( Lateraltorsional, compacta) | C-F |
| Cortante | C-F4 |
| Interacción P-M | C-H |
| Conexiones/soldaduras | C-J |

Catálogo IPN/IPE/HEB/HEA ya cargado; optimización de perfil sugerido.

### M5 · Pestaña «Diseño Concreto» — (fase futura)

Venezuela diseña concreto con **ACI 318** (referido también por la propia
1618-98) y las exigencias sismorresistentes del 1756-1 (rigideces previsibles
§8.2.4.3, factor R). Flexión/cortante de vigas e interacción P-M de columnas.

### M6 · Pestaña «Diseño Madera» — (fase futura)

Sin norma COVENIN de diseño estructural de madera de uso generalizado; el
referente de práctica es NDS (EE. UU.). Ya existe base en el repo
(`ai_studio_code.html` incluye acero + madera).

---

## 2. Organización de la interfaz

- Barra superior de **espacios de trabajo** (pestañas de aplicación):
  `Análisis 2D · Acciones · Plantillas · Acero · Concreto · Madera`.
- Cada espacio: **página independiente** (ruta propia), su propio layout de
  3 paneles, sus propios resultados.
- **Proyecto compartido**: un solo archivo `.json` con el modelo + parámetros
  de acciones + combinaciones. Cambias de pestaña sin perder el proyecto.
- Regla: cada pestaña **consume** la envolvente de la anterior, no la duplica
  (`Plantillas → genera modelo → Análisis 2D → calcula casos → Acciones →
  combinaciones/envolvente → Acero → verifica perfiles`).

## 3. Fases de implementación

| Fase | Contenido | Estado |
|---|---|---|
| **F1** | Motor + Análisis 2D (M0, M1) | ✅ hecho y validado (8 tests) |
| **F2** | M2 Acciones y Combinaciones + envolvente (+ casos de carga en M1) | ✅ hecho (gravedad + sismo; viento queda para F4) |
| **F3** | M3 Plantillas: pórtico, nave a dos aguas, cercha plana, cercha curva | ⏳ |
| **F4** | M4 Diseño Acero 1618-98 (+ viento COVENIN 2003-86) | ⏳ **siguiente** |
| **F5** | M5/M6 Concreto y Madera | ⏳ |
