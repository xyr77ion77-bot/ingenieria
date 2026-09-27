/* ================================================================
   memoria.js — Modo aprendizaje
   ------------------------------------------------------------------
   · Tooltips «¿por qué?»: junto a cada campo/resultado clave hay un
     botón ¿? que explica la fórmula, la sustitución y la referencia
     (§ de la norma COVENIN aplicable o página del formulario).
   · Memoria de cálculo: cada corrida deja el paso a paso
     fórmula → sustitución con los valores reales → resultado →
     fuente → porqué. Imprimible con 🖨.
   · ES2015 sin azúcar sintáctico posterior (navegadores antiguos).
   ================================================================ */
window.Memoria = (function () {
  'use strict';

  var SECCIONES = [];   /* memoria en curso */
  var J = null;         /* última respuesta /api/combinaciones */
  var ctx = null;       /* {acc, niveles, cfg, cpCv} desde AccionesApp */
  var pop = null;       /* popover abierto */

  /* ---------------- catálogo «¿por qué?» ---------------- */
  var CAT = [
    { k: 'tipo2002', ancla: 'sel-tipo-2002',
      t: 'Tipo de edificación',
      f: 'CV(ambiente) = valor de la Tabla 5.1 según el uso',
      p: 'La carga variable NO se inventa: la norma la asigna por tabla ' +
         'según lo que se aloje en cada ambiente (vivienda, oficinas, ' +
         'aulas, comercio…). El tipo de edificación agrupa los ambientes.',
      r: 'COVENIN 2002-88 · Tabla 5.1' },
    { k: 'ambiente', cls: 'in-amb',
      t: 'Ambiente del nivel',
      f: 'CV = valor tabulado para el uso del nivel',
      p: 'Cada nivel puede tener usos distintos (planta comercial, pisos ' +
         'de vivienda…). El ambiente elige la fila de la Tabla 5.1 que ' +
         'aplica a ese nivel.',
      r: 'COVENIN 2002-88 · Tabla 5.1' },
    { k: 'cobertura', cls: 'in-cob',
      t: 'Cobertura del techo',
      f: 'pp < 50 → 40 · pp ≥ 50 y p ≤ 15% → 100 · p > 15% → 50 · ' +
         'azotea con uso ≥ 100',
      p: 'Sobre los techos actúa gente de mantenimiento y lluvia, no el ' +
         'uso del edificio; por eso la CV del techo se define por el peso ' +
         'propio de la cobertura y su pendiente, no por la Tabla 5.1.',
      r: 'COVENIN 2002-88 · §5.2.4.2' },
    { k: 'ancho', cls: 'in-ancho',
      t: 'Ancho tributario',
      f: 'q_viga = (CP + CV) · ancho',
      p: 'Cada viga entrega a su pórtico la carga de la franja de losa ' +
         'que le toca: media distancia a las vigas vecinas de cada lado. ' +
         'Es la franja sombreada que verás en la planta.',
      r: 'Reparto de losa (ancho tributario)' },
    { k: 'fracc', ancla: 's-fracc',
      t: 'Fracción de CV para el sismo',
      f: 'CV_sísmico = frac · CV',
      p: 'Cuando ocurre el sismo no está toda la gente ni todo el ' +
         'mobiliario: la norma fracciona la CV según el uso (oficinas 25%).',
      r: 'COVENIN 1756:2019 · Tabla 20' },
    { k: 'rho', ancla: 's-rho',
      t: 'ρ — amortiguamiento',
      f: 'modifica la meseta del espectro',
      p: 'Ajusta el espectro por el amortiguamiento real de la ' +
         'estructura (acero estructural ≈ 1,0 salvo estudios especiales).',
      r: 'COVENIN 1756:2019 · §7.3.4' },
    { k: 'FI', ancla: 's-FI',
      t: 'FI — factor de importancia',
      f: 'multiplica Ad(T)',
      p: 'Según la uso-importancia de la edificación: hospitales y ' +
         'cuerpos de rescate exigen más (FI > 1) que viviendas (FI = 1).',
      r: 'COVENIN 1756:2019 · §6.4' },
    { k: 'ct', ancla: 's-ct',
      t: 'ct — coeficiente del período',
      f: 'Ta = ct · hn^0,75',
      p: 'Estima el período fundamental sin calcular modos: depende del ' +
         'material y sistema (0,08 acero pórtico rígido, Tabla 24).',
      r: 'COVENIN 1756:2019 · §9.4.3.3 + Tabla 24' },
    { k: 'A0', ancla: 's-A0',
      t: 'A₀ — amenaza sísmica',
      f: 'AA = FA·α·A₀',
      p: 'Aceleración pico horizontal del suelo según la zona sísmica ' +
         'del mapa (Tabla 4.1 del mapa). Es la materia prima del espectro.',
      r: 'COVENIN 1756:2019 · §4 + Tabla 8' },
    { k: 'A1', ancla: 's-A1',
      t: 'A₁ — amenaza (velocidad)',
      f: 'AV = FV·α·A₁',
      p: 'Aceleración asociada a la velocidad del suelo; controla la ' +
         'meseta del espectro (TC = (1/β)·AV/AA).',
      r: 'COVENIN 1756:2019 · §4 + Tabla 9' },
    { k: 'TL', ancla: 's-TL',
      t: 'TL — período de transición',
      f: 'TD ≈ TL·FD/FV',
      p: 'Límite donde el espectro deja de descender: limita las ' +
         'fuerzas de estructuras muy flexibles.',
      r: 'COVENIN 1756:2019 · Tabla 4.3' },
    { k: 'nd', ancla: 's-nd',
      t: 'Sistema estructural (ND)',
      f: 'R · Cd · Ω₀',
      p: 'La capacidad de disipar energía del sistema (pórtico ' +
         'articulado, rígido, arriostrado…) define R: a mayor ' +
         'ductilidad, menores fuerzas de diseño.',
      r: 'COVENIN 1756:2019 · Tablas 14–16' },
    { k: 'sitio', ancla: 's-sitio',
      t: 'Perfil de suelo',
      f: 'FA, FV según AA y A₁',
      p: 'El suelo amplifica o atenúa el movimiento (roca vs. lago). ' +
         'Los factores FA/FV vienen de tablas según la severidad.',
      r: 'COVENIN 1756:2019 · Tablas 8–9' },
    { k: 'topo', ancla: 's-topo',
      t: 'Topografía',
      f: 'Fat, Fvt, Fdt',
      p: 'Laderas y crestas concentran el movimiento (efecto ' +
         'topográfico); factores > 1 en terreno irregular.',
      r: 'COVENIN 1756:2019 · Tabla 11' },
    { k: 'o-sismo', ancla: 'o-sismo',
      t: '¿Incluir el sismo?',
      f: 'SH actúa en ± ambas direcciones',
      p: 'Si el pórtico resiste gravedad pero el modelo es de ' +
         'gravedad-only (p. ej. verificación previa), desactiva SH. El ' +
         'flujo normal es dejarlo activo.',
      r: 'COVENIN 1756:2019 · §8' },
    { k: 'o-sv', ancla: 'o-sv',
      t: 'Sismo vertical',
      f: 'SV = CSV · CP,  CSV = 2,3·AA·γmáx·E0',
      p: 'El sismo también agita verticalmente la masa. Va con signo ± y ' +
         'al 30% en las combinaciones (8.6–8.10) porque rara vez ' +
         'coincide el peor efecto vertical y horizontal.',
      r: 'COVENIN 1756:2019 · §8.3.1.4 (8.4–8.5)' },
    { k: 'o-omega', ancla: 'o-omega',
      t: 'Sobrerresistencia Ω₀·ρ',
      f: 'SH → (Ω₀ρ)·SH',
      p: 'Para verificar elementos frágiles (conexiones, columnas de ' +
         'filas críticas) el sismo se amplifica por Ω₀·ρ: el capítulo de ' +
         'acero pedirá esas combinaciones en su momento.',
      r: 'COVENIN 1756:2019 · (8.11–8.15)' },
    { k: 'o-gamma', ancla: 'o-gamma',
      t: 'γ de la carga variable',
      f: 'γ = 0,5 si CV < 500 kgf/m² · 1 en los demás casos',
      p: 'Con cargas variables livianas es improbable que estén ' +
         'completas justo durante el sismo → 50%. Salvo reunión pública ' +
         'o estacionamiento, que van a tope.',
      r: 'COVENIN 1756:2019 · §8.3.2.b' }
  ];

  /* ---------------- popover «¿por qué?» ---------------- */
  function cerrarPop() {
    if (pop && pop.parentNode) pop.parentNode.removeChild(pop);
    pop = null;
  }
  function abrirPop(item, ancla) {
    cerrarPop();
    pop = document.createElement('div');
    pop.className = 'popover-porque';
    var h = '<b>' + item.t + '</b>';
    if (item.f) h += '<div class="mem-f">' + item.f + '</div>';
    if (typeof item.s === 'string' && item.s) h += '<div class="mem-s">= ' + item.s + '</div>';
    if (item.p) h += '<p class="mem-pq">' + item.p + '</p>';
    if (item.r) h += '<span class="mem-fuente">' + item.r + '</span>';
    pop.innerHTML = h;
    document.body.appendChild(pop);
    var r = ancla.getBoundingClientRect();
    var top = (r.bottom + window.pageYOffset || 0) + 6;
    var left = Math.max(8, r.left + (window.pageXOffset || 0) - 40);
    pop.style.top = top + 'px';
    pop.style.left = left + 'px';
    setTimeout(function () {
      document.addEventListener('click', fuera, true);
      window.addEventListener('resize', cerrarPop);
    }, 0);
  }
  function fuera(e) {
    if (pop && !pop.contains(e.target)) { cerrarPop(); }
    if (!pop) {
      document.removeEventListener('click', fuera, true);
      window.removeEventListener('resize', cerrarPop);
    }
  }
  function boton(item, ancla) {
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'btn-porque';
    b.title = '¿Por qué? — ' + item.t;
    b.textContent = '¿?';
    b.addEventListener('click', function (ev) {
      ev.preventDefault(); ev.stopPropagation();
      if (pop) { cerrarPop(); return; }
      abrirPop(item, ancla);
    });
    return b;
  }
  function vincular() {
    CAT.forEach(function (item) {
      if (item.ancla) {
        var el = document.getElementById(item.ancla);
        if (el && el.parentNode) el.parentNode.insertBefore(boton(item, el), el.nextSibling);
      } else if (item.cls) {
        var todos = document.querySelectorAll('.' + item.cls);
        for (var i = 0; i < todos.length; i++) {
          var el2 = todos[i];
          if (el2.parentNode && !el2.nextSibling || !(el2.nextSibling && el2.nextSibling.className === 'btn-porque')) {
            el2.parentNode.insertBefore(boton(item, el2), el2.nextSibling);
          }
        }
      }
    });
  }

  /* ---------------- sección 0: cargas de la norma (JS) ---------------- */
  function sec0() {
    if (!ctx) return null;
    var acc = ctx.acc();
    var niveles = ctx.niveles() || [];
    if (!niveles.length) return null;
    var pasos = [];
    niveles.forEach(function (n) {
      var cfg = ctx.cfg(n.nombre);
      var r = ctx.cpCv(n, cfg);
      var losa = cfg.losa_cm / 100 * 2500;
      pasos.push({
        formula: 'CP = losa + acabado + tabiquería',
        sustitucion: n.nombre + ': ' + cfg.losa_cm + ' cm × 2500 kg/m³ = ' +
          fmtN(losa) + ' + ' + (+cfg.acabado || 0) + ' + ' + (+cfg.tabiq || 0) +
          ' = ' + fmtN(r.cp) + ' kg/m²',
        resultado: fmtN(r.cp) + ' kg/m²',
        fuente: 'COVENIN 2002-88 · §4.1 + Tabla 4.1 (concreto 2500) + §4.4',
        porque: 'Peso propio de la losa (espesor × densidad del concreto ' +
                'armado), acabados estimados y tabiquería equivalente ' +
                '(§4.4: si no está definida, 150 kg/m²).'
      });
      pasos.push({
        formula: n.es_techo ? 'CV techo (según cobertura y pendiente)'
                            : 'CV = valor de Tabla 5.1',
        sustitucion: n.nombre + ': ' + (r.fuente_cv || '') + ' → CV = ' +
          fmtN(r.cv) + ' kg/m²',
        resultado: fmtN(r.cv) + ' kg/m²',
        fuente: n.es_techo ? 'COVENIN 2002-88 · §5.2.4.2' : 'COVENIN 2002-88 · Tabla 5.1',
        porque: n.es_techo
          ? 'En techos la CV la define la cobertura y su pendiente (gente ' +
            'de mantenimiento, lluvia), no el uso del edificio.'
          : 'La carga variable depende del uso del ambiente elegido para ' +
            'ese nivel.'
      });
      if (+cfg.ancho > 0) {
        pasos.push({
          formula: 'q_viga = (CP + CV) · ancho tributario',
          sustitucion: n.nombre + ': (' + fmtN(r.cp) + ' + ' + fmtN(r.cv) +
            ') × ' + cfg.ancho + ' m = ' + fmtN((r.cp + r.cv) * cfg.ancho) + ' kg/m',
          resultado: fmtN((r.cp + r.cv) * cfg.ancho) + ' kg/m por viga',
          fuente: 'Reparto de losa',
          porque: 'La viga carga la franja de losa hasta la mitad de cada ' +
                  'vano vecino; el generador la aplica a las vigas del ' +
                  'pórtico activo.'
        });
      }
    });
    return { seccion: '0 · Cargas de la norma (COVENIN 2002-88)', pasos: pasos };
  }

  /* ---------------- render de la memoria ---------------- */
  function fmtN(x) {
    var t = (Math.round(x * 100) / 100).toFixed(2);
    t = t.replace(/0$/, '').replace(/\.$/, '').replace('.', ',');
    return t;
  }
  function pasoHTML(p) {
    var h = '<div class="mem-paso"><div class="mem-f">' + p.formula + '</div>';
    if (p.sustitucion) h += '<div class="mem-s">= ' + p.sustitucion + '</div>';
    if (p.resultado) h += '<div class="mem-r">→ ' + p.resultado + '</div>';
    if (p.fuente) h += '<span class="mem-fuente">' + p.fuente + '</span>';
    if (p.porque) h += '<p class="mem-pq">' + p.porque + '</p>';
    return h + '</div>';
  }
  function render() {
    var div = document.getElementById('memoria-cuerpo');
    if (!div) return;
    if (!SECCIONES.length) {
      div.innerHTML = '<div class="mini">Pulsa «⚡ Calcular combinaciones» y aquí ' +
        'queda la memoria paso a paso: cada valor con su fórmula, los números ' +
        'sustituidos, la referencia de la norma y el porqué.</div>';
      return;
    }
    div.innerHTML = SECCIONES.map(function (sec, i) {
      return '<div class="mem-sec"><button type="button" class="mem-sec-tit" data-sec="' + i + '">' +
        sec.seccion + ' (' + sec.pasos.length + ')</button>' +
        '<div class="mem-sec-cuerpo' + (i === 0 ? '' : ' oculto') + '">' +
        sec.pasos.map(pasoHTML).join('') + '</div></div>';
    }).join('');
    var btns = div.querySelectorAll('.mem-sec-tit');
    for (var i = 0; i < btns.length; i++) {
      btns[i].addEventListener('click', function () {
        var c = this.parentNode.querySelector('.mem-sec-cuerpo');
        if (c) c.classList.toggle('oculto');
      });
    }
  }
  function registrar(j) {
    J = j;
    var s0 = sec0();
    SECCIONES = (s0 ? [s0] : []).concat(j && j.memoria ? j.memoria : []);
    render();
  }
  function refrescarCargas() {
    if (!SECCIONES.length) { render(); return; }
    var s0 = sec0();
    SECCIONES = (s0 ? [s0] : []).concat(J && J.memoria ? J.memoria : []);
    render();
  }

  /* ---------------- impresión ---------------- */
  function imprimir() {
    if (!SECCIONES.length) return;
    var w = window.open('', '_blank');
    if (!w) { alert('Permite las ventanas emergentes para imprimir.'); return; }
    var cuerpo = SECCIONES.map(function (sec) {
      return '<h2>' + sec.seccion + '</h2>' + sec.pasos.map(function (p) {
        return pasoHTML(p);
      }).join('');
    }).join('');
    w.document.write('<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8">' +
      '<title>Memoria de cálculo</title><style>' +
      'body{font:13px system-ui,sans-serif;color:#0f172a;margin:24px;max-width:820px}' +
      'h1{font-size:19px} h2{font-size:15px;border-bottom:2px solid #2563eb;padding-bottom:3px;margin-top:22px}' +
      '.mem-paso{border-left:3px solid #2563eb;padding:6px 10px;margin:8px 0;background:#f8fafc;page-break-inside:avoid}' +
      '.mem-f{font-family:monospace;font-weight:700;font-size:13.5px}' +
      '.mem-s{font-family:monospace;color:#334155;font-size:12.5px;margin-top:2px}' +
      '.mem-r{font-weight:700;color:#1d4ed8;margin-top:2px}' +
      '.mem-fuente{display:inline-block;background:#dbeafe;color:#1e3a8a;font-size:11.5px;border-radius:4px;padding:1px 6px;font-weight:600;margin-top:4px}' +
      '.mem-pq{color:#475569;font-size:12.5px;margin:4px 0 0}' +
      '</style></head><body><h1>📘 Memoria de cálculo</h1>' +
      (document.getElementById('inp-titulo')
        ? '<p>' + document.getElementById('inp-titulo').value + '</p>' : '') +
      cuerpo +
      '<p style="margin-top:24px;color:#64748b;font-size:11.5px">Generado por el software — COVENIN 2002-88 · 1756:2019</p>' +
      '</body></html>');
    w.document.close();
    try { w.focus(); w.print(); } catch (e) { /* el usuario imprime a mano */ }
  }

  function init(c) {
    ctx = c;
    vincular();
    var b = document.getElementById('btn-imprimir-memoria');
    if (b) b.addEventListener('click', imprimir);
    render();
  }

  return { init: init, vincular: vincular, registrar: registrar,
           refrescarCargas: refrescarCargas };
})();
console.log('[UI] memoria v20260927h lista');
