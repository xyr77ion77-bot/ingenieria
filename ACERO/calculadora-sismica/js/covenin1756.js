/* ================================================================
   covenin1756.js — Motor sísmico COVENIN 1756-1:2019
   ---------------------------------------------------------------
   FASE 1–2 (funciones puras, SIN DOM).
   Implementación portada del motor auditado en la sesión anterior:
   se verificó numéricamente contra la norma que
   · espectro inelástico Ad(T)  → replica fórmulas 7.18–7.23
   · μ                          → fórmula 9.4
   · V0 = C·W, Cdin vs Cmin     → ecuación 9.1 y §9.2.2
   · Ta = Ct·hn^0.75 (acero)    → §9.4.3.3 + Tabla 24 (Ct = 0.08)
   · Ft = (0.06·T/TC − 0.02)·V0d, acotada [0.04, 0.10]·V0d → fórmula 9.10
   · σ (Tabla 23): 1.7 / 1.55 / 1.4 según AA
   · q (Tabla 17), factores de sitio (Tablas 8–13),
     α (Tabla 14), R/Cd por ND (Tabla 15), fracciones CV (Tabla 20).
   BUGS CONOCIDOS QUE NO ESTÁN AQUÍ (corregidos o diferidos):
   · verificarColumna con radio del eje fuerte → FASE 4 (no portar ese bug)
   · P-Δ con deriva inelástica y umbral 0.20   → FASE 4 (usar θ ≤ 0.625/R)
   ================================================================ */

const COVENIN = (function () {
  'use strict';

  /* ---------------- Tablas normativas ---------------- */

  const CLASES = ['A', 'AB', 'B', 'BC', 'C', 'CD', 'D', 'DE', 'E'];
  const AXS = [0.01, 0.05, 0.1, 0.2, 0.3, 0.4, 0.5];   // eje de A0/A1

  /* Tabla 8 — Factor de sitio FA (fijo) vs A0·α */
  const TAB8 = {
    'A':  [0.80, 0.80, 0.80, 0.80, 0.80, 0.80, 0.80],
    'AB': [0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85],
    'B':  [0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 0.90],
    'BC': [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
    'C':  [1.30, 1.30, 1.25, 1.25, 1.20, 1.20, 1.15],
    'CD': [1.60, 1.50, 1.45, 1.35, 1.25, 1.20, 1.15],
    'D':  [1.90, 1.75, 1.60, 1.40, 1.25, 1.15, 1.00],
    'DE': [2.40, 2.05, 1.75, 1.35, 1.10, 0.95, 0.80],
    'E':  [2.70, 2.20, 1.85, 1.35, 1.00, 0.85, 0.70]
  };

  /* Tabla 9 — Factor de sitio FV (flexible) vs A1·α */
  const TAB9 = {
    'A':  [0.80, 0.80, 0.80, 0.80, 0.80, 0.80, 0.80],
    'AB': [0.85, 0.85, 0.85, 0.85, 0.85, 0.85, 0.85],
    'B':  [0.90, 0.90, 0.90, 0.90, 0.90, 0.90, 0.90],
    'BC': [1.00, 1.00, 1.00, 1.00, 1.00, 1.00, 1.00],
    'C':  [1.40, 1.40, 1.40, 1.40, 1.40, 1.40, 1.40],
    'CD': [1.80, 1.75, 1.75, 1.70, 1.70, 1.65, 1.65],
    'D':  [2.30, 2.20, 2.10, 2.00, 1.95, 1.90, 1.85],
    'DE': [3.30, 3.00, 2.70, 2.50, 2.30, 2.15, 2.00],
    'E':  [4.00, 3.30, 3.00, 2.70, 2.45, 2.30, 2.15]
  };

  /* Tabla 10 — Factor de sitio FD (desplazamiento) por clase */
  const TAB10 = { 'A': 0.85, 'AB': 0.90, 'B': 0.95, 'BC': 1.00, 'C': 1.20, 'CD': 1.40, 'D': 1.70, 'DE': 2.25, 'E': 2.65 };

  /* Tabla 11 — Factores topográficos [FAT, FVT, FDT] */
  const TAB11 = { leve: [1.00, 1.00, 1.00], mod: [1.20, 1.10, 1.05], sev: [1.40, 1.20, 1.10] };

  /* Tablas 12–13 — Factores de altura (H en m) FAH, FVH, FDH */
  const TAB12H = [0, 10, 30, 60, 100, 200, 300, 500, 750, 1000];
  const TAB12 = {
    FAH: [1.00, 1.00, 1.00, 1.00, 1.01, 1.02, 1.03, 1.05, 1.07, 1.10],
    FVH: [0.98, 1.00, 1.00, 1.02, 1.05, 1.08, 1.10, 1.20, 1.30, 1.40],
    FDH: [0.93, 0.96, 1.00, 1.05, 1.10, 1.20, 1.30, 1.60, 2.10, 2.80]
  };

  /* Tabla 17 — Exponente q de la rama TD < T */
  const TABQ = { 'A': 1.5, 'AB': 1.5, 'B': 1.5, 'BC': 1.7, 'C': 1.7, 'CD': 1.9, 'D': 1.9, 'DE': 2.0, 'E': 2.0 };

  /* Tabla 14 — Factor de importancia de uso α */
  const ALFA = { A1: 2.0, A2: 1.5, B1: 1.2, B2: 1.0, C: 0.7 };

  /* Tabla 15 — Pórticos de acero (Resistentes a Momento) */
  const R_ACERO = { ND3: 6, ND2: 3.5, ND1: 2.5 };
  const CD_ACERO = { ND3: 4.25, ND2: 3.25, ND1: 2.25 };
  const OMEGA_ACERO = { ND3: 3, ND2: 2.5, ND1: 2 };

  /* Tabla 20 — Fracción de la carga variable CV a incluir en el peso sísmico */
  const FRACC_CV = {
    vivienda: 0.15, oficina: 0.25, comercio: 0.25, agrupacion: 0.50,
    estacionamiento: 0.50, almacen: 0.80, recipientes: 1.00, ascensor: 1.00, techo: 0.00
  };

  /* ---------------- Interpoladores ---------------- */

  function interp(aX, clase, TABLA) {
    const arr = TABLA[clase];
    if (aX <= AXS[0]) return arr[0];
    if (aX >= AXS[AXS.length - 1]) return arr[AXS.length - 1];
    let i = 0;
    while (i < AXS.length - 2 && aX > AXS[i + 1]) i++;
    const t = (aX - AXS[i]) / (AXS[i + 1] - AXS[i]);
    return arr[i] + t * (arr[i + 1] - arr[i]);
  }

  function interpH(x, col) {
    const arr = TAB12[col];
    if (x <= TAB12H[0]) return arr[0];
    for (let i = 0; i < TAB12H.length - 1; i++) {
      if (x >= TAB12H[i] && x <= TAB12H[i + 1]) {
        const t = (x - TAB12H[i]) / (TAB12H[i + 1] - TAB12H[i]);
        return arr[i] + t * (arr[i + 1] - arr[i]);
      }
    }
    return arr[arr.length - 1];
  }

  /* ---------------- Peso sísmico (Tabla 20) ----------------
     W_i = área_i · (CP_i + frac·CV_i) + ppest · área_i
     frac según el uso del nivel (Tabla 20). Devuelve también el
     área usada por nivel (placeholder null → área de planta). */
  function pesosPorNivel(niveles, areaDefecto, ppest) {
    const areas = [], W = [], qs = [];
    for (const n of niveles) {
      const area = (n.area && n.area > 0) ? n.area : areaDefecto;
      const frac = FRACC_CV[n.uso] !== undefined ? FRACC_CV[n.uso] : 0.15;
      const qSis = (n.cp + frac * n.cv + ppest);      // kg/m² peso sísmico nivel
      areas.push(area);
      qs.push(qSis);
      W.push(area * qSis);
    }
    return { areas, qs, W };
  }

  /* ---------------- Área tributaria (para el inspector) ----------------
     Nodo (i = fila, j = columna). Medios vanos adyacentes; en los
     bordes el área NO se extiende hacia afuera del edificio
     (criterio de las referencias auditadas: esquina = ¼ de vano). */
  function areaTributaria(i, j, lx, ly) {
    const nx = lx.length, ny = ly.length;
    const axL = (j > 0 ? lx[j - 1] / 2 : 0);
    const axR = (j < nx ? lx[j] / 2 : 0);
    const ayT = (i > 0 ? ly[i - 1] / 2 : 0);
    const ayB = (i < ny ? ly[i] / 2 : 0);
    const Ax = axL + axR, Ay = ayT + ayB;
    let pos = 'central';
    if ((i === 0 || i === ny) && (j === 0 || j === nx)) pos = 'esquina';
    else if (i === 0 || i === ny || j === 0 || j === nx) pos = 'perimetral';
    return { Ax, Ay, At: Ax * Ay, pos };
  }

  /* ---------------- Espectro inelástico Ad(T) ----------------
     p: {A0, A1, TL, grupo, nd, sitio, topo, H, rho, FI, N, hsAbs[], W[]}
     Devuelve s con todos los parámetros intermedios (auditables). */
  function calcularSismo(p) {
    const R = R_ACERO[p.nd] || 6;
    const Cd = CD_ACERO[p.nd] || 4.25;
    const Omega = OMEGA_ACERO[p.nd] || 3;
    const alpha = ALFA[p.grupo] || 1.0;

    /* Factores de sitio (Tablas 8–13) */
    const aA0 = alpha * p.A0, aA1 = alpha * p.A1;
    const cl = p.sitio;
    const FAC = interp(aA0, cl, TAB8);
    const FVC = interp(aA1, cl, TAB9);
    const FDC = TAB10[cl];
    const [FAT, FVT, FDT] = TAB11[p.topo];
    const FAH = interpH(p.H, 'FAH'), FVH = interpH(p.H, 'FVH'), FDH = interpH(p.H, 'FDH');
    const FA = FAC * FAH * FAT, FV = FVC * FVH * FVT, FD = FDC * FDH * FDT;

    /* Aceleraciones de diseño (7.x) */
    const AA = FA * alpha * p.A0;
    const AV = FV * alpha * p.A1;

    /* Ramas del espectro (7.x): TA ≤ TB ≤ TC ≤ TD */
    const beta = 2.4;                       // β*
    const betaS = Math.max(beta, AV / AA);
    const TC = (1 / beta) * (AV / AA);
    const TB = 0.25 * TC;
    const TA = Math.min(0.05, Math.max(0.02, 0.2 * TB));
    const TD = p.TL * (FD / FV);
    const q = TABQ[cl];

    /* Período fundamental Ta (§9.4.3.3 + Tabla 24: acero Ct = 0.08)
       y límite σ·Ta (Tabla 23). Se calcula con T = Ta (criterio
       conservador; la regla 0.85·V0 de la norma no se activa). */
    const hn = p.hsAbs[p.N - 1];
    const Ta = 0.08 * Math.pow(hn, 0.75);
    const T = Ta;
    const sigma = AA <= 0.10 ? 1.7 : (AA <= 0.20 ? 1.55 : 1.4);
    const Tmax = sigma * Ta;

    /* Punto de quiebre T+ de la meseta elástica (fórmula 7.23) */
    let Tp = (R >= 5) ? 0.4 : 0.1 * ((R || 6) - 1);
    Tp = Math.min(TC, Math.max(0.25 * TC, Tp));

    /* Espectro inelástico de pseudoaceleraciones Ad(T) (7.18–7.23) */
    function Ad(Tx) {
      if (Tx <= TA) return p.rho * p.FI * AA / 1.5;
      if (Tx <= Tp) return p.rho * p.FI * (AA / 1.5) * (1 + ((Tx - TA) / (Tp - TA)) * ((betaS / R) / (1 / 1.5) - 1));
      if (Tx <= TC) return p.rho * p.FI * (betaS * AA) / R;
      if (Tx <= TD) return p.rho * p.FI * (betaS * AA / R) * (TC / Tx);
      return p.rho * p.FI * (betaS * AA / R) * (TC / TD) * Math.pow(TD / Tx, q);
    }

    const AdT = Ad(T);

    /* Coeficiente sísmico C = μ·Ad (9.3–9.4) */
    const mu1 = 1.4 * (p.N + 9) / (2 * p.N + 12);
    const mu2 = 0.80 + (1 / 20) * (T / TC - 1);
    const mu = Math.max(mu1, mu2);
    const C = mu * AdT;

    /* Coeficiente mínimo Cmin = AA/R (§9.2.2) y corte de diseño */
    const Cmin = AA / R;
    const Wtot = p.W.reduce((a, b) => a + b, 0);
    const V0 = C * Wtot;
    const escala = (C < Cmin) ? Cmin / C : 1;
    const V0d = V0 * escala;

    /* Fuerza de tope Ft (9.10): 4 % ≤ coef ≤ 10 % de V0d */
    const coefFt = Math.min(0.10, Math.max(0.04, 0.06 * T / TC - 0.02));
    const Ft = coefFt * V0d;
    const Veff = V0d - Ft;

    /* Distribución de fuerzas por nivel (9.11): Fi = k·Wi·hi */
    const Wh = p.W.map((w, i) => w * p.hsAbs[i]);
    const sumWh = Wh.reduce((a, b) => a + b, 0);
    const Fis = Wh.map(wh => Veff * wh / sumWh);
    const Vpisos = new Array(p.N).fill(0);          // cortante de entrepiso (i = 0 base)
    /* CORRECCIÓN vs. la calculadora de referencia: el cortante del
       entrepiso superior DEBE incluir Ft (aplicada como fuerza
       concentrada en el tope, 9.10): V_tope = Fi_N + Ft.
       La referencia acumulaba solo Fi y subestimaba el corte superior. */
    for (let i = p.N - 1; i >= 0; i--) {
      Vpisos[i] = (i === p.N - 1 ? Ft : Vpisos[i + 1]) + Fis[i];
    }
    const espesor = p.hsAbs.map((h, i) => (i === 0 ? h : h - p.hsAbs[i - 1]));

    return {
      R, Cd, Omega, alpha, aA0, aA1,
      FAC, FVC, FDC, FAH, FVH, FDH, FAT, FVT, FDT, FA, FV, FD,
      AA, AV, betaS, TA, TB, TC, TD, q,
      hn, Ta, T, Tmax, sigma, Tp,
      AdT, mu1, mu2, mu, C, Cmin, Wtot, V0, escala, V0d,
      coefFt, Ft, Veff, Wh, sumWh, Fis, Vpisos, espesor,
      Ad                                    // función expuesta (para el gráfico)
    };
  }

  /* Muestreo del espectro para el gráfico (no normativo, solo visual) */
  function espectroCurva(p, s, nPts) {
    const pts = [];
    const Tfin = Math.max(s.TD * 1.05, s.TC * 3);
    const n = nPts || 240;
    for (let k = 0; k <= n; k++) {
      const Tx = (Tfin * k) / n;
      pts.push({ T: Tx, Ad: s.Ad(Tx) });
    }
    return pts;
  }

  return {
    CLASES, TAB8, TAB9, TAB10, TAB11, TAB12H, TAB12, TABQ, ALFA,
    R_ACERO, CD_ACERO, OMEGA_ACERO, FRACC_CV,
    interp, interpH, pesosPorNivel, areaTributaria,
    calcularSismo, espectroCurva
  };
})();
