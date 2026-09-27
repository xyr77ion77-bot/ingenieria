/* ================================================================
   acciones.js — Pestaña «Acciones y Combinaciones» (Fase 2)
   ------------------------------------------------------------------
   · Lee el modelo del proyecto (localStorage compartido con la
     pestaña Análisis 2D).
   · Administra CP/CV por barra y por nudo + parámetros del sismo.
   · POST /api/combinaciones → KPIs, espectro Ad(T), Fi por nivel,
     combinaciones §8.3.2 y envolvente.
   ================================================================ */

const AccionesApp = (function () {
  'use strict';

  const $ = id => document.getElementById(id);
  const fmt = new Intl.NumberFormat('es-VE', { maximumFractionDigits: 2 });
  const CLAVE_MODELO = 'analisis2d.autosave';
  const CLAVE_ACC = 'analisis2d.acciones';
  const CLAVE_MODELADOR = 'modelador_v1';      /* proyecto único compartido */
  const CLAVE_CARGAS_API = '/api/cargas2002';
  let TAB = null;   /* tablas COVENIN 2002-88 servidas por el motor */

  let modelo = null;   // dict del modelo (JSON del motor)
  let acc = null;      // dict de acciones
  let res = null;      // última respuesta de /api/combinaciones

  /* ---------------- estado por defecto ---------------- */
  function accPorDefecto() {
    return {
      barra_cp: {}, barra_cv: {}, nodo_cp: {}, nodo_cv: {},
      cargas2002: { tipo: '5', por_nivel: {} },
      sismo: {
        A0: 0.21, A1: 0.18, TL: 3.9, grupo: 'B2', nd: 'ND3',
        sitio: 'CD', topo: 'leve', H: 0, rho: 1.0, FI: 1.0,
        ct: 0.08, fraccion_cv: 0.25, fraccion_portico: 100,
        incluir_sismo: true, incluir_sv: true,
        sobrerresistencia: false, rho_redundancia: 1.0, gamma_manual: null
      }
    };
  }

  function guardarLocal() {
    try {
      localStorage.setItem(CLAVE_ACC, JSON.stringify(acc));
    } catch (e) { /* noop */ }
  }

  function cargarLocal() {
    try {
      const s = localStorage.getItem(CLAVE_ACC);
      if (s) { acc = { ...accPorDefecto(), ...JSON.parse(s) }; return true; }
    } catch (e) { /* noop */ }
    acc = accPorDefecto();
    return false;
  }

  function cargarModeloProyecto() {
    try {
      const s = localStorage.getItem(CLAVE_MODELO);
      if (s) { modelo = JSON.parse(s); return true; }
    } catch (e) { /* noop */ }
    return false;
  }

  /* ================= construcción de tablas ================= */
  function longBarra(b) {
    const ni = modelo.nudos.find(n => n.id === b.ni);
    const nj = modelo.nudos.find(n => n.id === b.nj);
    if (!ni || !nj) return 0;
    return Math.hypot(nj.x - ni.x, nj.y - ni.y);
  }

  function renderTablaBarras() {
    const div = $('tabla-barras-cargas');
    if (!modelo || !modelo.barras.length) {
      div.innerHTML = '<div class="mini">El proyecto no tiene barras. Crea el modelo en la pestaña Análisis 2D.</div>';
      return;
    }
    let html = '<table><thead><tr><th>Barra</th><th>L (m)</th><th>CP</th><th>CV</th></tr></thead><tbody>';
    for (const b of modelo.barras) {
      html += `<tr><td>${b.id}${b.peso_propio ? ' <span title="con peso propio">⚖</span>' : ''}</td>
        <td class="num">${fmt.format(longBarra(b))}</td>
        <td><input type="number" step="50" class="in-cp" data-id="${b.id}" value="${acc.barra_cp[b.id] ?? 0}"></td>
        <td><input type="number" step="50" class="in-cv" data-id="${b.id}" value="${acc.barra_cv[b.id] ?? 0}"></td></tr>`;
    }
    div.innerHTML = html + '</tbody></table>';
    div.querySelectorAll('.in-cp').forEach(inp =>
      inp.addEventListener('input', () => { acc.barra_cp[inp.dataset.id] = +inp.value || 0; guardarLocal(); }));
    div.querySelectorAll('.in-cv').forEach(inp =>
      inp.addEventListener('input', () => { acc.barra_cv[inp.dataset.id] = +inp.value || 0; guardarLocal(); }));
  }

  function renderTablaNudos() {
    const div = $('tabla-nudos-cargas');
    if (!modelo || !modelo.nudos.length) { div.innerHTML = ''; return; }
    let html = '<table><thead><tr><th>Nudo</th><th>Fy CP (kg)</th><th>Fy CV (kg)</th></tr></thead><tbody>';
    for (const n of modelo.nudos) {
      const cp = acc.nodo_cp[n.id]?.Fy ?? 0;
      const cv = acc.nodo_cv[n.id]?.Fy ?? 0;
      html += `<tr><td>${n.id}</td>
        <td><input type="number" step="100" class="in-ncp" data-id="${n.id}" value="${cp}"></td>
        <td><input type="number" step="100" class="in-ncv" data-id="${n.id}" value="${cv}"></td></tr>`;
    }
    div.innerHTML = html + '</tbody></table>';
    div.querySelectorAll('.in-ncp').forEach(inp =>
      inp.addEventListener('input', () => {
        acc.nodo_cp[inp.dataset.id] = { Fx: 0, Fy: +inp.value || 0, Mz: 0 };
        guardarLocal();
      }));
    div.querySelectorAll('.in-ncv').forEach(inp =>
      inp.addEventListener('input', () => {
        acc.nodo_cv[inp.dataset.id] = { Fx: 0, Fy: +inp.value || 0, Mz: 0 };
        guardarLocal();
      }));
  }

  /* ============ cargas por nivel — COVENIN-MINDUR 2002-88 ============ */

  function proyectoModelador() {
    try {
      const s = localStorage.getItem(CLAVE_MODELADOR);
      if (s) return JSON.parse(s);
    } catch (e) { /* noop */ }
    return null;
  }

  function nivelesModelador() {
    const p = proyectoModelador();
    if (!p || !p.geometria || !p.geometria.niveles) return [];
    let y = 0;
    return p.geometria.niveles.map(n => {
      y += +n.h_piso || 0;
      return { nombre: n.nombre, es_techo: !!n.es_techo,
               pp_techo: +n.pp_techo || 50, pendiente: +n.pendiente || 0,
               y };
    });
  }

  function cfgNivel(nombre) {
    acc.cargas2002.por_nivel = acc.cargas2002.por_nivel || {};
    if (!acc.cargas2002.por_nivel[nombre]) {
      acc.cargas2002.por_nivel[nombre] =
        { ambiente: 'B', ancho: 3.0, losa_cm: 12, acabado: 80, tabiq: 150,
          cobertura: 'metalico_liviano' };
    }
    return acc.cargas2002.por_nivel[nombre];
  }

  function cpCvNivel(nivel, cfg) {
    /* → {cp, cv, fuente_cv} en kg/m² (norma: cap. 4 y 5) */
    if (nivel.es_techo) {
      const cvTecho = {
        metalico_liviano: TAB.techo.metalico_liviano,
        p_le_15: TAB.techo.p_le_15,
        p_gt_15: TAB.techo.p_gt_15,
      };
      if (cfg.cobertura === 'azotea_uso') {
        const tipo = TAB.tipos[acc.cargas2002.tipo];
        const v = tipo && tipo.valores[cfg.ambiente];
        const cv = Math.max(v != null ? v : 0, TAB.techo.azotea_min_con_uso);
        return { cp: nivel.pp_techo, cv,
                 fuente_cv: 'azotea de uso (≥' + TAB.techo.azotea_min_con_uso + ')' };
      }
      return { cp: nivel.pp_techo, cv: cvTecho[cfg.cobertura],
               fuente_cv: '§5.2.4.2' };
    }
    const tipo = TAB.tipos[acc.cargas2002.tipo];
    const cv = tipo && tipo.valores[cfg.ambiente] != null
      ? tipo.valores[cfg.ambiente] : 0;
    const cp = cfg.losa_cm / 100 * TAB.pesos.concreto_armado
             + (+cfg.acabado || 0) + (+cfg.tabiq || 0);
    return { cp, cv, fuente_cv: 'Tabla 5.1' };
  }

  function renderCargasNivel() {
    const div = $('tabla-cargas-nivel');
    const banner = $('banner-modelador');
    const niveles = nivelesModelador();
    if (!TAB) { div.innerHTML = '<div class="mini">…</div>'; return; }
    if (!niveles.length) {
      banner.classList.remove('oculto');
      banner.innerHTML = '⚠ No hay proyecto del <b>Modelador</b>: ábrelo, ' +
        'define la estructura y vuelve (proyecto único del flujo).';
      div.innerHTML = '';
      return;
    }
    banner.classList.add('oculto');
    const tipo = TAB.tipos[acc.cargas2002.tipo] || Object.values(TAB.tipos)[0];
    let html = '<table><thead><tr><th>Nivel</th><th>amb.</th>' +
      '<th>CV (kg/m²)</th><th>CP (kg/m²)</th><th>ancho trib. (m)</th>' +
      '<th>q = (CP+CV)·ancho (kg/m)</th></tr></thead><tbody>';
    niveles.forEach(n => {
      const c = cfgNivel(n.nombre);
      const { cp, cv } = cpCvNivel(n, c);
      const q = (cp + cv) * (+c.ancho || 0);
      const ambSel = n.es_techo
        ? `<select class="in-cob" data-n="${n.nombre}" ${c.cobertura === 'azotea_uso' ? '' : 'title="CV fija por §5.2.4.2"'}>
             ${[['metalico_liviano', 'techo met. liviano (40)'],
                ['p_le_15', 'pp≥50 · p≤15% (100)'],
                ['p_gt_15', 'pp≥50 · p>15% (50)'],
                ['azotea_uso', 'azotea de uso (≥100)']]
               .map(([k, t]) => `<option value="${k}" ${c.cobertura === k ? 'selected' : ''}>${t}</option>`).join('')}
           </select>`
        : `<select class="in-amb" data-n="${n.nombre}">
             ${Object.entries(TAB.ambientes)
               .filter(([k]) => k !== 'O')
               .map(([k, t]) => `<option value="${k}" ${c.ambiente === k ? 'selected' : ''}
                   title="${t}">${k}</option>`).join('')}
           </select>`;
      html += `<tr>
        <td>${n.nombre}${n.es_techo ? ' <span class="badge-techo" title="CV por §5.2.4">techo</span>' : ''}</td>
        <td>${ambSel}</td>
        <td class="num">${fmt.format(cv)}</td>
        <td class="num">${fmt.format(cp)}</td>
        <td><input type="number" step="0.5" min="0" class="in-ancho"
                   data-n="${n.nombre}" value="${c.ancho}" style="width:64px"></td>
        <td class="num"><b>${fmt.format(q)}</b></td></tr>`;
    });
    div.innerHTML = html + '</tbody></table>';

    div.querySelectorAll('.in-amb').forEach(sel =>
      sel.addEventListener('change', () => {
        cfgNivel(sel.dataset.n).ambiente = sel.value;
        guardarLocal(); renderCargasNivel();
      }));
    div.querySelectorAll('.in-cob').forEach(sel =>
      sel.addEventListener('change', () => {
        cfgNivel(sel.dataset.n).cobertura = sel.value;
        guardarLocal(); renderCargasNivel();
      }));
    div.querySelectorAll('.in-ancho').forEach(inp =>
      inp.addEventListener('input', () => {
        cfgNivel(inp.dataset.n).ancho = +inp.value || 0;
        guardarLocal();
        /* refresca solo la columna q sin perder el foco */
        const tr = inp.closest('tr');
        const n = niveles.find(x => x.nombre === inp.dataset.n);
        const { cp, cv } = cpCvNivel(n, cfgNivel(n.nombre));
        tr.children[5].innerHTML = '<b>' + fmt.format((cp + cv) * (+inp.value || 0)) + '</b>';
      }));
  }

  function aplicarNivelesABarras() {
    const niveles = nivelesModelador();
    if (!modelo || !modelo.barras.length || !niveles.length) {
      alert('No hay barras en el proyecto (genera el modelo 2D desde el Modelador).');
      return;
    }
    let aplicadas = 0;
    const detalle = [];
    for (const b of modelo.barras) {
      const ni = modelo.nudos.find(n => n.id === b.ni);
      const nj = modelo.nudos.find(n => n.id === b.nj);
      if (!ni || !nj) continue;
      const yViga = Math.min(ni.y, nj.y) + 1e-9;
      const nivel = niveles.find(n => Math.abs(n.y - yViga) < 0.05);
      if (!nivel) continue;
      const { cp, cv } = cpCvNivel(nivel, cfgNivel(nivel.nombre));
      const ancho = +cfgNivel(nivel.nombre).ancho || 0;
      acc.barra_cp[b.id] = Math.round(cp * ancho * 100) / 100;
      acc.barra_cv[b.id] = Math.round(cv * ancho * 100) / 100;
      aplicadas++;
    }
    niveles.forEach(n => {
      const { cp, cv } = cpCvNivel(n, cfgNivel(n.nombre));
      const a = +cfgNivel(n.nombre).ancho || 0;
      detalle.push(n.nombre + ': CP ' + Math.round(cp * a) +
                   ' · CV ' + Math.round(cv * a) + ' kg/m');
    });
    guardarLocal();
    renderTablaBarras();
    alert('Barras actualizadas: ' + aplicadas + '\n\n' + detalle.join('\n'));
  }

  async function cargarTablas2002() {
    try {
      const r = await fetch(CLAVE_CARGAS_API);
      TAB = await r.json();
      const sel = $('sel-tipo-2002');
      sel.innerHTML = TAB.opciones_tipo
        .map(([k, t]) => `<option value="${k}" ${k === acc.cargas2002.tipo ? 'selected' : ''}>${t}</option>`)
        .join('');
      sel.addEventListener('change', () => {
        acc.cargas2002.tipo = sel.value;
        guardarLocal(); renderCargasNivel();
      });
      renderCargasNivel();
    } catch (e) {
      $('tabla-cargas-nivel').innerHTML =
        '<div class="mini">No se pudieron cargar las tablas 2002-88 (¿backend caído?).</div>';
    }
  }

  /* ================= formulario sismo ================= */
  function leerFormulario() {
    const s = acc.sismo;
    s.A0 = +$('s-A0').value || 0;
    s.A1 = +$('s-A1').value || 0;
    s.TL = +$('s-TL').value || 0;
    s.grupo = $('s-grupo').value;
    s.nd = $('s-nd').value;
    s.sitio = $('s-sitio').value;
    s.topo = $('s-topo').value;
    s.H = +$('s-H').value || 0;
    s.rho = +$('s-rho').value || 1;
    s.FI = +$('s-FI').value || 1;
    s.ct = +$('s-ct').value || 0.08;
    s.fraccion_cv = +$('s-fracc').value || 0.25;
    s.fraccion_portico = +$('s-fracp').value || 100;
    s.incluir_sismo = $('o-sismo').checked;
    s.incluir_sv = $('o-sv').checked;
    s.sobrerresistencia = $('o-omega').checked;
    s.rho_redundancia = +$('o-rhoR').value || 1;
    s.gamma_manual = $('o-gamma').value === 'auto' ? null : +$('o-gamma').value;
    // API espera fraccion_portico en fracción (0–1)
    acc.sismo = s;
    guardarLocal();
  }

  function escribirFormulario() {
    const s = acc.sismo;
    $('s-A0').value = s.A0; $('s-A1').value = s.A1; $('s-TL').value = s.TL;
    $('s-grupo').value = s.grupo; $('s-nd').value = s.nd;
    $('s-sitio').value = s.sitio; $('s-topo').value = s.topo;
    $('s-H').value = s.H; $('s-rho').value = s.rho; $('s-FI').value = s.FI;
    $('s-ct').value = s.ct; $('s-fracc').value = String(s.fraccion_cv);
    $('s-fracp').value = s.fraccion_portico;
    $('o-sismo').checked = !!s.incluir_sismo;
    $('o-sv').checked = !!s.incluir_sv;
    $('o-omega').checked = !!s.sobrerresistencia;
    $('o-rhoR').value = s.rho_redundancia ?? 1;
    $('o-gamma').value = s.gamma_manual == null ? 'auto' : String(s.gamma_manual);
  }

  /* ================= cálculo ================= */
  async function calcular() {
    if (!modelo) {
      mostrarError('No hay modelo en el proyecto. Ve a la pestaña Análisis 2D, crea o carga un ejemplo y vuelve.');
      return;
    }
    leerFormulario();
    // normalizar % V0 del pórtico → fracción (0–1) para la API
    const fp = acc.sismo.fraccion_portico;
    const accAPI = { ...acc, sismo: { ...acc.sismo,
      fraccion_portico: fp > 1 ? fp / 100 : fp } };
    const t0 = performance.now();
    try {
      const r = await fetch('/api/combinaciones', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ modelo, acciones: accAPI })
      });
      const j = await r.json();
      const ms = Math.round(performance.now() - t0);
      if (!j.ok) { mostrarError(j.error || 'Error desconocido'); return; }
      res = j;
      $('caja-error').classList.add('oculto');
      $('lbl-tiempo').textContent = `resuelto en ${ms} ms · γ = ${j.gamma} · CSV = ${fmt.format(j.csv)}`;
      renderKPIs(j);
      dibujarEspectro(j);
      renderNiveles(j);
      renderCombos(j);
      renderEnvolvente(j);
    } catch (e) {
      mostrarError('Sin conexión con el motor: verifica que el servidor esté corriendo.');
      console.error(e);
    }
  }

  function mostrarError(msg) {
    $('caja-error').classList.remove('oculto');
    $('texto-error').textContent = msg;
  }

  /* ================= render de resultados ================= */
  function renderKPIs(j) {
    const s = j.sismo;
    $('k-AA').textContent = fmt.format(s.AA);
    $('k-TC').textContent = fmt.format(s.TC);
    $('k-Ta').textContent = fmt.format(s.Ta);
    $('k-mu').textContent = fmt.format(s.mu);
    $('k-C').textContent = fmt.format(s.C);
    $('k-Cmin').textContent = fmt.format(s.Cmin);
    $('k-V0d').textContent = fmt.format(s.V0d);
    $('k-Ft').textContent = fmt.format(s.Ft);
    $('k-CSV').textContent = j.csv ? fmt.format(j.csv) : '—';
    $('k-gamma').textContent = String(j.gamma);
  }

  function dibujarEspectro(j) {
    const cv = $('espectro');
    const ctx = cv.getContext('2d');
    const W = cv.clientWidth, H = 240;
    cv.width = W * (window.devicePixelRatio || 1);
    cv.height = H * (window.devicePixelRatio || 1);
    ctx.setTransform(window.devicePixelRatio || 1, 0, 0, window.devicePixelRatio || 1, 0, 0);
    const pts = j.espectro;
    if (!pts || !pts.length) return;
    const Tmax = pts[pts.length - 1].T;
    const Amax = Math.max(...pts.map(p => p.Ad));
    const mx = 46, my = 24;
    ctx.clearRect(0, 0, W, H);

    // rejilla y ejes
    ctx.strokeStyle = '#e2e8f0';
    ctx.fillStyle = '#64748b';
    ctx.font = '10px system-ui';
    for (let i = 0; i <= 5; i++) {
      const x = mx + (W - mx - 10) * i / 5;
      ctx.beginPath(); ctx.moveTo(x, my); ctx.lineTo(x, H - my); ctx.stroke();
      ctx.fillText((Tmax * i / 5).toFixed(2) + ' s', x - 12, H - 8);
    }
    for (let i = 0; i <= 4; i++) {
      const y = my + (H - 2 * my) * i / 4;
      ctx.beginPath(); ctx.moveTo(mx, y); ctx.lineTo(W - 10, y); ctx.stroke();
      ctx.fillText((Amax * (4 - i) / 4).toFixed(3), 4, y + 3);
    }

    // curva
    ctx.strokeStyle = '#dc2626';
    ctx.lineWidth = 2;
    ctx.beginPath();
    pts.forEach((p, i) => {
      const x = mx + (W - mx - 10) * p.T / Tmax;
      const y = H - my - (H - 2 * my) * p.Ad / Amax;
      i ? ctx.lineTo(x, y) : ctx.moveTo(x, y);
    });
    ctx.stroke();

    // marcadores Ta / TC / TD
    const s = j.sismo;
    const marca = (T, txt, color) => {
      const x = mx + (W - mx - 10) * T / Tmax;
      ctx.strokeStyle = color; ctx.setLineDash([4, 4]);
      ctx.beginPath(); ctx.moveTo(x, my); ctx.lineTo(x, H - my); ctx.stroke();
      ctx.setLineDash([]);
      ctx.fillStyle = color;
      ctx.fillText(txt, x + 3, my + 10);
    };
    marca(s.Ta, 'Ta', '#2563eb');
    marca(s.TC, 'TC', '#059669');
    marca(Math.min(s.TD, Tmax), "T'", '#b45309');
  }

  function renderNiveles(j) {
    const tb = $('tabla-niveles').querySelector('tbody');
    tb.innerHTML = '';
    j.niveles.forEach((n, i) => {
      tb.insertAdjacentHTML('beforeend',
        `<tr><td>${i + 1}</td><td class="num">${fmt.format(n.y)}</td>
         <td class="num">${fmt.format(n.W)}</td><td class="num">${fmt.format(n.Fi)}</td></tr>`);
    });
  }

  function renderCombos(j) {
    const div = $('lista-combos');
    div.innerHTML = j.combos.map(c =>
      `<div class="combo-fila"><b>${c.nombre}</b> · ${c.formula}</div>`).join('');
  }

  function celdaEnv(e, dec) {
    if (!e || e.min === null) return '—';
    const t = `${fmt.format(e.min)} → ${fmt.format(e.max)}`;
    const combos = `min: ${e.cmin || '—'}\nmax: ${e.cmax || '—'}`;
    return `<span class="env-celda" title="${combos}">${t}</span>`;
  }

  function renderEnvolvente(j) {
    const env = j.envolvente;
    const tb = $('tabla-env-barras').querySelector('tbody');
    tb.innerHTML = '';
    for (const [bid, e] of Object.entries(env.barras)) {
      tb.insertAdjacentHTML('beforeend', `<tr>
        <td>${bid}</td>
        <td>${celdaEnv(e.Ni)}</td>
        <td>${celdaEnv(e.Vi)}</td>
        <td>${celdaEnv(e.Mmax)}</td>
        <td>${celdaEnv(e.Mmin)}</td></tr>`);
    }
    const tb2 = $('tabla-env-reacciones').querySelector('tbody');
    tb2.innerHTML = '';
    for (const [rk, e] of Object.entries(env.reacciones)) {
      const [nudo, comp] = rk.split(':');
      tb2.insertAdjacentHTML('beforeend', `<tr>
        <td>${nudo}</td><td>${comp}</td>
        <td class="num">${fmt.format(e.valor.min)}<br><span class="mini">${e.valor.cmin}</span></td>
        <td class="num">${fmt.format(e.valor.max)}<br><span class="mini">${e.valor.cmax}</span></td></tr>`);
    }
    const tb3 = $('tabla-env-nudos').querySelector('tbody');
    tb3.innerHTML = '';
    for (const [nid, e] of Object.entries(env.nudos)) {
      tb3.insertAdjacentHTML('beforeend', `<tr>
        <td>${nid}</td>
        <td>${celdaEnv(e.ux)}</td>
        <td>${celdaEnv(e.uy)}</td></tr>`);
    }
  }

  /* ================= proyecto (modelo + acciones) ================= */
  function guardarProyecto() {
    const datos = { version: 2, modelo, acciones: acc };
    const blob = new Blob([JSON.stringify(datos, null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = ((modelo && modelo.titulo) || 'proyecto').replace(/[^\w\-áéíóúñ ]+/gi, '').trim().replace(/\s+/g, '_') + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function abrirProyecto(e) {
    const f = e.target.files[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = () => {
      try {
        const j = JSON.parse(rd.result);
        if (j.modelo) {
          modelo = j.modelo;
          localStorage.setItem(CLAVE_MODELO, JSON.stringify(modelo));
        }
        if (j.acciones) {
          acc = { ...accPorDefecto(), ...j.acciones };
          guardarLocal();
          escribirFormulario();
          renderTablaBarras();
          renderTablaNudos();
        }
      } catch (err) {
        mostrarError('El archivo no es un proyecto válido: ' + err.message);
      }
    };
    rd.readAsText(f);
    e.target.value = '';
  }

  /* ================= init ================= */
  function init() {
    cargarLocal();
    const tenia = cargarModeloProyecto();
    escribirFormulario();
    renderTablaBarras();
    renderTablaNudos();

    $('btn-calcular').addEventListener('click', calcular);
    $('btn-guardar').addEventListener('click', guardarProyecto);
    $('btn-abrir').addEventListener('click', () => $('file-abrir').click());
    $('file-abrir').addEventListener('change', abrirProyecto);
    $('btn-aplicar-niveles').addEventListener('click', aplicarNivelesABarras);
    cargarTablas2002();
    $('btn-cp-todas').addEventListener('click', () => {
      const v = prompt('CP para todas las barras (kg/m):', '1000');
      if (v === null) return;
      modelo?.barras.forEach(b => { acc.barra_cp[b.id] = +v || 0; });
      guardarLocal(); renderTablaBarras();
    });
    $('btn-cv-todas').addEventListener('click', () => {
      const v = prompt('CV para todas las barras (kg/m):', '300');
      if (v === null) return;
      modelo?.barras.forEach(b => { acc.barra_cv[b.id] = +v || 0; });
      guardarLocal(); renderTablaBarras();
    });

    document.querySelectorAll('#tabs-env .tab').forEach(t => {
      t.addEventListener('click', () => {
        document.querySelectorAll('#tabs-env .tab').forEach(x =>
          x.classList.toggle('activo', x === t));
        ['barras', 'reacciones', 'nudos'].forEach(id =>
          $('tab-env-' + id).classList.toggle('oculto', id !== t.dataset.tab));
      });
    });

    if (!tenia) {
      // cargar un ejemplo automáticamente para probar rápido
      fetch('/api/ejemplos/portico_sismo')
        .then(r => r.json())
        .then(j => {
          modelo = j.modelo;
          localStorage.setItem(CLAVE_MODELO, JSON.stringify(modelo));
          renderTablaBarras();
          renderTablaNudos();
        })
        .catch(() => {});
    }
  }

  document.addEventListener('DOMContentLoaded', init);
  return { calcular };
})();
