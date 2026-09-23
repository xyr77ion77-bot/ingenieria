/* ================================================================
   estado.js — Fuente única de verdad (single source of truth)
   ---------------------------------------------------------------
   FASE 1–2.
   · Toda la geometría y parámetros viven en Estado.datos.
   · Los módulos de UI leen/escriben Estado.datos y llaman
     Estado.notificar(); nadie mantiene copias paralelas.
   · Persistencia: exportar/importar JSON (proyecto completo).
   Convención de niveles:
     niveles[i].h = ALTURA ACUMULADA hasta el nivel i+1 (m), índice
     0 = nivel 1 (base), ascendente. El motor la ordena por si el
     usuario la desordena (igual que la norma exige hn = altura total).
   ================================================================ */

const Estado = (function () {
  'use strict';

  function nivelPorDefecto(i, hpiso) {
    return {
      h: +(hpiso * (i + 1)).toFixed(2),   // altura acumulada (m)
      cp: 450,                            // carga permanente kg/m²
      cv: 200,                            // carga variable kg/m²
      uso: 'oficina',                     // clave de FRACC_CV (Tabla 20)
      area: null,                         // null → área de planta
      perfil: 'HEB 240'                   // columna representativa del nivel
    };
  }

  function datosPorDefecto() {
    return {
      proyecto: 'Edificio sin nombre',
      sismo: {
        A0: 0.21, A1: 0.18, TL: 3.9,      // p.ej. Higuerote (mapas 4.1–4.3)
        grupo: 'B2', nd: 'ND3', sitio: 'CD', topo: 'leve',
        H: 0, rho: 1.0, FI: 1.0, tabique: 0.018
      },
      material: {
        Fy: 2530,        // kg/cm² (A36 → 2530)
        E: 2100000,      // kg/cm²
        viga: 'IPE 400',
        ppest: 60        // kg/m² pp vigas + columnas + losa metálica adicional
      },
      geometria: {
        lx: [5.0, 5.0, 5.0],              // vanos dirección X (m)
        ly: [5.0, 5.0, 4.0, 4.0],         // vanos dirección Y (m)
        hpiso: 3.2                         // altura típica de piso (m)
      },
      niveles: [nivelPorDefecto(0, 3.2), nivelPorDefecto(1, 3.2),
                nivelPorDefecto(2, 3.2), nivelPorDefecto(3, 3.2)]
    };
  }

  const Estado = {
    datos: datosPorDefecto(),
    seleccion: { nodo: null, tramo: null },   // nodo: {i,j} · tramo: {dir:'X'|'Y', idx}
    resultados: null,                          // {p, s} tras calcular
    _subs: [],

    suscribir(fn) { this._subs.push(fn); },

    notificar(que) {
      for (const fn of this._subs) {
        try { fn(que); } catch (e) { console.error('Suscriptor falló:', e); }
      }
    },

    seleccionarNodo(ij) { this.seleccion.nodo = ij; this.seleccion.tramo = null; this.notificar('seleccion'); },
    seleccionarTramo(t) { this.seleccion.tramo = t; this.seleccion.nodo = null; this.notificar('seleccion'); },
    limpiarSeleccion() { this.seleccion.nodo = null; this.seleccion.tramo = null; this.notificar('seleccion'); },

    /* --- mutadores de geometría con validación mínima --- */
    agregarVano(dir) {
      const g = this.datos.geometria;
      const arr = dir === 'X' ? g.lx : g.ly;
      if (arr.length >= 12) return;
      arr.push(+(arr[arr.length - 1] || 5).toFixed(2));
      this.notificar('geometria');
    },
    quitarVano(dir, idx) {
      const g = this.datos.geometria;
      const arr = dir === 'X' ? g.lx : g.ly;
      if (arr.length <= 1) return;
      arr.splice(idx, 1);
      /* limpiar selecciones que queden fuera de rango */
      if (this.seleccion.tramo && this.seleccion.tramo.dir === dir && this.seleccion.tramo.idx >= arr.length) {
        this.seleccion.tramo = null;
      }
      this.notificar('geometria');
    },
    agregarNivel() {
      if (this.datos.niveles.length >= 10) return;
      const n = this.datos.niveles.length;
      this.datos.niveles.push(nivelPorDefecto(n, this.datos.geometria.hpiso));
      this.notificar('niveles');
    },
    quitarNivel(idx) {
      if (this.datos.niveles.length <= 1) return;
      this.datos.niveles.splice(idx, 1);
      this.notificar('niveles');
    },

    /* --- persistencia JSON --- */
    serializar() {
      return JSON.stringify({
        app: 'calculadora-sismica', version: '0.2 (Fase 1-2)', fecha: new Date().toISOString(),
        datos: this.datos
      }, null, 2);
    },
    cargarJSON(texto) {
      const obj = JSON.parse(texto);
      if (!obj || !obj.datos || !obj.datos.sismo || !Array.isArray(obj.datos.niveles)) {
        throw new Error('El archivo no parece un proyecto de esta calculadora.');
      }
      this.datos = Object.assign(datosPorDefecto(), obj.datos);
      this.resultados = null;
      this.limpiarSeleccion();
      this.notificar('proyecto');
    }
  };

  return Estado;
})();
