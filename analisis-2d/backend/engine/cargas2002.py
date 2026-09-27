# ==================================================================
#  cargas2002.py — COVENIN-MINDUR 2002-88
#  «Criterios y Acciones Mínimas para el Proyecto de Edificaciones»
#  ------------------------------------------------------------------
#  Fuente: ACERO/Norma2002_8_CRITERIOS.pdf (norma completa, 123 págs).
#  El Modelador toma de aquí las cargas: la carga viva mínima por uso
#  (Tabla 5.1), techos (§5.2.4), estacionamientos (§5.2.5), barandas
#  (§5.3.4), reducción por nº de pisos (§5.2.3), tabiquería (§4.4) y
#  pesos de materiales (Tablas 4.1/4.3).
#
#  Unidades del motor: kg, m  →  kgf/m² ≡ kg/m², kgf/m ≡ kg/m,
#  kgf/m³ ≡ kg/m³ (1 kgf = 1 kg en este sistema).
# ==================================================================

# ------------------------------------------------------------------
# TABLA 5.1 — Mínimas cargas distribuidas variables sobre entrepisos
#             (kgf/m²) · filas = tipo de edificación (1-8), columnas
#             = ambiente (A-O). None = sin valor en la norma (se
#             asimila a caso semejante — nota GENERAL de la Tabla).
# ------------------------------------------------------------------

AMBIENTES_5_1 = {
    "A": "Áreas públicas (pasillos, comedores, vestuarios, salas de estar)",
    "B": "Áreas privadas (oficinas, aulas, quirófanos, cocinas, lavanderías, servicios) (1)",
    "C": "Áreas con asientos fijos",
    "D": "Áreas con asientos móviles, salones de fiesta",
    "E": "Azoteas o terrazas (2) (3)",
    "F": "Balcón con L > 1,20 m (3) (4)",
    "G": "Bibliotecas, archivos y similares (5)",
    "H": "Escaleras y escaleras de escape (3)",
    "I": "Escenarios, plataformas y zonas de exposiciones",
    "J": "Estacionamientos (6)",
    "K": "Habitaciones; pasillo interno, camerinos, vestuarios, estudios de radio y TV, celdas",
    "L": "Áreas con cargas livianas de máquinas",
    "M": "Áreas con cargas medianas de máquinas",
    "N": "Depósitos en general (8) (9)",
    "O": "Techos (ver carga_techo §5.2.4.2)",
}

# tipo → (título, {ambiente: valor | ("nota", [notas])})
TIPOS_5_1 = {
    "1a": ("1a. Viviendas unifamiliares y multifamiliares", {
        "A": 300, "D": 500, "E": 100, "F": 300, "H": 300, "J": ("nota", 6),
        "K": 175,
    }),
    "1b": ("1b. Hoteles, moteles, clubes", {
        "A": 300, "B": 300, "C": 400, "D": 500, "E": 100, "F": 300,
        "G": ("nota", 5), "H": 500, "I": 500, "J": ("nota", 6), "K": 175,
        "L": 600, "M": 1200, "N": ("nota", [8, 9]),
    }),
    "2": ("2. Edificaciones educacionales (escuelas, liceos, universidades, institutos)",
          {
        "A": 400, "B": 300, "C": 400, "D": 500, "E": 100, "F": 300,
        "G": ("nota", 5), "H": 500, "I": 500, "J": ("nota", 6), "K": 175,
        "L": 600, "N": ("nota", 8),
    }),
    "3": ("3. Lugares de concentración pública (teatros, cines, restaurantes, culto, museos, gimnasios)",
          {
        "A": 500, "B": 300, "C": 400, "D": 500, "E": 100, "F": 300,
        "G": ("nota", 5), "H": 500, "I": 750, "J": ("nota", 6), "K": 175,
        "L": 600, "N": ("nota", [8, 9]),
    }),
    "4": ("4. Edificaciones institucionales (médico-asistenciales, cuarteles, cárceles, ministerios)",
          {
        "A": 300, "B": 250, "C": 400, "D": 500, "E": 100, "F": 300,
        "G": ("nota", 5), "H": 500, "I": 500, "J": ("nota", 6), "K": 175,
        "L": 600, "M": 1200, "N": ("nota", [8, 9]),
    }),
    "5": ("5. Edificaciones comerciales (almacenes, tiendas, supermercados, locales, oficinas y bancos)",
          {
        "A": 300, "B": 250, "C": 400, "D": 500, "E": 100, "F": 300,
        "G": ("nota", 5), "H": 500, "I": 500, "J": ("nota", 6), "K": 175,
        "L": 600, "N": ("nota", [8, 9]),
    }),
    "6": ("6. Transporte y depósitos (estacionamientos, depósitos livianos, frigoríficos, morgue)",
          {
        "A": 500, "B": 300, "C": 400, "D": 500, "E": 100, "F": 300,
        "G": ("nota", 5), "H": 500, "J": ("nota", 6), "K": 175, "L": 600,
        "N": ("nota", [8, 9]),
    }),
    "7": ("7. Edificaciones industriales (talleres, imprentas, estudios de radio, cine y TV)",
          {
        "A": 500, "B": 300, "C": 400, "D": 500, "E": 100, "F": 300,
        "G": ("nota", 5), "H": 500, "I": 750, "J": ("nota", 6), "K": 175,
        "L": 600, "M": 1200, "N": ("nota", 8),
    }),
    "8": ("8. Construcciones varias (heliopuertos, puentes peatonales, terminales)",
          {
        "A": 500, "B": 300, "C": 400, "D": 500, "E": 100, "F": 300,
        "G": ("nota", 5), "H": 500, "J": ("nota", 6), "K": 175, "L": 600,
        "N": ("nota", 8),
    }),
}

# Notas de la Tabla 5.1 (valores particulares que la UI ofrece como opciones)
NOTAS_5_1 = {
    1: {"oficinas": 250, "aulas_quirofanos_laboratorios": 300,
        "cocinas_servicios": 400},
    2: {"azotea_con_uso_minimo": 100},
    4: {"balcon_L_le_120_usa_nota_2": True,
        "carga_lineal_extremo_volado_kgf_m": 150},
    5: {"salas_lectura": 300, "salas_archivo_min": 500,
        "estanterias_libros_kgf_m2_por_m_altura": 250, "estanterias_min": 700},
    6: {"vehiculos_pasajeros": 250, "concentrada_kgf": 900,
        "autobuses_camiones": 1000},
    8: {"por_m_altura_deposito_min": 250,
        "libros_apilados_kgf_m2_por_m_altura": 1100},
    9: {"frigorificos_min": 1500, "morgue": 600},
}


def cp_minima(tipo, ambiente):
    """Carga variable mínima (kgf/m²) de la Tabla 5.1.
    Devuelve None si el ambiente no tiene valor para ese tipo (nota
    GENERAL: se asimila a un caso semejante)."""
    titulo, fila = TIPOS_5_1[tipo]
    v = fila.get(ambiente)
    if v is None:
        return None
    if isinstance(v, tuple):
        return None      # la celda es nota, no valor
    return v


def opciones_tipo():
    """[(clave, título)] para selectores de UI, en orden de la tabla."""
    return [(k, v[0]) for k, v in TIPOS_5_1.items()]


# ------------------------------------------------------------------
# §5.2.3 — Reducción de CV acumulada según nº de pisos soportados
#          (columnas, muros y fundaciones; NO aplica a depósitos ni
#          garajes; desde 3 pisos soportados)
# ------------------------------------------------------------------
REDUCCION_5_2_3 = {1: 1.0, 2: 1.0, 3: 0.9, 4: 0.8, 5: 0.7, 6: 0.6}


def factor_reduccion_cv(n_pisos_soportados, es_deposito_o_garaje=False):
    """Factor sobre ΣCV de los pisos soportados por el miembro."""
    if es_deposito_o_garaje or n_pisos_soportados < 3:
        return 1.0
    if n_pisos_soportados >= 7:
        return 0.5
    return REDUCCION_5_2_3[n_pisos_soportados]


# ------------------------------------------------------------------
# §5.2.4 — Azoteas y techos (kgf/m² de proyección horizontal)
# ------------------------------------------------------------------
AZOTEA_MIN_CON_USO = 100        # §5.2.4.1


def azotea_con_uso(cp_uso):
    """§5.2.4.1: la carga del uso, pero no menor de 100 kgf/m²."""
    return max(float(cp_uso), AZOTEA_MIN_CON_USO)


def carga_techo(pp_techo, pendiente_pct):
    """§5.2.4.2 — techo inaccesible salvo mantenimiento.
    pp_techo: peso propio del techo (kgf/m²) · pendiente_pct: %.
      pp < 50            → 40  (techos metálicos livianos)
      pp ≥ 50, p ≤ 15 %  → 100
      pp ≥ 50, p > 15 %  → 50
    Nota: las correas se verifican además para 80 kgf concentrados
    (no simultáneos con la carga uniforme)."""
    if pp_techo < 50:
        return 40.0
    return 100.0 if pendiente_pct <= 15 else 50.0


CONCENTRADA_CORREA_KGF = 80     # §5.2.4.2, no simultánea con la uniforme


# ------------------------------------------------------------------
# §5.2.5 — Estacionamientos
# ------------------------------------------------------------------
ESTACIONAMIENTO = {
    "autos": {"uniforme": 250, "concentrada_kgf": 900, "lado_cuadrado_m": 0.15},
    "autobuses_camiones": {"uniforme": 1000},
}


# ------------------------------------------------------------------
# §5.3.4 — Antepechos, barandas y pasamanos (kgf/m, transversal, en el
#          borde superior)
# ------------------------------------------------------------------
def baranda_kgf_m(uso_publico):
    return 100.0 if uso_publico else 50.0


# §5.3.1 tribunas: fuerza horizontal = 5 % de la CV de la grada
TRIBUNA_FRACCION = 0.05
# §5.3.3 apuntalamientos: 1 % de las cargas verticales, en la parte superior
APUNTALAMIENTO_FRACCION = 0.01


# ------------------------------------------------------------------
# §5.4.1 — Incrementos de CV verticales por impacto (fracciones)
# ------------------------------------------------------------------
IMPACTO_VERTICAL = {
    "apoyos_ascensores": 1.00,
    "grua_cabina": 0.25,
    "grua_controles_colgantes": 0.10,
    "maquinaria_liviana_min": 0.20,
    "maquinaria_oscilante_min": 0.50,
    "barras_suspension_unico_soporte": 1.00,
    "barras_suspension_otros": 0.33,
}


# ------------------------------------------------------------------
# §4.4 — Tabiquería
# ------------------------------------------------------------------
PESO_TABIQUERIA_EQUIVALENTE = 150   # kgf/m² mín. si el tabique no está definido
PESO_TABIQUERIA_LIVIANA = 100       # kgf/m² si peso unitario < 150 kgf/m
LIMITE_TABIQUE_LINEAL = 900         # kgf/m: ≤ 900 → carga equivalente distribuida


def carga_tabiquería(peso_lineal_kgf_m=None, definida=True, liviana=False,
                     area_panel_m2=None):
    """Carga distribuida equivalente de tabiquería (kgf/m²) — §4.4.
    · Tabique definido con peso ≤ 900 kgf/m → peso total / área del panel.
    · No definida → ≥ 150 kgf/m² (100 si liviana, peso unit. < 150 kgf/m).
    · Peso > 900 kgf/m → None (determinarse de manera más precisa; si
      corre sobre vigas se aplica como carga lineal)."""
    if not definida:
        return PESO_TABIQUERIA_LIVIANA if liviana else PESO_TABIQUERIA_EQUIVALENTE
    if peso_lineal_kgf_m is None:
        return None
    if peso_lineal_kgf_m > LIMITE_TABIQUE_LINEAL:
        return None
    if area_panel_m2 is None or area_panel_m2 <= 0:
        return None
    return peso_lineal_kgf_m / area_panel_m2


# Tabla 4.3.1 — tabiques de mampostería frisados por ambas caras (kgf/m²
# de pared; el peso lineal = kgf/m² × altura del tabique)
TABIQUES_4_3 = {
    ("bloque_arcilla", 10): 180, ("bloque_arcilla", 15): 230,
    ("bloque_arcilla", 20): 280,
    ("bloque_concreto", 10): 210, ("bloque_concreto", 15): 270,
    ("bloque_concreto", 20): 330,
    ("ladrillo_macizo", 12): 280, ("ladrillo_macizo", 25): 520,
}


# ------------------------------------------------------------------
# Tabla 4.1 — pesos unitarios probables (los de uso corriente)
# ------------------------------------------------------------------
PESOS_MATERIALES = {     # kgf/m³
    "concreto_armado_ordinario": 2500,
    "concreto_ordinario": 2400,
    "ladrillo_macizo_arcilla": 1800,
    "bloque_multicelular_arcilla": 1250,
    "bloque_hueco_concreto_liviano": 1400,
    "mortero_cemento": 2150,
    "mortero_cal_y_cemento": 1900,
    "cemento_en_sacos": 1600,
    "arena": 1600,
    "gravilla": 1800,
    "acero": 7850,          # (peso específico del acero; γ del motor)
}

# Tabla 4.3 — elementos constructivos corrientes (kgf/m²)
PESOS_ELEMENTOS = {
    "tabique_arcilla_10_frisado": 180,
    "tabique_arcilla_15_frisado": 230,
    "tabique_arcilla_20_frisado": 280,
    "tabique_concreto_10_frisado": 210,
    "tabique_concreto_15_frisado": 270,
    "tabique_concreto_20_frisado": 330,
    "machihembrado_sobre_correas": 50,
    "cielo_raso_colgado": 20,
    "impermeabilizacion_gravilla": 60,
    "impermeabilizacion_panelas": 80,
    "pavimento_vinilico_mortero_2cm": 50,
    "pavimento_gres_mortero_3cm": 80,
    "pavimento_granito_5cm": 100,
    "pavimento_marmol_2cm_mortero_3cm": 120,
    "pavimento_parquet_mortero_3cm": 70,
    "friso_por_cm": 19,      # cal y cemento (kgf/m² por cm de espesor)
}
