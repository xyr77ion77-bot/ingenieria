# ==================================================================
#  modelo.py — Entidades del modelo estructural 2D (pórtico plano)
#  ------------------------------------------------------------------
#  Unidades: m, kg, kg·m, kg/cm², cm², cm⁴, kg/m  (ver __init__.py)
#
#  Convención de ejes: X → derecha, Y → arriba, θz → antihorario (+).
# ==================================================================

from dataclasses import dataclass, field, asdict


# ---- Excepción del dominio (mensajes amables para la UI) ----------
class ERROR(Exception):
    """Error de modelado: mensaje apto para mostrar al usuario."""
    pass


# ---- Entidades ----------------------------------------------------

@dataclass
class Nudo:
    id: str
    x: float          # m
    y: float          # m


@dataclass
class Barra:
    id: str
    ni: str           # id del nudo inicial i
    nj: str           # id del nudo final j
    E: float          # kg/cm²
    A: float          # cm²
    I: float          # cm⁴
    nombre_seccion: str = ""        # etiqueta informativa
    q_perp: float = 0.0             # carga uniforme ⊥ al eje, kg/m
    q_axial: float = 0.0            # carga uniforme a lo largo del eje, kg/m
    peso_propio: bool = False       # si True: suma peso = A[kg/m] = A·7850/10⁴
    # liberaciones de extremo (rótula: momento interno = 0 en ese extremo)
    rel_i: bool = False             # True = rótula en el nudo inicial i
    rel_j: bool = False             # True = rótula en el nudo final j


@dataclass
class Apoyo:
    nudo: str         # id del nudo
    ux: bool = False  # True = restringido
    uy: bool = False
    rz: bool = False


@dataclass
class CargaNodal:
    nudo: str
    Fx: float = 0.0   # kg  (+ → derecha)
    Fy: float = 0.0   # kg  (+ → arriba)
    Mz: float = 0.0   # kg·m (+ antihorario)


@dataclass
class Modelo:
    """Contenedor del modelo completo + validaciones de consistencia."""
    titulo: str = "Estructura sin nombre"
    nudos: list = field(default_factory=list)          # [Nudo]
    barras: list = field(default_factory=list)         # [Barra]
    apoyos: list = field(default_factory=list)         # [Apoyo]
    cargas_nodales: list = field(default_factory=list) # [CargaNodal]

    # ---------------- utilidades de búsqueda ----------------
    def nudo(self, nid):
        for n in self.nudos:
            if n.id == nid:
                return n
        return None

    def barra(self, bid):
        for b in self.barras:
            if b.id == bid:
                return b
        return None

    def apoyo_de(self, nid):
        for a in self.apoyos:
            if a.nudo == nid:
                return a
        return None

    def cargas_de(self, nid):
        return [c for c in self.cargas_nodales if c.nudo == nid]

    def barras_conectadas(self, nid):
        return [b for b in self.barras if b.ni == nid or b.nj == nid]

    # ---------------- validación ----------------
    def validar(self):
        """Lanza ERROR si el modelo no es coherente."""
        if not self.nudos:
            raise ERROR("El modelo no tiene nudos.")
        if not self.barras:
            raise ERROR("El modelo no tiene barras.")

        ids_n = [n.id for n in self.nudos]
        if len(ids_n) != len(set(ids_n)):
            raise ERROR("Hay nudos con id duplicado.")
        ids_b = [b.id for b in self.barras]
        if len(ids_b) != len(set(ids_b)):
            raise ERROR("Hay barras con id duplicado.")

        for b in self.barras:
            if self.nudo(b.ni) is None:
                raise ERROR(f"La barra '{b.id}' apunta a un nudo inexistente ({b.ni}).")
            if self.nudo(b.nj) is None:
                raise ERROR(f"La barra '{b.id}' apunta a un nudo inexistente ({b.nj}).")
            if b.ni == b.nj:
                raise ERROR(f"La barra '{b.id}' conecta un nudo consigo mismo.")
            if b.E <= 0:
                raise ERROR(f"La barra '{b.id}' tiene E ≤ 0.")
            if b.A <= 0:
                raise ERROR(f"La barra '{b.id}' tiene área A ≤ 0.")
            if b.I < 0:
                raise ERROR(f"La barra '{b.id}' tiene inercia I negativa.")

        n = self.nudo(self.barras[0].ni)
        ni = self.nudo(self.barras[0].nj)
        L = ((ni.x - n.x) ** 2 + (ni.y - n.y) ** 2) ** 0.5
        if L <= 1e-9:
            raise ERROR("Hay barras de longitud nula.")

        for a in self.apoyos:
            if self.nudo(a.nudo) is None:
                raise ERROR(f"El apoyo en '{a.nudo}' apunta a un nudo inexistente.")
        for c in self.cargas_nodales:
            if self.nudo(c.nudo) is None:
                raise ERROR(f"La carga nodal en '{c.nudo}' apunta a un nudo inexistente.")

        if not self.apoyos:
            raise ERROR("La estructura no tiene apoyos.")

    # ---------------- serialización ----------------
    def a_dict(self):
        return asdict(self)

    @staticmethod
    def desde_dict(d):
        try:
            m = Modelo(
                titulo=str(d.get("titulo", "Estructura sin nombre")),
                nudos=[Nudo(str(n["id"]), float(n["x"]), float(n["y"])) for n in d.get("nudos", [])],
                barras=[
                    Barra(
                        str(b["id"]), str(b["ni"]), str(b["nj"]),
                        float(b["E"]), float(b["A"]), float(b["I"]),
                        nombre_seccion=str(b.get("nombre_seccion", "")),
                        q_perp=float(b.get("q_perp", 0) or 0),
                        q_axial=float(b.get("q_axial", 0) or 0),
                        peso_propio=bool(b.get("peso_propio", False)),
                        rel_i=bool(b.get("rel_i", False)),
                        rel_j=bool(b.get("rel_j", False)),
                    ) for b in d.get("barras", [])
                ],
                apoyos=[
                    Apoyo(str(a["nudo"]),
                          bool(a.get("ux", False)),
                          bool(a.get("uy", False)),
                          bool(a.get("rz", False)))
                    for a in d.get("apoyos", [])
                ],
                cargas_nodales=[
                    CargaNodal(str(c["nudo"]),
                               float(c.get("Fx", 0) or 0),
                               float(c.get("Fy", 0) or 0),
                               float(c.get("Mz", 0) or 0))
                    for c in d.get("cargas_nodales", [])
                ],
            )
        except (KeyError, TypeError, ValueError) as e:
            raise ERROR(f"El archivo/projecto no tiene el formato esperado ({e}).")
        m.validar()
        return m
