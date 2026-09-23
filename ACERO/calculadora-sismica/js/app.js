/* ================================================================
   app.js — Orquestación UI ↔ Estado ↔ Motor ↔ Canvas
   ---------------------------------------------------------------
   FASE 1–2.
   Flujo (una sola dirección, sin lógica duplicada):
     input → Estado.datos → COVENIN.calcularSismo() → resultados
           → KPIs + tabla + espectro + canvas de planta
   Reglas:
     · Escribir en un input NO reconstruye el DOM (no se pierde el foco).
     · Cambios estructurales (± vanos, ± niveles, abrir proyecto) sí
       reconstruyen su bloque de UI.
     · El cálculo es automático ante cualquier cambio.
   ================================================================ */

const App = (function () {
  'use strict';

  const $ = (id) => document.getElementById(id);
  let fmtES;
  try { fmtES = new Intl.NumberFormat('es-VE'); } catch (e) { fmtES = new Intl.NumberFormat('es'); }
  const fmt = (x, dec = 0) => fmtES.format(+(Number(x) || 0).toFixed(dec));
  const num = (id, def) => { const v = parseFloat($(id) && $(id).value); return isFinite(v) ? v : (def || 0); };

  const USOS = [
    ['vivienda', 'Vivienda (15 %)'], ['oficina', 'Oficinas (25 %)'],
    ['comercio', 'Comercio (25 %)'], ['agrupacion', 'Agrupación pública (50 %)'],
    ['estacionamiento', 'Estacionamiento (50 %)'], ['almacen', 'Almacén (80 %)'],
    ['recipientes', 'Recipientes (100 %)'], ['ascensor', 'Ascensor (100 %)'],
    ['techo', 'Techo no accesible (0 %)']
  ];
  const GRUPOS = [['A1', 'A1 — Esencial (α=2.0)'], ['A2', 'A2 — α=1.5'], ['B1', 'B1 — α=1.2'],
                  ['B2', 'B2 — α=1.0 (vivienda/oficinas)'], ['C', 'C — α=0.7 (provisional)']];
  const NDS = [['ND3', 'ND3 — R=6 · Cd=4,25'], ['ND2', 'ND2 — R=3,5 · Cd=3,25'], ['ND1', 'ND1 — R=2,5 · Cd=2,25']];

  /* ================= actualización global ================= */

  function update() {
    calcular();
    CanvasPlanta.render();
    renderInspector();
    renderResumen();
  }

  function construirP() {
    const d = Estado.datos;
    const hsAbs = d.niveles.map(n => Math.max(0.5, Number(n.h) || 1));
    /* ordenar ascendente (índice 0 = base) y reordenar W igual */
    const idx = hsAbs.map((h, i) => i).sort((a, b) => hsAbs[a] - hsAbs[b]);
    const ord = (arr) => idx.map(k => arr[k]);
    const areaPlanta = d.geometria.lx.reduce((a, b) => a + b, 0) * d.geometria.ly.reduce((a, b) => a + b, 0);
    const { areas, qs, W } = COVENIN.pesosPorNivel(d.niveles, areaPlanta, d.material.ppest);
    return {
      A0: d.sismo.A0, A1: d.sismo.A1, TL: d.sismo.TL,
      grupo: d.sismo.grupo, nd: d.sismo.nd, sitio: d.sismo.sitio, topo: d.sismo.topo,
      H: d.sismo.H, rho: d.sismo.rho, FI: d.sismo.FI,
      N: d.niveles.length,
      hsAbs: ord(hsAbs), W: ord(W), areas: ord(areas), qs: ord(qs),
      Fy: d.material.Fy, E: d.material.E,
      lucesX: d.geometria.lx, lucesY: d.geometria.ly,
      areaTotal: areaPlanta
    };
  }

  function calcular() {
    const badge = $('badge-motor');
    const lx = Estado.datos.geometria.lx, ly = Estado.datos.geometria.ly;
    if (lx.some(v => !(v > 0)) || ly.some(v => !(v > 0))) {
      badge.textContent = '⚠ Todas las luces deben ser > 0';
      badge.className = 'badge warn';
      Estado.resultados = null;
      $('kpis').innerHTML = '<div class="vacio">Corrige la geometría para calcular.</div>';
      return;
    }
    try {
      const p = construirP();
      const s = COVENIN.calcularSismo(p);
      Estado.resultados = { p, s };
      renderKPIs(p, s);
      renderTablaFuerzas(p, s);
      CanvasPlanta.dibujarEspectro('espectro', p, s);
      badge.textContent = '✔ Motor COVENIN 1756-1:2019';
      badge.className = 'badge ok';
    } catch (err) {
      badge.textContent = '✗ Error: ' + err.message;
      badge.className = 'badge error';
      console.error(err);
    }
  }

  /* ================= KPIs ================= */

  function kpi(v, l, extra) {
    return `<div class="kpi"><div class="v">${v}</div><div class="l">${l}${extra ? ' · <span class="mini">' + extra + '</span>' : ''}</div></div>`;
  }

  function renderKPIs(p, s) {
    const d = Estado.datos;
    const cumC = s.C >= s.Cmin
      ? '<span class="ok">CUMPLE</span>'
      : `<span class="mal">NO CUMPLE → escalado ×${fmt(s.escala, 3)}</span>`;
    $('kpis').innerHTML =
      kpi(fmt(s.AA, 3), 'A<sub>A</sub> = FA·α·A<sub>0</sub>', `FA=${fmt(s.FA, 3)}`) +
      kpi(fmt(s.AV, 3), 'A<sub>V</sub> = FV·α·A<sub>1</sub>', `FV=${fmt(s.FV, 3)}`) +
      kpi(fmt(s.T, 3) + ' s', 'T = T<sub>a</sub> = 0,08·h<sub>n</sub><sup>0,75</sup>', `h<sub>n</sub>=${fmt(s.hn, 2)} m · máx σ·Ta=${fmt(s.Tmax, 3)} s`) +
      kpi(fmt(s.TC, 3) + ' s', 'T<sub>C</sub> (meseta)', `TA=${fmt(s.TA, 3)} · TB=${fmt(s.TB, 3)} · TD=${fmt(s.TD, 2)} s`) +
      kpi(fmt(s.AdT, 4), 'A<sub>d</sub>(T)', `R=${s.R} · ρ=${d.sismo.rho} · FI=${d.sismo.FI}`) +
      kpi(fmt(s.mu, 3), 'μ = 1,4(N+9)/(2N+12)', `N=${p.N}`) +
      kpi(fmt(s.C, 4), 'C = μ·A<sub>d</sub>', `C<sub>mín</sub>=AA/R=${fmt(s.Cmin, 4)} → ${cumC}`) +
      kpi(fmt(s.V0d) + ' kg', 'V<sub>0</sub> = C·W', `W=${fmt(s.Wtot)} kg · Ft=${fmt(s.Ft)} kg (${fmt(s.coefFt * 100, 1)} %)`);
  }

  function renderTablaFuerzas(p, s) {
    let filas = '';
    for (let i = 0; i < p.N; i++) {
      filas += `<tr>
        <td>${i + 1}${i === p.N - 1 ? ' (tope)' : ''}</td>
        <td>${fmt(p.hsAbs[i], 2)}</td>
        <td>${fmt(p.W[i])}</td>
        <td>${fmt(s.Wh[i])}</td>
        <td>${fmt(s.Fis[i])}</td>
        <td>${fmt(s.Vpisos[i])}</td>
      </tr>`;
    }
    $('tabla-fuerzas').innerHTML = filas;
    $('ft-nota').innerHTML =
      `F<sub>t</sub> = ${fmt(s.coefFt * 100, 1)} % de V<sub>0d</sub> = ${fmt(s.Ft)} kg se aplica <b>en el tope</b>; ` +
      `las F<sub>i</sub> reparten V<sub>0d</sub> − F<sub>t</sub> = ${fmt(s.Veff)} kg proporcional a W<sub>i</sub>·h<sub>i</sub> (fórmula 9.11).`;
  }

  /* ================= resumen (chips) ================= */

  function renderResumen() {
    const d = Estado.datos;
    const totX = d.geometria.lx.reduce((a, b) => a + b, 0);
    const totY = d.geometria.ly.reduce((a, b) => a + b, 0);
    const hn = d.niveles.length ? Math.max(...d.niveles.map(n => Number(n.h) || 0)) : 0;
    $('chip-geo').textContent = `${d.geometria.lx.length}×${d.geometria.ly.length} vanos · ${fmt(totX, 2)}×${fmt(totY, 2)} m`;
    $('chip-niv').textContent = `${d.niveles.length} niveles · hn = ${fmt(hn, 2)} m`;
    if (Estado.resultados) {
      $('chip-w').textContent = `W = ${fmt(Estado.resultados.s.Wtot)} kg · V0 = ${fmt(Estado.resultados.s.V0d)} kg`;
    } else {
      $('chip-w').textContent = 'W = — · V0 = —';
    }
  }

  /* ================= grillas editables ================= */

  function renderGrilla(dir) {
    const g = Estado.datos.geometria;
    const arr = dir === 'X' ? g.lx : g.ly;
    const cont = dir === 'X' ? $('lista-vx') : $('lista-vy');
    let html = '';
    arr.forEach((v, i) => {
      html += `<div class="fila-vano">
        <span class="etq">${dir === 'X' ? 'VX' : 'VY'}${i + 1}</span>
        <input type="number" step="0.1" min="0.1" value="${v}" data-dir="${dir}" data-i="${i}">
        <button class="btn-micro" data-dir="${dir}" data-i="${i}" title="Eliminar vano">−</button>
      </div>`;
    });
    cont.innerHTML = html;
    /* eventos */
    cont.querySelectorAll('input').forEach(inp => {
      inp.addEventListener('input', () => {
        const a = inp.dataset.dir === 'X' ? g.lx : g.ly;
        a[+inp.dataset.i] = parseFloat(inp.value) || 0;
        update();
      });
    });
    cont.querySelectorAll('button').forEach(btn => {
      btn.addEventListener('click', () => { Estado.quitarVano(btn.dataset.dir, +btn.dataset.i); reconstruir(); });
    });
  }

  /* ================= niveles ================= */

  function renderNiveles() {
    const d = Estado.datos;
    const tb = $('cuerpo-niveles');
    const perfilesCol = Catalogo.lista('columna');
    let html = '';
    d.niveles.forEach((n, i) => {
      const ops = USOS.map(([k, lbl]) => `<option value="${k}" ${n.uso === k ? 'selected' : ''}>${lbl}</option>`).join('');
      const pf = perfilesCol.map(p => `<option value="${p.nombre}" ${n.perfil === p.nombre ? 'selected' : ''}>${p.nombre}</option>`).join('');
      html += `<tr>
        <td>${i + 1}</td>
        <td><input type="number" step="0.05" min="0.5" value="${n.h}" data-campo="h" data-i="${i}" title="Altura acumulada hasta el nivel ${i + 1}"></td>
        <td><input type="number" step="10" min="0" value="${n.cp}" data-campo="cp" data-i="${i}"></td>
        <td><input type="number" step="10" min="0" value="${n.cv}" data-campo="cv" data-i="${i}"></td>
        <td><select data-campo="uso" data-i="${i}">${ops}</select></td>
        <td><select data-campo="perfil" data-i="${i}">${pf}</select></td>
        <td><input type="number" step="5" min="0" value="${n.area === null ? '' : n.area}" placeholder="auto" data-campo="area" data-i="${i}"></td>
        <td><button class="btn-micro" data-del="${i}" ${d.niveles.length <= 1 ? 'disabled' : ''} title="Eliminar nivel">−</button></td>
      </tr>`;
    });
    tb.innerHTML = html;

    tb.querySelectorAll('input,select').forEach(el => {
      el.addEventListener('input', () => {
        const n = d.niveles[+el.dataset.i];
        if (!n) return;
        const c = el.dataset.campo;
        if (c === 'area') { const v = parseFloat(el.value); n.area = isFinite(v) && v > 0 ? v : null; }
        else if (c === 'uso' || c === 'perfil') { n[c] = el.value; }
        else { n[c] = parseFloat(el.value) || 0; }
        update();
      });
    });
    tb.querySelectorAll('button[data-del]').forEach(btn => {
      btn.addEventListener('click', () => { Estado.quitarNivel(+btn.dataset.del); reconstruir(); });
    });
  }

  /* ================= inspector ================= */

  function renderInspector() {
    const box = $('inspector');
    const d = Estado.datos;
    const selN = Estado.seleccion.nodo, selT = Estado.seleccion.tramo;
    if (!selN && !selT) {
      box.innerHTML = '<div class="vacio">Selecciona en el plano un <b>nodo</b> (columna) o una <b>línea</b> (viga) para ver sus cargas tributarias.</div>';
      return;
    }
    if (selN) {
      const { i, j } = selN;
      const at = COVENIN.areaTributaria(i, j, d.geometria.lx, d.geometria.ly);
      const ppest = d.material.ppest;
      let filas = '', suma = 0;
      d.niveles.forEach((n, k) => {
        const frac = COVENIN.FRACC_CV[n.uso] !== undefined ? COVENIN.FRACC_CV[n.uso] : 0.15;
        const q = n.cp + frac * n.cv + ppest;
        const P = q * at.At;
        suma += P;
        filas += `<tr><td>${k + 1}</td><td>${fmt(q, 0)}</td><td>${fmt(P)}</td></tr>`;
      });
      box.innerHTML = `
        <div class="insp-titulo">COLUMNA · Nodo (${j + 1}, ${String.fromCharCode(65 + i)}) <span class="pill">${at.pos}</span></div>
        <div class="insp-datos">A<sub>x</sub> = ${fmt(at.Ax, 2)} m · A<sub>y</sub> = ${fmt(at.Ay, 2)} m ·
          <b>A<sub>t</sub> = ${fmt(at.At, 2)} m²</b> · perfil (tope): ${d.niveles[d.niveles.length - 1].perfil}</div>
        <table class="mini-tabla"><thead><tr><th>Nivel</th><th>q sísmica (kg/m²)</th><th>P nivel (kg)</th></tr></thead>
        <tbody>${filas}</tbody>
        <tfoot><tr><td colspan="2">ΣP acumulada en base (referencia, sin factores)</td><td><b>${fmt(suma)}</b></td></tr></tfoot></table>
        <div class="mini">q = CP + frac·CV + pp estructural (Tabla 20). Verificación del miembro y sismo axial: Fase 4.</div>`;
      return;
    }
    /* tramo */
    const dir = selT.dir, idx = selT.idx;
    const luz = dir === 'X' ? d.geometria.lx[idx] : d.geometria.ly[idx];
    const perp = dir === 'X' ? d.geometria.ly : d.geometria.lx;
    const anchoT = perp.reduce((a, b) => a + b, 0) / perp.length;   // ancho tributario promedio
    let filas = '';
    d.niveles.forEach((n, k) => {
      const frac = COVENIN.FRACC_CV[n.uso] !== undefined ? COVENIN.FRACC_CV[n.uso] : 0.15;
      const q = (n.cp + frac * n.cv + d.material.ppest) * anchoT;   // kg/m
      filas += `<tr><td>${k + 1}</td><td>${fmt(q, 0)}</td></tr>`;
    });
    box.innerHTML = `
      <div class="insp-titulo">VIGA · ${dir === 'X' ? 'VX' : 'VY'}${idx + 1} <span class="pill">L = ${fmt(luz, 2)} m</span></div>
      <div class="insp-datos">Perfil de piso: <b>${d.material.viga}</b> · ancho tributario promedio:
        <b>${fmt(anchoT, 2)} m</b> (vanos medios; extremos llevan la mitad)</div>
      <table class="mini-tabla"><thead><tr><th>Nivel</th><th>q lineal sísmica (kg/m)</th></tr></thead>
      <tbody>${filas}</tbody></table>
      <div class="mini">Verificación de la viga (M, V, flecha, LRFD/ASD): Fase 4.</div>`;
  }

  /* ================= parámetros (bind) ================= */

  function bindParametros() {
    const d = Estado.datos;
    $('in-proyecto').value = d.proyecto;
    $('in-proyecto').addEventListener('input', e => { d.proyecto = e.target.value; });

    const mapNum = [
      ['s-A0', d.sismo, 'A0'], ['s-A1', d.sismo, 'A1'], ['s-TL', d.sismo, 'TL'],
      ['s-H', d.sismo, 'H'], ['s-rho', d.sismo, 'rho'], ['s-FI', d.sismo, 'FI'],
      ['s-tabique', d.sismo, 'tabique'],
      ['m-ppest', d.material, 'ppest'], ['m-Fy', d.material, 'Fy'], ['m-E', d.material, 'E'],
      ['g-hpiso', d.geometria, 'hpiso']
    ];
    mapNum.forEach(([id, obj, key]) => {
      $(id).value = obj[key];
      $(id).addEventListener('input', e => { obj[key] = parseFloat(e.target.value) || 0; update(); });
    });

    const mapSel = [
      ['s-grupo', d.sismo, 'grupo', GRUPOS], ['s-nd', d.sismo, 'nd', NDS],
      ['s-sitio', d.sismo, 'sitio', COVENIN.CLASES.map(c => [c, 'Clase ' + c])],
      ['s-topo', d.sismo, 'topo', [['leve', 'Leve'], ['mod', 'Moderada'], ['sev', 'Severa']]]
    ];
    mapSel.forEach(([id, obj, key, opts]) => {
      $(id).innerHTML = opts.map(([v, l]) => `<option value="${v}" ${obj[key] === v ? 'selected' : ''}>${l}</option>`).join('');
      $(id).addEventListener('change', e => { obj[key] = e.target.value; update(); });
    });

    /* viga de piso */
    const selV = $('m-viga');
    selV.innerHTML = Catalogo.lista('viga').map(p => `<option value="${p.nombre}" ${d.material.viga === p.nombre ? 'selected' : ''}>${p.nombre}</option>`).join('');
    selV.addEventListener('change', e => { d.material.viga = e.target.value; update(); });
  }

  /* ================= reconstrucción estructural ================= */

  function reconstruir() {
    renderGrilla('X');
    renderGrilla('Y');
    renderNiveles();
    update();
  }

  /* ================= guardar / abrir ================= */

  function guardar() {
    const blob = new Blob([Estado.serializar()], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (Estado.datos.proyecto || 'proyecto').replace(/[^\w\- áéíóúñÁÉÍÓÚÑ]/g, '').trim().replace(/\s+/g, '_') + '.json';
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(() => URL.revokeObjectURL(a.href), 2000);
  }

  function abrir(file) {
    const rd = new FileReader();
    rd.onload = () => {
      try {
        Estado.cargarJSON(rd.result);
        bindParametros();          /* re-llenar valores de parámetros */
        reconstruir();
      } catch (err) { alert('No se pudo abrir: ' + err.message); }
    };
    rd.readAsText(file);
  }

  /* ================= init ================= */

  function init() {
    bindParametros();
    reconstruir();

    $('btn-vx-add').addEventListener('click', () => { Estado.agregarVano('X'); reconstruir(); });
    $('btn-vy-add').addEventListener('click', () => { Estado.agregarVano('Y'); reconstruir(); });
    $('btn-nivel-add').addEventListener('click', () => { Estado.agregarNivel(); reconstruir(); });
    $('btn-calcular').addEventListener('click', () => {
      update();
      $('resultados').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
    $('btn-png').addEventListener('click', () => CanvasPlanta.exportarPNG((Estado.datos.proyecto || 'planta').replace(/\s+/g, '_')));
    $('toggle-perfil-real').addEventListener('change', () => CanvasPlanta.render());
    $('btn-guardar').addEventListener('click', guardar);
    $('btn-abrir').addEventListener('click', () => $('file-abrir').click());
    $('file-abrir').addEventListener('change', e => { if (e.target.files[0]) abrir(e.target.files[0]); e.target.value = ''; });

    /* el canvas refresca cuando cambia la selección hecha desde la UI */
    Estado.suscribir(que => {
      if (que === 'seleccion') { renderInspector(); CanvasPlanta.render(); }
    });

    CanvasPlanta.init('planta');
    renderResumen();
  }

  return { init };
})();

document.addEventListener('DOMContentLoaded', App.init);
