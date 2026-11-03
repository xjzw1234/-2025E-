"""Generate all paper figures from results/ CSVs.

Run after `python run_model.py --task all`:
    python make_figures.py
"""

from __future__ import annotations

import os
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

HERE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(HERE, "figures")
RES = os.path.join(HERE, "results")
os.makedirs(FIG, exist_ok=True)

SKILL_ROOT = r"C:\Users\ASUS\.claude\skills\math-modeling"
sys.path.insert(0, os.path.join(SKILL_ROOT, "tools", "figure", "scripts"))
from setup_style import setup_style  # noqa: E402
from export_figure import export_figure  # noqa: E402

setup_style(journal="nature", lang="en")

import model_core as mc  # noqa: E402

BLUE = "#0072B2"
ORANGE = "#E69F00"
GREEN = "#009E73"
RED = "#D55E00"
PURPLE = "#CC79A7"
SKY = "#56B4E9"
GREY = "#6B7280"


def save(fig, name, size=(7.2, 3.2)):
    path = os.path.join(FIG, name)
    export_figure(fig, path, formats=["svg", "png"], dpi=300, size_inches=size,
                  grayscale_preview=False, tight=False)
    plt.close(fig)
    print("saved", name)


def load(name):
    return pd.read_csv(os.path.join(RES, name))


def _gates(t, p):
    ta = p.Tbar + p.dT * np.cos(2 * np.pi * (t - p.tpeak) / 365.0)
    sig = lambda t0, t1: 1.0 / (1.0 + np.exp(-(t - t0) / p.tau_s)) * (
        1.0 - 1.0 / (1.0 + np.exp(-(t - t1) / p.tau_s))
    )
    return ta, sig(p.tp, p.th), sig(p.tfl1, p.tfl2), sig(p.ta1, p.ta2)


def fig_raw_q1(p):
    t = np.arange(0, 365)
    ta, sc, sfl, sact = _gates(t, p)
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    ax = axes[0]
    ax.plot(t, ta, color=RED, lw=1.4, label="Air temperature")
    ax.set_xlabel("Day of year")
    ax.set_ylabel("Temperature (°C)")
    ax.set_xlim(0, 365)
    ax2 = ax.twinx()
    ax2.plot(t, sc, color=BLUE, lw=1.2, ls="--", label="Crop window")
    ax2.plot(t, sfl, color=GREEN, lw=1.2, ls=":", label="Flowering window")
    ax2.set_ylabel("Phenology gate (–)")
    ax2.set_ylim(0, 1.05)
    ax.legend(loc="upper left", frameon=False, fontsize=7)
    ax2.legend(loc="lower left", frameon=False, fontsize=7)
    ax.set_title("Seasonal forcing", loc="left", fontsize=9)

    ts = load("q1_baseline_timeseries.csv")
    m = ts.t < 365
    ax = axes[1]
    ax.plot(ts.t[m], ts.XH[m], color=ORANGE, lw=1.2, label="Herbicide residue")
    ax.plot(ts.t[m], ts.XP[m], color=PURPLE, lw=1.2, label="Insecticide residue")
    ax.set_xlabel("Day of year")
    ax.set_ylabel("Residue (mg a.i. kg$^{-1}$)")
    ax.legend(frameon=False, fontsize=7)
    ax.set_title("Chemical forcing", loc="left", fontsize=9)
    save(fig, "raw_q1_forcing")


def fig_process_q1():
    ts = load("q1_baseline_timeseries.csv")
    m = ts.t < 730
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.4), sharex=True)
    axes[0].plot(ts.t[m], ts.C[m], color=GREEN, lw=1.2, label="Crop $C$")
    axes[0].plot(ts.t[m], ts.W[m], color=ORANGE, lw=1.0, label="Weeds $W$")
    axes[0].set_ylabel("Biomass (g C m$^{-2}$)")
    axes[0].legend(frameon=False, fontsize=7)
    axes[0].set_title("Producers", loc="left", fontsize=9)

    axes[1].plot(ts.t[m], ts.H[m], color=RED, lw=1.0, label="Pests $H$")
    axes[1].plot(ts.t[m], ts.A[m], color=BLUE, lw=1.0, label="Predators $A$")
    axes[1].set_xlabel("Day")
    axes[1].legend(frameon=False, fontsize=7)
    axes[1].set_title("Herbivores and natural enemies", loc="left", fontsize=8)

    axes[2].plot(ts.t[m], ts.B[m] * 100, color=PURPLE, lw=1.0, label="Bats $B$ ×100")
    axes[2].plot(ts.t[m], ts.P[m], color=SKY, lw=1.0, label="Pollinators $P$")
    axes[2].legend(frameon=False, fontsize=7)
    axes[2].set_title("Vertebrates and pollinators", loc="left", fontsize=8)
    for ax in axes:
        ax.set_xlim(0, 730)
    save(fig, "process_q1_timeseries")


def fig_result_q1():
    d = load("q1_chemical_gradient.csv")
    piv_y = d.pivot(index="uP", columns="uH", values="yield_grain")
    piv_h = d.pivot(index="uP", columns="uH", values="mean_H")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for ax, piv, title, cmap, fmt in [
        (axes[0], piv_y, "Grain yield (kg ha$^{-1}$)", "viridis", "{:.0f}"),
        (axes[1], piv_h, "Mean pest biomass (g C m$^{-2}$)", "magma_r", "{:.2f}"),
    ]:
        vmin, vmax = float(np.min(piv.values)), float(np.max(piv.values))
        norm = plt.Normalize(vmin, vmax)
        im = ax.pcolormesh(np.arange(piv.shape[1] + 1), np.arange(piv.shape[0] + 1),
                           piv.values, cmap=cmap, norm=norm, shading="flat")
        ax.set_xticks(np.arange(len(piv.columns)) + 0.5, [f"{v:.2f}" for v in piv.columns])
        ax.set_yticks(np.arange(len(piv.index)) + 0.5, [f"{v:.2f}" for v in piv.index])
        ax.set_xlabel("Herbicide intensity $u_H$")
        ax.set_ylabel("Insecticide intensity $u_P$")
        cmap_obj = plt.get_cmap(cmap)
        for i in range(piv.shape[0]):
            for j in range(piv.shape[1]):
                val = piv.values[i, j]
                rgb = cmap_obj(norm(val))[:3]
                lum = 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]
                ax.text(j + 0.5, i + 0.5, fmt.format(val), ha="center", va="center",
                        fontsize=7, color="black" if lum > 0.5 else "white")
        ax.set_title(title, loc="left", fontsize=8)
    save(fig, "result_q1_gradient")


def fig_result_q1_stability():
    d = load("q1_stability_floquet.csv")
    fig, ax = plt.subplots(figsize=(3.5, 2.6))
    x = np.arange(len(d))
    ax.bar(x, d.rho_f, color=[BLUE, ORANGE, GREEN], width=0.55)
    for xi, rho, tr in zip(x, d.rho_f, d.TR_days):
        ax.text(xi, rho + 0.004, f"$T_R$={tr:.0f} d", ha="center", fontsize=7)
    ax.set_xticks(x, ["Conventional", "No insecticide", "Herbicide removal"], fontsize=7)
    ax.set_ylabel("Floquet spectral radius ρf")
    ax.set_ylim(0, max(d.rho_f) * 1.45)
    ax.set_title("Seasonal-cycle stability", loc="left", fontsize=9)
    save(fig, "result_q1_stability", size=(3.6, 2.7))


def fig_raw_q2():
    d = load("q2_maturation.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    axes[0].plot(d.year, d.E, color=GREEN, marker="o", ms=3, lw=1.2)
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("Edge maturity $E$ (–)")
    axes[0].set_title("Habitat maturation", loc="left", fontsize=9)
    axes[1].plot(d.year, d.mean_D, color=ORANGE, marker="s", ms=3, lw=1.2, label="Earthworms $D$")
    axes[1].plot(d.year, d.mean_O * 1000, color=PURPLE, marker="^", ms=3, lw=1.2, label="Raptors $O$ ×1000")
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("Biomass (g C m$^{-2}$)")
    axes[1].legend(frameon=False, fontsize=7)
    axes[1].set_title("Returning species", loc="left", fontsize=9)
    save(fig, "raw_q2_returning_species")


def fig_process_q2():
    d = load("q2_maturity_lambda.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    axes[0].plot(d.year, d.dE, color=BLUE, marker="o", ms=3, lw=1.2)
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("$\\Delta E_y$ (per year)")
    axes[0].set_title("Maturation increment", loc="left", fontsize=9)
    axes[1].plot(d.year, d.Lambda_y, color=RED, marker="s", ms=3, lw=1.2)
    axes[1].axhline(0, color=GREY, lw=0.8, ls=":")
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("$\\Lambda_y$ (d$^{-1}$)")
    axes[1].set_title("Finite-time contraction", loc="left", fontsize=9)
    save(fig, "process_q2_contraction")


def fig_result_q2():
    d = load("q2_species_variants.csv")
    order = ["none", "earthworm", "raptor", "both"]
    d = d.set_index("variant").loc[order].reset_index()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6))
    x = np.arange(len(d))
    axes[0].bar(x, d.yield_grain, color=BLUE, width=0.55)
    axes[0].set_ylabel("Grain yield (kg ha$^{-1}$)")
    axes[0].set_title("Yield", loc="left", fontsize=9)
    axes[1].bar(x, d.mean_H, color=RED, width=0.55)
    axes[1].set_ylabel("Pest biomass (g C m$^{-2}$)")
    axes[1].set_title("Pest pressure", loc="left", fontsize=9)
    bars = axes[2].bar(x, d.SOM_final, color=GREEN, width=0.55)
    for b, v in zip(bars, d.SOM_final):
        axes[2].text(b.get_x() + b.get_width() / 2, v, f"{v:.0f}",
                     ha="center", va="bottom", fontsize=6.5)
    axes[2].set_ylim(1500, 1720)
    axes[2].set_ylabel("Soil organic carbon (g C m$^{-2}$)")
    axes[2].set_title("Soil carbon", loc="left", fontsize=9)
    for ax in axes:
        ax.set_xticks(x, ["None", "Earthworm", "Raptor", "Both"], fontsize=7, rotation=20)
    save(fig, "result_q2_species_effects")


def fig_result_q2_stability():
    d = load("q2_stability.csv")
    order = ["none", "earthworm", "raptor", "both"]
    d = d.set_index("variant").loc[order].reset_index()
    fig, ax = plt.subplots(figsize=(3.8, 2.7))
    x = np.arange(len(d))
    ax.bar(x, d.rho_f, color=[GREY, GREEN, ORANGE, BLUE], width=0.55)
    for xi, rho, tr in zip(x, d.rho_f, d.TR_days):
        ax.text(xi, rho + 0.004, f"$T_R$={tr:.0f} d", ha="center", fontsize=6.5)
    ax.set_xticks(x, ["None", "Earthworm", "Raptor", "Both"], fontsize=7)
    ax.set_ylabel("Floquet spectral radius ρf")
    ax.set_ylim(0, max(d.rho_f) * 1.35)
    ax.set_title("Stability after species return", loc="left", fontsize=9)
    save(fig, "result_q2_stability", size=(3.9, 2.8))


def fig_result_q4_components():
    d = load("q4_components.csv")
    base = d[d.variable == "baseline"].iloc[0]
    names = ["uH", "uP", "uF", "uM", "uE", "uB", "uorg"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    for ax, col, title in [(axes[0], "yield", "Yield"), (axes[1], "pest_biomass", "Pest biomass")]:
        vals_lo, vals_hi = [], []
        for nm in names:
            sub = d[d.variable == nm]
            lo = sub[sub.level == sub.level.min()][col].iloc[0]
            hi = sub[sub.level == sub.level.max()][col].iloc[0]
            vals_lo.append(lo / base[col] - 1.0)
            vals_hi.append(hi / base[col] - 1.0)
        y = np.arange(len(names))
        ax.barh(y - 0.18, vals_lo, height=0.34, color=SKY, label="set to 0")
        ax.barh(y + 0.18, vals_hi, height=0.34, color=RED, label="set to 1")
        ax.axvline(0, color=GREY, lw=0.8)
        ax.set_yticks(y, names, fontsize=7)
        ax.set_xlabel("Relative change from knee point")
        ax.set_title(title, loc="left", fontsize=8)
    axes[0].legend(frameon=False, fontsize=6.5)
    save(fig, "result_q4_components")


def fig_result_q1_sensitivity():
    d = load("q1_sensitivity.csv")
    params = d.parameter.unique().tolist()
    mag = {}
    for pname in params:
        sub = d[d.parameter == pname]
        mag[pname] = float(np.max(np.abs(sub.rel_yield)))
    params = sorted(params, key=lambda k: mag[k])
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.9))
    for ax, col, title in [(axes[0], "rel_yield", "Yield"), (axes[1], "rel_H", "Pest biomass")]:
        lo = [float(d[(d.parameter == p0) & (d.level == -1)][col].iloc[0]) for p0 in params]
        hi = [float(d[(d.parameter == p0) & (d.level == 1)][col].iloc[0]) for p0 in params]
        y = np.arange(len(params))
        ax.barh(y - 0.18, lo, height=0.34, color=SKY, label="-20%")
        ax.barh(y + 0.18, hi, height=0.34, color=RED, label="+20%")
        ax.axvline(0, color=GREY, lw=0.8)
        ax.set_yticks(y, params, fontsize=7)
        ax.set_xlabel("Relative change")
        ax.set_title(title, loc="left", fontsize=8)
    axes[0].legend(frameon=False, fontsize=6.5)
    save(fig, "result_q1_sensitivity")


def fig_raw_q3(p):
    ts = load("q3_herbicide_removal_timeseries.csv")
    t = ts.t.values
    u = np.where(t < 3 * 365, 1.0, np.clip(1.0 - (t / 365.0 - 3.0), 0, 1))
    fig, axes = plt.subplots(2, 1, figsize=(7.2, 3.2), sharex=True,
                             gridspec_kw={"height_ratios": [1, 1.4]})
    axes[0].plot(t / 365.0, u, color=ORANGE, lw=1.4)
    axes[0].set_ylabel("Herbicide intensity\nu_H(t) (-)")
    axes[0].set_ylim(-0.05, 1.1)
    axes[0].set_title("Herbicide withdrawal schedule and weed response", loc="left", fontsize=9)
    axes[1].plot(ts.t / 365.0, ts.W, color=GREEN, lw=1.0)
    axes[1].set_xlabel("Year")
    axes[1].set_ylabel("Weed biomass (g C m$^{-2}$)")
    save(fig, "raw_q3_withdrawal_schedule")


def fig_process_q3():
    ts = load("q3_herbicide_removal_timeseries.csv")
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.6))
    axes[0].plot(ts.t / 365.0, ts.C, color=GREEN, lw=1.2, label="Crop $C$")
    axes[0].plot(ts.t / 365.0, ts.W, color=ORANGE, lw=1.0, label="Weeds $W$")
    axes[0].axvline(3, color=GREY, ls=":", lw=1)
    axes[0].set_xlabel("Year")
    axes[0].set_ylabel("Biomass (g C m$^{-2}$)")
    axes[0].legend(frameon=False, fontsize=7)
    axes[0].set_title("Producers after withdrawal", loc="left", fontsize=9)
    axes[1].plot(ts.t / 365.0, ts.H, color=RED, lw=1.1, label="Pests $H$")
    axes[1].plot(ts.t / 365.0, ts.A, color=BLUE, lw=1.1, label="Predators $A$")
    axes[1].plot(ts.t / 365.0, ts.B * 100, color=PURPLE, lw=1.0, label="Bats $B$ ×100")
    axes[1].axvline(3, color=GREY, ls=":", lw=1)
    axes[1].set_xlabel("Year")
    axes[1].legend(frameon=False, fontsize=7)
    axes[1].set_title("Consumers after withdrawal", loc="left", fontsize=9)
    save(fig, "process_q3_withdrawal")


def fig_result_q3():
    d = load("q3_scenarios.csv")
    main = ["conventional", "herbicide_removal", "removal_no_bats", "removal_bats", "removal_parasitoid"]
    d = d[d.scenario.isin(main)].copy()
    conv = d[d.scenario == "conventional"].iloc[0]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 2.8))
    x = np.arange(len(d))
    labels = ["Conventional", "Removal", "No bats", "+ bat houses", "+ parasitoid"]
    axes[0].bar(x - 0.18, d.yield_grain / conv.yield_grain, width=0.36, color=BLUE, label="Yield")
    axes[0].bar(x + 0.18, d.mean_H / conv.mean_H, width=0.36, color=RED, label="Pests")
    axes[0].axhline(1, color=GREY, lw=0.8, ls=":")
    axes[0].set_ylabel("Relative to conventional")
    axes[0].set_xticks(x, labels, rotation=20, fontsize=6.5)
    axes[0].legend(frameon=False, fontsize=7)
    axes[0].set_title("Production and pest pressure", loc="left", fontsize=8)
    axes[1].bar(x, d.cv_H, width=0.55, color=ORANGE)
    axes[1].axhline(float(conv.cv_H), color=GREY, lw=0.8, ls=":")
    axes[1].set_ylabel("Pest CV (–)")
    axes[1].set_xticks(x, labels, rotation=20, fontsize=6.5)
    axes[1].set_title("Pest variability", loc="left", fontsize=8)
    save(fig, "result_q3_alternatives")


def fig_result_q3_ablation():
    d = load("q3_scenarios.csv")
    order = ["herbicide_removal", "removal_no_bats", "ablate_insectivory",
             "ablate_pollination", "ablate_predation"]
    labels = ["Full bats", "No bats", "No insectivory", "No pollination", "No predation"]
    d = d.set_index("scenario").loc[order].reset_index()
    fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.6))
    x = np.arange(len(d))
    axes[0].bar(x, d.mean_H, color=RED, width=0.55)
    axes[0].set_ylabel("Pest biomass (g C m$^{-2}$)")
    axes[0].set_title("Pest suppression", loc="left", fontsize=8)
    axes[1].bar(x, d.lam_poll, color=SKY, width=0.55)
    axes[1].set_ylabel("Fruit-set factor $\lambda_{poll}$ (–)")
    axes[1].set_title("Pollination", loc="left", fontsize=8)
    axes[2].bar(x, d.yield_grain, color=BLUE, width=0.55)
    axes[2].set_ylabel("Grain yield (kg ha$^{-1}$)")
    axes[2].set_title("Yield", loc="left", fontsize=8)
    for ax in axes:
        ax.set_xticks(x, labels, rotation=25, fontsize=6.2)
    save(fig, "result_q3_ablation")


def fig_result_q3_bat_dose():
    d = load("q3_bat_house_dose.csv")
    fig, axes = plt.subplots(2, 1, figsize=(4.8, 4.2), sharex=True)
    axes[0].plot(d.multiplier, d.yield_grain, color=BLUE, marker="o", ms=3)
    axes[0].axvline(1.5, color=GREY, ls=":", lw=1)
    axes[0].set_ylabel("Yield (kg ha$^{-1}$)")
    axes[0].set_title("Bat-house intensity and yield", loc="left", fontsize=8)
    axes[1].plot(d.multiplier, d.mean_B, color=PURPLE, marker="o", ms=3, label="Bats $B$")
    axes[1].plot(d.multiplier, d.mean_H, color=RED, marker="s", ms=3, label="Pests $H$")
    axes[1].axvline(1.5, color=GREY, ls=":", lw=1)
    axes[1].set_yscale("log")
    axes[1].set_ylabel("Biomass (g C m$^{-2}$, log scale)")
    axes[1].set_xlabel("Bat capacity and colonization multiplier")
    axes[1].legend(frameon=False, fontsize=7)
    save(fig, "result_q3_bat_dose", size=(4.8, 4.2))


def fig_raw_q4():
    d = load("q4_decision_samples.csv")
    fig, ax = plt.subplots(figsize=(3.8, 2.9))
    size = 16 + 45 * (d.profit - d.profit.min()) / (d.profit.max() - d.profit.min() + 1e-9)
    bins = [(0.0, 0.33, "Organic < 33%", BLUE),
            (0.33, 0.66, "33–66%", ORANGE),
            (0.66, 1.01, "> 66%", GREEN)]
    for lo, hi, lab, col in bins:
        m = (d.uorg >= lo) & (d.uorg < hi)
        ax.scatter(d.uH[m], d.uP[m], s=size[m], color=col, label=lab)
    ax.set_xlabel("Herbicide intensity $u_H$")
    ax.set_ylabel("Insecticide intensity $u_P$")
    ax.legend(frameon=False, fontsize=7, title="Organic area", title_fontsize=7)
    ax.set_title("Decision space (marker size proportional to profit)", loc="left", fontsize=9)
    save(fig, "raw_q4_decision_space", size=(3.9, 3.0))

def fig_process_q4():
    d = load("q4_decision_samples.csv")
    fig, ax = plt.subplots(figsize=(3.8, 2.9))
    m = d.pareto == 1
    ax.scatter(d.profit[~m], d.stability[~m], s=14, color=GREY, alpha=0.6, label="Dominated")
    ax.scatter(d.profit[m], d.stability[m], s=26, color=BLUE, label="Pareto")
    ax.set_xlabel("Profit (CNY ha$^{-1}$)")
    ax.set_ylabel("Stability proxy $1/(1+CV_H)$")
    ax.legend(frameon=False, fontsize=7)
    ax.set_title("Objective space", loc="left", fontsize=9)
    save(fig, "process_q4_objectives", size=(3.9, 3.0))


def fig_result_q4():
    d = load("q4_decision_samples.csv")
    m = d.pareto == 1
    p = d[m].sort_values("profit")
    fig, ax = plt.subplots(figsize=(5.2, 3.0))
    ax.scatter(d.profit[~m], d["yield"][~m], s=14, color=GREY, alpha=0.5, label="Dominated")
    ax.plot(p.profit, p["yield"], color=BLUE, lw=1.0, label="Pareto front")
    ax.scatter(p.profit, p["yield"], s=26, color=BLUE)
    # knee point: max distance from the chord
    if len(p) >= 3:
        x1, y1 = float(p.profit.iloc[0]), float(p["yield"].iloc[0])
        x2, y2 = float(p.profit.iloc[-1]), float(p["yield"].iloc[-1])
        dx, dy = x2 - x1, y2 - y1
        norm = np.hypot(dx, dy) + 1e-12
        dist = np.abs(dy * (p.profit - x1) - (x2 - x1) * (p["yield"] - y1)) / norm
        k = p.iloc[int(np.argmax(dist.values))]
        ax.scatter([k.profit], [k["yield"]], s=90, facecolor="none", edgecolor=RED, lw=1.5,
                   label="Knee point")
        ax.annotate("$u_H$=%.2f, $u_{org}$=%.2f" % (k.uH, k.uorg), (k.profit, k["yield"]),
                    textcoords="offset points", xytext=(10, 12), fontsize=7)
    ax.set_xlabel("Profit (CNY ha$^{-1}$)")
    ax.set_ylabel("Grain yield (kg ha$^{-1}$)")
    ax.legend(frameon=False, fontsize=7)
    ax.set_title("Profit–yield trade-off", loc="left", fontsize=9)
    save(fig, "result_q4_pareto", size=(5.3, 3.1))


def fig_flow():
    fig, ax = plt.subplots(figsize=(7.2, 4.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 60)
    ax.axis("off")

    def box(x, y, w, h, text, fc="#F2F2F2"):
        ax.add_patch(FancyBboxPatch((x - w / 2, y - h / 2), w, h,
                                    boxstyle="round,pad=0.4,rounding_size=1.2",
                                    fc=fc, ec="#333333", lw=0.8))
        ax.text(x, y, text, ha="center", va="center", fontsize=7.8)

    def arrow(x1, y1, x2, y2):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                     mutation_scale=8, lw=0.7, color="#333333"))

    box(9, 50, 15, 7, "Inputs\nclimate, prices", "#E8F1F8")
    box(9, 38, 15, 7, "Assumptions\nA1-A8", "#E8F1F8")
    box(31, 50, 17, 8, "Core food-web model\n12 fast + 2 slow")
    box(31, 38, 17, 7, "Scenario builder", "#E8F1F8")

    box(55, 51, 15, 6.5, "Q1 chemicals\nand seasonality")
    box(55, 42, 15, 6.5, "Q2 returning\nspecies")
    box(55, 33, 15, 6.5, "Q3 herbicide\nwithdrawal")
    box(55, 24, 15, 6.5, "Q4 organic\nportfolio")

    box(77, 51, 15, 6.5, "RK4 + Radau\ncheck", "#FFF4DE")
    box(77, 40, 15, 6.5, "Floquet, annual\nmap, maturity", "#FFF4DE")
    box(77, 24, 15, 6.5, "Pareto search\n+ knee point", "#FFF4DE")

    box(93, 45, 12, 8, "Validation\nmass balance")
    box(93, 20, 12, 7, "Outputs\nfig, tables, letter", "#E6F4EC")

    arrow(16.5, 50, 22.5, 50)
    arrow(16.5, 38, 22.5, 42)
    arrow(31, 46, 31, 41.5)
    arrow(39.5, 38, 47.5, 51)
    arrow(39.5, 38, 47.5, 42)
    arrow(39.5, 38, 47.5, 33)
    arrow(39.5, 38, 47.5, 24)
    arrow(62.5, 51, 69.5, 51)
    arrow(62.5, 42, 69.5, 41)
    arrow(62.5, 33, 69.5, 40)
    arrow(62.5, 24, 69.5, 24)
    arrow(84.5, 49, 87, 46)
    arrow(84.5, 40, 87, 44)
    arrow(84.5, 24, 87, 21)
    arrow(93, 41, 93, 23.5)

    save(fig, "flow_overall_model", size=(7.2, 4.2))

def main():
    p = mc.Params()
    fig_raw_q1(p)
    fig_process_q1()
    fig_result_q1()
    fig_result_q1_stability()
    fig_result_q1_sensitivity()
    fig_raw_q2()
    fig_process_q2()
    fig_result_q2()
    fig_result_q2_stability()
    fig_raw_q3(p)
    fig_process_q3()
    fig_result_q3()
    fig_result_q3_ablation()
    fig_result_q3_bat_dose()
    fig_raw_q4()
    fig_process_q4()
    fig_result_q4()
    fig_result_q4_components()
    fig_flow()


if __name__ == "__main__":
    main()
