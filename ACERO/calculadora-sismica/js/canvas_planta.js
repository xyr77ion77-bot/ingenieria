/* ================================================================
   canvas_planta.js — Lienzo de planta interactivo + espectro
   ---------------------------------------------------------------
   FASE 1–2.
   Patrón (heredado de los archivos auditados):
     1. estado → coordenadas (arX/arY) → dibujo → hitBoxes
     2. pointerdown → ¿qué hitbox? → Estado.seleccionar… → render()
   Mejoras aplicadas:
     · devicePixelRatio → líneas nítidas en pantallas HiDPI
     · pointer events (unifica mouse y táctil), touch-action: none
     · exportarPNG() para pegar la planta en la memoria de cálculo
     · modo "perfil real": vigas con peralte y columnas con huella
       (los colores D/C llegarán en Fase 3)
   Dibujo del espectro Ad(T) incluido (dibujarEspectro).
   ================================================================ */

const CanvasPlanta = (function () {
  'use strict';

  const MARGEN = 58;
  let cv = null, ctx = null, wrap = null;
  let hitBoxes = [];
  let geom = null;                    // {arX, arY, lx, ly, scale}

  const $id = (id) => document.getElementById(id);
  const sum = (a) => a.reduce((x, y) => x + y, 0);

  /* ---------------- init ---------------- */

  function init(canvasId) {
    cv = $id(canvasId);
    if (!cv) return;
    ctx = cv.getContext('2d');
    wrap = cv.parentElement;
    cv.addEventListener('pointerdown', onTap);
    cv.addEventListener('pointermove', onHover);
    window.addEventListener('resize', render);
    render();
  }

  /* ---------------- render principal ---------------- */

  function render() {
    if (!cv) return;
    const d = Estado.datos;
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

    const scale = Math.min((w - 2 * MARGEN) / totX, (h - 2 * MARGEN) / totY, 95);
    const arX = [MARGEN]; lx.forEach(v => arX.push(arX[arX.length - 1] + v * scale));
    const arY = [MARGEN]; ly.forEach(v => arY.push(arY[arY.length - 1] + v * scale));

    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = '#fbfcfd';
    ctx.fillRect(0, 0, w, h);
    hitBoxes = [];

    const selN = Estado.seleccion.nodo;                       // {i,j}
    const selT = Estado.seleccion.tramo;                      // {dir,idx}
    const modoReal = $id('toggle-perfil-real') ? $id('toggle-perfil-real').checked : false;

    /* --- área tributaria del nodo seleccionado --- */
    if (selN) {
      const { i, j } = selN;
      const nx = lx.length, ny = ly.length;
      const xc = arX[j], yc = arY[i];
      /* en los bordes el área tributaria NO sale del edificio (½ vano interno) */
      const axL = (j > 0 ? lx[j - 1] / 2 : 0) * scale;
      const axR = (j < nx ? lx[j] / 2 : 0) * scale;
      const ayT = (i > 0 ? ly[i - 1] / 2 : 0) * scale;
      const ayB = (i < ny ? ly[i] / 2 : 0) * scale;
      const x1 = xc - axL, y1 = yc - ayT, x2 = xc + axR, y2 = yc + ayB;
      ctx.save();
      ctx.fillStyle = 'rgba(139,92,246,0.16)';
      ctx.fillRect(x1, y1, x2 - x1, y2 - y1);
      ctx.setLineDash([6, 5]); ctx.strokeStyle = '#8b5cf6'; ctx.lineWidth = 1.6;
      ctx.strokeRect(x1, y1, x2 - x1, y2 - y1);
      ctx.setLineDash([]);
      ctx.fillStyle = '#6d28d9';
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.font = 'bold 11px system-ui, sans-serif';
      ctx.fillText(((axL + axR) / scale).toFixed(2) + ' m', xc, y1 - 9);
      ctx.save();
      ctx.translate(x1 - 11, yc); ctx.rotate(-Math.PI / 2);
      ctx.fillText(((ayT + ayB) / scale).toFixed(2) + ' m', 0, 0);
      ctx.restore();
      ctx.font = 'bold 12px system-ui, sans-serif'; ctx.fillStyle = '#5b21b6';
      ctx.fillText('At = ' + ((axL + axR) * (ayT + ayB) / (scale * scale)).toFixed(2) + ' m²', xc, yc);
      ctx.restore();
    }

    /* --- resaltar tramo seleccionado (todas las líneas del vano) --- */
    if (selT) {
      ctx.save();
      ctx.strokeStyle = '#3b82f6'; ctx.lineWidth = 7; ctx.globalAlpha = 0.32;
      if (selT.dir === 'X') {
        for (let i = 0; i < arY.length; i++) {
          ctx.beginPath();
          ctx.moveTo(arX[selT.idx], arY[i]);
          ctx.lineTo(arX[selT.idx + 1], arY[i]);
          ctx.stroke();
        }
      } else {
        for (let j = 0; j < arX.length; j++) {
          ctx.beginPath();
          ctx.moveTo(arX[j], arY[selT.idx]);
          ctx.lineTo(arX[j], arY[selT.idx + 1]);
          ctx.stroke();
        }
      }
      ctx.restore();
    }

    /* --- ejes de referencia --- */
    ctx.save();
    ctx.setLineDash([5, 4]); ctx.strokeStyle = '#cbd5e1'; ctx.lineWidth = 1;
    arY.forEach(y => { ctx.beginPath(); ctx.moveTo(arX[0] - 18, y); ctx.lineTo(arX[arX.length - 1] + 18, y); ctx.stroke(); });
    arX.forEach(x => { ctx.beginPath(); ctx.moveTo(x, arY[0] - 18); ctx.lineTo(x, arY[arY.length - 1] + 18); ctx.stroke(); });
    ctx.restore();

    /* --- vigas --- */
    if (modoReal) {
      /* peralte a escala física real: d (mm) → m × px/m; mínimo 9 px visible */
      const pv = Catalogo.get(d.material.viga) || Catalogo.get('IPE 400');
      const prof = Math.max(9, (pv.d / 1000) * scale);
      for (let i = 0; i < arY.length; i++) for (let j = 0; j < lx.length; j++) {
        ctx.fillStyle = '#d9e4ee'; ctx.strokeStyle = '#7f96ab'; ctx.lineWidth = 1;
        ctx.fillRect(arX[j], arY[i] - prof / 2, arX[j + 1] - arX[j], prof);
        ctx.strokeRect(arX[j], arY[i] - prof / 2, arX[j + 1] - arX[j], prof);
      }
    } else {
      ctx.save();
      ctx.lineWidth = Math.max(3, scale / 8); ctx.setLineDash([]);
      ctx.strokeStyle = '#f97316';                       // vigas X
      for (let i = 0; i < arY.length; i++) {
        ctx.beginPath(); ctx.moveTo(arX[0], arY[i]); ctx.lineTo(arX[arX.length - 1], arY[i]); ctx.stroke();
      }
      ctx.strokeStyle = '#0f172a';                       // vigas Y
      for (let j = 0; j < arX.length; j++) {
        ctx.beginPath(); ctx.moveTo(arX[j], arY[0]); ctx.lineTo(arX[j], arY[arY.length - 1]); ctx.stroke();
      }
      ctx.restore();
    }
    /* hitboxes de tramos (siempre, independientemente del modo) */
    for (let i = 0; i < ly.length; i++) for (let j = 0; j < lx.length; j++) {
      hitBoxes.push({ t: 'X', i: j, x1: arX[j], y1: arY[i] - 12, x2: arX[j + 1], y2: arY[i] + 12 });
      hitBoxes.push({ t: 'Y', i: i, x1: arX[j] - 12, y1: arY[i], x2: arX[j] + 12, y2: arY[i + 1] });
    }

    /* --- nodos (columnas) --- */
    const rN = Math.max(5.5, scale / 9);
    let colPerfil = null;
    if (modoReal) {
      colPerfil = Catalogo.get(d.niveles[d.niveles.length - 1].perfil) || Catalogo.get('HEB 240');
    }
    for (let i = 0; i < arY.length; i++) for (let j = 0; j < arX.length; j++) {
      const activo = selN && selN.i === i && selN.j === j;
      if (modoReal) {
        const cw = Math.max(8, (colPerfil.bf / 1000) * scale);   /* huella bf a escala */
        ctx.fillStyle = activo ? '#8b5cf6' : '#93c5fd';
        ctx.globalAlpha = 0.88;
        ctx.fillRect(arX[j] - cw / 2, arY[i] - cw / 2, cw, cw);
        ctx.globalAlpha = 1;
        ctx.strokeStyle = '#334155'; ctx.lineWidth = 1;
        ctx.strokeRect(arX[j] - cw / 2, arY[i] - cw / 2, cw, cw);
        hitBoxes.push({ t: 'NODE', i, j, x1: arX[j] - cw - 6, y1: arY[i] - cw - 6, x2: arX[j] + cw + 6, y2: arY[i] + cw + 6 });
      } else {
        ctx.fillStyle = activo ? '#8b5cf6' : '#f8fafc';
        ctx.beginPath();
        ctx.arc(arX[j], arY[i], activo ? rN + 2 : rN, 0, 2 * Math.PI);
        ctx.fill();
        ctx.strokeStyle = activo ? '#ffffff' : '#475569'; ctx.lineWidth = 2.5;
        ctx.stroke();
        hitBoxes.push({ t: 'NODE', i, j, x1: arX[j] - rN - 9, y1: arY[i] - rN - 9, x2: arX[j] + rN + 9, y2: arY[i] + rN + 9 });
      }
    }

    /* --- etiquetas --- */
    ctx.save();
    ctx.font = 'bold 13px system-ui, sans-serif'; ctx.fillStyle = '#64748b';
    ctx.textAlign = 'center'; ctx.textBaseline = 'alphabetic';
    arX.forEach((x, j) => ctx.fillText(String(j + 1), x, arY[0] - 26));
    ctx.textAlign = 'right';
    arY.forEach((y, i) => ctx.fillText(String.fromCharCode(65 + i), arX[0] - 30, y + 5));
    /* luces por vano */
    ctx.font = '10px system-ui, sans-serif'; ctx.fillStyle = '#94a3b8'; ctx.textAlign = 'center';
    for (let j = 0; j < lx.length; j++) {
      ctx.fillText(lx[j].toFixed(1) + ' m', (arX[j] + arX[j + 1]) / 2, arY[arY.length - 1] + 18);
    }
    for (let i = 0; i < ly.length; i++) {
      ctx.save();
      ctx.translate(arX[0] - 40, (arY[i] + arY[i + 1]) / 2);
      ctx.rotate(-Math.PI / 2); ctx.textAlign = 'center';
      ctx.fillText(ly[i].toFixed(1) + ' m', 0, 0);
      ctx.restore();
    }
    /* leyenda */
    const ly2 = 16;
    ctx.textAlign = 'left'; ctx.font = '11px system-ui, sans-serif';
    ctx.strokeStyle = '#f97316'; ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(MARGEN, ly2); ctx.lineTo(MARGEN + 22, ly2); ctx.stroke();
    ctx.fillStyle = '#64748b'; ctx.fillText('vigas X', MARGEN + 28, ly2 + 4);
    ctx.strokeStyle = '#0f172a';
    ctx.beginPath(); ctx.moveTo(MARGEN + 88, ly2); ctx.lineTo(MARGEN + 110, ly2); ctx.stroke();
    ctx.fillText('vigas Y', MARGEN + 116, ly2 + 4);
    ctx.fillStyle = '#94a3b8'; ctx.font = '10.5px system-ui, sans-serif';
    ctx.fillText('Pulsa un nodo (columna) o una línea (viga) para inspeccionar', MARGEN, h - 8);
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
    if (hb.t === 'NODE') Estado.seleccionarNodo({ i: hb.i, j: hb.j });
    else Estado.seleccionarTramo({ dir: hb.t, idx: hb.i });
    render();
  }

  function onHover(e) {
    if (!geom) return;
    const { x, y } = localXY(e);
    cv.style.cursor = buscarHit(x, y) ? 'pointer' : 'default';
  }

  /* ---------------- exportar PNG ---------------- */

  function exportarPNG(nombre) {
    if (!cv) return;
    const a = document.createElement('a');
    a.download = (nombre || 'planta') + '_' + Date.now() + '.png';
    a.href = cv.toDataURL('image/png');
    document.body.appendChild(a);
    a.click();
    a.remove();
  }

  /* ---------------- espectro Ad(T) ---------------- */

  function dibujarEspectro(canvasId, p, s) {
    const ce = $id(canvasId);
    if (!ce) return;
    const c = ce.getContext('2d');
    const wCSS = Math.max(ce.parentElement.clientWidth, 220);
    const hCSS = 230, padIzq = 46, padDer = 12, padSup = 14, padInf = 30;
    const dpr = window.devicePixelRatio || 1;
    ce.width = Math.round(wCSS * dpr); ce.height = Math.round(hCSS * dpr);
    ce.style.width = wCSS + 'px'; ce.style.height = hCSS + 'px';
    c.setTransform(dpr, 0, 0, dpr, 0, 0);
    c.clearRect(0, 0, wCSS, hCSS);

    const pts = COVENIN.espectroCurva(p, s, 240);
    const Tfin = pts[pts.length - 1].T;
    const AdMax = Math.max(...pts.map(q => q.Ad), s.AdT) * 1.15 || 1;
    const X = (T) => padIzq + (wCSS - padIzq - padDer) * (T / Tfin);
    const Y = (A) => hCSS - padInf - (hCSS - padSup - padInf) * (A / AdMax);

    /* ejes */
    c.strokeStyle = '#e2e8f0'; c.lineWidth = 1;
    c.beginPath(); c.moveTo(padIzq, padSup); c.lineTo(padIzq, hCSS - padInf); c.lineTo(wCSS - padDer, hCSS - padInf); c.stroke();

    /* marcadores verticales TA / TC / TD */
    [[s.TA, 'TA'], [s.TC, 'TC'], [s.TD, 'TD']].forEach(([Tv, lbl]) => {
      c.save();
      c.setLineDash([4, 4]); c.strokeStyle = '#94a3b8'; c.lineWidth = 1;
      c.beginPath(); c.moveTo(X(Tv), padSup); c.lineTo(X(Tv), hCSS - padInf); c.stroke();
      c.fillStyle = '#64748b'; c.font = '10px system-ui, sans-serif'; c.textAlign = 'center';
      c.fillText(lbl, X(Tv), hCSS - padInf + 12);
      c.restore();
    });

    /* curva */
    c.strokeStyle = '#2563eb'; c.lineWidth = 2;
    c.beginPath();
    pts.forEach((q, k) => { const px = X(q.T), py = Y(q.Ad); k === 0 ? c.moveTo(px, py) : c.lineTo(px, py); });
    c.stroke();

    /* punto de diseño T = Ta */
    c.save();
    c.setLineDash([3, 3]); c.strokeStyle = '#ef4444';
    c.beginPath(); c.moveTo(X(s.T), hCSS - padInf); c.lineTo(X(s.T), Y(s.AdT)); c.stroke();
    c.setLineDash([]);
    c.fillStyle = '#ef4444';
    c.beginPath(); c.arc(X(s.T), Y(s.AdT), 4.5, 0, 2 * Math.PI); c.fill();
    c.font = 'bold 11px system-ui, sans-serif'; c.textAlign = 'left';
    c.fillText('T = ' + s.T.toFixed(3) + ' s · Ad = ' + s.AdT.toFixed(4), Math.min(X(s.T) + 8, wCSS - 160), Y(s.AdT) - 8);
    /* etiquetas de eje */
    c.fillStyle = '#64748b'; c.font = '10px system-ui, sans-serif';
    c.fillText('T [s]', wCSS - padDer - 24, hCSS - padInf + 24);
    c.save(); c.translate(12, padSup + 40); c.rotate(-Math.PI / 2); c.textAlign = 'right';
    c.fillText('Ad(T) [g]', 0, 0);
    c.restore();
    c.restore();
  }

  return { init, render, exportarPNG, dibujarEspectro };
})();
