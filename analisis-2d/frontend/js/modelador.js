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
        { nombre: 'N3', h_piso: 3.2, es_techo: true,
          pp_techo: 50, pendiente: 0 },
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

  /* configuración del pórtico (cortes["X:1"]) — se crea al vuelo y se
     completa si la retícula creció (§5 de la espec) */
  clavesColumnas(dir) {
    const g = this.datos.geometria;
    /* ejes = vanos + 1 (2 vanos en Y → A,B,C) */
    const n = (dir === 'X' ? g.ly.length : g.lx.length) + 1;
    const out = [];
    for (let i = 0; i < n; i++) out.push(dir === 'X' ? this.letraEje(i) : String(i + 1));
    return out;
  },

  corteDe(dir, id) {
    const key = dir + ':' + id;
    const cs = this.datos.cortes;
    if (!cs[key]) {
      const columnas = {};
      this.clavesColumnas(dir).forEach(k => {
        columnas[k] = { activa: true, base: 'empotrada' };
      });
      cs[key] = {
        niveles_propios: this.datos.geometria.niveles.length,
        columnas,
        uniones: { patron: 'pr_momento', excepciones: {} },
      };
    } else {
      /* asegurar columnas nuevas (± vanos después de crear el corte) */
      this.clavesColumnas(dir).forEach(k => {
        if (!cs[key].columnas[k]) {
          cs[key].columnas[k] = { activa: true, base: 'empotrada' };
        }
      });
    }
    return cs[key];
  },

  /* tipo efectivo de unión de un nudo (patrón salvo excepción) */
  tipoUnion(corte, nodoKey) {
    const ex = corte.uniones.excepciones[nodoKey];
    if (ex) return ex;
    return corte.uniones.patron === 'pr_momento' ? 'rígida' : 'articulada';
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
  /* luces válidas (> 0); un estado corrupto/viejo cae a los de fábrica */
  const lx = (g.lx || []).map(Number).filter(v => v > 0);
  const ly = (g.ly || []).map(Number).filter(v => v > 0);
  const geo = {
    lx: lx.length ? lx : [5, 5, 5],
    ly: ly.length ? ly : [5, 5, 4, 4],
      niveles: (g.niveles && g.niveles.length
        ? g.niveles
        : [{ nombre: 'N1', h_piso: 4 }]).map(n => ({
            nombre: String(n.nombre), h_piso: Number(n.h_piso) || 3.0,
            es_techo: !!n.es_techo,
            pp_techo: (n.pp_techo != null && n.pp_techo !== '')
              ? Number(n.pp_techo) : 50,
            pendiente: (n.pendiente != null && n.pendiente !== '')
              ? Number(n.pendiente) : 0,
          })),
  };
  /* resistentes: guardar los válidos del estado; si el estado viejo no
     traía la clave (o todos resultaron inválidos), recuperar los de
     fábrica: primer y último eje en cada dirección. Sin esto, la planta
     queda «0 ejes» y no hay nada que clicar. */
  const r = d.ejes_resistentes || {};
  const res = {
    X: (Array.isArray(r.X) ? r.X : []).map(Number)
        .filter(j => j >= 1 && j <= geo.lx.length),
    Y: (Array.isArray(r.Y) ? r.Y : []).map(String)
        .filter(l => /^[A-Z]$/.test(l) && (l.charCodeAt(0) - 65) < geo.ly.length),
  };
  if (!res.X.length && !res.Y.length) {
    res.X = [1, geo.lx.length + 1];                 /* ejes = vanos + 1 */
    res.Y = ['A', String.fromCharCode(65 + geo.ly.length)];
  }
  return {
    titulo: d.titulo || 'Estructura sin nombre',
    geometria: geo,
    ejes_resistentes: res,
    cortes: d.cortes || {},
  };
}

/* ---------------- compat de eventos (compartido Planta/Corte) ----------------
   Navegadores sin Pointer Events usan mousedown/touchstart; «gestoUnico»
   evita el doble disparo cuando el navegador manda varios eventos por el
   mismo gesto (p. ej. pointerdown + mousedown). Vive a nivel de archivo
   porque la planta Y el corte lo usan. */
const ultimoGesto = {};
function gestoUnico(clave, tipo) {
  const t = Date.now();
  const a = ultimoGesto[clave];
  if (a && a.tipo !== tipo && t - a.t < 250) return false;
  ultimoGesto[clave] = { tipo, t };
  return true;
}

/* ---------------- lienzo de la PLANTA ---------------- */

const Planta = (function () {
  const MARGEN = 58;
  let cv = null, ctx = null, wrap = null;
  let hitBoxes = [];
  let hoverHB = null;          /* hitbox bajo el cursor (resaltado) */
  let toastTimer = null;
  function toastPlanta(msg) {
    if (!wrap) return;
    let t = document.getElementById('toast-planta');
    if (!t) {
      t = document.createElement('div');
      t.id = 'toast-planta';
      t.style.cssText = 'position:absolute;left:50%;bottom:10px;transform:translateX(-50%);' +
        'background:#0f172a;color:#fff;padding:6px 12px;border-radius:8px;' +
        'font:12.5px system-ui,sans-serif;pointer-events:none;z-index:5;transition:opacity .3s';
      wrap.appendChild(t);
    }
    t.textContent = msg; t.style.opacity = '1';
    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { t.style.opacity = '0'; }, 1800);
  }
  let geom = null;                    /* {arX, arY, lx, ly, scale} */

  const $id = (id) => document.getElementById(id);
  const sum = (a) => a.reduce((x, y) => x + y, 0);

  function init() {
    cv = $id('cv-planta');
    if (!cv) return;
    ctx = cv.getContext('2d');
    wrap = cv.parentElement;
    const down = (e) => {
      if (e.type === 'touchstart' && e.cancelable) e.preventDefault();
      if (gestoUnico('P', e.type)) onTap(e);
    };
    wrap.addEventListener('mousedown', down);
    wrap.addEventListener('touchstart', down, { passive: false });
    if (window.PointerEvent) wrap.addEventListener('pointerdown', down);
    wrap.addEventListener('mousemove', onHover);
    if (window.PointerEvent) wrap.addEventListener('pointermove', onHover);
    wrap.addEventListener('mouseleave', () => {
      hoverHB = null; wrap.style.cursor = 'default'; render();
    });
    if (window.ResizeObserver) {
      try { new ResizeObserver(render).observe(wrap); } catch (e) { /* opcional */ }
    }
    window.addEventListener('resize', render);
    window.addEventListener('pestana-activada', (e) => {
      if (e.detail === 'modelador') render();
    });
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
    /* sello de versión: permite confirmar de un vistazo qué JS corre */
    ctx.fillStyle = '#94a3b8'; ctx.font = '10px monospace'; ctx.textAlign = 'right';
    ctx.fillText('v20260927e', w - 6, h - 6); ctx.textAlign = 'left';
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

    /* --- ejes: resistentes gruesos con color; el resto gris punteado.
           TODOS son clicables → la planta siempre se puede recuperar --- */
    ctx.setLineDash([]);
    for (let j = 1; j <= arX.length; j++) {
      const x = arX[j - 1];
      if (x == null) continue;
      const esRes = EstadoM.ejeResistente('X', j);
      const selAqui = sel && sel.dir === 'X' && sel.id === j;
      ctx.lineWidth = esRes ? 4 : 1.5;
      ctx.setLineDash(esRes ? [] : [6, 5]);
      ctx.strokeStyle = selAqui ? '#b91c1c'
        : (esRes ? '#dc2626' : '#94a3b8');
      ctx.beginPath(); ctx.moveTo(x, y0); ctx.lineTo(x, y1); ctx.stroke();
      hitBoxes.push({ t: 'EJE', dir: 'X', id: j,
                      x1: x - 11, y1: y0 - 14, x2: x + 11, y2: y1 + 14 });
    }
    for (let i = 0; i < arY.length; i++) {
      const l = EstadoM.letraEje(i);
      const y = arY[i];
      const esRes = EstadoM.ejeResistente('Y', l);
      const selAqui = sel && sel.dir === 'Y' && sel.id === l;
      ctx.lineWidth = esRes ? 4 : 1.5;
      ctx.setLineDash(esRes ? [] : [6, 5]);
      ctx.strokeStyle = selAqui ? '#1d4ed8'
        : (esRes ? '#2563eb' : '#94a3b8');
      ctx.beginPath(); ctx.moveTo(x0, y); ctx.lineTo(x1, y); ctx.stroke();
      hitBoxes.push({ t: 'EJE', dir: 'Y', id: l,
                      x1: x0 - 14, y1: y - 11, x2: x1 + 14, y2: y + 11 });
    }
    ctx.setLineDash([]);

    /* --- nudos de cruce --- */
    const rN = Math.max(5, scale / 10);
    for (let i = 0; i < arY.length; i++) {
      for (let j = 0; j < arX.length; j++) {
        ctx.fillStyle = '#f8fafc';
        ctx.beginPath(); ctx.arc(arX[j], arY[i], rN, 0, 2 * Math.PI); ctx.fill();
        ctx.strokeStyle = '#475569'; ctx.lineWidth = 1.8; ctx.stroke();
      }
    }

    /* --- hitboxes de tramos (editar luz): franja CORRIDA de 18 px en el
           centro del vano, retirada 14 px de los ejes para no pisarlas --- */
    for (let j = 0; j < lx.length; j++) {
      const yc = (y0 + y1) / 2;
      if (arX[j + 1] - arX[j] <= 30) continue;
      hitBoxes.push({ t: 'TRAMO', dir: 'X', idx: j,
                      x1: arX[j] + 14, y1: yc - 9, x2: arX[j + 1] - 14, y2: yc + 9 });
    }
    for (let i = 0; i < ly.length; i++) {
      const xc = (x0 + x1) / 2;
      if (arY[i + 1] - arY[i] <= 30) continue;
      hitBoxes.push({ t: 'TRAMO', dir: 'Y', idx: i,
                      x1: xc - 9, y1: arY[i] + 14, x2: xc + 9, y2: arY[i + 1] - 14 });
    }

    /* --- resaltado del hitbox bajo el cursor --- */
    if (hoverHB) {
      ctx.strokeStyle = '#f59e0b'; ctx.lineWidth = 2;
      ctx.strokeRect(hoverHB.x1 - 3, hoverHB.y1 - 3,
                     (hoverHB.x2 - hoverHB.x1) + 6, (hoverHB.y2 - hoverHB.y1) + 6);
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
    if (e.touches && e.touches[0]) e = e.touches[0];
    const r = cv.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  function buscarHit(px, py) {
    /* el eje SIEMPRE gana sobre el tramo: recorre al revés y devuelve la
       primera EJE encontrada; los tramos solo ganan si no hay eje debajo */
    let otro = null;
    for (let k = hitBoxes.length - 1; k >= 0; k--) {
      const hb = hitBoxes[k];
      if (px < hb.x1 || px > hb.x2 || py < hb.y1 || py > hb.y2) continue;
      if (hb.t === 'EJE') return hb;
      if (!otro) otro = hb;
    }
    return otro;
  }

  /* en pantallas angostas el corte queda debajo de la planta:
     al elegir un pórtico, llévalo a la vista (si está fuera de pantalla) */
  function llevarCorteAVista() {
    const wc = $id('wrap-corte');
    if (!wc || !wc.getBoundingClientRect) return;
    let top = 0;
    try { top = wc.getBoundingClientRect().top; } catch (e) { return; }
    const vh = window.innerHeight || 0;
    if (top > vh) {
      try { wc.scrollIntoView({ behavior: 'smooth', block: 'start' }); }
      catch (e) { try { wc.scrollIntoView(true); } catch (e2) { /* opcional */ } }
    }
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
      toastPlanta('EJE ' + hb.dir + ':' + hb.id +
                  (EstadoM.ejeResistente(hb.dir, hb.id)
                    ? ' → resistente ✓'
                    : ' → quitado de resistentes'));
      if (EstadoM.ejeResistente(hb.dir, hb.id)) llevarCorteAVista();

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
      toastPlanta('Luz vano ' + hb.dir + ' #' + (hb.idx + 1) + ' = ' + nv + ' m');
    }
  }

  function onHover(e) {
    if (!geom || !wrap) return;
    const { x, y } = localXY(e);
    const hb = buscarHit(x, y);
    hoverHB = hb;
    wrap.style.cursor = hb ? 'pointer' : 'default';
    if (hb) cv.title = hb.t === 'EJE'
      ? 'Eje ' + hb.dir + ':' + hb.id
      : 'Vano ' + hb.dir + ' #' + (hb.idx + 1);
    render();
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

  /* -------- editor de niveles globales (nombre · h · techo) -------- */
  function renderNiveles() {
    const div = $id('tabla-niveles-m');
    if (!div) return;
    const ns = EstadoM.datos.geometria.niveles;
    let html = '<table><thead><tr><th>Nivel</th><th>h piso (m)</th>' +
      '<th title="CV por §5.2.4 en lugar de la Tabla 5.1">techo</th>' +
      '<th>pp techo (kg/m²)</th><th>pendiente (%)</th></tr></thead><tbody>';
    ns.forEach((n, i) => {
      html += `<tr>
        <td><input class="in-nom" data-i="${i}" value="${n.nombre}" size="6"></td>
        <td><input type="number" step="0.1" min="1" class="in-h" data-i="${i}"
                   value="${n.h_piso}" style="width:70px"></td>
        <td style="text-align:center"><input type="checkbox" class="in-techo"
                   data-i="${i}" ${n.es_techo ? 'checked' : ''}></td>
        <td><input type="number" step="5" min="0" class="in-pp" data-i="${i}"
                   value="${n.pp_techo == null ? 50 : n.pp_techo}" style="width:70px"
                   ${n.es_techo ? '' : 'disabled'}></td>
        <td><input type="number" step="1" min="0" class="in-pend" data-i="${i}"
                   value="${n.pendiente == null ? 0 : n.pendiente}" style="width:70px"
                   ${n.es_techo ? '' : 'disabled'}></td></tr>`;
    });
    div.innerHTML = html + '</tbody></table>';

    const alCambiar = () => {
      renderNiveles();
      Planta.render();
      Panel.actualizar();
      EstadoM.guardarLocal();
    };
    div.querySelectorAll('.in-nom').forEach(inp =>
      inp.addEventListener('change', () => {
        ns[+inp.dataset.i].nombre = inp.value.trim() || ('N' + (+inp.dataset.i + 1));
        alCambiar();
      }));
    div.querySelectorAll('.in-h').forEach(inp =>
      inp.addEventListener('input', () => {
        const v = parseFloat(inp.value);
        if (v > 0 && v <= 30) { ns[+inp.dataset.i].h_piso = v; EstadoM.guardarLocal(); }
      }));
    div.querySelectorAll('.in-techo').forEach(inp =>
      inp.addEventListener('change', () => {
        const n = ns[+inp.dataset.i];
        n.es_techo = inp.checked;
        /* solo el último nivel puede ser techo: si marco uno, desmarco otros */
        if (n.es_techo) ns.forEach((o, k) => { if (k !== +inp.dataset.i) o.es_techo = false; });
        alCambiar();
      }));
    div.querySelectorAll('.in-pp').forEach(inp =>
      inp.addEventListener('input', () => {
        const v = parseFloat(inp.value);
        if (v >= 0) { ns[+inp.dataset.i].pp_techo = v; EstadoM.guardarLocal(); }
      }));
    div.querySelectorAll('.in-pend').forEach(inp =>
      inp.addEventListener('input', () => {
        const v = parseFloat(inp.value);
        if (v >= 0) { ns[+inp.dataset.i].pendiente = v; EstadoM.guardarLocal(); }
      }));
  }

  function setEje(dir, id) {
    const lbl = $id('lbl-corte');
    if (dir == null) {
      lbl.textContent = 'sin pórtico seleccionado';
      const selc = $id('sel-corte');
      if (selc) selc.value = '';
      $id('lbl-np').textContent = '–';
      dibujar();
      return;
    }
    lbl.textContent = 'Pórtico ' + dir + ':' + id +
      ' (corre en ' + (dir === 'X' ? 'Y' : 'X') + ')';
    const corte = EstadoM.corteDe(dir, id);
    $id('sel-patron').value = corte.uniones.patron;
    $id('lbl-np').textContent = corte.niveles_propios + ' / ' +
      EstadoM.datos.geometria.niveles.length;
    dibujar();
  }

  /* ---------------- dibujo del CORTE ---------------- */
  let cvC = null, ctxC = null, wrapC = null;
  let hitsC = [];
  let geomC = null;

  const M = 62;                       /* margen del lienzo del corte */

  function lienzos() {
    if (cvC) return true;
    cvC = $id('cv-corte');
    if (!cvC) return false;
    ctxC = cvC.getContext('2d');
    wrapC = cvC.parentElement;
    const downC = (e) => {
      if (e.type === 'touchstart' && e.cancelable) e.preventDefault();
      if (gestoUnico('C', e.type)) onTapC(e);
    };
    wrapC.addEventListener('mousedown', downC);
    wrapC.addEventListener('touchstart', downC, { passive: false });
    if (window.PointerEvent) wrapC.addEventListener('pointerdown', downC);
    cvC.addEventListener('pointermove', onHoverC);
    window.addEventListener('resize', dibujar);
    return true;
  }

  function dibujar() {
    if (!lienzos()) return;
    const d = EstadoM.datos;
    const w = Math.max(wrapC.clientWidth, 240);
    const h = Math.max(wrapC.clientHeight || 300, 240);
    const dpr = window.devicePixelRatio || 1;
    cvC.width = Math.round(w * dpr);
    cvC.height = Math.round(h * dpr);
    cvC.style.width = w + 'px';
    cvC.style.height = h + 'px';
    ctxC.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctxC.clearRect(0, 0, w, h);
    ctxC.fillStyle = '#fbfcfd';
    ctxC.fillRect(0, 0, w, h);
    hitsC = [];

    const sel = EstadoM.seleccion.eje;
    if (!sel) {
      ctxC.fillStyle = '#94a3b8';
      ctxC.font = '13px system-ui, sans-serif';
      ctxC.textAlign = 'center';
      ctxC.fillText('Selecciona un eje resistente en la planta (o arriba)',
                    w / 2, h / 2);
      geomC = null;
      return;
    }

    const corte = EstadoM.corteDe(sel.dir, sel.id);
    const niveles = d.geometria.niveles.slice(0, corte.niveles_propios);
    const luces = (sel.dir === 'X' ? d.geometria.ly : d.geometria.lx)
      .map(Number);
    const claves = EstadoM.clavesColumnas(sel.dir);
    const totL = luces.reduce((a, b) => a + b, 0) || 1;
    const H = niveles.reduce((s2, n) => s2 + (+n.h_piso || 0), 0) || 1;

    const scale = Math.min((w - 2 * M) / totL, (h - 2 * M - 14) / H, 95);
    const xs = [M];
    luces.forEach(v => xs.push(xs[xs.length - 1] + v * scale));
    const y0 = h - M;                                  /* línea de base */
    const elev = [0];                                  /* metros acumulados */
    niveles.forEach(n => elev.push(elev[elev.length - 1] + (+n.h_piso || 0)));

    /* terreno */
    ctxC.strokeStyle = '#64748b'; ctxC.lineWidth = 2;
    ctxC.beginPath();
    ctxC.moveTo(xs[0] - 24, y0 + 1); ctxC.lineTo(xs[xs.length - 1] + 24, y0 + 1);
    ctxC.stroke();
    ctxC.lineWidth = 1;
    for (let x = xs[0] - 20; x < xs[xs.length - 1] + 20; x += 9) {
      ctxC.beginPath(); ctxC.moveTo(x, y0 + 2); ctxC.lineTo(x - 6, y0 + 9); ctxC.stroke();
    }

    /* niveles (líneas + etiquetas izquierda y h de piso a la derecha) */
    ctxC.textBaseline = 'middle';
    for (let k = 1; k < elev.length; k++) {
      const y = y0 - elev[k] * scale;
      ctxC.strokeStyle = '#cbd5e1'; ctxC.lineWidth = 1;
      ctxC.beginPath(); ctxC.moveTo(xs[0], y); ctxC.lineTo(xs[xs.length - 1], y); ctxC.stroke();
      ctxC.fillStyle = '#475569';
      ctxC.font = 'bold 11.5px system-ui, sans-serif'; ctxC.textAlign = 'right';
      ctxC.fillText(niveles[k - 1].nombre, xs[0] - 10, y);
      ctxC.font = '10px system-ui, sans-serif'; ctxC.fillStyle = '#94a3b8';
      ctxC.fillText('+' + elev[k].toFixed(2), xs[0] - 10, y + 12);
      ctxC.textAlign = 'left';
      ctxC.fillText('h=' + niveles[k - 1].h_piso.toFixed(2),
                    xs[xs.length - 1] + 10, y);
    }

    /* columnas + bases + nudos */
    const yTop = y0 - H * scale;
    for (let i = 0; i < claves.length; i++) {
      const clave = claves[i];
      const colCfg = corte.columnas[clave];
      const x = xs[i];
      if (colCfg.activa) {
        ctxC.strokeStyle = '#334155'; ctxC.lineWidth = 3;
        ctxC.setLineDash([]);
        ctxC.beginPath(); ctxC.moveTo(x, y0); ctxC.lineTo(x, yTop); ctxC.stroke();
      } else {
        ctxC.strokeStyle = '#94a3b8'; ctxC.lineWidth = 2;
        ctxC.setLineDash([6, 5]);
        ctxC.beginPath(); ctxC.moveTo(x, y0); ctxC.lineTo(x, yTop); ctxC.stroke();
        ctxC.setLineDash([]);
      }
      /* base */
      const artic = colCfg.base === 'articulada';
      ctxC.beginPath();
      ctxC.moveTo(x - 8, y0); ctxC.lineTo(x + 8, y0); ctxC.lineTo(x, y0 - 9);
      ctxC.closePath();
      if (artic) {
        ctxC.strokeStyle = '#334155'; ctxC.lineWidth = 1.6; ctxC.stroke();
        ctxC.fillStyle = '#334155';
        [-4, 4].forEach(dx => {
          ctxC.beginPath(); ctxC.arc(x + dx, y0 + 4, 2.2, 0, 7); ctxC.fill();
        });
      } else {
        ctxC.fillStyle = '#334155'; ctxC.fill();
      }
      hitsC.push({ t: 'BASE', clave, x1: x - 13, y1: y0 - 12, x2: x + 13, y2: y0 + 9 });
      /* nudo en la cima de cada nivel (columna activa) */
      if (colCfg.activa) {
        for (let k = 1; k < elev.length; k++) {
          const y = y0 - elev[k] * scale;
          const nk = 'N' + k + '|' + clave;
          const tipo = EstadoM.tipoUnion(corte, nk);
          const ex = !!corte.uniones.excepciones[nk];
          if (tipo === 'rígida') {
            ctxC.fillStyle = '#0f172a';
            ctxC.fillRect(x - 4, y - 4, 8, 8);
          } else {
            ctxC.fillStyle = '#f8fafc';
            ctxC.beginPath(); ctxC.arc(x, y, 3.8, 0, 7); ctxC.fill();
            ctxC.strokeStyle = '#0f172a'; ctxC.lineWidth = 1.6; ctxC.stroke();
          }
          if (ex) {
            ctxC.fillStyle = '#f59e0b';
            ctxC.beginPath(); ctxC.arc(x + 7, y - 7, 3, 0, 7); ctxC.fill();
          }
          hitsC.push({ t: 'JUNT', clave, nivel: k, x1: x - 9, y1: y - 9, x2: x + 11, y2: y + 9 });
        }
      }
      /* alternar columna (zona media del fuste) */
      hitsC.push({ t: 'COL', clave, x1: x - 9, y1: yTop + 14, x2: x + 9, y2: y0 - 18 });
    }

    /* vigas entre columnas activas consecutivas (luz heredada) */
    for (let k = 1; k < elev.length; k++) {
      const y = y0 - elev[k] * scale;
      let i = -1;
      for (let j = 0; j < claves.length; j++) {
        const activa = corte.columnas[claves[j]].activa;
        if (!activa) continue;
        if (i >= 0) {
          ctxC.strokeStyle = '#2563eb'; ctxC.lineWidth = 3.5;
          ctxC.beginPath(); ctxC.moveTo(xs[i], y); ctxC.lineTo(xs[j], y); ctxC.stroke();
          const luz = luces.slice(i, j).reduce((a, b) => a + b, 0);
          if ((xs[j] - xs[i]) > 34) {
            ctxC.fillStyle = '#64748b'; ctxC.font = '10px system-ui';
            ctxC.textAlign = 'center';
            ctxC.fillText(luz.toFixed(1) + ' m', (xs[i] + xs[j]) / 2, y + 12);
          }
        }
        i = j;
      }
    }

    /* leyenda */
    ctxC.fillStyle = '#64748b'; ctxC.font = '10.5px system-ui';
    ctxC.textAlign = 'left'; ctxC.textBaseline = 'alphabetic';
    const lx0 = M - 50, ly0 = h - 16;
    ctxC.fillStyle = '#0f172a'; ctxC.fillRect(lx0, ly0 - 4, 7, 7);
    ctxC.fillStyle = '#64748b'; ctxC.fillText('rígida', lx0 + 11, ly0 + 2);
    ctxC.beginPath(); ctxC.arc(lx0 + 62, ly0, 3.4, 0, 7); ctxC.fillStyle = '#f8fafc'; ctxC.fill();
    ctxC.strokeStyle = '#0f172a'; ctxC.lineWidth = 1.4; ctxC.stroke();
    ctxC.fillStyle = '#64748b'; ctxC.fillText('articulada', lx0 + 70, ly0 + 2);
    ctxC.fillStyle = '#f59e0b'; ctxC.beginPath(); ctxC.arc(lx0 + 132, ly0, 3, 0, 7); ctxC.fill();
    ctxC.fillStyle = '#64748b'; ctxC.fillText('excepción', lx0 + 139, ly0 + 2);
    ctxC.strokeStyle = '#94a3b8'; ctxC.setLineDash([4, 3]); ctxC.lineWidth = 2;
    ctxC.beginPath(); ctxC.moveTo(lx0 + 198, ly0 - 4); ctxC.lineTo(lx0 + 220, ly0 - 4); ctxC.stroke();
    ctxC.setLineDash([]);
    ctxC.fillText('columna fuera', lx0 + 225, ly0 + 2);

    geomC = { xs, y0, elev, scale };
  }

  /* ---------------- interacción del corte ---------------- */

  function localXYC(e) {
    if (e.touches && e.touches[0]) e = e.touches[0];
    const r = cvC.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  function buscarHitC(px, py) {
    for (let k = hitsC.length - 1; k >= 0; k--) {
      const hb = hitsC[k];
      if (px >= hb.x1 && px <= hb.x2 && py >= hb.y1 && py <= hb.y2) return hb;
    }
    return null;
  }

  function guardarYDibujar() {
    EstadoM.guardarLocal();
    dibujar();
  }

  function onTapC(e) {
    e.preventDefault();
    if (!geomC) return;
    const { x, y } = localXYC(e);
    const hb = buscarHitC(x, y);
    if (!hb) return;
    const sel = EstadoM.seleccion.eje;
    if (!sel) return;
    const corte = EstadoM.corteDe(sel.dir, sel.id);

    if (hb.t === 'COL') {
      const c = corte.columnas[hb.clave];
      c.activa = !c.activa;
      guardarYDibujar();
    } else if (hb.t === 'BASE') {
      const c = corte.columnas[hb.clave];
      c.base = c.base === 'empotrada' ? 'articulada' : 'empotrada';
      guardarYDibujar();
    } else if (hb.t === 'JUNT') {
      const nk = 'N' + hb.nivel + '|' + hb.clave;
      const actual = EstadoM.tipoUnion(corte, nk);
      const nuevoT = actual === 'rígida' ? 'articulada' : 'rígida';
      const porPatron = corte.uniones.patron === 'pr_momento'
        ? 'rígida' : 'articulada';
      if (nuevoT === porPatron) delete corte.uniones.excepciones[nk];
      else corte.uniones.excepciones[nk] = nuevoT;
      guardarYDibujar();
    }
  }

  function onHoverC(e) {
    if (!geomC) return;
    const { x, y } = localXYC(e);
    const hb = buscarHitC(x, y);
    cvC.style.cursor = hb ? 'pointer' : 'default';
    if (hb) {
      cvC.title = hb.t === 'COL' ? 'Columna ' + hb.clave +
          ' (clic: activar/desactivar)'
        : hb.t === 'BASE' ? 'Base ' + hb.clave + ' (clic: alterna)'
        : 'Nudo N' + hb.nivel + '|' + hb.clave + ' (clic: excepción ⚡)';
    }
  }

  /* ---------------- controles del corte ---------------- */

  function refrescarSelector() {
    const selc = $id('sel-corte');
    if (!selc) return;
    const r = EstadoM.datos.ejes_resistentes;
    const opts = ['<option value="">— elige un pórtico —</option>'];
    r.X.forEach(j => opts.push(
      `<option value="X:${j}">X:${j} · corre en Y</option>`));
    r.Y.forEach(l => opts.push(
      `<option value="Y:${l}">Y:${l} · corre en X</option>`));
    selc.innerHTML = opts.join('');
    const sel = EstadoM.seleccion.eje;
    selc.value = sel ? sel.dir + ':' + sel.id : '';
  }

  function vincularCorte() {
    $id('sel-corte').addEventListener('change', (e) => {
      const v = e.target.value;
      if (!v) { EstadoM.seleccion.eje = null; setEje(null); Panel.actualizar(); return; }
      const [dir, idTxt] = v.split(':');
      const id = dir === 'X' ? +idTxt : idTxt;
      EstadoM.seleccion.eje = { dir, id };
      setEje(dir, id);
      Planta.render();
      EstadoM.guardarLocal();
    });
    $id('sel-patron').addEventListener('change', (e) => {
      const sel = EstadoM.seleccion.eje;
      if (!sel) { e.target.value = 'pr_momento'; return; }
      const corte = EstadoM.corteDe(sel.dir, sel.id);
      corte.uniones.patron = e.target.value;
      /* el patrón reemplaza las uniones NO marcadas como excepción */
      corte.uniones.excepciones = {};
      guardarYDibujar();
    });
    $id('btn-menos-np').onclick = () => {
      const sel = EstadoM.seleccion.eje;
      if (!sel) return;
      const corte = EstadoM.corteDe(sel.dir, sel.id);
      if (corte.niveles_propios <= 1) return;
      corte.niveles_propios--;
      $id('lbl-np').textContent = corte.niveles_propios + ' / ' +
        EstadoM.datos.geometria.niveles.length;
      guardarYDibujar();
    };
    $id('btn-mas-np').onclick = () => {
      const sel = EstadoM.seleccion.eje;
      if (!sel) return;
      const corte = EstadoM.corteDe(sel.dir, sel.id);
      const total = EstadoM.datos.geometria.niveles.length;
      if (corte.niveles_propios >= total) return;
      corte.niveles_propios++;
      $id('lbl-np').textContent = corte.niveles_propios + ' / ' + total;
      guardarYDibujar();
    };
    $id('btn-generar-2d').onclick = generarModelo2D;
    $id('btn-png-corte').onclick = () => {
      if (!cvC) return;
      const a = document.createElement('a');
      a.download = 'corte_' + (EstadoM.seleccion.eje
        ? EstadoM.seleccion.eje.dir + EstadoM.seleccion.eje.id : 'x') +
        '_' + Date.now() + '.png';
      a.href = cvC.toDataURL('image/png');
      a.click();
    };
  }

  function vincularNiveles() {
    $id('btn-mas-nivel').onclick = () => {
      const ns = EstadoM.datos.geometria.niveles;
      ns.forEach(n => { n.es_techo = false; });
      const k = ns.length + 1;
      ns.push({ nombre: 'N' + k, h_piso: 3.0, es_techo: true,
                pp_techo: 50, pendiente: 0 });
      renderNiveles();
      EstadoM.guardarLocal();
    };
    $id('btn-menos-nivel').onclick = () => {
      const ns = EstadoM.datos.geometria.niveles;
      if (ns.length <= 1) return;
      if (!confirm('¿Eliminar el nivel ' + ns[ns.length - 1].nombre + '?')) return;
      ns.pop();
      if (ns.length && !ns.some(n => n.es_techo)) ns[ns.length - 1].es_techo = true;
      renderNiveles();
      EstadoM.guardarLocal();
    };
  }

  return { setEje, renderNiveles, vincularNiveles, dibujar,
           vincularCorte, refrescarSelector };

  /* ---------------- ⚡ Generar modelo 2D (paso 4) ---------------- */

async function generarModelo2D() {
  const sel = EstadoM.seleccion.eje;
  if (!sel) {
    alert('Selecciona primero un pórtico resistente (clic en la planta o en el selector del corte).');
    return;
  }
  const previo = localStorage.getItem('analisis2d.autosave');
  if (previo && !confirm('Ya existe un modelo en Análisis 2D.\n¿Reemplazarlo con el pórtico ' +
      sel.dir + ':' + sel.id + '?')) {
    return;
  }
  let j;
  try {
    const r = await fetch('/api/generar', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ modelador: EstadoM.datos,
                             corte: sel.dir + ':' + sel.id }),
    });
    j = await r.json();
  } catch (e) {
    alert('No hay conexión con el backend (¿uvicorn está corriendo?).');
    return;
  }
  if (!j.ok) {
    alert('No se pudo generar el modelo:\n' + (j.error || 'error desconocido'));
    return;
  }
  /* 1) modelo al Análisis 2D */
  localStorage.setItem('analisis2d.autosave', JSON.stringify(j.modelo));
  if (window.Estado && Estado.cargarModelo) Estado.cargarModelo(j.modelo);
  /* 2) cargas de la norma a las vigas (CP·ancho / CV·ancho por nivel) */
  try {
    if (window.AccionesApp && AccionesApp.cargarModeloProyecto) {
      AccionesApp.cargarModeloProyecto();
      AccionesApp.aplicarNivelesABarras(true);
    }
  } catch (e) { /* sin dock de acciones (página suelta) */ }
  const rs = j.resumen;
  let msg = 'Modelo «' + j.modelo.titulo + '» generado:\n' +
    '· ' + rs.n_nudos + ' nudos · ' + rs.n_barras + ' barras' +
    ' (' + rs.n_columnas + ' columnas + ' + rs.n_vigas + ' vigas)\n' +
    '· ' + rs.niveles + ' niveles';
  if (rs.saltados && rs.saltados.length) {
    msg += '\n· Vanos salteados: ' + rs.saltados.join(' · ');
  }
  if (rs.bases_articuladas && rs.bases_articuladas.length) {
    msg += '\n· Bases articuladas: ' + rs.bases_articuladas.join(', ');
  }
  msg += '\n\nSecciones genéricas: asigna los perfiles en Análisis/Acero.';
  alert(msg);
  /* 3) abrir la pestaña de Análisis */
  if (window.Pestanas) Pestanas.activar('analisis');
  else location.href = '/#analisis';
}
})();

/* ---------------- controles y etiquetas del panel izquierdo ---------------- */

const Panel = (function () {
  const $id = (id) => document.getElementById(id);

  function actualizar() {
    const g = EstadoM.datos.geometria;
    const r = EstadoM.datos.ejes_resistentes;
    $id('lbl-planta').textContent =
      'Estructura: ' + EstadoM.datos.titulo +
      ' · ' + (g.lx.length + 1) + ' ejes X (' + r.X.length + ' resist.) × ' +
      (g.ly.length + 1) + ' ejes Y (' + r.Y.length + ' resist.)';
    $id('lbl-resistentes').textContent =
      'Resist. X: ' + r.X.length + ' · Y: ' + r.Y.length;
    const aviso = $id('aviso-rho');
    const falta = r.X.length < 2 || r.Y.length < 2;
    aviso.classList.toggle('oculto', !falta);
    if (typeof Corte !== 'undefined' && Corte.refrescarSelector) {
      Corte.refrescarSelector();
    }
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

    /* Guardar/Abrir del modelador suelto solo en la página independiente;
       en la app única lo sustituye el proyecto completo (proyecto.js) */
    if ($id('btn-guardar')) $id('btn-guardar').onclick = () => {
      const a = document.createElement('a');
      a.download = 'modelador_' +
        EstadoM.datos.titulo.replace(/\s+/g, '_') + '.json';
      a.href = URL.createObjectURL(
        new Blob([JSON.stringify(EstadoM.datos, null, 1)],
                 { type: 'application/json' }));
      a.click();
    };

    if ($id('btn-abrir')) $id('btn-abrir').onclick = () => $id('file-abrir').click();
    if ($id('file-abrir')) $id('file-abrir').addEventListener('change', (e) => {
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
    /* app única: al volver a esta pestaña, redibuja el lienzo */
    window.addEventListener('pestana-activada', (e) => {
      if (e.detail === 'modelador') Planta.render();
    });

    $id('btn-limpiar-modelador').onclick = () => {
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
    Corte.refrescarSelector();
    Corte.dibujar();
    EstadoM.guardarLocal();
  }

  return { actualizar, vincular };
})();

/* ---------------- arranque ---------------- */

document.addEventListener('DOMContentLoaded', () => {
  try {
    EstadoM.cargarLocal();
    Panel.vincular();
    Planta.init();
    Corte.vincularNiveles();
    Corte.renderNiveles();
    Corte.vincularCorte();
    Corte.refrescarSelector();
    Panel.actualizar();
    Corte.setEje(EstadoM.seleccion.eje ? EstadoM.seleccion.eje.dir : null,
                 EstadoM.seleccion.eje ? EstadoM.seleccion.eje.id : null);
  } catch (err) {
    /* nunca un init muerto en silencio: banner visible + consola */
    console.error('Modelador: error al iniciar', err);
    const d = document.createElement('div');
    d.style.cssText = 'position:fixed;left:0;right:0;bottom:0;z-index:9999;' +
      'background:#b91c1c;color:#fff;padding:10px 16px;font:13px system-ui,sans-serif';
    d.textContent = '⚠ El Modelador no pudo iniciar: ' + err.message +
                    '  (recarga con Ctrl+Shift+R si el navegador sirvió JS viejo)';
    document.body.appendChild(d);
  }
});
console.log('[UI] modelador v20260927e listo');
