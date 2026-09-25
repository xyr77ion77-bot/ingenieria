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


@app.post("/api/validar")
def api_validar(modelo: dict):
    try:
        Modelo.desde_dict(modelo)
        return {"ok": True}
    except ERROR as e:
        return JSONResponse(status_code=422, content={"ok": False, "error": str(e)})


@app.get("/api/ejemplos")
def api_ejemplos():
    return {"ok": True, "ejemplos": ejemplos.lista()}


@app.get("/api/ejemplos/{eid}")
def api_ejemplo(eid: str):
    try:
        return {"ok": True, "modelo": ejemplos.obtener(eid)}
    except ERROR as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.get("/api/salud")
def api_salud():
    return {"ok": True, "motor": "rigideces-2d", "unidades": "kg·m·kg/cm²"}


# ---------- frontend estático (al final para no tapar /api) ----------
app.mount("/", StaticFiles(directory=FRONT, html=True), name="frontend")
