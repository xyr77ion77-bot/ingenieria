/* ================================================================
   verificaciones.js — Verificación de miembros y P-Δ
   ---------------------------------------------------------------
   *** FASE 4 — PENDIENTE DE IMPLEMENTAR ***

   Plan de portado (corrigiendo los bugs detectados en la auditoría):

   · verificarViga(perfil, Mu, Vu, Fy)          [LRFD]
       Mu/Mp con Zx, corte φVn = 0.9·0.6·Fy·Aw… con verificación de
       alma compacta (⚠️ NO usar φVn = 0.9·0.6Fy·A/2: sobreestima
       ~26 % en perfiles IPE según la auditoría).
   · verificarColumna(perfil, Pu, Mux, Muy, L, E, Fy)
       ⚠️ Corrección obligatoria: controlar pandeo con el radio de
       giro DEL EJE QUE GOBIERNA (min(Rx, Ry) según el arriostramiento
       real de extremos y de alma/ala), no con el radio del eje fuerte
       como hacía la calculadora de referencia (+7.7 % a +52 % de φPn).
       Interacción AISC H1: Pu/φPn + 8/9·(Mux/φMnx + Muy/φMny).
   · verificarSoldaduraAISC(...)  [AISC 14ª — ya validado en la
       referencia: 1.392/0.928·D·l, J2-5, J2.4]
   · combinaciones (COVENIN 1756-1:2019 §8.3):
       U = 1.2·CP + γ·CV ± S        (8.9)
       U = 0.9·CP ± S               (8.10)
       γ = 0.5 si CV < 500 kg/m² (salvo reunión pública/estacionamiento),
       γ = 1.0 en los demás casos. S = √(Sx²+Sy²+Sv²) (8.8) o método
       del 30 %: SH → 0.3(SX ± SY), SV → SV.
       ⚠️ NO usar "1.2D+1.6L+E" sin los coeficientes de la norma.
   · calcPDelta(p, s, der)
       θ según fórmulas 8.16–8.17, límite θmáx = 0.625/R (R = 6 →
       0.104). NO portar el umbral 0.20 ni la deriva inelástica de la
       referencia.

   API prevista:
     VERIF.verificarTodo(p, s, muto)  → {vigas[], columnas[], pdelta}
   ================================================================ */

const VERIF = (function () {
  'use strict';

  function verificarTodo() {
    /* TODO Fase 4: portar verificaciones LRFD/ASD corregidas según
       las notas de auditoría de este encabezado. */
    console.info('VERIF.verificarTodo(): Fase 4 pendiente.');
    return null;
  }

  return { verificarTodo };
})();
