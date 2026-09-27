# ==================================================================
#  api.py — API HTTP del motor de análisis (FastAPI)
#  ------------------------------------------------------------------
#  Endpoints:
#    POST /api/analizar        → análisis de un modelo (JSON)
#    POST /api/validar         → validación sin análisis
#    GET  /api/ejemplos        → lista de ejemplos disponibles
#    GET  /api/ejemplos/{id}   → modelo de ejemplo (JSON)
#    GET  /api/salud           → ping
#
#  La misma app sirve el frontend estático desde ../frontend.
# ==================================================================

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from engine import ERROR
from engine.modelo import Modelo
from engine.solver import analizar
from engine.acciones import analizar_con_combinaciones
from engine.diseno_acero import disenar as diseno_acero_disenar
from engine.diseno_acero import cargar_perfiles, _SERIES_ARCHIVO
from engine import ejemplos

BASE = os.path.dirname(os.path.abspath(__file__))
FRONT = os.path.join(os.path.dirname(BASE), "frontend")

app = FastAPI(title="Análisis Estructural 2D", version="1.0.0")


class ModeloIn(BaseModel):
    """El modelo llega como dict libre (lo valida engine.modelo)."""
    class Config:
        extra = "allow"


@app.post("/api/analizar")
def api_analizar(modelo: dict):
    try:
        m = Modelo.desde_dict(modelo)
    except ERROR as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=422, content={
            "ok": False, "error": f"JSON del modelo inválido: {e}"})
    try:
        res = analizar(m)
        return res
    except ERROR as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=500, content={
            "ok": False, "error": f"Error interno del motor: {e}"})


@app.post("/api/diseno-acero")
def api_diseno_acero(payload: dict):
    """
    Fase 4: diseño de pórticos COVENIN 1618-1998 (estados límites).
    payload = {modelo, acciones, params:{fy, perfil_viga, perfil_columna,
    k_col, lb_viga_m, cb, limite_flecha, series, optimizar}}
    Devuelve filas por barra (ratios ✓/✗), perfil óptimo y memoria.
    """
    modelo = payload.get("modelo")
    acciones = payload.get("acciones") or {}
    if not isinstance(modelo, dict):
        return JSONResponse(status_code=422, content={
            "ok": False, "error": "Falta el objeto 'modelo'."})
    try:
        return diseno_acero_disenar(modelo, acciones,
                                    payload.get("params") or {})
    except ERROR as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=500, content={
            "ok": False, "error": f"Error interno del motor: {e}"})


@app.post("/api/validar")
def api_validar(modelo: dict):
    try:
        Modelo.desde_dict(modelo)
        return {"ok": True}
    except ERROR as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})


@app.post("/api/combinaciones")
def api_combinaciones(payload: dict):
    """
    Fase 2: casos CP/CV/SH/SV + combinaciones COVENIN 1756-1 §8.3.2
    + envolvente. payload = {modelo, acciones}
    """
    modelo = payload.get("modelo")
    acciones = payload.get("acciones") or {}
    if not isinstance(modelo, dict):
        return JSONResponse(status_code=422, content={
            "ok": False, "error": "Falta el objeto 'modelo'."})
    try:
        return analizar_con_combinaciones(modelo, acciones)
    except ERROR as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=500, content={
            "ok": False, "error": f"Error interno del motor: {e}"})


@app.get("/api/ejemplos")
def api_ejemplos():
    return {"ok": True, "ejemplos": ejemplos.lista()}


@app.get("/api/ejemplos/{eid}")
def api_ejemplo(eid: str):
    try:
        return {"ok": True, "modelo": ejemplos.obtener(eid)}
    except ERROR as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/generar")
def api_generar(payload: dict):
    """Modelador → modelo 2D del pórtico (espec §6).
    body: {modelador: {geometría, cortes…}, corte: "X:1"}"""
    try:
        from engine.generador import generar_portico
        modelo, resumen = generar_portico(payload.get("modelador") or {},
                                          payload.get("corte") or "")
        return {"ok": True, "modelo": modelo, "resumen": resumen}
    except ERROR as e:
        return JSONResponse(status_code=422, content={"ok": False,
                                                      "error": str(e)})
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=500, content={
            "ok": False, "error": f"Error generando el modelo: {e}"})


@app.get("/api/perfiles")
def api_perfiles():
    """Catálogo de perfiles (BD 874) para los datalists del diseño: {serie, nombre, G}."""
    try:
        return {"ok": True, "perfiles": cargar_perfiles(list(_SERIES_ARCHIVO.keys()))}
    except Exception as e:  # noqa: BLE001
        return JSONResponse(status_code=500, content={
            "ok": False, "error": f"Error interno del motor: {e}"})


@app.get("/api/salud")
def api_salud():
    return {"ok": True, "motor": "rigideces-2d", "unidades": "kg·m·kg/cm²"}


@app.get("/api/cargas2002")
def api_cargas2002():
    """Tablas de cargas mínimas COVENIN-MINDUR 2002-88 para la UI
    (fuente única de verdad: engine/cargas2002.py)."""
    from engine import cargas2002 as C
    tipos = {
        clave: {"titulo": titulo,
                "valores": {amb: v for amb, v in fila.items()
                            if isinstance(v, (int, float))}}
        for clave, (titulo, fila) in C.TIPOS_5_1.items()
    }
    return {
        "ambientes": C.AMBIENTES_5_1,
        "tipos": tipos,
        "opciones_tipo": C.opciones_tipo(),
        "techo": {"metalico_liviano": 40, "p_le_15": 100, "p_gt_15": 50,
                  "azotea_min_con_uso": C.AZOTEA_MIN_CON_USO},
        "pesos": {"concreto_armado": C.PESOS_MATERIALES[
                      "concreto_armado_ordinario"],
                  "acabados": C.PESOS_ELEMENTOS,
                  "tabiquería_defecto": C.PESO_TABIQUERIA_EQUIVALENTE},
    }


# ---------- frontend estático (al final para no tapar /api) ----------
app.mount("/", StaticFiles(directory=FRONT, html=True), name="frontend")
