import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import Polygon, FancyArrowPatch
import numpy as np

NAVY, GOLD, RED, SOFT = "#0F2A43", "#E8A020", "#B3202C", "#EAF1F8"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": NAVY,
                     "axes.edgecolor": NAVY, "figure.dpi": 200})

# ---------- Figura 1: Lente de Ghyben-Herzberg ----------
fig, ax = plt.subplots(figsize=(10.2, 6.4))

# Topografía (superficie del terreno), caída hacia la costa
xs = np.linspace(0, 6.5, 100)
surf = 2.4 * (1 - (xs / 6.5) ** 1.6) + 0.12
ax.plot(xs, surf, color=NAVY, lw=2.2)
ax.text(0.25, 2.62, "Superficie del terreno (planicie aluvial de Brión)", fontsize=8.5)

# Mar: superficie en y=0
ax.fill_between([6.5, 10], -6, 0, color="#9CC4E4", alpha=0.85)
ax.plot([6.5, 10], [0, 0], color=NAVY, lw=2.2)
ax.text(9.85, 0.28, "Nivel del mar", fontsize=8.5, ha="right")
ax.text(9.8, -0.7, "AGUA\nSALADA", fontsize=10, ha="center", color=NAVY, fontweight="bold")

# Nivel freático (h sobre el nivel del mar), desciende hacia la costa
wt_left = 1.35
xs_w = np.linspace(0, 6.5, 100)
wt = wt_left * (1 - (xs_w / 6.5) ** 1.35) + 0.02
ax.plot(xs_w, wt, color=GOLD, lw=2.4, ls="--")
ax.text(2.15, 1.62, "Nivel freático (h)", fontsize=9, color="#8a5a00", fontweight="bold")

# Interfaz agua dulce-salada (z = 40 h)  -> hipérbola que toca el mar
xs_i = np.linspace(0.02, 6.5, 300)
z = 40 * wt_left * (1 - (xs_i / 6.5) ** 1.35)
z = np.minimum(z, 5.6)
yi = -z
ax.plot(xs_i, yi, color=RED, lw=2.6)
ax.fill_between(xs_i, yi, -6, color=RED, alpha=0.16)
ax.text(3.05, -4.35, "CUÑA DE INTRUSIÓN SALINA", fontsize=10, color=RED, fontweight="bold", ha="center")

# Lente de agua dulce
ax.fill_between(xs_w, np.interp(xs_w, xs, surf), np.interp(xs_w, xs_i, yi), color="#2E6FA8", alpha=0.28)
ax.text(2.0, 0.42, "LENTE DE\nAGUA DULCE", fontsize=9, color=NAVY, fontweight="bold", ha="center")

# Zona de mezcla
ix, iy = 5.15, np.interp(5.15, xs_i, yi)
ax.fill_between([ix-0.55, ix+0.55], iy-0.55, iy+0.55, color=GOLD, alpha=0.35, zorder=1)
ax.text(ix+0.75, iy-1.15, "Zona de mezcla\n(interfaz difusa)", fontsize=8, color="#8a5a00")

# Flecha de recarga
for xr, yr in [(0.7, 3.4), (1.6, 3.15), (2.5, 2.9)]:
    ax.annotate("", xy=(xr, np.interp(xr, xs, surf) + 0.08), xytext=(xr, yr + 0.55),
                arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=2))
ax.text(1.6, 4.15, "Recarga por precipitación", fontsize=9, ha="center", color="#8a5a00", fontweight="bold")

# Pozo de bombeo + cono de depresión
xw = 4.2
wt_at = np.interp(xw, xs_w, wt)
ax.plot([xw, xw], [np.interp(xw, xs, surf) + 0.55, -3.4], color=NAVY, lw=3)
ax.add_patch(plt.Circle((xw, np.interp(xw, xs, surf) + 0.62), 0.10, color=NAVY))
# cono
cone_x = np.linspace(xw - 1.0, xw + 1.0, 60)
cone = wt_at - 0.55 * np.exp(-((cone_x - xw) / 0.42) ** 2)
ax.plot(cone_x, cone, color=RED, lw=2, ls=":")
ax.annotate("Cono de depresión\n(bombeo turístico)", xy=(xw, wt_at - 0.52), xytext=(xw + 1.35, wt_at + 1.15),
            fontsize=8, color=RED, arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.6))

# Flecha descarga al mar
ax.annotate("", xy=(6.75, -1.1), xytext=(5.6, -1.5),
            arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.8))
ax.text(5.15, -2.25, "Descarga subterránea al mar", fontsize=8)

# Fórmula
ax.text(0.15, -5.55, "Equilibrio de Ghyben–Herzberg:   z = (ρf / (ρs − ρf)) · h ≈ 40 · h",
        fontsize=9.5, style="italic", color=NAVY,
        bbox=dict(boxstyle="round,pad=0.45", fc=SOFT, ec=NAVY, lw=1.2))

ax.set_xlim(0, 10); ax.set_ylim(-6, 4.6)
ax.set_xticks([]); ax.set_yticks([])
for s in ["left", "right", "top", "bottom"]: ax.spines[s].set_visible(False)
ax.set_title("Modelo conceptual del equilibrio hidrostático en un acuífero costero", fontsize=11, fontweight="bold", color=NAVY, pad=10)
plt.tight_layout()
plt.savefig("/home/user/ingenieria/informes/tema4-caso3-brion/fig1_ghyben_herzberg.png", bbox_inches="tight")
plt.close()

# ---------- Figura 2: CE por sitio (datos Silva et al., 2014) ----------
sites = ["OCP1","OCP2","OCP3","OCP4","OCP5","SVP6","SVP7","SVP8","SVM1","SVP9","OCP10","OCP11"]
ce    = [1540,1075,1162,1885,804,370,999,976,804,442,1413,1240]
fig, ax = plt.subplots(figsize=(10.2, 4.6))
colors = [GOLD if v < 1000 else ("#D07B2A" if v < 1500 else RED) for v in ce]
bars = ax.bar(sites, ce, color=colors, edgecolor=NAVY, linewidth=1.1)
ax.axhline(1000, color=NAVY, ls="--", lw=1.2, alpha=0.7)
ax.text(11.45, 1035, "1 000 µS/cm", fontsize=7.5, color=NAVY, ha="right")
for b, v in zip(bars, ce):
    ax.text(b.get_x() + b.get_width()/2, v + 28, str(v), ha="center", fontsize=8, color=NAVY, fontweight="bold")
ax.set_ylabel("Conductividad eléctrica (µS/cm)")
ax.set_ylim(0, 2150)
ax.set_title("Conductividad eléctrica en pozos, aljibes y manantial inventariados\n(parroquia Higuerote, Municipio Brión — muestreo preliminar 2013–2014)",
             fontsize=9.5, fontweight="bold", color=NAVY)
ax.spines[["top","right"]].set_visible(False)
plt.tight_layout()
plt.savefig("/home/user/ingenieria/informes/tema4-caso3-brion/fig2_conductividad.png", bbox_inches="tight")
plt.close()
print("figures done")
