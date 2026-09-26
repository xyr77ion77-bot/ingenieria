/* ================================================================
   modelador.js — Pestaña Modelador: geometría del edificio
   ---------------------------------------------------------------
   PASO 2 del plan (docs/MODELADOR-ESPEC.md §8): esqueleto + PLANTA.
   El panel de corte muestra el pórtico seleccionado (vista completa
   en el paso 3) y el botón «Generar modelo 2D» en el paso 4.

   Patrón (heredado de calculadora-sismica/js/canvas_planta.js):
     1. estado → coordenadas (arX/arY) → dibujo → hitBoxes
     2. pointerdown → ¿qué hitbox? → estado → render()
   Mejoras: devicePixelRatio, pointer events, exportarPNG().

   Convención de ejes (igual que la calculadora):
     · Ejes verticales: 1, 2, 3…  separados por las luces lx[]
     · Ejes horizontales: A, B, C… separados por las luces ly[]
   Un eje resistente es un pórtico: «X:2» corre en Y (vertical 2),
   «Y:A» corre en X (horizontal A) — ver MODELADOR-ESPEC §5.
   ================================================================ */

'use strict';

/* ---------------- estado ---------------- */

const EstadoM = {
  datos: {
    titulo: 'Estructura sin nombre',
    geometria: {
      lx: [5.0, 5.0, 5.0],
      ly: [5.0, 5.0, 4.0, 4.0],
      niveles: [
        { nombre: 'N1', h_piso: 4.0 },
        { nombre: 'N2', h_piso: 3.2 },
        { nombre: 'N3', h_piso: 3.2 },
      ],
    },
    ejes_resistentes: { X: [1, 3], Y: ['A', 'C'] },
    cortes: {},          /* «X:2» → config del pórtico (paso 3) */
  },
  seleccion: {
    eje: null,           /* { dir: 'X'|'Y', id } — pórtico abierto en el corte */
  },

  /* ---------- utilidades ---------- */
  letraEje(i) { return String.fromCharCode(65 + i); },          /* 0 → A */
  idxLetra(l) { return l.charCodeAt(0) - 65; },                 /* A → 0 */
  numEje(j) { return j + 1; },                                  /* col 0 → 1 */

  ejeResistente(dir, id) {
    const arr = this.datos.ejes_resistentes[dir];
    return arr.includes(id);
  },

  toggleResistente(dir, id) {
    const arr = this.datos.ejes_resistentes[dir];
    const k = arr.indexOf(id);
    if (k >= 0) arr.splice(k, 1);
    else arr.push(id);
  },

  /* ¿tiene el pórtico configuración que se perdería al desmarcar? */
  ejeTieneCorte(dir, id) {
    return !!this.datos.cortes[dir + ':' + id];
  },

  guardarLocal() {
    try {
      localStorage.setItem('modelador_v1', JSON.stringify(this.datos));
    } catch (e) { /* almacenamiento lleno/inhabilitado: ignoro */ }
  },

  cargarLocal() {
    try {
      const s = localStorage.getItem('modelador_v1');
      if (s) this.datos = ModeladorMigrar(JSON.parse(s));
    } catch (e) { /* datos corruptos: quedan los de fábrica */ }
  },
};

function ModeladorMigrar(d) {
  /* normaliza un objeto venido de archivo/localStorage */
  const g = d.geometria || {};
  return {
    titulo: d.titulo || 'Estructura sin nombre',
    geometria: {
      lx: (g.lx || [5, 5, 5]).map(Number),
      ly: (g.ly || [5, 5, 4, 4]).map(Number),
      niveles: (g.niveles && g.niveles.length
        ? g.niveles
        : [{ nombre: 'N1', h_piso: 4 }]).map(n => ({
            nombre: String(n.nombre), h_piso: Number(n.h_piso) || 3.0,
          })),
    },
    ejes_resistentes: {
      X: ((d.ejes_resistentes || {}).X || []).map(Number),
      Y: ((d.ejes_resistentes || {}).Y || []).map(String),
    },
    cortes: d.cortes || {},
  };
}

/* ---------------- lienzo de la PLANTA ---------------- */

const Planta = (function () {
  const MARGEN = 58;
  let cv = null, ctx = null, wrap = null;
  let hitBoxes = [];
  let geom = null;                    /* {arX, arY, lx, ly, scale} */

  const $id = (id) => document.getElementById(id);
  const sum = (a) => a.reduce((x, y) => x + y, 0);

  function init() {
    cv = $id('cv-planta');
    if (!cv) return;
    ctx = cv.getContext('2d');
    wrap = cv.parentElement;
    cv.addEventListener('pointerdown', onTap);
    cv.addEventListener('pointermove', onHover);
    window.addEventListener('resize', render);
    render();
  }

  function render() {
    if (!cv) return;
    const d = EstadoM.datos;
    const lx = d.geometria.lx.map(Number);
    const ly = d.geometria.ly.map(Number);
    const totX = Math.max(sum(lx), 1), totY = Math.max(sum(ly), 1);

    const w = Math.max(wrap.clientWidth, 240);
    const h = Math.max(wrap.clientHeight || 420, 260);
    const dpr = window.devicePixelRatio || 1;
    cv.width = Math.round(w * dpr);
    cv.height = Math.round(h * dpr);
    cv.style.width = w + 'px';
    cv.style.height = h + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

    const scale = Math.min((w - 2 * MARGEN) / totX,
                           (h - 2 * MARGEN) / totY, 95);
    const arX = [MARGEN];
    lx.forEach(v => arX.push(arX[arX.length - 1] + v * scale));
    const arY = [MARGEN];
    ly.forEach(v => arY.push(arY[arY.length - 1] + v * scale));

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#fbfcfd';
    ctx.fillRect(0, 0, w, h);
    hitBoxes = [];

    const sel = EstadoM.seleccion.eje;
    const resX = d.ejes_resistentes.X;       /* números 1..n */
    const resY = d.ejes_resistentes.Y;       /* letras A..   */
    const y0 = arY[0], y1 = arY[arY.length - 1];
    const x0 = arX[0], x1 = arX[arX.length - 1];

    /* --- sombreado de bandas resistentes (detrás de todo) --- */
    for (const j of resX) {
      const x = arX[j - 1];
      if (x == null) continue;
      const selAqui = sel && sel.dir === 'X' && sel.id === j;
      ctx.fillStyle = selAqui ? 'rgba(220,38,38,.18)' : 'rgba(220,38,38,.09)';
      ctx.fillRect(x - 7, y0, 14, y1 - y0);
    }
    for (const l of resY) {
      const y = arY[EstadoM.idxLetra(l)];
      if (y == null) continue;
      const selAqui = sel && sel.dir === 'Y' && sel.id === l;
      ctx.fillStyle = selAqui ? 'rgba(37,99,235,.18)' : 'rgba(37,99,235,.09)';
      ctx.fillRect(x0, y - 7, x1 - x0, 14);
    }

    /* --- retícula base (gris) --- */
    ctx.strokeStyle = '#cbd5e1'; ctx.lineWidth = 1;
    for (let j = 0; j < arX.length; j++) {
      ctx.beginPath(); ctx.moveTo(arX[j], y0); ctx.lineTo(arX[j], y1); ctx.stroke();
    }
    for (let i = 0; i < arY.length; i++) {
      ctx.beginPath(); ctx.moveTo(x0, arY[i]); ctx.lineTo(x1, arY[i]); ctx.stroke();
    }

    /* --- ejes resistentes: gruesos y con color --- */
    ctx.lineWidth = 4; ctx.setLineDash([]);
    for (const j of resX) {
      const x = arX[j - 1];
      if (x == null) continue;
      const selAqui = sel && sel.dir === 'X' && sel.id === j;
      ctx.strokeStyle = selAqui ? '#b91c1c' : '#dc2626';
      ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x, y1); ctx.stroke();
      hitBoxes.push({ t: 'EJE', dir: 'X', id: j,
                      x1: x - 11, y1: y0 - 14, x2: x + 11, y2: y1 + 14 });
    }
    for (const l of resY) {
      const y = arY[EstadoM.idxLetra(l)];
      if (y == null) continue;
      const selAqui = sel && sel.dir === 'Y' && sel.id === l;
      ctx.strokeStyle = selAqui ? '#1d4ed8' : '#2563eb';
      ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
      hitBoxes.push({ t: 'EJE', dir: 'Y', id: l,
                      x1: x0 - 14, y1: y - 11, x2: x1 + 14, y2: y + 11 });
    }

    /* --- nudos de cruce --- */
    const rN = Math.max(5, scale / 10);
    for (let i = 0; i < arY.length; i++) {
      for (let j = 0; j < arX.length; j++) {
        ctx.fillStyle = '#f8fafc';
        ctx.beginPath(); ctx.arc(arX[j], arY[i], rN, 0, 2 * Math.PI); ctx.fill();
        ctx.strokeStyle = '#475569'; ctx.lineWidth = 1.8; ctx.stroke();
      }
    }

    /* --- hitboxes de tramos (editar luz) — franja central del tramo --- */
    for (let j = 0; j < lx.length; j++) {
      const xc = (arX[j] + arX[j + 1]) / 2, yc = (y0 + y1) / 2;
      hitBoxes.push({ t: 'TRAMO', dir: 'X', idx: j,
                      x1: xc - 26, y1: yc - 10, x2: xc + 26, y2: yc + 10 });
    }
    for (let i = 0; i < ly.length; i++) {
      const xc = (x0 + x1) / 2, yc = (arY[i] + arY[i + 1]) / 2;
      hitBoxes.push({ t: 'TRAMO', dir: 'Y', idx: i,
                      x1: xc - 26, y1: yc - 10, x2: xc + 26, y2: yc + 10 });
    }

    /* --- etiquetas de ejes --- */
    ctx.save();
    ctx.font = 'bold 13px system-ui, sans-serif';
    ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    arX.forEach((x, j) => {
      const esRes = resX.includes(EstadoM.numEje(j));
      ctx.fillStyle = esRes ? '#dc2626' : '#64748b';
      ctx.fillText(String(EstadoM.numEje(j)), x, y0 - 26);
    });
    ctx.textAlign = 'right';
    arY.forEach((y, i) => {
      const esRes = resY.includes(EstadoM.letraEje(i));
      ctx.fillStyle = esRes ? '#2563eb' : '#64748b';
      ctx.fillText(EstadoM.letraEje(i), x0 - 30, y + 5);
    });

    /* --- luces por vano --- */
    ctx.font = '10px system-ui, sans-serif'; ctx.fillStyle = '#94a3b8';
    ctx.textAlign = 'center';
    for (let j = 0; j < lx.length; j++) {
      ctx.fillText(lx[j].toFixed(1) + ' m',
                   (arX[j] + arX[j + 1]) / 2, (y0 + y1) / 2 + 4);
    }
    for (let i = 0; i < ly.length; i++) {
      ctx.save();
      ctx.translate((x0 + x1) / 2, (arY[i] + arY[i + 1]) / 2);
      ctx.rotate(-Math.PI / 2); ctx.textAlign = 'center';
      ctx.fillText(ly[i].toFixed(1) + ' m', 0, 0);
      ctx.restore();
    }

    /* --- leyenda --- */
    ctx.textAlign = 'left'; ctx.font = '11px system-ui, sans-serif';
    ctx.lineWidth = 3.5;
    ctx.strokeStyle = '#dc2626';
    ctx.beginPath(); ctx.moveTo(MARGEN, 16); ctx.lineTo(MARGEN + 22, 16); ctx.stroke();
    ctx.fillStyle = '#64748b'; ctx.fillText('pórtico X', MARGEN + 28, 20);
    ctx.strokeStyle = '#2563eb';
    ctx.beginPath(); ctx.moveTo(MARGEN + 96, 16); ctx.lineTo(MARGEN + 118, 16); ctx.stroke();
    ctx.fillText('pórtico Y', MARGEN + 124, 20);
    ctx.fillStyle = '#94a3b8'; ctx.font = '10.5px system-ui, sans-serif';
    ctx.fillText('Clic en un eje = pórtico resistente · clic en una luz = editar',
                 MARGEN, h - 8);
    ctx.restore();

    geom = { arX, arY, lx, ly, scale };
  }

  /* ---------------- interacción ---------------- */

  function localXY(e) {
    const r = cv.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  function buscarHit(px, py) {
    for (let k = hitBoxes.length - 1; k >= 0; k--) {
      const hb = hitBoxes[k];
      if (px >= hb.x1 && px <= hb.x2 && py >= hb.y1 && py <= hb.y2) return hb;
    }
    return null;
  }

  function onTap(e) {
    e.preventDefault();
    if (!geom) return;
    const { x, y } = localXY(e);
    const hb = buscarHit(x, y);
    if (!hb) return;

    if (hb.t === 'EJE') {
      /* desmarcar un eje con corte configurado pide confirmación */
      if (EstadoM.ejeResistente(hb.dir, hb.id)
          && EstadoM.ejeTieneCorte(hb.dir, hb.id)
          && !confirm('El eje ' + hb.dir + ':' + hb.id +
                      ' tiene un corte configurado. ¿Quitarlo de los ' +
                      'resistentes?')) {
        return;
      }
      EstadoM.toggleResistente(hb.dir, hb.id);
      if (EstadoM.ejeResistente(hb.dir, hb.id)) {
        EstadoM.seleccion.eje = { dir: hb.dir, id: hb.id };
        Corte.setEje(hb.dir, hb.id);
      } else if (EstadoM.seleccion.eje
                 && EstadoM.seleccion.eje.dir === hb.dir
                 && EstadoM.seleccion.eje.id === hb.id) {
        EstadoM.seleccion.eje = null;
        Corte.setEje(null);
      }
      render();
      Panel.actualizar();
      EstadoM.guardarLocal();

    } else if (hb.t === 'TRAMO') {
      const arr = hb.dir === 'X'
        ? EstadoM.datos.geometria.lx : EstadoM.datos.geometria.ly;
      const v = arr[hb.idx];
      const txt = prompt('Luz del vano ' + hb.dir + ' #' + (hb.idx + 1) +
                         ' (m):', v);
      if (txt == null) return;
      const nv = parseFloat(txt.replace(',', '.'));
      if (!(nv > 0) || nv > 100) {
        alert('Introduce una luz válida en metros (0 < L ≤ 100).');
        return;
      }
      arr[hb.idx] = nv;
      render();
      Panel.actualizar();
      EstadoM.guardarLocal();
    }
  }

  function onHover(e) {
    if (!geom) return;
    const { x, y } = localXY(e);
    const hb = buscarHit(x, y);
    cv.style.cursor = hb ? 'pointer' : 'default';
    if (hb) cv.title = hb.t === 'EJE'
      ? 'Eje ' + hb.dir + ':' + hb.id
      : 'Vano ' + hb.dir + ' #' + (hb.idx + 1);
  }

  function exportarPNG(nombre) {
    if (!cv) return;
    const a = document.createElement('a');
    a.download = (nombre || 'planta') + '_' + Date.now() + '.png';
    a.href = cv.toDataURL('image/png');
    a.click();
  }

  return { init, render, exportarPNG };
})();

/* ---------------- panel derecho (CORTE — esqueleto, paso 3) ---------------- */

const Corte = (function () {
  const $id = (id) => document.getElementById(id);

  function setEje(dir, id) {
    const lbl = $id('lbl-corte');
    if (dir == null) {
      lbl.textContent = 'sin pórtico seleccionado';
      $id('ayuda-corte').innerHTML =
        'Selecciona un eje resistente en la planta para ver y editar su ' +
        'corte aquí (niveles, columnas, uniones y bases).';
      return;
    }
    lbl.textContent = 'Pórtico ' + dir + ':' + id;
    $id('ayuda-corte').innerHTML =
      'Pórtico <b>' + dir + ':' + id + '</b> seleccionado. La vista editable ' +
      'del corte (niveles, columnas, uniones y bases) se activa en el ' +
      '<b>paso 3</b> del plan (MODELADOR-ESPEC §8).';
  }

  return { setEje };
})();

/* ---------------- controles y etiquetas del panel izquierdo ---------------- */

const Panel = (function () {
  const $id = (id) => document.getElementById(id);

  function actualizar() {
    const g = EstadoM.datos.geometria;
    const r = EstadoM.datos.ejes_resistentes;
    $id('lbl-planta').textContent =
      'Estructura: ' + EstadoM.datos.titulo +
      ' · ' + r.X.length + ' ejes X × ' + r.Y.length + ' ejes Y';
    $id('lbl-resistentes').textContent =
      'Resist. X: ' + r.X.length + ' · Y: ' + r.Y.length;
    const aviso = $id('aviso-rho');
    const falta = r.X.length < 2 || r.Y.length < 2;
    aviso.classList.toggle('oculto', !falta);
    if (falta) {
      aviso.title = 'COVENIN 1756-1 §6.3, Tabla 13: con menos de 2 pórticos ' +
        'resistentes por dirección puede penalizar el factor de redundancia ρ. ' +
        'Marca al menos 2 ejes en X y 2 en Y.';
    }
    /* el título del proyecto vive en el header */
    if ($id('inp-titulo').value !== EstadoM.datos.titulo) {
      $id('inp-titulo').value = EstadoM.datos.titulo;
    }
  }

  function vincular() {
    $id('btn-mas-lx').onclick = () => {
      EstadoM.datos.geometria.lx.push(EstadoM.datos.geometria.lx.slice(-1)[0] || 5);
      trasCambioGeometria();
    };
    $id('btn-menos-lx').onclick = () => {
      if (EstadoM.datos.geometria.lx.length <= 1) return;
      if (!confirm('¿Eliminar el último vano en X?')) return;
      EstadoM.datos.geometria.lx.pop();
      limpiarEjesFuera();
      trasCambioGeometria();
    };
    $id('btn-mas-ly').onclick = () => {
      EstadoM.datos.geometria.ly.push(EstadoM.datos.geometria.ly.slice(-1)[0] || 5);
      trasCambioGeometria();
    };
    $id('btn-menos-ly').onclick = () => {
      if (EstadoM.datos.geometria.ly.length <= 1) return;
      if (!confirm('¿Eliminar el último vano en Y?')) return;
      EstadoM.datos.geometria.ly.pop();
      limpiarEjesFuera();
      trasCambioGeometria();
    };

    $id('inp-titulo').addEventListener('change', (e) => {
      EstadoM.datos.titulo = e.target.value.trim() || 'Estructura sin nombre';
      Panel.actualizar();
      EstadoM.guardarLocal();
    });

    $id('btn-png-planta').onclick = () =>
      Planta.exportarPNG('planta_' + EstadoM.datos.titulo.replace(/\s+/g, '_'));

    $id('btn-guardar').onclick = () => {
      const a = document.createElement('a');
      a.download = 'modelador_' +
        EstadoM.datos.titulo.replace(/\s+/g, '_') + '.json';
      a.href = URL.createObjectURL(
        new Blob([JSON.stringify(EstadoM.datos, null, 1)],
                 { type: 'application/json' }));
      a.click();
    };

    $id('btn-abrir').onclick = () => $id('file-abrir').click();
    $id('file-abrir').addEventListener('change', (e) => {
      const f = e.target.files[0];
      if (!f) return;
      const rd = new FileReader();
      rd.onload = () => {
        try {
          EstadoM.datos = ModeladorMigrar(JSON.parse(rd.result));
          trasCambioGeometria();
          Corte.setEje(null);
          EstadoM.seleccion.eje = null;
        } catch (err) {
          alert('El archivo no tiene el formato del Modelador.');
        }
      };
      rd.readAsText(f);
      e.target.value = '';
    });

    $id('btn-limpiar').onclick = () => {
      if (!confirm('¿Borrar TODA la geometría del modelador?')) return;
      EstadoM.datos = ModeladorMigrar({});
      EstadoM.seleccion.eje = null;
      Corte.setEje(null);
      trasCambioGeometria();
    };
  }

  function limpiarEjesFuera() {
    /* ejes resistentes que quedaron fuera de la retícula */
    const g = EstadoM.datos.geometria;
    EstadoM.datos.ejes_resistentes.X =
      EstadoM.datos.ejes_resistentes.X.filter(j => j >= 1 && j <= g.lx.length);
    EstadoM.datos.ejes_resistentes.Y =
      EstadoM.datos.ejes_resistentes.Y.filter(
        l => EstadoM.idxLetra(l) < g.ly.length);
    if (EstadoM.seleccion.eje
        && !EstadoM.ejeResistente(EstadoM.seleccion.eje.dir,
                                  EstadoM.seleccion.eje.id)) {
      EstadoM.seleccion.eje = null;
      Corte.setEje(null);
    }
  }

  function trasCambioGeometria() {
    Planta.render();
    Panel.actualizar();
    EstadoM.guardarLocal();
  }

  return { actualizar, vincular };
})();

/* ---------------- arranque ---------------- */

document.addEventListener('DOMContentLoaded', () => {
  EstadoM.cargarLocal();
  Panel.vincular();
  Planta.init();
  Panel.actualizar();
});
