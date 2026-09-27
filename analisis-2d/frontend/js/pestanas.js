/* ================================================================
   pestanas.js — Navegación interna de la aplicación única
   ---------------------------------------------------------------
   La app es UNA página con DOS vistas:
     · #modelador = «Modelador + Acciones» (planta | corte | acciones)
     · #analisis  = Análisis 2D
   (#acciones también cae en la primera, por compatibilidad).
   Al activar una vista se re-renderiza (resize de lienzos y
   reconstrucción de las tablas de Acciones desde el proyecto).
   ================================================================ */

'use strict';

const Pestanas = (function () {
  const ORDEN = ['modelador', 'analisis'];   /* Acciones vive DENTRO de Modelador */

  function actual() {
    const h = location.hash.replace('#', '');
    if (h === 'acciones') return 'modelador';   /* compat: unidas en una pestaña */
    return ORDEN.includes(h) ? h : 'modelador';
  }

  function activar(nombre, empujar) {
    if (!ORDEN.includes(nombre)) nombre = 'modelador';
    document.querySelectorAll('.vista').forEach(v =>
      v.classList.toggle('activa', v.id === 'vista-' + nombre));
    document.querySelectorAll('.app-tabs a[data-tab]').forEach(a =>
      a.classList.toggle('activo', a.dataset.tab === nombre));
    if (empujar !== false && location.hash !== '#' + nombre) {
      history.replaceState(null, '', '#' + nombre);
    }
    /* re-render de la vista activa:
       · resize → los lienzos (Planta, canvas del análisis) se redibujan
       · pestana-activada → las tablas de Acciones se reconstruyen */
    window.dispatchEvent(new Event('resize'));
    window.dispatchEvent(new CustomEvent('pestana-activada',
                                         { detail: nombre }));
  }

  function init() {
    document.querySelectorAll('.app-tabs a[data-tab]').forEach(a =>
      a.addEventListener('click', (e) => {
        e.preventDefault();
        activar(a.dataset.tab);
      }));
    window.addEventListener('hashchange', () => activar(actual(), false));
    activar(actual(), true);
  }

  return { init, activar, actual };
})();

document.addEventListener('DOMContentLoaded', () => Pestanas.init());
