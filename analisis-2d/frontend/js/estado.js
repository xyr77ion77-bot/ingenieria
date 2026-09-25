/* ================================================================
   estado.js — Fuente única de verdad del modelo (patrón del repo)
   ------------------------------------------------------------------
   · Toda la geometría/cargas vive en Estado.datos (mismo JSON que
     consume el motor Python).
   · Los módulos se suscriben con Estado.suscribir(fn).
   · Convención de cargas de barra (UI ↔ motor):
       w_grav (kg/m ↓ global)  →  q_perp = −w·c , q_axial = −w·s
       con (c, s) = cos/sin del eje i→j.
   · Persistencia: localStorage (autosave) + archivo .json.
   ================================================================ */

const Estado = (function () {
  'use strict';

  const CLAVE_LS = 'analisis2d.autosave';

  const datos = {
    titulo: 'Estructura sin nombre',
    nudos: [],            // {id, x, y}
    barras: [],           // {id, ni, nj, E, A, I, nombre_seccion, q_perp, q_axial, peso_propio}
    apoyos: [],           // {nudo, ux, uy, rz}
    cargas_nodales: []    // {nudo, Fx, Fy, Mz}
  };

  /* ---------- configuración de la herramienta (no se analiza) ---------- */
  const herr = {
    modo: 'seleccionar',
    material: 2100000,          // kg/cm²
    tipoSeccion: 'perfil',      // 'perfil' | 'rect' | 'manual'
    perfil: 'IPE 300',
    rect_b: 30, rect_h: 50,     // cm
    manual_A: 100, manual_I: 10000,
    apoyoTipo: 'articulado',    // fijo | articulado | deslizX | deslizY | ninguno
    Fx: 0, Fy: -1000, Mz: 0,    // kg, kg, kg·m
    wGrav: 1000,                // kg/m hacia abajo
    pesoPropio: false,
    vista: { grid: true, etiquetas: true, M: true, V: true, N: false, deformada: false },
    autoCalcular: true,
    snap: true
  };

  /* ---------- estado de sesión ---------- */
  const sesion = {
    seleccion: null,        // {tipo:'nudo'|'barra', id}
    hover: null,
    barraEnCurso: null,     // id del nudo origen en modo barra
    resultado: null,        // última respuesta OK del motor
    error: null             // último error del motor
  };

  const obs = [];
  function suscribir(fn) { obs.push(fn); }
  function notificar(que) {
    que = que || { todo: true };
    autosave();
    obs.forEach(fn => { try { fn(que); } catch (e) { console.error(e); } });
  }

  /* ---------- utilidades ---------- */
  function siguienteId(prefijo, lista) {
    let n = lista.length + 1;
    while (lista.some(o => o.id === prefijo + n)) n++;
    return prefijo + n;
  }

  function nudo(x, y) {
    const nu = { id: siguienteId('N', datos.nudos), x: +x.toFixed(4), y: +y.toFixed(4) };
    datos.nudos.push(nu);
    notificar({ nudos: true });
    return nu;
  }

  function propsSeccion() {
    if (herr.tipoSeccion === 'perfil') {
      const p = Perfiles.get(herr.perfil);
      return { A: p.A, I: p.Ix, nombre: p.nombre };
    }
    if (herr.tipoSeccion === 'rect') {
      const b = +herr.rect_b, h = +herr.rect_h;
      return { A: b * h, I: b * Math.pow(h, 3) / 12, nombre: `Rect ${b}×${h}` };
    }
    return { A: +herr.manual_A, I: +herr.manual_I, nombre: 'Personalizada' };
  }

  function barra(ni, nj) {
    const s = propsSeccion();
    const ba = {
      id: siguienteId('B', datos.barras),
      ni: ni.id, nj: nj.id,
      E: +herr.material, A: s.A, I: s.I,
      nombre_seccion: s.nombre,
      q_perp: 0, q_axial: 0,
      peso_propio: false
    };
    if (herr.pesoPropio && herr.modo === 'barra') ba.peso_propio = true;
    datos.barras.push(ba);
    notificar({ barras: true });
    return ba;
  }

  function eliminar(sel) {
    if (!sel) return;
    if (sel.tipo === 'nudo') {
      const conectadas = datos.barras.filter(b => b.ni === sel.id || b.nj === sel.id).map(b => b.id);
      datos.barras = datos.barras.filter(b => !conectadas.includes(b.id));
      datos.nudos = datos.nudos.filter(n => n.id !== sel.id);
      datos.apoyos = datos.apoyos.filter(a => a.nudo !== sel.id);
      datos.cargas_nodales = datos.cargas_nodales.filter(c => c.nudo !== sel.id);
    } else {
      datos.barras = datos.barras.filter(b => b.id !== sel.id);
    }
    sesion.seleccion = null;
    notificar({ todo: true });
  }

  function apoyoDe(nid) { return datos.apoyos.find(a => a.nudo === nid) || null; }

  const TIPOS_APOYO = {
    fijo: { ux: true, uy: true, rz: true },
    articulado: { ux: true, uy: true, rz: false },
    deslizX: { ux: false, uy: true, rz: false },   // rueda que rueda en X: restringe Y
    deslizY: { ux: true, uy: false, rz: false },
    ninguno: null
  };

  function asignarApoyo(nid) {
    const t = TIPOS_APOYO[herr.apoyoTipo];
    datos.apoyos = datos.apoyos.filter(a => a.nudo !== nid);
    if (t) datos.apoyos.push({ nudo: nid, ...t });
    notificar({ apoyos: true });
  }

  function cargaDe(nid) { return datos.cargas_nodales.find(c => c.nudo === nid) || null; }

  function aplicarCargaPuntual(nid) {
    let c = cargaDe(nid);
    if (!c) { c = { nudo: nid, Fx: 0, Fy: 0, Mz: 0 }; datos.cargas_nodales.push(c); }
    c.Fx = +(c.Fx + (+herr.Fx || 0)).toFixed(3);
    c.Fy = +(c.Fy + (+herr.Fy || 0)).toFixed(3);
    c.Mz = +(c.Mz + (+herr.Mz || 0)).toFixed(3);
    if (!c.Fx && !c.Fy && !c.Mz) datos.cargas_nodales = datos.cargas_nodales.filter(x => x.nudo !== nid);
    notificar({ cargas: true });
  }

  /* carga repartida gravitacional (↓ global) sobre una barra */
  function aplicarCargaRepartida(bid) {
    const b = datos.barras.find(x => x.id === bid);
    if (!b) return;
    const ni = datos.nudos.find(n => n.id === b.ni);
    const nj = datos.nudos.find(n => n.id === b.nj);
    const L = Math.hypot(nj.x - ni.x, nj.y - ni.y) || 1;
    const c = (nj.x - ni.x) / L, s = (nj.y - ni.y) / L;
    const w = +herr.wGrav || 0;
    b.q_perp = +(-w * c).toFixed(4);
    b.q_axial = +(-w * s).toFixed(4);
    notificar({ barras: true });
  }

  function cargarModelo(m) {
    datos.titulo = m.titulo || 'Estructura sin nombre';
    datos.nudos = (m.nudos || []).map(n => ({ id: String(n.id), x: +n.x, y: +n.y }));
    datos.barras = (m.barras || []).map(b => ({
      id: String(b.id), ni: String(b.ni), nj: String(b.nj),
      E: +b.E, A: +b.A, I: +b.I,
      nombre_seccion: b.nombre_seccion || '',
      q_perp: +(b.q_perp || 0), q_axial: +(b.q_axial || 0),
      peso_propio: !!b.peso_propio
    }));
    datos.apoyos = (m.apoyos || []).map(a => ({ nudo: String(a.nudo), ux: !!a.ux, uy: !!a.uy, rz: !!a.rz }));
    datos.cargas_nodales = (m.cargas_nodales || []).map(c => ({
      nudo: String(c.nudo), Fx: +c.Fx || 0, Fy: +c.Fy || 0, Mz: +c.Mz || 0
    }));
    sesion.seleccion = null; sesion.barraEnCurso = null;
    sesion.resultado = null; sesion.error = null;
    notificar({ todo: true });
  }

  function aJSON() {
    return JSON.stringify({ version: 1, ...datos }, null, 2);
  }

  /* ---------- autosave ---------- */
  let tSave = null;
  function autosave() {
    clearTimeout(tSave);
    tSave = setTimeout(() => {
      try { localStorage.setItem(CLAVE_LS, aJSON()); } catch (e) { /* noop */ }
    }, 400);
  }

  function restaurar() {
    try {
      const s = localStorage.getItem(CLAVE_LS);
      if (s) { cargarModelo(JSON.parse(s)); return true; }
    } catch (e) { /* noop */ }
    return false;
  }

  return {
    datos, herr, sesion,
    suscribir, notificar,
    nudo, barra, eliminar, apoyoDe, asignarApoyo,
    cargaDe, aplicarCargaPuntual, aplicarCargaRepartida,
    propsSeccion, cargarModelo, aJSON, restaurar,
    TIPOS_APOYO
  };
})();
