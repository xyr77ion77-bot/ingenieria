/* ================================================================
   acero.js — Sección ⑦ «Acero — COVENIN 1618-1998» (Fase 4)
   ------------------------------------------------------------------
   · Verifica las barras del pórtico activo: vigas (flexión + corte +
     flecha) y columnas (compresión + interacción P-M).
   · POST /api/diseno-acero {modelo, acciones, params}.
   · Optimizador: el perfil más liviano de la BD que pasa TODO.
   · Flechas con el caso de servicio SERV = 1,0·CP + 1,0·CV
     (límites L/300 normal · L/360 exigente, formulario del Ing. Laine).
   · Registra la memoria de diseño (sección 5) en Memoria.
   · Fuera de la página de cálculo no hace nada (faltan los ids).
   ================================================================ */

const AceroApp = (function () {
  'use strict';

  const $ = id => document.getElementById(id);
  const fmt = new Intl.NumberFormat('es-VE', { maximumFractionDigits: 2 });
  let ultimo = null;   // última respuesta de /api/diseno-acero

  function mostrarError(msg) {
    const caja = $('acero-caja-error');
    if (!caja) return;
    caja.textContent = msg;
    caja.classList.remove('oculto');
  }

  function limpiarError() {
    const caja = $('acero-caja-error');
    if (caja) { caja.textContent = ''; caja.classList.add('oculto'); }
  }

  function estado(msg) {
    const el = $('acero-estado');
    if (el) el.textContent = msg || '';
  }

  /* ---------- catálogo (datalists) ---------- */

  async function cargarCatalogo() {
    const dlV = $('dl-perfiles-viga');
    const dlC = $('dl-perfiles-col');
    if (!dlV || !dlC) return;
    try {
      const r = await fetch('/api/perfiles');
      const j = await r.json();
      if (!j.ok || !j.perfiles) return;
      const fragV = document.createDocumentFragment();
      const fragC = document.createDocumentFragment();
      j.perfiles.forEach(p => {
        const o1 = document.createElement('option');
        o1.value = p.nombre;
        o1.label = p.serie + ' · ' + fmt.format(p.G) + ' kg/m';
        fragV.appendChild(o1);
        const o2 = document.createElement('option');
        o2.value = p.nombre;
        o2.label = p.serie + ' · ' + fmt.format(p.G) + ' kg/m';
        fragC.appendChild(o2);
      });
      dlV.appendChild(fragV);
      dlC.appendChild(fragC);
    } catch (e) { /* sin catálogo: los inputs siguen manuales */ }
  }

  /* ---------- llamada al motor ---------- */

  function params(optimizar) {
    const lb = $('ac-lb').value.trim();
    return {
      fy: parseFloat($('ac-fy').value) || 2500,
      k_col: parseFloat($('ac-kcol').value) || 1.5,
      cb: parseFloat($('ac-cb').value) || 1.0,
      lb_viga_m: lb ? parseFloat(lb) : null,
      limite_flecha: parseInt($('ac-lim').value, 10) || 300,
      perfil_viga: $('ac-perfil-viga').value.trim(),
      perfil_columna: $('ac-perfil-col').value.trim(),
      optimizar: !!optimizar,
    };
  }

  async function ejecutar(optimizar) {
    /* AccionesApp es const de script clásico: vive en el ámbito global
       léxico, NO como propiedad de window → probar con typeof */
    const d = (typeof AccionesApp !== 'undefined' && AccionesApp.datosAPI)
      ? AccionesApp.datosAPI() : null;
    if (!d || !d.modelo) {
      mostrarError('No hay modelo en el proyecto. Ve a «Modelador + Acciones», ' +
                   'genera el pórtico con ⚡ y vuelve aquí.');
      return;
    }
    limpiarError();
    estado(optimizar ? '⚡ Optimizando (buscando el perfil más liviano que pasa)…'
                     : '🔍 Verificando sección asignada…');
    const t0 = performance.now();
    try {
      const r = await fetch('/api/diseno-acero', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modelo: d.modelo, acciones: d.acciones,
                               params: params(optimizar) })
      });
      const j = await r.json();
      const ms = Math.round(performance.now() - t0);
      if (!j.ok) { mostrarError(j.error || 'Error desconocido'); estado(''); return; }
      ultimo = j;
      render(j, optimizar, ms);
      if (window.Memoria) Memoria.registrar(j);
    } catch (e) {
      mostrarError('No se pudo contactar el motor: ' + e.message);
      estado('');
    }
  }

  /* ---------- render ---------- */

  function badge(nombre, ratio) {
    const v = (typeof ratio === 'number') ? ratio : 0;
    let cls = 'rat-ok';
    if (v > 1.0) cls = 'rat-mal';
    else if (v > 0.85) cls = 'rat-casi';
    return '<span class="rat ' + cls + '" title="' + nombre + '">' +
           nombre + ' ' + fmt.format(v) + '</span>';
  }

  function ordenEstados(ratios) {
    /* flexión · corte · flecha (viga) / interacción · esbeltez (columna);
       «interacción (18-1a)» también ordena como interacción */
    const orden = ['flexión', 'corte', 'flecha', 'interacción', 'esbeltez'];
    function pos(k) {
      const s = String(k).toLowerCase();
      for (var i = 0; i < orden.length; i++) {
        if (s.indexOf(orden[i]) === 0) return i;
      }
      return 99;
    }
    return Object.keys(ratios || {}).sort(function (a, b) {
      return pos(a) - pos(b);
    });
  }

  function render(j, optimizar, ms) {
    const tb = document.querySelector('#tabla-acero tbody');
    const wrap = $('acero-tabla-wrap');
    if (!tb || !wrap) return;
    tb.innerHTML = '';
    j.filas.forEach(f => {
      const tr = document.createElement('tr');
      const per = (optimizar && f.optimo && f.optimo !== f.perfil)
        ? f.perfil + ' → <b>' + f.optimo + '</b>' : f.perfil;
      const estados = ordenEstados(f.ratios)
        .map(k => badge(k, f.ratios[k])).join(' ');
      tr.innerHTML =
        '<td>' + f.barra + '</td>' +
        '<td>' + (f.tipo === 'viga' ? '〈 viga' : '⏐ col') + '</td>' +
        '<td>' + per + '</td>' +
        '<td class="num">' + f.Pu + '</td>' +
        '<td class="num">' + f.Vu + '</td>' +
        '<td class="num">' + f.Mu + '</td>' +
        '<td class="num">' + f.L_m + '</td>' +
        '<td>' + estados + '</td>' +
        '<td class="num"><b>' + fmt.format(f.gobierna) + '</b></td>' +
        '<td class="mini">' + (f.combo || '') + '</td>' +
        '<td class="' + (f.pasa ? 'verifica-ok' : 'verifica-mal') + '">' +
          (f.pasa ? '✓' : '✗') + '</td>';
      tb.appendChild(tr);
    });
    wrap.classList.remove('oculto');

    /* chips del optimizador + θ P-Δ */
    const chip = $('acero-optimo');
    if (chip) {
      const o = j.optimo || {};
      let html = '';
      if (o.viga || o.columna) {
        html += '<span class="chip-optimo">⚡ óptimo viga: <b>' + (o.viga || '—') +
                '</b></span> <span class="chip-optimo">⚡ óptimo columna: <b>' +
                (o.columna || '—') + '</b></span>';
        if (!optimizar && (o.viga || o.columna)) {
          html += ' <button type="button" class="suave" id="btn-aplicar-optimo">' +
                  '⤵ aplicar a los perfiles asignados</button>';
        }
      }
      const th = j.thetas || {};
      const ks = Object.keys(th);
      if (ks.length) {
        html += '<div class="mini">θ P-Δ por nivel: ' + ks.map(k =>
          'h=' + (isNaN(parseFloat(k)) ? k : fmt.format(parseFloat(k))) + ' m → ' +
          fmt.format(th[k]) +
          (th[k] > 0.25 ? ' ⚠ (>0,25)' : '')).join(' · ') +
          '. Amplificación B1 = Cm/(1−N/Ne), Mu amplificado = Mu/(1−θ).</div>';
      }
      chip.innerHTML = html;
      chip.classList.remove('oculto');
      const btn = $('btn-aplicar-optimo');
      if (btn) btn.addEventListener('click', function () {
        if (o.viga) $('ac-perfil-viga').value = o.viga;
        if (o.columna) $('ac-perfil-col').value = o.columna;
        estado('Perfiles óptimos copiados a los asignados. Pulsa «Verificar» para confirmarlos.');
      });
    }
    estado((j.avisos && j.avisos.length
      ? '⚠ ' + j.avisos.join(' · ') + ' — ' : '')
      + 'diseñado en ' + ms + ' ms · γ = ' + j.gamma);
  }

  /* ---------- init ---------- */

  function init() {
    if (!$('sec-acero')) return;      // no es la página de cálculo
    $('btn-verificar-acero').addEventListener('click', () => ejecutar(false));
    $('btn-optimizar-acero').addEventListener('click', () => ejecutar(true));
    cargarCatalogo();
  }

  document.addEventListener('DOMContentLoaded', function () {
    try { init(); } catch (err) {
      mostrarError('⚠ El módulo de Acero no pudo iniciar: ' + err.message);
    }
  });

  return { ejecutar, init };
})();
