# ==================================================================
#  tests_cargas2002.py — COVENIN-MINDUR 2002-88 (criterios de cargas)
#  Valores dorados tomados de ACERO/Norma2002_8_CRITERIOS.pdf:
#    · Tabla 5.1 (p. 33 impresa): cargas vivas mínimas por uso
#    · §5.2.3 reducción por pisos · §5.2.4 techos · §5.2.5 estacion.
#    · §5.3.4 barandas · §4.4 tabiquería · Tabla 4.1 materiales
# ==================================================================

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine import cargas2002 as C

FALLOS = []


def chequear(nombre, condicion, detalle=""):
    ok = bool(condicion)
    print(("✓" if ok else "✗"), nombre, detalle)
    if not ok:
        FALLOS.append(nombre)


def aprox(a, b, tol=1e-9):
    return a is not None and b is not None and abs(a - b) <= tol


# ---------- Tabla 5.1 (valores leídos de la norma) ----------
chequear("T1a Vivienda: habitaciones (K) = 175",
         C.cp_minima("1a", "K") == 175)
chequear("T1b Vivienda: escaleras (H) = 300",
         C.cp_minima("1a", "H") == 300)
chequear("T1c Vivienda: azotea (E) = 100",
         C.cp_minima("1a", "E") == 100)
chequear("T1d Hoteles: áreas privadas (B) = 300",
         C.cp_minima("1b", "B") == 300)
chequear("T1e Educacional: áreas públicas (A) = 400, aulas (B) = 300",
         C.cp_minima("2", "A") == 400 and C.cp_minima("2", "B") == 300)
chequear("T1f Concentración: escenarios (I) = 750",
         C.cp_minima("3", "I") == 750)
chequear("T1g Comercial/institucional: oficinas (B) = 250",
         C.cp_minima("5", "B") == 250 and C.cp_minima("4", "B") == 250)
chequear("T1h Todos los tipos: asientos móviles (D) = 500",
         all(C.cp_minima(t, "D") == 500
             for t in ("1b", "2", "3", "4", "5", "6", "7", "8")))
chequear("T1i Vivienda no define bibliotecas (G) → None",
         C.cp_minima("1a", "G") is None)
chequear("T1j Industrial: máquinas medianas (M) = 1200",
         C.cp_minima("7", "M") == 1200)
chequear("T1k Maquinaria liviana (L) = 600 (tipos 1b-8; 1a no la define)",
         all(C.cp_minima(t, "L") == 600
             for t in ("1b", "2", "3", "4", "5", "6", "7", "8")))

# ---------- §5.2.3 reducción por pisos ----------
chequear("T2a 2 pisos → 1.0", C.factor_reduccion_cv(2) == 1.0)
chequear("T2b 4 pisos → 0.8", C.factor_reduccion_cv(4) == 0.8)
chequear("T2c 6 pisos → 0.6", C.factor_reduccion_cv(6) == 0.6)
chequear("T2d 10 pisos → 0.5", C.factor_reduccion_cv(10) == 0.5)
chequear("T2e Depósitos/garajes NO se reducen",
         C.factor_reduccion_cv(6, es_deposito_o_garaje=True) == 1.0)

# ---------- §5.2.4 azoteas y techos ----------
chequear("T3a Azotea con uso 180 → 180",
         C.azotea_con_uso(180) == 180)
chequear("T3b Azotea con uso 60 → 100 (mínimo)",
         C.azotea_con_uso(60) == 100)
chequear("T3c Techo metálico liviano (pp 30) → 40",
         C.carga_techo(30, 10) == 40)
chequear("T3d Techo pp 120 pendiente 10 % → 100",
         C.carga_techo(120, 10) == 100)
chequear("T3e Techo pp 120 pendiente 30 % → 50",
         C.carga_techo(120, 30) == 50)

# ---------- §5.2.5 estacionamientos ----------
chequear("T4a Autos: 250 kgf/m² + 900 kg concentrada",
         C.ESTACIONAMIENTO["autos"]["uniforme"] == 250
         and C.ESTACIONAMIENTO["autos"]["concentrada_kgf"] == 900)
chequear("T4b Autobuses/camiones: 1000 kgf/m²",
         C.ESTACIONAMIENTO["autobuses_camiones"]["uniforme"] == 1000)

# ---------- §5.3.4 barandas ----------
chequear("T5a Baranda uso público = 100 kgf/m",
         C.baranda_kgf_m(True) == 100)
chequear("T5b Baranda vivienda = 50 kgf/m",
         C.baranda_kgf_m(False) == 50)

# ---------- §4.4 tabiquería ----------
chequear("T6a No definida → 150 kgf/m²",
         C.carga_tabiquería(definida=False) == 150)
chequear("T6b No definida liviana → 100 kgf/m²",
         C.carga_tabiquería(definida=False, liviana=True) == 100)
chequear("T6c 500 kgf/m sobre panel de 12,5 m² → 40 kgf/m²",
         aprox(C.carga_tabiquería(500, area_panel_m2=12.5), 40))
chequear("T6d > 900 kgf/m → None (se calcula con precisión)",
         C.carga_tabiquería(1200, area_panel_m2=10) is None)

# ---------- Tabla 4.3 tabiques frisados ----------
chequear("T7a Bloque arcilla 15 cm frisado = 230 kgf/m²",
         C.TABIQUES_4_3[("bloque_arcilla", 15)] == 230)
chequear("T7b Bloque concreto 20 cm frisado = 330 kgf/m²",
         C.TABIQUES_4_3[("bloque_concreto", 20)] == 330)
chequear("T7c Ladrillo macizo 25 cm frisado = 520 kgf/m²",
         C.TABIQUES_4_3[("ladrillo_macizo", 25)] == 520)

# ---------- Tabla 4.1 materiales ----------
chequear("T8a Concreto armado ordinario = 2500 kgf/m³",
         C.PESOS_MATERIALES["concreto_armado_ordinario"] == 2500)
chequear("T8b Concreto ordinario = 2400 kgf/m³",
         C.PESOS_MATERIALES["concreto_ordinario"] == 2400)

# ---------- ejemplo de uso del Modelador ----------
# Edificio comercial de 5 pisos: oficinas B=250; columna que soporta
# 4 pisos + techo (5 niveles) → ΣCV reducida al 70 %
cp = C.cp_minima("5", "B")
f5 = C.factor_reduccion_cv(5)
chequear("T9 Oficinas (250) × 5 pisos soportados → factor 0,7",
         cp == 250 and f5 == 0.7,
         f"ΣCV_col = 5·250·0,7 = {5 * 250 * f5:.0f} kgf/m²")

print()
if FALLOS:
    print(f"═══ {len(FALLOS)} TESTS DE CARGAS 2002-88 FALLARON ═══")
    sys.exit(1)
print("═══ TODOS LOS TESTS DE CARGAS 2002-88 PASARON ═══")
