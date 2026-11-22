# -*- coding: utf-8 -*-
"""Figuras esquematicas para el Informe Caso 5 - Municipio Paez (El Guapo)."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.path import Path
import numpy as np

TEAL   = "#0E4D64"
TEAL2  = "#1D6E8C"
WATER  = "#2A9D8F"
SAND   = "#E76F51"
GOLD   = "#C9A227"
GRAY   = "#5B6770"
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.edgecolor": GRAY, "axes.labelcolor": TEAL,
    "figure.dpi": 200, "savefig.bbox": "tight",
})

# ---------------------------------------------------------------- Figura 1
fig, ax = plt.subplots(figsize=(10.2, 5.6))
ax.set_xlim(0, 100); ax.set_ylim(0, 62); ax.axis("off")

# relieve: montaña -> cono -> terrazas -> llanura
xs = np.array([0, 8, 14, 20, 27, 35, 44, 55, 66, 78, 89, 100])
ys = np.array([58, 52, 44, 38, 31.5, 25, 19, 14.5, 11, 8.5, 7, 6])
xg = np.linspace(0, 100, 400)
yg = np.interp(xg, xs, ys)
ax.fill_between(xg, 0, yg, color="#F3EDE2", zorder=0)
ax.plot(xg, yg, color=TEAL, lw=2.2, zorder=5)

# basamento / roca de base
xb = np.array([0, 20, 40, 100]); yb = np.array([26, 18, 6, 1.5])
ax.plot(np.linspace(0,100,300), np.interp(np.linspace(0,100,300), xb, yb),
        color=GRAY, lw=1.6, ls="--", alpha=0.9)
ax.text(3, 33.5, "Basamento\nrocoso", fontsize=8, color=GRAY, style="italic")

# nivel freatico
xn = np.array([16, 30, 45, 62, 80, 100]); yn = np.array([36.5, 28.5, 17.5, 12.3, 6.4, 3.4])
ax.plot(np.linspace(16,100,300), np.interp(np.linspace(16,100,300), xn, yn),
        color=WATER, lw=2.0, ls="-.")
ax.text(93.5, 5.0, "NAF", fontsize=8, color=WATER, fontweight="bold")

# rio (de la montaña a la llanura)
ax.plot([2,12,22,33],[57.5,46.5,36.5,27.5], color=WATER, lw=3.2, alpha=.85)
ax.text(4.5, 54.6, "Río Guapo", color=WATER, fontsize=8.5, fontweight="bold", rotation=-38)

# zona saturada (abajo del NAF arriba del basamento, aprox.)
yg_clip = np.interp(np.linspace(16,100,300), xg, yg)
yw = np.interp(np.linspace(16,100,300), xn, yn)
ax.fill_between(np.linspace(16,100,300), 0, yw, color=WATER, alpha=0.16, zorder=1)

# pozo
px = 84
gy = np.interp(px, xg, yg)
ax.plot([px, px], [gy, 2.2], color=TEAL, lw=5, solid_capstyle="butt", zorder=6)
ax.plot([px, px], [gy, gy-9], color="white", lw=2.4, zorder=7)
ax.text(px-1.5, gy+1.2, "Pozo\ncaptación", fontsize=8, color=TEAL, fontweight="bold", ha="right")
ax.annotate("", xy=(px, 2.6), xytext=(px, gy-12),
            arrowprops=dict(arrowstyle="-|>", color=SAND, lw=1.8))

# flechas de recarga (lluvia e infiltracion)
for rx, ry in [(30, 34), (45, 24), (60, 19)]:
    ax.annotate("", xy=(rx, ry-4.5), xytext=(rx, ry+3.5),
                arrowprops=dict(arrowstyle="-|>", color=TEAL2, lw=1.6))
ax.text(27.5, 37.5, "Lluvia e infiltración\n(recarga directa)", fontsize=8, color=TEAL2)

# flujo subterraneo
for fx in (38, 55, 70):
    ax.annotate("", xy=(fx+9, 8 if fx<60 else 5), xytext=(fx, 10 if fx<60 else 6.6),
                arrowprops=dict(arrowstyle="-|>", color=WATER, lw=1.6))
ax.text(44, 3.4, "Flujo del acuífero de piedemonte →", fontsize=8, color=WATER, fontweight="bold")

# etiquetas de zonas
for zx, zy, lab in [(10, 43.5, "SERRANÍA\nDEL INTERIOR\n(~1.000 msnm)"),
                    (29, 26.5, "Apical\ncantos rodados\n(recarga)"),
                    (49, 15.5, "Media\ngravas y arenas"),
                    (68, 9.6, "Distal / terrazas\narenas finas–limos"),
                    (90.5, 1.2, "Llanura de Barlovento")]:
    ax.text(zx, zy, lab, fontsize=7.6, color=TEAL, ha="center",
            fontweight="bold" if zx<25 else "normal",
            bbox=dict(boxstyle="round,pad=0.28", fc="white", ec=TEAL2, lw=0.7, alpha=0.9))
ax.set_title("Perfil hidrogeológico esquemático: transición montaña → planicie (piedemonte de El Guapo)",
             color=TEAL, fontsize=9.5, fontweight="bold", pad=10)
fig.savefig("/home/user/ingenieria/OBRAS-HIDRAULICAS/figs/fig1_perfil_abanico.png")
plt.close(fig)

# ---------------------------------------------------------------- Figura 2
meses = ["Ene","Feb","Mar","Abr","May","Jun","Jul","Ago","Sep","Oct","Nov","Dic"]
rel    = [7.2, 3.6, 3.1, 3.4, 5.4, 8.1, 9.7, 9.0, 6.9, 7.4, 8.6, 8.1]
colors = [SAND if m in("Jun","Jul","Ago") else (WATER if m in("Nov","Dic","Ene") else "#B9CBD3") for m in meses]
fig, ax = plt.subplots(figsize=(9.6, 4.6))
bars = ax.bar(meses, rel, color=colors, edgecolor=TEAL, linewidth=0.7)
ax.set_ylabel("Índice pluviométrico relativo (sin escala)")
ax.set_xlabel("Mes del año")
ax.set_title("Régimen de doble máxima — sub-tipo Tapipa–El Guapo (referencia esquemática)",
             color=TEAL, fontweight="bold", fontsize=10)
ax.spines[["top","right"]].set_visible(False)
ax.grid(axis="y", ls=":", alpha=.5)
handles = [mpatches.Patch(color=SAND, label="Máxima principal (jun–ago)"),
           mpatches.Patch(color=WATER, label="Máxima secundaria (nov–ene)"),
           mpatches.Patch(color="#B9CBD3", label="Meses de transición")]
ax.legend(handles=handles, loc="upper center", frameon=False, ncols=3, fontsize=8)
ax.set_ylim(0, 11)
fig.savefig("/home/user/ingenieria/OBRAS-HIDRAULICAS/figs/fig2_regimen_pluvial.png")
plt.close(fig)

# ---------------------------------------------------------------- Figura 3
fig, ax = plt.subplots(figsize=(8.6, 4.8))
ab = np.array([1, 1.6, 2.6, 4, 6.3, 10, 16, 25, 40, 63, 100, 160, 250, 400])
# curva tipo H (resistividad aparente decreciente): gravas secas sobre gravas saturadas sobre basamento
rho = 14 + 95*np.exp(-ab/2.2) + 0.028*ab**1.55
ax.loglog(ab, rho, "o-", color=TEAL, ms=6, lw=1.8, mfc=GOLD, mec=TEAL)
ax.set_xlabel("AB/2 — semi-apertura de electrodos de corriente (m)")
ax.set_ylabel("Resistividad aparente ρa (Ω·m)")
ax.set_title("Curva SEV tipo H (esquemática): capa superficial resistiva sobre acuífero de baja resistividad",
             color=TEAL, fontweight="bold", fontsize=9)
ax.grid(True, which="both", ls=":", alpha=.45)
ax.spines[["top","right"]].set_visible(False)
for xpos, note in [(1.35, "Gravas secas\n(alta ρa)"), (9, "Gravas y arenas\nsaturadas (baja ρa)"), (260, "Basamento\n(ρa creciente)")]:
    ax.annotate(note, xy=(xpos, np.interp(np.log(xpos), np.log(ab), rho)),
                xytext=(xpos*1.05, {1.35:95, 9:26, 260:120}[xpos]),
                fontsize=8, color=GRAY,
                arrowprops=dict(arrowstyle="-", color=GRAY, lw=.9))
fig.savefig("/home/user/ingenieria/OBRAS-HIDRAULICAS/figs/fig3_sev.png")
plt.close(fig)
print("figs ok")
