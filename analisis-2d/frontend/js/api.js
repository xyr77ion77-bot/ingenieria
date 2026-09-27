/* ================================================================
   api.js — Cliente HTTP del motor (backend FastAPI)
   ================================================================ */

const API = (function () {
  'use strict';

  async function analizar(modelo) {
    const r = await fetch('/api/analizar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(modelo)
    });
    const j = await r.json().catch(() => ({ ok: false, error: 'Respuesta inválida del servidor' }));
    return j;
  }

  async function ejemplo(id) {
    const r = await fetch('/api/ejemplos/' + encodeURIComponent(id));
    if (!r.ok) throw new Error('No se pudo cargar el ejemplo');
    const j = await r.json();
    return j.modelo;
  }

  async function listaEjemplos() {
    const r = await fetch('/api/ejemplos');
    const j = await r.json();
    return j.ejemplos || [];
  }

  return { analizar, ejemplo, listaEjemplos };
})();
