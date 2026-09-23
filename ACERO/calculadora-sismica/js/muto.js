/* ================================================================
   muto.js — Análisis de pórticos por el método de Muto + torsión 6 %
   ---------------------------------------------------------------
   *** FASE 3 — PENDIENTE DE IMPLEMENTAR ***

   Aquí se portará (auditado y comentado) el bloque del motor de la
   calculadora de referencia, que en la verificación previa resultó
   correcto frente a la norma:

   · mutoPorFrame(p, s, dir)
       Rigideces D = 12E·Kc/h² (Kc = Ic/h) y D vigas = Σ(E·Ib/L);
       α borde/interior según relación ΣKv/ΣKc; factor de distribución
       de cortante por columna; punto de inflexión y del contraviento;
       momentos sup/inf de vigas y columnas.
   · derivas(p, s, muto, dir)
       η2019 = Cd·δe/h (Tabla 25 — límite B2 = 0.018 dúctil,
       0.022 no susceptible, 0.012 frágil según muros adosados),
       con δe = V_entrepiso / ΣD del pórtico crítico.
   · repartoPorPortico(p, s, mutoX, mutoY)
       Torsión adicional del 6 % de la dimensión perpendicular:
       ex = 0.06·B (B = dimensión perpendicular a la dirección del
       sismo), factor de amplificación por torsión y reparto del
       cortante de entrepiso entre pórticos proporcional a D·di.
   · calcPDelta (FASE 4, corregido)
       θ = Cd·δ/(h·?) comparado con θmáx = 0.625/R (fórmulas 8.16–8.17).
       ⚠️ NO portar el bug de la referencia (usaba deriva inelástica
       ×Cd y umbral 0.20).

   API prevista (app.js ya está preparado para no llamarla hasta Fase 3):
     MUTO.calcularTodo(p, s)  → {mutoX, mutoY, derX, derY, rep}
   ================================================================ */

const MUTO = (function () {
  'use strict';

  function calcularTodo() {
    /* TODO Fase 3: portar mutoPorFrame / derivas / repartoPorPortico /
       torsión 6 % desde el motor auditado, con los comentarios de
       verificación correspondientes. */
    console.info('MUTO.calcularTodo(): Fase 3 pendiente.');
    return null;
  }

  return { calcularTodo };
})();
