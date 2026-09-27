/* ================================================================
   proyecto.js — Proyecto ÚNICO de la aplicación
   ---------------------------------------------------------------
   El proyecto es una sola pieza con tres partes:
     { version: 3,
       titulo:   "…",
       modelador: { geometría, ejes_resistentes, cortes, niveles },
       acciones:  { barra_cp/cv, nodo_cp/cv, sismo, cargas2002 },
       modelo:    { nudos, barras, apoyos, … (motor 2D) } }

   Almacén: localStorage bajo UNA clave (proyecto_v1) — y por
   compatibilidad se espejan las claves antiguas que consumen los
   módulos (modelador_v1 · analisis2d.autosave · analisis2d.acciones).
   Guardar/Abrir = el proyecto COMPLETO desde cualquier pestaña.
   ================================================================ */

'use strict';

const Proyecto = (function () {
  const K_TODO = 'proyecto_v1';
  const K_MOD = 'modelador_v1';
  const K_MOD2D = 'analisis2d.autosave';
  const K_ACC = 'analisis2d.acciones';

  const $ = (id) => document.getElementById(id);

  function recoger() {
    const lee = (k) => {
      try {
        const s = localStorage.getItem(k);
        return s ? JSON.parse(s) : null;
      } catch (e) { return null; }
    };
    return {
      modelador: lee(K_MOD),
      acciones: lee(K_ACC),
      modelo: lee(K_MOD2D),
    };
  }

  function tituloDe(p) {
    return (p && p.modelador && p.modelador.titulo)
      || (p && p.modelo && p.modelo.titulo) || 'proyecto';
  }

  function guardarArchivo() {
    const p = { version: 3, ...recoger() };
    p.titulo = tituloDe(p);
    const a = document.createElement('a');
    a.download = 'proyecto_' +
      String(p.titulo).replace(/[^\w\-áéíóúñ ]+/gi, '').trim()
        .replace(/\s+/g, '_') + '.json';
    a.href = URL.createObjectURL(
      new Blob([JSON.stringify(p, null, 1)], { type: 'application/json' }));
    a.click();
  }

  function distribuir(p) {
    /* escribe las claves que traiga el archivo (v3 completo o parciales) */
    if (p.modelador) localStorage.setItem(K_MOD, JSON.stringify(p.modelador));
    if (p.acciones) localStorage.setItem(K_ACC, JSON.stringify(p.acciones));
    if (p.modelo) localStorage.setItem(K_MOD2D, JSON.stringify(p.modelo));
    /* archivo viejo de una sola pieza (modelo del análisis a secas) */
    if (!p.modelador && !p.acciones && p.nudos) {
      localStorage.setItem(K_MOD2D, JSON.stringify(p));
    }
    localStorage.setItem(K_TODO, JSON.stringify({ version: 3, ...recoger() }));
  }

  function abrirArchivo(file) {
    const rd = new FileReader();
    rd.onload = () => {
      try {
        const p = JSON.parse(rd.result);
        if (typeof p !== 'object' || p === null) throw new Error('mal');
        distribuir(p);
        /* recarga para que las tres vistas re-lean el proyecto */
        location.reload();
      } catch (e) {
        alert('El archivo no es un proyecto válido.');
      }
    };
    rd.readAsText(file);
  }

  function init() {
    const g = $('btn-guardar-proyecto');
    if (g) g.addEventListener('click', guardarArchivo);
    const b = $('btn-abrir-proyecto');
    if (b) b.addEventListener('click', () => $('file-proyecto').click());
    const f = $('file-proyecto');
    if (f) f.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (file) abrirArchivo(file);
      e.target.value = '';
    });
  }

  return { init, guardarArchivo, abrirArchivo, recoger, distribuir };
})();

document.addEventListener('DOMContentLoaded', () => Proyecto.init());
