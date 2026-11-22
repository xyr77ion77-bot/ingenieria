import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

NAVY, GOLD, RED, SOFT = "#0F2A43", "#E8A020", "#B3202C", "#EAF1F8"
plt.rcParams.update({"font.family": "DejaVu Sans", "text.color": NAVY, "figure.dpi": 200})

fig, ax = plt.subplots(figsize=(10.4, 6.2))

# --- Topografía: de elevada (interior, x=0) a nivel del mar (costa, x=6.5) ---
xs = np.linspace(0, 6.5, 200)
surf = 2.3 * (1 - (xs / 6.5) ** 1.7) + 0.10
ax.plot(xs, surf, color=NAVY, lw=2.4)

# --- Nivel del mar (y=0) ---
ax.fill_between([6.5, 10], -6, 0, color="#9CC4E4", alpha=0.9)
ax.plot([6.5, 10], [0, 0], color=NAVY, lw=2.4)
ax.text(9.85, 0.32, "Nivel del mar", fontsize=9, ha="right", color=NAVY)
ax.text(8.25, -0.85, "AGUA\nSALADA", fontsize=11, ha="center", color=NAVY, fontweight="bold")

# --- Nivel freático (h sobre el nivel del mar) ---
h = np.linspace(0, 1.35, 200)
# h(x) decreciente de izquierda (interior) a derecha (costa)
wt = 1.35 * (1 - (xs / 6.5) ** 1.35) + 0.02
ax.plot(xs, wt, color=GOLD, lw=2.4, ls="--")
ax.text(0.45, 1.62, "Nivel freático (h sobre el nivel del mar)", fontsize=9, color="#8a5a00", fontweight="bold")

# --- Interfaz agua dulce–salada: z = 40·h (más profunda tierra adentro) ---
yi = -np.minimum(40 * wt, 5.5)
ax.plot(xs, yi, color=RED, lw=2.6)
ax.fill_between(xs, yi, -6, color=RED, alpha=0.16)
ax.fill_between([6.5, 10], 0, -6, color=RED, alpha=0.10)
ax.text(3.35, -2.9, "CUÑA DE\nINTRUSIÓN SALINA", fontsize=10.5, color=RED,
        fontweight="bold", ha="center")
ax.text(0.18, -5.0, "(el pie de la cuña se extiende tierra adentro según la recarga y el bombeo)",
        fontsize=7, color=RED, style="italic")

# --- Lente de agua dulce (entre superficie y la interfaz) ---
ax.fill_between(xs, surf, yi, color="#2E6FA8", alpha=0.25)
ax.text(1.35, 0.28, "LENTE DE\nAGUA DULCE", fontsize=9.5, color=NAVY, fontweight="bold", ha="center")

# --- Zona de mezcla a lo largo de la interfaz ---
im = xs[np.argmin(np.abs(yi + 2.6))]
ym = -min(40 * np.interp(im, xs, wt), 5.5)
ax.plot([im], [ym], marker="o", ms=9, color=GOLD, mec="#8a5a00", zorder=6)
ax.annotate("Zona de mezcla\n(interfaz difusa)", xy=(im, ym), xytext=(4.35, -4.7),
            fontsize=8.5, color="#8a5a00", fontweight="bold",
            arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=1.8))

# --- Flechas de recarga ---
for xr in (0.55, 1.35, 2.15):
    ax.annotate("", xy=(xr, np.interp(xr, xs, surf) + 0.05), xytext=(xr, np.interp(xr, xs, surf) + 1.05),
                arrowprops=dict(arrowstyle="-|>", color=GOLD, lw=2.2))
ax.text(1.35, 3.62, "Recarga por precipitación", fontsize=9.5, ha="center", color="#8a5a00", fontweight="bold")
ax.text(0.3, 2.62, "Planicie aluvial de Brión", fontsize=8.5, color=NAVY)

# --- Pozo de bombeo con cono de depresión ---
xw = 3.6
surf_w = np.interp(xw, xs, surf)
wt_w = np.interp(xw, xs, wt)
ax.plot([xw, xw], [surf_w + 0.62, -3.1], color=NAVY, lw=3.2)
ax.add_patch(plt.Circle((xw, surf_w + 0.7), 0.11, color=NAVY, zorder=5))
cone_x = np.linspace(xw - 1.05, xw + 1.05, 80)
cone = wt_w - 0.5 * np.exp(-((cone_x - xw) / 0.45) ** 2)
ax.plot(cone_x, cone, color=RED, lw=2, ls=":")
ax.annotate("Cono de depresión\n(abatimiento por bombeo)", xy=(xw, wt_w - 0.48), xytext=(xw + 1.5, wt_w + 1.35),
            fontsize=8.5, color=RED, arrowprops=dict(arrowstyle="-|>", color=RED, lw=1.6))

# --- Descarga subterránea al mar ---
ax.annotate("", xy=(6.85, -0.55), xytext=(5.75, -1.15),
            arrowprops=dict(arrowstyle="-|>", color=NAVY, lw=1.8))
ax.text(5.62, -1.45, "Descarga subterránea\nal mar", fontsize=8.5, ha="right")

# --- Fórmula ---
ax.text(0.15, -5.62, "Ghyben–Herzberg:   z = (ρf / (ρs − ρf)) · h ≈ 40 · h",
        fontsize=9.5, style="italic", color=NAVY,
        bbox=dict(boxstyle="round,pad=0.4", fc=SOFT, ec=NAVY, lw=1.2))

ax.set_xlim(0, 10); ax.set_ylim(-6, 4.35)
ax.set_xticks([]); ax.set_yticks([])
for s in ax.spines.values(): s.set_visible(False)
ax.set_title("Modelo conceptual del equilibrio hidrostático en un acuífero costero (caso Higuerote)",
             fontsize=11, fontweight="bold", color=NAVY, pad=10)
plt.tight_layout()
plt.savefig("/home/user/ingenieria/informes/tema4-caso3-brion/fig1_ghyben_herzberg.png", bbox_inches="tight")
print("fig1 ok")
