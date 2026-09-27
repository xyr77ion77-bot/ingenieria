/* ================================================================
   canvas.js — Lienzo interactivo del modelo 2D
   ------------------------------------------------------------------
   · Render: rejilla, barras, nudos, apoyos, cargas, selección,
     diagramas M/V/N y deformada.
   · Interacción por modo (seleccionar/nudo/barra/apoyo/puntual/
     repartida), pan (arrastre), zoom (rueda), snap magnético.
   · El dibujo de resultados usa Estado.sesion.resultado.
   ================================================================ */

const Canvas2D = (function () {
  'use strict';

  let cv, ctx, dpr = 1;
  const vista = { esc: 60, ox: 0, oy: 0 };   // px/m · origen pantalla
  let W = 0, H = 0;

  const COLOR = {
    fondo: '#ffffff',
    rejillaMenor: '#eef2f7',
    rejillaMayor: '#dde5ee',
    ejeX: '#e8b4b4', ejeY: '#b4cfe8',
    barra: '#334155', barraSel: '#2563eb', barraHover: '#60a5fa',
    nudo: '#ffffff', nudoBorde: '#334155', nudoSel: '#2563eb',
    texto: '#475569', textoSel: '#1d4ed8',
    dist: '#b45309', puntual: '#dc2626', momento: '#7c3aed',
    M: '#dc2626', V: '#2563eb', N: '#059669',
    deformada: '#7c3aed', apoyo: '#334155'
  };

  /* ---------------- utilidades coordenadas ---------------- */
  function aPantalla(x, y) { return { x: vista.ox + x * vista.esc, y: vista.oy - y * vista.esc }; }
  function aMundo(px, py) { return { x: (px - vista.ox) / vista.esc, y: (vista.oy - py) / vista.esc }; }

  function snap(v) {
    if (!Estado.herr.snap) return v;
    return Math.round(v / 0.25) * 0.25;
  }

  function nudoEn(px, py, radio) {
    radio = radio || 12;
    let mejor = null, dMin = radio;
    for (const n of Estado.datos.nudos) {
      const p = aPantalla(n.x, n.y);
      const d = Math.hypot(p.x - px, p.y - py);
      if (d < dMin) { dMin = d; mejor = n; }
    }
    return mejor;
  }

  function barraEn(px, py, tol) {
    tol = tol || 8;
    let mejor = null, dMin = tol;
    for (const b of Estado.datos.barras) {
      const ni = Estado.datos.nudos.find(n => n.id === b.ni);
      const nj = Estado.datos.nudos.find(n => n.id === b.nj);
      if (!ni || !nj) continue;
      const pi = aPantalla(ni.x, ni.y), pj = aPantalla(nj.x, nj.y);
      const d = distSeg(px, py, pi.x, pi.y, pj.x, pj.y);
      if (d < dMin) { dMin = d; mejor = b; }
    }
    return mejor;
  }

  function distSeg(px, py, x1, y1, x2, y2) {
    const dx = x2 - x1, dy = y2 - y1;
    const l2 = dx * dx + dy * dy;
    if (!l2) return Math.hypot(px - x1, py - y1);
    let t = ((px - x1) * dx + (py - y1) * dy) / l2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(px - (x1 + t * dx), py - (y1 + t * dy));
  }

  /* ---------------- escalas de resultados ---------------- */
  function escalas() {
    const res = Estado.sesion.resultado;
    if (!res) return null;
    let mM = 1e-9, mV = 1e-9, mN = 1e-9;
    for (const b of res.barras) {
      for (const d of (res.diagramas[b.id] ? [res.diagramas[b.id].M] : []))
        for (const v of d) mM = Math.max(mM, Math.abs(v));
      for (const v of res.diagramas[b.id].V) mV = Math.max(mV, Math.abs(v));
      for (const v of res.diagramas[b.id].N) mN = Math.max(mN, Math.abs(v));
    }
    return {
      M: (H * 0.10) / mM,
      V: (H * 0.10) / mV,
      N: (H * 0.10) / mN
    };
  }

  function escalaDeformada(res) {
    let m = 1e-12;
    for (const n of res.nudos) m = Math.max(m, Math.abs(n.uy), Math.abs(n.ux));
    return (H * 0.08) / m;
  }

  /* ---------------- formatos ---------------- */
  const fmtN = new Intl.NumberFormat('es-VE', { maximumFractionDigits: 2 });
  function fMomento(v) {
    const a = Math.abs(v);
    if (a >= 1000) return (v / 1000).toLocaleString('es-VE', { maximumFractionDigits: 1 }) + ' t·m';
    return fmtN.format(v) + ' kg·m';
  }
  function fFuerza(v) {
    const a = Math.abs(v);
    if (a >= 1000) return (v / 1000).toLocaleString('es-VE', { maximumFractionDigits: 1 }) + ' t';
    return fmtN.format(v) + ' kg';
  }

  /* ================= DIBUJO ================= */
  function dibujar() {
    if (!ctx) return;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = COLOR.fondo;
    ctx.fillRect(0, 0, W, H);
    if (Estado.herr.vista.grid) rejilla();
    ejes();

    const res = Estado.sesion.resultado;
    if (res && Estado.herr.vista.deformada) deformada(res);

    for (const b of Estado.datos.barras) dibujarBarra(b);
    if (res) {
      if (Estado.herr.vista.N) diagrama('N', COLOR.N, +1);
      if (Estado.herr.vista.V) diagrama('V', COLOR.V, +1);
      if (Estado.herr.vista.M) diagrama('M', COLOR.M, -1);   // M+ hacia el lado de tracción (−n)
    }
    for (const a of Estado.datos.apoyos) dibujarApoyo(a);
    for (const c of Estado.datos.cargas_nodales) dibujarCargaPuntual(c);
    for (const b of Estado.datos.barras) if (b.q_perp || b.q_axial) dibujarCargaRepartida(b);
    for (const n of Estado.datos.nudos) dibujarNudo(n);
    if (Estado.sesion.barraEnCurso) gomaBarra();
  }

  function rejilla() {
    const pasoMenor = 0.25, pasoMayor = 1;
    const p1 = aMundo(0, H), p2 = aMundo(W, 0);
    if (vista.esc < 12) { soloMayor(pasoMayor * 5); return; }
    rejillaPaso(pasoMenor, COLOR.rejillaMenor);
    rejillaPaso(pasoMayor, COLOR.rejillaMayor);
    if (vista.esc < 25) soloMayor(pasoMayor);

    function rejillaPaso(paso, color) {
      ctx.strokeStyle = color;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = Math.floor(p1.x / paso) * paso; x <= p2.x; x += paso) {
        const s = aPantalla(x, 0);
        ctx.moveTo(s.x, 0); ctx.lineTo(s.x, H);
      }
      for (let y = Math.floor(p2.y / paso) * paso; y <= p1.y; y += paso) {
        const s = aPantalla(0, y);
        ctx.moveTo(0, s.y); ctx.lineTo(W, s.y);
      }
      ctx.stroke();
    }
    function soloMayor(paso) {
      ctx.strokeStyle = COLOR.rejillaMayor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      for (let x = Math.floor(p1.x / paso) * paso; x <= p2.x; x += paso) {
        const s = aPantalla(x, 0); ctx.moveTo(s.x, 0); ctx.lineTo(s.x, H);
      }
      for (let y = Math.floor(p2.y / paso) * paso; y <= p1.y; y += paso) {
        const s = aPantalla(0, y); ctx.moveTo(0, s.y); ctx.lineTo(W, s.y);
      }
      ctx.stroke();
    }
  }

  function ejes() {
    const o = aPantalla(0, 0);
    ctx.strokeStyle = COLOR.ejeX; ctx.lineWidth = 1.5;
    ctx.beginPath(); ctx.moveTo(0, o.y); ctx.lineTo(W, o.y); ctx.stroke();
    ctx.strokeStyle = COLOR.ejeY;
    ctx.beginPath(); ctx.moveTo(o.x, 0); ctx.lineTo(o.x, H); ctx.stroke();
  }

  function dibujarBarra(b) {
    const ni = Estado.datos.nudos.find(n => n.id === b.ni);
    const nj = Estado.datos.nudos.find(n => n.id === b.nj);
    if (!ni || !nj) return;
    const pi = aPantalla(ni.x, ni.y), pj = aPantalla(nj.x, nj.y);
    const sel = Estado.sesion.seleccion && Estado.sesion.seleccion.tipo === 'barra' && Estado.sesion.seleccion.id === b.id;
    const hov = Estado.sesion.hover && Estado.sesion.hover.tipo === 'barra' && Estado.sesion.hover.id === b.id;
    ctx.strokeStyle = sel ? COLOR.barraSel : (hov ? COLOR.barraHover : COLOR.barra);
    ctx.lineWidth = sel || hov ? 6 : 4;
    ctx.lineCap = 'round';
    ctx.beginPath(); ctx.moveTo(pi.x, pi.y); ctx.lineTo(pj.x, pj.y); ctx.stroke();

    if (Estado.herr.vista.etiquetas) {
      const mx = (pi.x + pj.x) / 2, my = (pi.y + pj.y) / 2;
      const L = Math.hypot(nj.x - ni.x, nj.y - ni.y);
      ctx.font = '600 11px system-ui';
      ctx.textAlign = 'center';
      const txt = `${b.id} · ${b.nombre_seccion || ''} · ${fmtN.format(L)} m`;
      const wtx = ctx.measureText(txt).width;
      ctx.fillStyle = 'rgba(255,255,255,.85)';
      ctx.fillRect(mx - wtx / 2 - 4, my - 16, wtx + 8, 14);
      ctx.fillStyle = sel ? COLOR.textoSel : COLOR.texto;
      ctx.fillText(txt, mx, my - 5);
    }
  }

  function dibujarNudo(n) {
    const p = aPantalla(n.x, n.y);
    const sel = Estado.sesion.seleccion && Estado.sesion.seleccion.tipo === 'nudo' && Estado.sesion.seleccion.id === n.id;
    const hov = Estado.sesion.hover && Estado.sesion.hover.tipo === 'nudo' && Estado.sesion.hover.id === n.id;
    const origen = Estado.sesion.barraEnCurso === n.id;
    ctx.beginPath();
    ctx.arc(p.x, p.y, origen ? 8 : 5.5, 0, Math.PI * 2);
    ctx.fillStyle = sel || origen ? COLOR.nudoSel : COLOR.nudo;
    ctx.fill();
    ctx.lineWidth = 2.5;
    ctx.strokeStyle = sel || origen ? COLOR.nudoSel : (hov ? COLOR.barraHover : COLOR.nudoBorde);
    ctx.stroke();
    if (Estado.herr.vista.etiquetas) {
      ctx.font = '700 10px system-ui';
      ctx.fillStyle = sel ? COLOR.textoSel : COLOR.texto;
      ctx.textAlign = 'left';
      ctx.fillText(n.id, p.x + 8, p.y - 8);
    }
  }

  function dibujarApoyo(a) {
    const n = Estado.datos.nudos.find(x => x.id === a.nudo);
    if (!n) return;
    const p = aPantalla(n.x, n.y);
    ctx.strokeStyle = COLOR.apoyo;
    ctx.fillStyle = 'rgba(51,65,85,.08)';
    ctx.lineWidth = 2;

    const dibTri = (dx, dy, ruedas) => {
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x - 11 + dx, p.y + 16 + dy);
      ctx.lineTo(p.x + 11 + dx, p.y + 16 + dy);
      ctx.closePath();
      ctx.fill(); ctx.stroke();
      if (ruedas) {
        ctx.beginPath();
        ctx.arc(p.x - 6 + dx, p.y + 20 + dy, 3.5, 0, Math.PI * 2);
        ctx.arc(p.x + 6 + dx, p.y + 20 + dy, 3.5, 0, Math.PI * 2);
        ctx.stroke();
      }
    };

    if (a.ux && a.uy && a.rz) {
      // empotramiento: rayitas diagonales
      dibTri(0, 0, false);
      ctx.beginPath();
      for (let i = -1; i <= 1; i++) {
        ctx.moveTo(p.x - 11 + i * 4, p.y + 19);
        ctx.lineTo(p.x - 4 + i * 4, p.y + 26);
      }
      ctx.stroke();
    } else if (a.ux && a.uy) {
      dibTri(0, 0, false);           // articulado
    } else if (a.uy && !a.ux) {
      dibTri(0, 0, true);            // deslizante horizontal (libre en X)
    } else if (a.ux && !a.uy) {
      // deslizante vertical: triángulo tumbado
      ctx.beginPath();
      ctx.moveTo(p.x, p.y);
      ctx.lineTo(p.x - 16, p.y - 11);
      ctx.lineTo(p.x - 16, p.y + 11);
      ctx.closePath();
      ctx.fill(); ctx.stroke();
    }
  }

  function flecha(x1, y1, x2, y2, color, grosor) {
    const ang = Math.atan2(y2 - y1, x2 - x1);
    const cab = 8;
    ctx.strokeStyle = color; ctx.fillStyle = color; ctx.lineWidth = grosor || 1.8;
    ctx.beginPath(); ctx.moveTo(x1, y1); ctx.lineTo(x2, y2); ctx.stroke();
    ctx.beginPath();
    ctx.moveTo(x2, y2);
    ctx.lineTo(x2 - cab * Math.cos(ang - 0.4), y2 - cab * Math.sin(ang - 0.4));
    ctx.lineTo(x2 - cab * Math.cos(ang + 0.4), y2 - cab * Math.sin(ang + 0.4));
    ctx.closePath(); ctx.fill();
  }

  function dibujarCargaPuntual(c) {
    const n = Estado.datos.nudos.find(x => x.id === c.nudo);
    if (!n) return;
    const p = aPantalla(n.x, n.y);
    const L = 34;
    if (c.Fy) flecha(p.x, p.y + Math.sign(c.Fy) * L, p.x, p.y, COLOR.puntual, 2.2);
    if (c.Fx) flecha(p.x - Math.sign(c.Fx) * L, p.y, p.x, p.y, COLOR.puntual, 2.2);
    if (c.Mz) {
      ctx.strokeStyle = COLOR.momento; ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(p.x, p.y, 14, -0.4, Math.PI * 1.4, c.Mz < 0);
      ctx.stroke();
      // cabeza
      const aa = c.Mz < 0 ? -0.4 : Math.PI * 1.4;
      const hx = p.x + 14 * Math.cos(aa), hy = p.y + 14 * Math.sin(aa);
      const tang = aa + (c.Mz < 0 ? -Math.PI / 2 : Math.PI / 2);
      flecha(hx - 6 * Math.cos(tang), hy - 6 * Math.sin(tang), hx, hy, COLOR.momento, 2);
    }
    if (Estado.herr.vista.etiquetas && (c.Fy || c.Fx || c.Mz)) {
      const partes = [];
      if (c.Fx) partes.push(fFuerza(c.Fx) + ' ←→');
      if (c.Fy) partes.push(fFuerza(c.Fy) + ' ↓↑');
      if (c.Mz) partes.push(fMomento(c.Mz) + ' ↺');
      ctx.font = '700 10px system-ui';
      ctx.fillStyle = COLOR.puntual;
      ctx.textAlign = 'center';
      ctx.fillText(partes.join('  '), p.x, p.y - 40);
    }
  }

  function dibujarCargaRepartida(b) {
    const ni = Estado.datos.nudos.find(n => n.id === b.ni);
    const nj = Estado.datos.nudos.find(n => n.id === b.nj);
    if (!ni || !nj) return;
    const pi = aPantalla(ni.x, ni.y), pj = aPantalla(nj.x, nj.y);
    const ang = Math.atan2(pj.y - pi.y, pj.x - pi.x);
    // carga gravitacional: siempre hacia abajo global; magnitud = |w|
    const w = Math.hypot(b.q_perp, b.q_axial);
    if (w < 1e-9) return;
    const h = Math.min(26, 8 + w / 80);
    const nx = Math.sin(ang), ny = -Math.cos(ang);   // normal en pantalla
    const nSeg = Math.max(4, Math.round(Math.hypot(pj.x - pi.x, pj.y - pi.y) / 46));
    ctx.strokeStyle = COLOR.dist; ctx.lineWidth = 2;
    // línea superior
    const ox = nx * h * 0, oy = 0;
    const tx = nx * h, ty = ny * h;
    ctx.beginPath();
    ctx.moveTo(pi.x + tx, pi.y + ty);
    ctx.lineTo(pj.x + tx, pj.y + ty);
    ctx.stroke();
    for (let i = 0; i <= nSeg; i++) {
      const t = i / nSeg;
      const x = pi.x + (pj.x - pi.x) * t + tx;
      const y = pi.y + (pj.y - pi.y) * t + ty;
      // flecha de la carga: hacia abajo global (gravedad)
      const lon = 12 + h * 0.4;
      flecha(x - 0 * lon, y - lon, x, y, COLOR.dist, 1.5);
    }
    if (Estado.herr.vista.etiquetas) {
      ctx.font = '700 10px system-ui';
      ctx.fillStyle = COLOR.dist;
      ctx.textAlign = 'center';
      const mx = (pi.x + pj.x) / 2 + tx, my = (pi.y + pj.y) / 2 + ty;
      ctx.fillText(w.toLocaleString('es-VE') + ' kg/m', mx, my - 6);
    }
  }

  function diagrama(tipo, color, lado) {
    const res = Estado.sesion.resultado;
    const esc = escalas();
    if (!res || !esc) return;
    const k = esc[tipo];

    ctx.save();
    for (const b of Estado.datos.barras) {
      const dg = res.diagramas[b.id];
      if (!dg) continue;
      const ni = Estado.datos.nudos.find(n => n.id === b.ni);
      const nj = Estado.datos.nudos.find(n => n.id === b.nj);
      const pi = aPantalla(ni.x, ni.y), pj = aPantalla(nj.x, nj.y);
      const ang = Math.atan2(pj.y - pi.y, pj.x - pi.x);
      const nx = Math.sin(ang), ny = -Math.cos(ang);       // normal (pantalla, y abajo)
      const xs = dg.x, vals = dg[tipo];
      const L = Math.hypot(pj.x - pi.x, pj.y - pi.y);

      ctx.beginPath();
      for (let i = 0; i < xs.length; i++) {
        const t = xs[i] / xs[xs.length - 1];
        const bx = pi.x + (pj.x - pi.x) * t;
        const by = pi.y + (pj.y - pi.y) * t;
        const off = lado * vals[i] * k * (vista.esc / 100);
        const x = bx + nx * off, y = by + ny * off;
        i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
      }
      // cerrar sobre el eje de la barra
      ctx.lineTo(pj.x, pj.y);
      ctx.lineTo(pi.x, pi.y);
      ctx.closePath();
      ctx.fillStyle = color + '33';   // transparencia
      ctx.fill();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.8;
      ctx.stroke();

      // valores en extremos y extremo de máximo
      ctx.font = '700 10px system-ui';
      ctx.fillStyle = color;
      ctx.textAlign = 'center';
      const etiqueta = (t, v) => {
        const bx = pi.x + (pj.x - pi.x) * t + nx * lado * v * k * (vista.esc / 100);
        const by = pi.y + (pj.y - pi.y) * t + ny * lado * v * k * (vista.esc / 100);
        const txt = tipo === 'M' ? fMomento(v) : fFuerza(v);
        ctx.fillText(txt, bx + nx * 14, by + ny * 14 + 3);
      };
      etiqueta(0, vals[0]);
      etiqueta(1, vals[vals.length - 1]);
      let iMax = 0;
      for (let i = 1; i < vals.length; i++) if (Math.abs(vals[i]) > Math.abs(vals[iMax])) iMax = i;
      if (iMax !== 0 && iMax !== vals.length - 1) etiqueta(xs[iMax] / xs[xs.length - 1], vals[iMax]);
    }
    ctx.restore();
  }

  function deformada(res) {
    const k = escalaDeformada(res);
    const pos = {};
    for (const n of res.nudos) {
      const n0 = Estado.datos.nudos.find(x => x.id === n.id);
      if (n0) pos[n.id] = aPantalla(n0.x + n.ux * k, n0.y + n.uy * k);
    }
    ctx.save();
    ctx.strokeStyle = COLOR.deformada;
    ctx.lineWidth = 2;
    ctx.setLineDash([6, 4]);
    for (const b of Estado.datos.barras) {
      const pi = pos[b.ni], pj = pos[b.nj];
      if (!pi || !pj) continue;
      ctx.beginPath(); ctx.moveTo(pi.x, pi.y); ctx.lineTo(pj.x, pj.y); ctx.stroke();
    }
    ctx.setLineDash([]);
    ctx.restore();
  }

  function gomaBarra() {
    const nid = Estado.sesion.barraEnCurso;
    const n0 = Estado.datos.nudos.find(x => x.id === nid);
    if (!n0 || Canvas2D._cursor == null) return;
    const p0 = aPantalla(n0.x, n0.y);
    const c = Canvas2D._cursor;
    ctx.save();
    ctx.strokeStyle = COLOR.barraSel;
    ctx.setLineDash([7, 5]);
    ctx.lineWidth = 3;
    ctx.beginPath(); ctx.moveTo(p0.x, p0.y); ctx.lineTo(c.x, c.y); ctx.stroke();
    ctx.setLineDash([]);
    const L = Math.hypot(c.x - p0.x, c.y - p0.y) / vista.esc;
    ctx.font = '700 11px system-ui';
    ctx.fillStyle = COLOR.textoSel;
    ctx.textAlign = 'center';
    ctx.fillText(fmtN.format(L) + ' m', (p0.x + c.x) / 2, (p0.y + c.y) / 2 - 8);
    ctx.restore();
  }

  /* ================= INTERACCIÓN ================= */
  let arrastre = null;   // {tipo:'pan'|'nudo', ...}

  function onPointerDown(e) {
    const r = cv.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    const modo = Estado.herr.modo;

    if (modo === 'seleccionar' || e.button === 1 || e.button === 2) {
      const n = nudoEn(px, py);
      if (n && e.button !== 1 && e.button !== 2) {
        Estado.sesion.seleccion = { tipo: 'nudo', id: n.id };
        arrastre = { tipo: 'nudo', id: n.id, movido: false };
        Estado.notificar({ seleccion: true });
        return;
      }
      const b = barraEn(px, py);
      if (b && e.button !== 1 && e.button !== 2) {
        Estado.sesion.seleccion = { tipo: 'barra', id: b.id };
        Estado.notificar({ seleccion: true });
        return;
      }
      arrastre = { tipo: 'pan', px, py, ox: vista.ox, oy: vista.oy };
      return;
    }

    if (modo === 'nudo') {
      const m = aMundo(px, py);
      const nu = Estado.nudo(snap(m.x), snap(m.y));
      Estado.sesion.seleccion = { tipo: 'nudo', id: nu.id };
      return;
    }

    if (modo === 'barra') {
      let n = nudoEn(px, py);
      if (!n) {
        const m = aMundo(px, py);
        n = Estado.nudo(snap(m.x), snap(m.y));   // encadenar creando nudos
      }
      if (!Estado.sesion.barraEnCurso) {
        Estado.sesion.barraEnCurso = n.id;
      } else if (Estado.sesion.barraEnCurso !== n.id) {
        Estado.barra({ id: Estado.sesion.barraEnCurso }, n);
        Estado.sesion.barraEnCurso = n.id;        // seguir encadenando
      }
      Estado.notificar({});
      return;
    }

    if (modo === 'apoyo') {
      const n = nudoEn(px, py);
      if (n) Estado.asignarApoyo(n.id);
      return;
    }

    if (modo === 'puntual') {
      const n = nudoEn(px, py);
      if (n) Estado.aplicarCargaPuntual(n.id);
      return;
    }

    if (modo === 'repartida') {
      const b = barraEn(px, py, 14);
      if (b) Estado.aplicarCargaRepartida(b.id);
      return;
    }
  }

  function onPointerMove(e) {
    const r = cv.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    Canvas2D._cursor = { x: px, y: py };
    Canvas2D._cursorMundo = aMundo(px, py);

    if (arrastre) {
      if (arrastre.tipo === 'pan') {
        vista.ox = arrastre.ox + (px - arrastre.px);
        vista.oy = arrastre.oy + (py - arrastre.py);
      } else if (arrastre.tipo === 'nudo') {
        const m = aMundo(px, py);
        const n = Estado.datos.nudos.find(x => x.id === arrastre.id);
        if (n) { n.x = snap(m.x); n.y = snap(m.y); arrastre.movido = true; }
      }
      dibujar();
      return;
    }

    const modo = Estado.herr.modo;
    if (modo === 'seleccionar' || modo === 'apoyo' || modo === 'puntual') {
      const n = nudoEn(px, py);
      Estado.sesion.hover = n ? { tipo: 'nudo', id: n.id } : (barraEn(px, py) ? { tipo: 'barra', id: barraEn(px, py).id } : null);
    } else if (modo === 'repartida') {
      const b = barraEn(px, py, 14);
      Estado.sesion.hover = b ? { tipo: 'barra', id: b.id } : null;
    } else {
      Estado.sesion.hover = null;
    }
    dibujar();
    if (Canvas2D.onStatus) Canvas2D.onStatus();
  }

  function onPointerUp() {
    if (arrastre && arrastre.tipo === 'nudo' && arrastre.movido) {
      Estado.notificar({ nudos: true });   // recalcula tras mover
    }
    arrastre = null;
  }

  function onWheel(e) {
    e.preventDefault();
    const r = cv.getBoundingClientRect();
    const px = e.clientX - r.left, py = e.clientY - r.top;
    const antes = aMundo(px, py);
    const f = e.deltaY < 0 ? 1.15 : 1 / 1.15;
    vista.esc = Math.min(600, Math.max(6, vista.esc * f));
    const despues = aMundo(px, py);
    vista.ox += (despues.x - antes.x) * vista.esc;
    vista.oy -= (despues.y - antes.y) * vista.esc;
    dibujar();
    if (Canvas2D.onStatus) Canvas2D.onStatus();
  }

  function onContextMenu(e) {
    e.preventDefault();
    if (Estado.herr.modo === 'barra') {
      Estado.sesion.barraEnCurso = null;
      dibujar();
    }
  }

  function onKeyDown(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
    if (e.key === 'Delete' || e.key === 'Backspace') {
      Estado.eliminar(Estado.sesion.seleccion);
    } else if (e.key === 'Escape') {
      Estado.sesion.barraEnCurso = null;
      Estado.sesion.seleccion = null;
      Estado.notificar({ seleccion: true });
      dibujar();
    }
  }

  /* ---------------- encuadre ---------------- */
  function ajustar() {
    const ns = Estado.datos.nudos;
    if (!ns.length) { vista.esc = 60; vista.ox = W * 0.2; vista.oy = H * 0.8; dibujar(); return; }
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const n of ns) {
      x0 = Math.min(x0, n.x); y0 = Math.min(y0, n.y);
      x1 = Math.max(x1, n.x); y1 = Math.max(y1, n.y);
    }
    const dx = Math.max(x1 - x0, 2), dy = Math.max(y1 - y0, 2);
    const margen = 90;
    vista.esc = Math.min((W - 2 * margen) / dx, (H - 2 * margen) / dy);
    vista.esc = Math.min(300, Math.max(8, vista.esc));
    const cx = (x0 + x1) / 2, cy = (y0 + y1) / 2;
    const c = aPantalla(cx, cy);
    vista.ox += W / 2 - c.x;
    vista.oy += H / 2 - c.y;
    dibujar();
  }

  /* ---------------- init ---------------- */
  function init() {
    cv = document.getElementById('lienzo');
    ctx = cv.getContext('2d');
    const wrap = document.getElementById('lienzo-wrap');

    function resize() {
      dpr = window.devicePixelRatio || 1;
      W = wrap.clientWidth; H = wrap.clientHeight;
      cv.width = W * dpr; cv.height = H * dpr;
      cv.style.width = W + 'px'; cv.style.height = H + 'px';
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      dibujar();
    }
    new ResizeObserver(resize).observe(wrap);
    resize();

    cv.addEventListener('pointerdown', onPointerDown);
    cv.addEventListener('pointermove', onPointerMove);
    window.addEventListener('pointerup', onPointerUp);
    cv.addEventListener('wheel', onWheel, { passive: false });
    cv.addEventListener('contextmenu', onContextMenu);
    window.addEventListener('keydown', onKeyDown);

    vista.ox = W * 0.15; vista.oy = H * 0.75;
  }

  return {
    init, dibujar, ajustar, aMundo,
    escala: () => vista.esc,
    _cursor: null, _cursorMundo: null, onStatus: null
  };
})();
