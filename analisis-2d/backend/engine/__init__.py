# ==================================================================
#  motor — Análisis estructural 2D por el método de matricial de
#  rigideces (pórticos planos: 3 GDL por nudo: ux, uy, θz).
#
#  SISTEMA DE UNIDADES (coherente en todo el motor):
#    Geometría ....... m
#    Fuerzas ......... kg
#    Momentos ........ kg·m
#    Material ........ E en kg/cm²  (se convierte internamente a kg/m²)
#    Secciones ....... A en cm², I en cm⁴ (se convierten a m², m⁴)
#    Cargas repartidas en kg/m
#
#  Los resultados salen en: kg, kg·m, m (desplazamientos), rad (giros).
# ==================================================================

from .modelo import Nudo, Barra, Apoyo, CargaNodal, Modelo, ERROR
from .solver import analizar
from . import ejemplos

__all__ = [
    "Nudo", "Barra", "Apoyo", "CargaNodal", "Modelo", "ERROR",
    "analizar", "ejemplos",
]
