/* ================================================================
   app.js — Orquestación UI ↔ Estado ↔ API ↔ Canvas
   ------------------------------------------------------------------
   Flujo: cambio en el modelo → Estado.notificar() → (auto)analizar
   → resultados → KPIs + tablas + overlays del lienzo.
   ================================================================ */

const App = (function () {
  'use strict';

  const $ = id => document.getElementById(id);
  const fmt = new Intl.NumberFormat('es-VE', { maximumFractionDigits: 2 });
  let tAuto = null;
  let calculando = false, pendiente = false;
  let selRenderizada = null;   // clave de la selección actualmente dibujada en el panel

  /* ================= arranque ================= */
  async function init() {
    Canvas2D.init();
    construirSelectorEjemplos();
    construirSelects();
    bindToolbar();
    bindHerramientas();
    bindAcciones();

    Estado.suscribir(alCambiar);

    if (!Estado.restaurar()) {
      await cargarEjemplo('viga_simple');
    } else {
      Estado.notificar({ todo: true });
    }
  }

  async function cargarEjemplo(id) {
    try {
      const m = await API.ejemplo(id);
      Estado.cargarModelo(m);
      setTimeout(() => Canvas2D.ajustar(), 50);
    } catch (e) {
      mostrarError('No se pudo cargar el ejemplo: ' + e.message);
    }
  }

  /* ================= construcción de UI ================= */
  function construirSelectorEjemplos() {
    API.listaEjemplos().then(lista => {
      const sel = $('sel-ejemplo');
      sel.innerHTML = '';
      for (const e of lista) {
        const op = document.createElement('option');
        op.value = e.id; op.textContent = e.nombre;
        sel.appendChild(op);
      }
    });
    $('btn-cargar-ejemplo').addEventListener('click', () => cargarEjemplo($('sel-ejemplo').value));
  }

  function construirSelects() {
    // perfiles
    const selPerfil = $('cfg-perfil');
    selPerfil.innerHTML = '';
    for (const p of Perfiles.lista()) {
      const op = document.createElement('option');
      op.value = p.nombre;
      op.textContent = `${p.nombre}  ·  A=${p.A} cm²  ·  I=${fmt.format(p.Ix)} cm⁴`;
      selPerfil.appendChild(op);
    }
    selPerfil.value = Estado.herr.perfil;

    // materiales
    const selMat = $('cfg-material');
    selMat.value = String(Estado.herr.material);

    // tipos de apoyo
    const selAp = $('cfg-apoyo-tipo');
    selAp.value = Estado.herr.apoyoTipo;
  }

  function bindToolbar() {
    document.querySelectorAll('#modos button').forEach(btn => {
      btn.addEventListener('click', () => setModo(btn.dataset.modo));
    });
    $('chk-snap').addEventListener('change', e => { Estado.herr.snap = e.target.checked; });
    $('chk-auto').addEventListener('change', e => {
      Estado.herr.autoCalcular = e.target.checked;
      if (e.target.checked) analizar();
    });
    $('chk-M').addEventListener('change', e => { Estado.herr.vista.M = e.target.checked; Canvas2D.dibujar(); });
    $('chk-V').addEventListener('change', e => { Estado.herr.vista.V = e.target.checked; Canvas2D.dibujar(); });
    $('chk-N').addEventListener('change', e => { Estado.herr.vista.N = e.target.checked; Canvas2D.dibujar(); });
    $('chk-def').addEventListener('change', e => { Estado.herr.vista.deformada = e.target.checked; Canvas2D.dibujar(); });
    $('chk-etiquetas').addEventListener('change', e => { Estado.herr.vista.etiquetas = e.target.checked; Canvas2D.dibujar(); });
    $('btn-zoom-mas').addEventListener('click', () => { zoomCentro(1.25); });
    $('btn-zoom-menos').addEventListener('click', () => { zoomCentro(0.8); });
    $('btn-zoom-fit').addEventListener('click', () => Canvas2D.ajustar());
    Canvas2D.onStatus = renderStatusBar;

    // pestañas de resultados
    document.querySelectorAll('#tabs-resultados .tab').forEach(t => {
      t.addEventListener('click', () => {
        document.querySelectorAll('#tabs-resultados .tab').forEach(x =>
          x.classList.toggle('activo', x === t));
        ['reacciones', 'barras', 'nudos'].forEach(id =>
          $('tab-' + id).classList.toggle('oculto', id !== t.dataset.tab));
      });
    });
  }

  function zoomCentro(f) {
    const cv = $('lienzo');
    const r = cv.getBoundingClientRect();
    cv.dispatchEvent(new WheelEvent('wheel', {
      deltaY: f > 1 ? -120 : 120,
      clientX: r.left + r.width / 2,
      clientY: r.top + r.height / 2,
      cancelable: true
    }));
  }

  const NOMBRES_MODO = {
    seleccionar: 'Clic: seleccionar · arrastrar nudo: mover · arrastrar fondo: desplazar · rueda: zoom',
    nudo: 'Clic para crear un nudo (imán 0,25 m)',
    barra: 'Clic: nudo inicial → clic: nudo final (crea nudos al vuelo) · clic derecho: terminar',
    apoyo: 'Clic sobre un nudo para asignar el tipo de apoyo configurado',
    puntual: 'Clic sobre un nudo para aplicar la carga puntual configurada (se acumula)',
    repartida: 'Clic sobre una barra para aplicarle la carga repartida configurada'
  };

  function setModo(m) {
    Estado.herr.modo = m;
    Estado.sesion.barraEnCurso = null;
    document.querySelectorAll('#modos button').forEach(b =>
      b.classList.toggle('activo', b.dataset.modo === m));
    document.querySelectorAll('.cfg-modo').forEach(el =>
      el.classList.toggle('oculto', el.dataset.modo !== m));
    renderStatusBar();
  }

  function bindHerramientas() {
    $('cfg-perfil').addEventListener('change', e => { Estado.herr.perfil = e.target.value; });
    $('cfg-material').addEventListener('change', e => { Estado.herr.material = +e.target.value; });
    $('cfg-rect-b').addEventListener('input', e => { Estado.herr.rect_b = +e.target.value || 1; });
    $('cfg-rect-h').addEventListener('input', e => { Estado.herr.rect_h = +e.target.value || 1; });
    $('cfg-man-A').addEventListener('input', e => { Estado.herr.manual_A = +e.target.value || 1; });
    $('cfg-man-I').addEventListener('input', e => { Estado.herr.manual_I = +e.target.value || 1; });
    $('cfg-tipo-seccion').addEventListener('change', e => {
      Estado.herr.tipoSeccion = e.target.value;
      document.querySelectorAll('.cfg-seccion').forEach(el =>
        el.classList.toggle('oculto', el.dataset.tipo !== e.target.value));
    });
    $('cfg-apoyo-tipo').addEventListener('change', e => { Estado.herr.apoyoTipo = e.target.value; });
    $('cfg-Fx').addEventListener('input', e => { Estado.herr.Fx = +e.target.value || 0; });
    $('cfg-Fy').addEventListener('input', e => { Estado.herr.Fy = +e.target.value || 0; });
    $('cfg-Mz').addEventListener('input', e => { Estado.herr.Mz = +e.target.value || 0; });
    $('cfg-w').addEventListener('input', e => { Estado.herr.wGrav = +e.target.value || 0; });
    $('cfg-pp').addEventListener('change', e => { Estado.herr.pesoPropio = e.target.checked; });
  }

  function bindAcciones() {
    $('btn-analizar').addEventListener('click', () => analizar());
    $('btn-guardar').addEventListener('click', guardarArchivo);
    $('btn-abrir').addEventListener('click', () => $('file-abrir').click());
    $('file-abrir').addEventListener('change', abrirArchivo);
    $('btn-limpiar').addEventListener('click', () => {
      if (!confirm('¿Borrar todo el modelo?')) return;
      Estado.cargarModelo({ titulo: 'Estructura sin nombre', nudos: [], barras: [], apoyos: [], cargas_nodales: [] });
    });
    $('btn-copiar-json').addEventListener('click', () => {
      navigator.clipboard.writeText(Estado.aJSON())
        .then(() => flash('JSON del modelo copiado'))
        .catch(() => {});
    });
  }

  function guardarArchivo() {
    const blob = new Blob([Estado.aJSON()], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = (Estado.datos.titulo || 'modelo').replace(/[^\w\-áéíóúñ ]+/gi, '').trim().replace(/\s+/g, '_') + '.json';
    a.click();
    URL.revokeObjectURL(a.href);
  }

  function abrirArchivo(e) {
    const f = e.target.files[0];
    if (!f) return;
    const rd = new FileReader();
    rd.onload = () => {
      try {
        Estado.cargarModelo(JSON.parse(rd.result));
        setTimeout(() => Canvas2D.ajustar(), 50);
      } catch (err) {
        mostrarError('El archivo no es un proyecto válido: ' + err.message);
      }
    };
    rd.readAsText(f);
    e.target.value = '';
  }

  /* ================= reacción a cambios ================= */
  function alCambiar() {
    Canvas2D.dibujar();
    renderResumen();
    renderSeleccion();
    if (Estado.herr.autoCalcular) {
      clearTimeout(tAuto);
      tAuto = setTimeout(analizar, 250);
    }
  }

  /* ================= análisis ================= */
  async function analizar() {
    if (calculando) { pendiente = true; return; }
    calculando = true;
    const t0 = performance.now();
    try {
      const res = await API.analizar(Estado.datos);
      const ms = Math.round(performance.now() - t0);
      if (res.ok) {
        Estado.sesion.resultado = res;
        Estado.sesion.error = null;
        $('caja-error').classList.add('oculto');
        renderKPIs(res, ms);
        renderTablas(res);
      } else {
        Estado.sesion.resultado = null;
        Estado.sesion.error = res.error || 'Error desconocido';
        mostrarError(Estado.sesion.error);
        $('kpi-delta').textContent = '—';
        $('kpi-mmax').textContent = '—';
        $('kpi-ry').textContent = '—';
        $('kpi-estado').textContent = 'Sin resolver';
        $('kpi-estado').className = 'kpi-valor mal';
      }
    } catch (e) {
      mostrarError('Sin conexión con el motor: ' + e.message);
    } finally {
      calculando = false;
      if (pendiente) { pendiente = false; analizar(); }
    }
  }

  function mostrarError(msg) {
    const caja = $('caja-error');
    caja.classList.remove('oculto');
    $('texto-error').textContent = msg;
  }

  /* ================= paneles de resultados ================= */
  function renderKPIs(res, ms) {
    $('kpi-delta').textContent = fmt.format(res.kpi.delta_max * 100) + ' cm';
    $('kpi-mmax').textContent = fmt.format(res.kpi.M_max) + ' kg·m';
    $('kpi-ry').textContent = fmt.format(res.kpi.suma_Ry) + ' kg';
    const ok = res.kpi.equilibrio_ok;
    $('kpi-estado').textContent = ok ? '✓ Equilibrio' : '⚠ Revisar';
    $('kpi-estado').className = 'kpi-valor ' + (ok ? 'bien' : 'mal');
    $('kpi-tiempo').textContent = `resuelto en ${ms} ms · ΣFx = ${fmt.format(res.kpi.suma_Rx)} kg`;
    renderAvisos(res);
  }

  function renderAvisos(res) {
    const div = $('caja-avisos');
    if (!res.avisos || !res.avisos.length) { div.classList.add('oculto'); return; }
    div.classList.remove('oculto');
    $('texto-avisos').innerHTML = res.avisos.map(a => '· ' + a).join('<br>');
  }

  function renderTablas(res) {
    /* --- reacciones --- */
    const tb = $('tabla-reacciones tbody');
    tb.innerHTML = '';
    for (const r of res.reacciones) {
      tb.insertAdjacentHTML('beforeend',
        `<tr><td>${r.nudo}</td><td>${r.comp}</td><td class="num">${fmt.format(r.valor)}</td></tr>`);
    }
    if (!res.reacciones.length) tb.innerHTML = '<tr><td colspan="3" class="vacio">—</td></tr>';

    /* --- barras --- */
    const tb2 = $('tabla-barras tbody');
    tb2.innerHTML = '';
    for (const b of res.barras) {
      tb2.insertAdjacentHTML('beforeend',
        `<tr>
          <td>${b.id}</td>
          <td class="num">${fmt.format(b.Ni)}</td>
          <td class="num">${fmt.format(b.Vi)}</td>
          <td class="num">${fmt.format(b.Mi)}</td>
          <td class="num">${fmt.format(b.Mj)}</td>
          <td class="num">${fmt.format(b.maxM)}</td>
        </tr>`);
    }
    if (!res.barras.length) tb2.innerHTML = '<tr><td colspan="6" class="vacio">—</td></tr>';

    /* --- desplazamientos --- */
    const tb3 = $('tabla-nudos tbody');
    tb3.innerHTML = '';
    for (const n of [...res.nudos].sort((a, b) => Math.abs(b.uy) - Math.abs(a.uy))) {
      tb3.insertAdjacentHTML('beforeend',
        `<tr>
          <td>${n.id}</td>
          <td class="num">${(n.ux * 100).toFixed(3)}</td>
          <td class="num">${(n.uy * 100).toFixed(3)}</td>
          <td class="num">${(n.rz * 1000).toFixed(2)}</td>
        </tr>`);
    }
    if (!res.nudos.length) tb3.innerHTML = '<tr><td colspan="4" class="vacio">—</td></tr>';
  }

  /* ================= panel izquierdo ================= */
  function renderResumen() {
    const d = Estado.datos;
    $('res-nudos').textContent = d.nudos.length;
    $('res-barras').textContent = d.barras.length;
    $('res-apoyos').textContent = d.apoyos.length;
    $('res-cargas').textContent = d.cargas_nodales.length + d.barras.filter(b => b.q_perp || b.q_axial || b.peso_propio).length;
    $('in-titulo').value = d.titulo;
  }

  function renderSeleccion() {
    const caja = $('card-seleccion');
    const s = Estado.sesion.seleccion;
    if (!s) { caja.classList.add('oculto'); selRenderizada = null; return; }
    caja.classList.remove('oculto');

    const clave = s.tipo + ':' + s.id;
    if (clave === selRenderizada) {
      // no reconstruir el DOM (se perdería el foco del input);
      // solo sincronizar valores que cambian desde el lienzo
      sincronizarSeleccion();
      return;
    }
    selRenderizada = clave;

    const d = Estado.datos;

    if (s.tipo === 'nudo') {
      const n = d.nudos.find(x => x.id === s.id);
      if (!n) { Estado.sesion.seleccion = null; caja.classList.add('oculto'); return; }
      const a = Estado.apoyoDe(n.id);
      const tipoAp = a ? (a.rz ? 'fijo' : (a.uy ? (a.ux ? 'articulado' : 'deslizX') : 'deslizY')) : 'ninguno';
      const c = Estado.cargaDe(n.id) || { Fx: 0, Fy: 0, Mz: 0 };
      caja.querySelector('.contenido').innerHTML = `
        <div class="fila"><span>Nudo</span><b>${n.id}</b></div>
        <label class="campo">X (m)<input type="number" step="0.25" id="sel-x" value="${n.x}"></label>
        <label class="campo">Y (m)<input type="number" step="0.25" id="sel-y" value="${n.y}"></label>
        <label class="campo">Apoyo
          <select id="sel-apoyo">
            <option value="ninguno">Ninguno</option>
            <option value="fijo">Empotrado</option>
            <option value="articulado">Articulado</option>
            <option value="deslizX">Deslizante (libre X)</option>
            <option value="deslizY">Deslizante (libre Y)</option>
          </select>
        </label>
        <label class="campo">Fx (kg)<input type="number" step="100" id="sel-Fx" value="${c.Fx}"></label>
        <label class="campo">Fy (kg)<input type="number" step="100" id="sel-Fy" value="${c.Fy}"></label>
        <label class="campo">Mz (kg·m)<input type="number" step="100" id="sel-Mz" value="${c.Mz}"></label>
        <button class="peligro ancho" id="sel-eliminar">🗑 Eliminar nudo</button>`;
      $('sel-x').addEventListener('input', e => { n.x = +e.target.value || 0; Estado.notificar({}); });
      $('sel-y').addEventListener('input', e => { n.y = +e.target.value || 0; Estado.notificar({}); });
      $('sel-apoyo').value = tipoAp;
      $('sel-apoyo').addEventListener('change', e => {
        Estado.herr.apoyoTipo = e.target.value;
        Estado.asignarApoyo(n.id);
      });
      const upd = () => {
        c.Fx = +$('sel-Fx').value || 0;
        c.Fy = +$('sel-Fy').value || 0;
        c.Mz = +$('sel-Mz').value || 0;
        if (!c.Fx && !c.Fy && !c.Mz)
          Estado.datos.cargas_nodales = Estado.datos.cargas_nodales.filter(x => x.nudo !== n.id);
        Estado.notificar({});
      };
      $('sel-Fx').addEventListener('input', upd);
      $('sel-Fy').addEventListener('input', upd);
      $('sel-Mz').addEventListener('input', upd);
      $('sel-eliminar').addEventListener('click', () => Estado.eliminar(s));
    } else {
      const b = d.barras.find(x => x.id === s.id);
      if (!b) { Estado.sesion.seleccion = null; caja.classList.add('oculto'); return; }
      const ni = d.nudos.find(n => n.id === b.ni), nj = d.nudos.find(n => n.id === b.nj);
      const L = ni && nj ? Math.hypot(nj.x - ni.x, nj.y - ni.y) : 0;
      const wMostrar = Math.hypot(b.q_perp, b.q_axial);
      caja.querySelector('.contenido').innerHTML = `
        <div class="fila"><span>Barra</span><b>${b.id}</b></div>
        <div class="fila"><span>Longitud</span><b>${fmt.format(L)} m</b></div>
        <label class="campo">Sección<input type="text" id="sel-nombre" value="${b.nombre_seccion}"></label>
        <label class="campo">E (kg/cm²)<input type="number" step="10000" id="sel-E" value="${b.E}"></label>
        <label class="campo">A (cm²)<input type="number" step="1" id="sel-A" value="${b.A}"></label>
        <label class="campo">I (cm⁴)<input type="number" step="100" id="sel-I" value="${b.I}"></label>
        <label class="campo">w gravedad (kg/m)<input type="number" step="50" id="sel-w" value="${wMostrar.toFixed(2)}"></label>
        <label class="check"><input type="checkbox" id="sel-pp" ${b.peso_propio ? 'checked' : ''}> Peso propio (7850 kg/m³)</label>
        <button class="peligro ancho" id="sel-eliminar">🗑 Eliminar barra</button>`;
      $('sel-nombre').addEventListener('input', e => { b.nombre_seccion = e.target.value; Estado.notificar({}); });
      $('sel-E').addEventListener('input', e => { b.E = +e.target.value || 1; Estado.notificar({}); });
      $('sel-A').addEventListener('input', e => { b.A = +e.target.value || 1; Estado.notificar({}); });
      $('sel-I').addEventListener('input', e => { b.I = Math.max(0, +e.target.value || 0); Estado.notificar({}); });
      $('sel-w').addEventListener('input', e => {
        Estado.herr.wGrav = +e.target.value || 0;
        Estado.aplicarCargaRepartida(b.id);
      });
      $('sel-pp').addEventListener('change', e => { b.peso_propio = e.target.checked; Estado.notificar({}); });
      $('sel-eliminar').addEventListener('click', () => Estado.eliminar(s));
    }
  }

  /* sincroniza (sin reconstruir) los valores del panel de selección
     cuando cambian desde el lienzo, p. ej. al arrastrar un nudo */
  function sincronizarSeleccion() {
    const s = Estado.sesion.seleccion;
    if (!s) return;
    const d = Estado.datos;
    if (s.tipo === 'nudo') {
      const n = d.nudos.find(x => x.id === s.id);
      if (!n) return;
      if ($('sel-x')) $('sel-x').value = n.x;
      if ($('sel-y')) $('sel-y').value = n.y;
    }
  }

  /* ================= status bar ================= */
  function renderStatusBar() {
    const m = Canvas2D._cursorMundo;
    const coords = m ? `x = ${m.x.toFixed(2)} m · y = ${m.y.toFixed(2)} m` : '';
    $('status-coords').textContent = coords;
    $('status-modo').textContent = NOMBRES_MODO[Estado.herr.modo] || '';
    $('status-escala').textContent = Math.round(Canvas2D.escala()) + ' px/m';
  }

  function flash(msg) {
    const el = $('toast');
    el.textContent = msg;
    el.classList.add('visible');
    setTimeout(() => el.classList.remove('visible'), 1800);
  }

  /* atajos de teclado para modos */
  window.addEventListener('keydown', e => {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'SELECT' || e.target.tagName === 'TEXTAREA') return;
    const mapa = { s: 'seleccionar', n: 'nudo', b: 'barra', a: 'apoyo', p: 'puntual', d: 'repartida' };
    if (mapa[e.key.toLowerCase()]) setModo(mapa[e.key.toLowerCase()]);
  });

  document.addEventListener('DOMContentLoaded', init);
  return { analizar, cargarEjemplo };
})();
