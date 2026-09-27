# ==================================================================
#  generador.py — Modelador → modelo 2D del pórtico (espec §6)
#  ------------------------------------------------------------------
#  Convierte la configuración de un corte (cortes["X:1"]) en el modelo
#  del motor: nudos, barras (con liberaciones rel_i/rel_j), apoyos.
#
#  Convención (igual que la planta del Modelador):
#    · Ejes = vanos + 1: ly de 2 vanos → ejes A,B,C (3 columnas).
#    · «X:1» corre en Y: columnas en los ejes A.. con luces ly.
#      «Y:A» corre en X: columnas en los ejes 1.. con luces lx.
#    · Nudos «{eje}_N{k}»: k=0 en la base, k=niveles_propios arriba.
#    · Vano salteado (columna desactivada) → viga única con L = Σ luces.
#    · Unión articulada en un nudo → la VIGA nace con rótula en ese
#      extremo (rel_i/rel_j); las columnas quedan continuas.
#    · Base de cada columna → apoyo empotrado (ux,uy,rz) o articulado
#      (ux,uy) según columnas[clave].base.
#  Secciones: genéricas E=2,1e6 · A=100 · I=20000 (se asignan perfiles
#  reales en Acero 1618 / Concreto o en Análisis 2D).
# ==================================================================

from .modelo import ERROR

E_DEF = 2_100_000.0    # kg/cm² (acero A36)
A_DEF = 100.0          # cm²
I_DEF = 20_000.0       # cm⁴


def _letra(i):
    return chr(65 + i)


def generar_portico(modelador: dict, corte_clave: str) -> tuple:
    """→ (modelo_dict, resumen_dict). Lanza ERROR con mensaje amable."""
    g = (modelador or {}).get("geometria") or {}
    lx = [float(v) for v in (g.get("lx") or []) if float(v) > 0]
    ly = [float(v) for v in (g.get("ly") or []) if float(v) > 0]
    niveles = g.get("niveles") or []
    cortes = (modelador or {}).get("cortes") or {}

    clave = (corte_clave or "").strip()
    if ":" not in clave:
        raise ERROR(f"«{clave}» no es un pórtico válido (usa «X:1» o «Y:A»).")
    dir_, id_txt = clave.split(":", 1)
    if dir_ not in ("X", "Y"):
        raise ERROR(f"Dirección «{dir_}» desconocida (usa X o Y).")

    corte = cortes.get(clave)
    if corte is None:
        raise ERROR(f"El pórtico {clave} no tiene corte configurado "
                    "(ábrelo en la vista Corte).")

    luces = ly if dir_ == "X" else lx
    if not luces:
        raise ERROR("La retícula no tiene vanos en la dirección del pórtico.")
    n_cols = len(luces) + 1                      # ejes = vanos + 1
    claves = ([_letra(i) for i in range(n_cols)] if dir_ == "X"
              else [str(i + 1) for i in range(n_cols)])

    np_ = int(corte.get("niveles_propios") or len(niveles))
    np_ = max(1, min(np_, len(niveles)))
    niveles = niveles[:np_]
    elev, y = [0.0], 0.0
    for n in niveles:
        h = float(n.get("h_piso") or 0)
        if h <= 0:
            raise ERROR("Las alturas de piso deben ser positivas.")
        y += h
        elev.append(y)

    cols_cfg = corte.get("columnas") or {}

    def cfg(clave_col):
        c = cols_cfg.get(clave_col) or {}
        return {"activa": bool(c.get("activa", True)),
                "base": c.get("base", "empotrada")}

    activas = [c for c in claves if cfg(c)["activa"]]
    if not activas:
        raise ERROR(f"El pórtico {clave} no tiene ninguna columna activa: "
                    "reactiva al menos una (clic en el corte).")

    uniones = corte.get("uniones") or {}
    patron = uniones.get("patron", "pr_momento")
    excepciones = uniones.get("excepciones") or {}

    def viga_articulada(nk, eje):
        ex = excepciones.get(f"N{nk}|{eje}")
        if ex:
            return ex == "articulada"
        return patron in ("vigas_articuladas", "todo_articulado")

    # ---- posiciones X de las columnas ----
    xs = [0.0]
    for v in luces:
        xs.append(xs[-1] + v)

    # ---- nudos (solo columnas activas) ----
    nudos = []
    for eje, x in zip(claves, xs):
        if not cfg(eje)["activa"]:
            continue
        for k in range(np_ + 1):
            nudos.append({"id": f"{eje}_N{k}", "x": round(x, 6),
                          "y": round(elev[k], 6)})

    # ---- barras ----
    barras = []
    for eje in claves:
        if not cfg(eje)["activa"]:
            continue
        for k in range(np_):
            barras.append({
                "id": f"C_{eje}_{k + 1}", "ni": f"{eje}_N{k}",
                "nj": f"{eje}_N{k + 1}",
                "E": E_DEF, "A": A_DEF, "I": I_DEF,
                "nombre_seccion": "columna (asignar perfil)",
                "q_perp": 0.0, "q_axial": 0.0, "peso_propio": False,
                "rel_i": False, "rel_j": False,
            })

    saltados = []
    for k in range(1, np_ + 1):
        seq = 0
        prev = None
        for i, eje in enumerate(claves):
            if not cfg(eje)["activa"]:
                continue
            if prev is not None:
                seq += 1
                luz = round(xs[i] - xs[prev_idx], 6)
                barras.append({
                    "id": f"V{k}_{seq}",
                    "ni": f"{claves[prev]}_N{k}", "nj": f"{eje}_N{k}",
                    "E": E_DEF, "A": A_DEF, "I": I_DEF,
                    "nombre_seccion":
                        f"viga N{k} · luz {luz:g} m (asignar perfil)",
                    "q_perp": 0.0, "q_axial": 0.0, "peso_propio": False,
                    "rel_i": viga_articulada(k, claves[prev]),
                    "rel_j": viga_articulada(k, eje),
                })
                if luz != luces[prev_idx]:
                    saltados.append(
                        f"{claves[prev]}→{eje} en N{k} (L={luz:g} m)")
            prev, prev_idx = i, i

    # ---- apoyos ----
    apoyos = []
    for eje in activas:
        art = cfg(eje)["base"] == "articulada"
        apoyos.append({"nudo": f"{eje}_N0", "ux": True, "uy": True,
                       "rz": not art})

    modelo = {
        "titulo": f"Pórtico {clave}",
        "nudos": nudos,
        "barras": barras,
        "apoyos": apoyos,
        "cargas_nodales": [],
    }
    resumen = {
        "corte": clave,
        "n_nudos": len(nudos),
        "n_barras": len(barras),
        "n_columnas": sum(1 for b in barras if b["id"].startswith("C_")),
        "n_vigas": sum(1 for b in barras if b["id"].startswith("V")),
        "niveles": np_,
        "saltados": saltados,
        "bases_articuladas": [e for e in activas
                              if cfg(e)["base"] == "articulada"],
    }
    return modelo, resumen
