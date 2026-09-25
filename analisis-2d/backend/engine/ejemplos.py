# ==================================================================
#  ejemplos.py — Modelos de ejemplo (unidades kg, m, kg/cm²)
#  ------------------------------------------------------------------
#  Cada ejemplo se entrega como dict listo para la API/UI y debe
#  cargar y analizarse sin errores.
# ==================================================================

from .modelo import Modelo, Nudo, Barra, Apoyo, CargaNodal, ERROR

E_ACERO = 2_100_000.0     # kg/cm²
# Sección rectangular de concreto/peligro genérica para ejemplos:
# 30×50 cm → A = 1500 cm², I = b·h³/12 = 30·50³/12 = 312500 cm⁴
A_R30x50 = 1500.0
I_R30x50 = 312_500.0
# Perfil de acero tipo IPE 300: A = 53.8 cm², I = 8356 cm⁴
A_IPE300, I_IPE300 = 53.8, 8356.0
# Columna HEB 200: A = 78.1 cm², I = 5696 cm⁴
A_HEB200, I_HEB200 = 78.1, 5696.0


def _a_dict(m: Modelo) -> dict:
    m.validar()
    return m.a_dict()


def viga_simple():
    """Viga simplemente apoyada de 6 m, 30×50, carga repartida."""
    L, w = 6.0, 2000.0
    return _a_dict(Modelo(
        titulo="Viga simplemente apoyada (30×50)",
        nudos=[Nudo("A", 0, 0), Nudo("B", L, 0)],
        barras=[Barra("V1", "A", "B", 217_000, A_R30x50, I_R30x50,
                      nombre_seccion="Rect 30×50 (GC)", q_perp=-w)],
        apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", uy=True)],
    ))


def voladizo():
    """Voladizo de acero 3 m con carga puntual y repartida."""
    return _a_dict(Modelo(
        titulo="Voladizo de acero (IPE 300)",
        nudos=[Nudo("A", 0, 0), Nudo("B", 3, 0)],
        barras=[Barra("V1", "A", "B", E_ACERO, A_IPE300, I_IPE300,
                      nombre_seccion="IPE 300", q_perp=-500)],
        apoyos=[Apoyo("A", ux=True, uy=True, rz=True)],
        cargas_nodales=[CargaNodal("B", Fy=-1500)],
    ))


def viga_continua():
    """Viga continua de 2 tramos con carga repartida."""
    L, w = 5.0, 1500.0
    return _a_dict(Modelo(
        titulo="Viga continua de 2 tramos (30×50)",
        nudos=[Nudo("A", 0, 0), Nudo("B", L, 0), Nudo("C", 2 * L, 0)],
        barras=[Barra("V1", "A", "B", 217_000, A_R30x50, I_R30x50,
                      nombre_seccion="Rect 30×50 (GC)", q_perp=-w),
                Barra("V2", "B", "C", 217_000, A_R30x50, I_R30x50,
                      nombre_seccion="Rect 30×50 (GC)", q_perp=-w)],
        apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", uy=True), Apoyo("C", uy=True)],
    ))


def portico_gravedad():
    """Pórtico de 1 nivel y 2 luces, carga de gravedad en vigas."""
    L1, L2, h = 5.0, 5.0, 3.5
    w = 1500.0
    return _a_dict(Modelo(
        titulo="Pórtico 1 nivel · gravedad",
        nudos=[Nudo("A", 0, 0), Nudo("B", L1, 0), Nudo("C", L1 + L2, 0),
               Nudo("D", 0, h), Nudo("E", L1, h), Nudo("F", L1 + L2, h)],
        barras=[
            Barra("C1", "A", "D", 217_000, A_R30x50, I_R30x50, nombre_seccion="Rect 30×50 (GC)"),
            Barra("C2", "B", "E", 217_000, A_R30x50, I_R30x50, nombre_seccion="Rect 30×50 (GC)"),
            Barra("C3", "C", "F", 217_000, A_R30x50, I_R30x50, nombre_seccion="Rect 30×50 (GC)"),
            Barra("V1", "D", "E", 217_000, A_R30x50, I_R30x50, nombre_seccion="Rect 30×50 (GC)", q_perp=-w),
            Barra("V2", "E", "F", 217_000, A_R30x50, I_R30x50, nombre_seccion="Rect 30×50 (GC)", q_perp=-w),
        ],
        apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", ux=True, uy=True),
                Apoyo("C", ux=True, uy=True)],
    ))


def portico_sismo():
    """Pórtico de acero con carga lateral (sismo/viento) + gravedad."""
    L, h = 6.0, 3.5
    w = 800.0
    H = 3000.0
    return _a_dict(Modelo(
        titulo="Pórtico de acero · sismo (H en N1)",
        nudos=[Nudo("A", 0, 0), Nudo("B", L, 0), Nudo("C", 0, h), Nudo("D", L, h)],
        barras=[
            Barra("C1", "A", "C", E_ACERO, A_HEB200, I_HEB200, nombre_seccion="HEB 200"),
            Barra("C2", "B", "D", E_ACERO, A_HEB200, I_HEB200, nombre_seccion="HEB 200"),
            Barra("V1", "C", "D", E_ACERO, A_IPE300, I_IPE300, nombre_seccion="IPE 300", q_perp=-w),
        ],
        apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", ux=True, uy=True)],
        cargas_nodales=[CargaNodal("C", Fx=H)],
    ))


def portico_2_niveles():
    """Edificio de 2 niveles con cargas laterales acumuladas."""
    L, h = 6.0, 3.2
    w = 1200.0
    return _a_dict(Modelo(
        titulo="Pórtico 2 niveles · sismo",
        nudos=[Nudo("A", 0, 0), Nudo("B", L, 0),
               Nudo("C", 0, h), Nudo("D", L, h),
               Nudo("E", 0, 2 * h), Nudo("F", L, 2 * h)],
        barras=[
            Barra("C1", "A", "C", E_ACERO, A_HEB200, I_HEB200, nombre_seccion="HEB 200"),
            Barra("C2", "B", "D", E_ACERO, A_HEB200, I_HEB200, nombre_seccion="HEB 200"),
            Barra("C3", "C", "E", E_ACERO, A_HEB200, I_HEB200, nombre_seccion="HEB 200"),
            Barra("C4", "D", "F", E_ACERO, A_HEB200, I_HEB200, nombre_seccion="HEB 200"),
            Barra("V1", "C", "D", E_ACERO, A_IPE300, I_IPE300, nombre_seccion="IPE 300", q_perp=-w),
            Barra("V2", "E", "F", E_ACERO, A_IPE300, I_IPE300, nombre_seccion="IPE 300", q_perp=-w),
        ],
        apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", ux=True, uy=True)],
        cargas_nodales=[CargaNodal("C", Fx=2000), CargaNodal("E", Fx=1000)],
    ))


def marco_inclinado():
    """Marco con cumbrera (cobertura inclinada)."""
    L, h, hc = 4.0, 3.0, 4.2
    w = 600.0
    return _a_dict(Modelo(
        titulo="Marco con cumbrera",
        nudos=[Nudo("A", 0, 0), Nudo("B", 2 * L, 0), Nudo("C", L, hc),
               Nudo("D", 0, h), Nudo("E", 2 * L, h)],
        barras=[
            Barra("C1", "A", "D", E_ACERO, A_HEB200, I_HEB200, nombre_seccion="HEB 200"),
            Barra("C2", "B", "E", E_ACERO, A_HEB200, I_HEB200, nombre_seccion="HEB 200"),
            Barra("T1", "D", "C", E_ACERO, A_IPE300, I_IPE300, nombre_seccion="IPE 300", q_perp=-w),
            Barra("T2", "C", "E", E_ACERO, A_IPE300, I_IPE300, nombre_seccion="IPE 300", q_perp=-w),
        ],
        apoyos=[Apoyo("A", ux=True, uy=True), Apoyo("B", ux=True, uy=True)],
    ))


EJEMPLOS = {
    "viga_simple": ("Viga simple + carga repartida", viga_simple),
    "voladizo": ("Voladizo de acero", voladizo),
    "viga_continua": ("Viga continua 2 tramos", viga_continua),
    "portico_gravedad": ("Pórtico 1 nivel · gravedad", portico_gravedad),
    "portico_sismo": ("Pórtico de acero · sismo", portico_sismo),
    "portico_2_niveles": ("Pórtico 2 niveles · sismo", portico_2_niveles),
    "marco_inclinado": ("Marco con cumbrera", marco_inclinado),
}


def lista():
    return [{"id": k, "nombre": v[0]} for k, v in EJEMPLOS.items()]


def obtener(eid: str) -> dict:
    if eid not in EJEMPLOS:
        raise ERROR(f"El ejemplo '{eid}' no existe.")
    return EJEMPLOS[eid][1]()
