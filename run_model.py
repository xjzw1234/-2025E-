"""Run scenarios for the four sub-questions and write result tables.

Usage (from PROJECT_ROOT):
    python run_model.py --task all
    python run_model.py --task q1 --quick
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import time

import numpy as np
import pandas as pd

import model_core as mc

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
os.makedirs(OUT, exist_ok=True)

SEED = 20251029


def _scen(**kw):
    s = mc.default_scenario()
    s.update(kw)
    return s


def _base(**kw):
    """Q1/Q4 base model: 12 fast states (no earthworm, no raptor)."""
    s = mc.default_scenario()
    s.update(dict(useD=0, useO=0))
    s.update(kw)
    return s


def run_q1(p, years=6.0, quick=False):
    """Chemical intensity gradients, stability vector."""
    rows = []
    levels = [0.0, 0.25, 0.5, 0.75, 1.0]
    if quick:
        levels = [0.0, 1.0]
    for uh in levels:
        for up in levels:
            sc = _base(uH=uh, uP=up)
            r = mc.simulate(p, sc, years=years, dt=0.05)
            m = mc.annual_metrics(r, sc)
            rows.append(
                {
                    "uH": uh,
                    "uP": up,
                    "mean_C": m["mean_C"],
                    "mean_W": m["mean_W"],
                    "mean_V": m["mean_V"],
                    "mean_SN": m["mean_SN"],
                    "mean_H": m["mean_H"],
                    "mean_A": m["mean_A"],
                    "mean_P": m["mean_P"],
                    "mean_B": m["mean_B"],
                    "mean_R": m["mean_R"],
                    "cv_H": m["cv_H"],
                    "min_C": m["min_C"],
                    "yield_grain": m["yield_grain"],
                    "lam_poll": m["lam_poll"],
                    "E_final": m["E_final"],
                    "SOM_final": m["SOM_final"],
                }
            )
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "q1_chemical_gradient.csv"), index=False)

    # time series for baseline
    sc = _base()
    r = mc.simulate(p, sc, years=min(years, 2.0), dt=0.05)
    ts = pd.DataFrame(
        {
            "t": r["t"],
            "C": r["y"][:, mc.C],
            "W": r["y"][:, mc.W],
            "H": r["y"][:, mc.H],
            "A": r["y"][:, mc.A],
            "P": r["y"][:, mc.P],
            "B": r["y"][:, mc.B],
            "SN": r["y"][:, mc.SN],
            "XH": r["y"][:, mc.XH],
            "XP": r["y"][:, mc.XP],
        }
    )
    ts.to_csv(os.path.join(OUT, "q1_baseline_timeseries.csv"), index=False)
    return df


def run_q2(p, years=20.0, quick=False):
    """Edge maturation and two returning species (earthworm D, raptor O)."""
    variants = {
        "none": dict(useD=0, useO=0),
        "earthworm": dict(useD=1, useO=0),
        "raptor": dict(useD=0, useO=1),
        "both": dict(useD=1, useO=1),
    }
    if quick:
        variants = {"none": dict(useD=0, useO=0), "both": dict(useD=1, useO=1)}
        years = min(years, 5.0)
    rows = []
    for name, kw in variants.items():
        sc = _scen(**kw)
        r = mc.simulate(p, sc, years=years, dt=0.05)
        m = mc.annual_metrics(r, sc)
        rows.append(
            {
                "variant": name,
                "mean_C": m["mean_C"],
                "mean_W": m["mean_W"],
                "mean_H": m["mean_H"],
                "mean_A": m["mean_A"],
                "mean_B": m["mean_B"],
                "mean_R": m["mean_R"],
                "yield_grain": m["yield_grain"],
                "E_final": m["E_final"],
                "SOM_final": m["SOM_final"],
            }
        )
        if name == "both":
            t = r["t"]
            yearly = pd.DataFrame(
                {
                    "year": np.arange(1, int(years) + 1),
                    "E": [float(r["E"][np.argmin(np.abs(t - 365 * y))]) for y in range(1, int(years) + 1)],
                    "SOM": [float(r["SOM"][np.argmin(np.abs(t - 365 * y))]) for y in range(1, int(years) + 1)],
                    "mean_C": [float(r["y"][(t >= (y - 1) * 365) & (t < y * 365), mc.C].mean()) for y in range(1, int(years) + 1)],
                    "mean_D": [float(r["y"][(t >= (y - 1) * 365) & (t < y * 365), 12].mean()) for y in range(1, int(years) + 1)],
                    "mean_O": [float(r["y"][(t >= (y - 1) * 365) & (t < y * 365), 14].mean()) for y in range(1, int(years) + 1)],
                }
            )
            yearly.to_csv(os.path.join(OUT, "q2_maturation.csv"), index=False)
            rows_m = mc.maturity_contraction(p, sc, years=int(min(years, 12)))
            pd.DataFrame(rows_m).to_csv(os.path.join(OUT, "q2_maturity_lambda.csv"), index=False)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "q2_species_variants.csv"), index=False)

    st_rows = []
    for name, kw in variants.items():
        sc = _scen(**kw)
        fl = mc.monodromy(p, sc, years_warm=6)
        st_rows.append({
            "variant": name,
            "rho_f": fl["rho"],
            "Lambda_per_day": fl["Lambda"],
            "TR_days": fl["TR"],
            "residual": fl["residual"],
        })
    pd.DataFrame(st_rows).to_csv(os.path.join(OUT, "q2_stability.csv"), index=False)
    return df


def run_q3(p, years=10.0, quick=False):
    """Herbicide removal, bats, alternative parasitoid."""
    rows = []
    # baseline (herbicide on) and removal at year 3
    def ramp_factory(y_start):
        def u(t):
            yr = t / 365.0
            if yr < y_start:
                return 1.0
            return max(0.0, 1.0 - (yr - y_start))

        return u

    scen = {
        "conventional": dict(uH=1.0),
        "herbicide_removal": dict(uH_t=ramp_factory(3.0)),
        "removal_no_bats": dict(uH_t=ramp_factory(3.0), bat_mult=0.0),
        "removal_bats": dict(uH_t=ramp_factory(3.0), p_over={"KB": 1.5 * p.KB, "cB": 1.5 * p.cB}),
        "removal_parasitoid": dict(uH_t=ramp_factory(3.0), useQ=1, uP=0.30),
        # channel ablations (bats present, one function disabled)
        "ablate_insectivory": dict(uH_t=ramp_factory(3.0), p_over={"aBH": 0.0}),
        "ablate_pollination": dict(uH_t=ramp_factory(3.0), p_over={"psiB": 0.0, "nuB": 0.0}),
        "ablate_predation": dict(uH_t=ramp_factory(3.0), p_over={"aOB": 0.0}),
    }
    if quick:
        scen = {"conventional": dict(uH=1.0), "herbicide_removal": dict(uH_t=ramp_factory(3.0))}
        years = min(years, 6.0)

    for name, kw in scen.items():
        kw = dict(kw)
        p_over = kw.pop("p_over", None)
        pp = copy.deepcopy(p)
        if p_over:
            for k, v in p_over.items():
                setattr(pp, k, v)
        sc = _scen(useD=0, useO=1, D_Q3=8.0, **kw)
        r = mc.simulate(pp, sc, years=years, dt=0.05)
        m = mc.annual_metrics(r, sc)
        rows.append(
            {
                "scenario": name,
                "mean_C": m["mean_C"],
                "mean_W": m["mean_W"],
                "mean_H": m["mean_H"],
                "mean_A": m["mean_A"],
                "mean_P": m["mean_P"],
                "mean_B": m["mean_B"],
                "mean_R": m["mean_R"],
                "mean_O": m.get("mean_O", 0.0),
                "cv_H": m["cv_H"],
                "yield_grain": m["yield_grain"],
                "lam_poll": m["lam_poll"],
                "E_final": m["E_final"],
            }
        )
        if name in ("herbicide_removal", "removal_bats"):
            t = r["t"]
            ts = pd.DataFrame(
                {
                    "t": t,
                    "C": r["y"][:, mc.C],
                    "W": r["y"][:, mc.W],
                    "H": r["y"][:, mc.H],
                    "A": r["y"][:, mc.A],
                    "B": r["y"][:, mc.B],
                    "P": r["y"][:, mc.P],
                }
            )
            ts.to_csv(os.path.join(OUT, f"q3_{name}_timeseries.csv"), index=False)
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "q3_scenarios.csv"), index=False)
    if not quick:
        dose = []
        for m in [round(1.0 + 0.1 * i, 1) for i in range(11)]:
            pp = copy.deepcopy(p)
            pp.KB = m * p.KB
            pp.cB = m * p.cB
            sc = _scen(useD=0, useO=1, D_Q3=8.0, uH_t=ramp_factory(3.0))
            r = mc.simulate(pp, sc, years=years, dt=0.05)
            met = mc.annual_metrics(r, sc)
            dose.append({
                "multiplier": m,
                "mean_B": met["mean_B"],
                "mean_H": met["mean_H"],
                "mean_A": met["mean_A"],
                "mean_P": met["mean_P"],
                "lam_poll": met["lam_poll"],
                "yield_grain": met["yield_grain"],
                "cv_H": met["cv_H"],
            })
        pd.DataFrame(dose).to_csv(os.path.join(OUT, "q3_bat_house_dose.csv"), index=False)
    return df


def _evaluate_decision(p, x, years=8.0):
    uh, up, uf, um, ue, ub, uorg = x
    sc = _base(
        uH=float(uh),
        uP=float(up),
        uF=float(uf),
        uM=float(um),
        uE=float(ue),
        uorg=float(uorg),
        chiQ4=1.0,
    )
    pp = copy.deepcopy(p)
    if ub > 0.5:
        pp.KB = 1.5 * p.KB
        pp.cB = 1.5 * p.cB
    r = mc.simulate(pp, sc, years=years, dt=0.05)
    m = mc.annual_metrics(r, sc)
    yg = m["yield_grain"]
    cost = (
        p.kH * uh * (1 - uorg)
        + p.kP * up * (1 - uorg)
        + p.k_mow * um
        + p.kbat * (ub > 0.5)
        + p.kland * ue
        + p.k_org * uorg
    )
    profit = p.pC * yg - cost
    states = [m["mean_C"], m["mean_W"], m["mean_V"], m["mean_H"], m["mean_A"],
              m["mean_P"], m["mean_B"], m["mean_R"]]
    tot = sum(max(s, 1e-9) for s in states)
    bd = -sum((max(s, 1e-9) / tot) * np.log(max(s, 1e-9) / tot) for s in states)
    cv = m["cv_H"]
    stab = 1.0 / (1.0 + cv)
    return {
        "profit": profit,
        "stability": stab,
        "biodiversity": float(bd),
        "yield": yg,
        "pest_biomass": m["mean_H"],
        "crop_health": m["mean_C"],
        "pollination": m["lam_poll"],
        "soil_carbon": m["SOM_final"],
        "cost": cost,
    }


def run_q4(p, n_samples=150, quick=False):
    """Latin-hypercube decision search, Pareto filter, knee and component scan."""
    from scipy.stats import qmc

    if quick:
        n_samples = 24
    sampler = qmc.LatinHypercube(d=7, seed=SEED)
    u = sampler.random(n_samples)
    u[:, 4] *= 0.2
    u[:, 5] = (u[:, 5] > 0.5).astype(float)

    rows = []
    for i in range(n_samples):
        x = u[i]
        m = _evaluate_decision(p, x, years=2.0 if quick else 5.0)
        rows.append({
            "sample": i,
            "uH": x[0], "uP": x[1], "uF": x[2], "uM": x[3],
            "uE": x[4], "uB": x[5], "uorg": x[6],
            **m,
        })
    df = pd.DataFrame(rows)

    def pareto_mask(frame, cols):
        vals = frame[cols].values
        n = len(vals)
        keep = np.ones(n, dtype=bool)
        for i in range(n):
            if not keep[i]:
                continue
            for j in range(n):
                if i == j:
                    continue
                if np.all(vals[j] >= vals[i]) and np.any(vals[j] > vals[i]):
                    keep[i] = False
                    break
        return keep

    cols = ["profit", "stability", "biodiversity", "yield"]
    df["pareto"] = pareto_mask(df, cols).astype(int)
    df.to_csv(os.path.join(OUT, "q4_decision_samples.csv"), index=False)

    par = df[df.pareto == 1].sort_values("profit")
    knee = None
    if len(par) >= 3:
        x1, y1 = float(par.profit.iloc[0]), float(par["yield"].iloc[0])
        x2, y2 = float(par.profit.iloc[-1]), float(par["yield"].iloc[-1])
        dx, dy = x2 - x1, y2 - y1
        norm = np.hypot(dx, dy) + 1e-12
        dist = np.abs(dy * (par.profit - x1) - dx * (par["yield"] - y1)) / norm
        knee = par.iloc[int(np.argmax(dist.values))]
    elif len(par) > 0:
        knee = par.iloc[0]

    comp = []
    if knee is not None:
        base = {k: float(knee[k]) for k in
                ["profit", "stability", "biodiversity", "yield", "pest_biomass",
                 "crop_health", "pollination", "soil_carbon", "cost"]}
        comp.append({"variable": "baseline", "level": -1.0, **base})
        x0 = np.array([knee.uH, knee.uP, knee.uF, knee.uM, knee.uE, knee.uB, knee.uorg], dtype=float)
        names = ["uH", "uP", "uF", "uM", "uE", "uB", "uorg"]
        for j, nm in enumerate(names):
            levels = [0.0, 0.2] if nm == "uE" else [0.0, 1.0]
            for lev in levels:
                x = x0.copy()
                x[j] = lev
                m = _evaluate_decision(p, x, years=2.0 if quick else 5.0)
                comp.append({"variable": nm, "level": lev, **m})
    pd.DataFrame(comp).to_csv(os.path.join(OUT, "q4_components.csv"), index=False)
    return df


def run_sensitivity(p, quick=False):
    """One-at-a-time +/-20% perturbation of eight key parameters."""
    sc = _scen(uH=1.0, uP=1.0, useD=0, useO=1)

    def metrics(pp):
        r = mc.simulate(pp, sc, years=2.0 if quick else 10.0, dt=0.05)
        return mc.annual_metrics(r, sc)

    b = metrics(p)
    params = ["KC", "aBH", "nuB", "aHC", "kappalit", "KN", "gseed", "N_rod"]
    rows = []
    for name in params:
        v0 = getattr(p, name)
        for sign, mult in [(-1, 0.8), (1, 1.2)]:
            pp = copy.deepcopy(p)
            setattr(pp, name, v0 * mult)
            m = metrics(pp)
            rows.append({
                "parameter": name,
                "level": sign,
                "mean_H": m["mean_H"],
                "mean_C": m["mean_C"],
                "yield_grain": m["yield_grain"],
                "cv_H": m["cv_H"],
                "rel_H": m["mean_H"] / b["mean_H"] - 1.0,
                "rel_C": m["mean_C"] / b["mean_C"] - 1.0,
                "rel_yield": m["yield_grain"] / b["yield_grain"] - 1.0,
                "rel_cv": m["cv_H"] / b["cv_H"] - 1.0,
            })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "q1_sensitivity.csv"), index=False)
    return df


def run_stability(p, quick=False):
    rows = []
    for name, kw in {
        "conventional": dict(),
        "no_insecticide": dict(uP=0.0),
        "herbicide_removal": dict(uH=0.0),
    }.items():
        sc = _base(**kw)
        t0 = time.time()
        fl = mc.monodromy(p, sc, years_warm=12)
        rows.append(
            {
                "scenario": name,
                "rho_f": fl["rho"],
                "Lambda_per_day": fl["Lambda"],
                "TR_days": fl["TR"],
                "residual": fl["residual"],
                "wall_s": time.time() - t0,
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "q1_stability_floquet.csv"), index=False)
    return df


def run_solver_check(p):
    r = mc.solver_check(p, mc.default_scenario())
    df = pd.DataFrame([{k: v for k, v in r.items() if k not in ("y_rk", "y_radau")}])
    df.to_csv(os.path.join(OUT, "solver_check.csv"), index=False)
    return df


def run_annual_map(p, quick=False):
    sc = _base()
    rows = []
    for eps in ([1e-4] if quick else [1e-4, 1e-5, 1e-6]):
        r = mc.annual_map_spectral_radius(p, sc, years_warm=4 if quick else 8, eps=eps)
        rows.append(
            {
                "scenario": "conventional",
                "eps": eps,
                "rho_y": r["rho_y"],
                "dim": r["dim"],
                "residual": r["residual"],
                "converged": bool(r["converged"]),
            }
        )
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(OUT, "q1_annual_map.csv"), index=False)
    return df


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--task", default="all", choices=["q1", "q2", "q3", "q4", "stab", "check", "amap", "sens", "all"])
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--seed", type=int, default=SEED)
    args = ap.parse_args()

    np.random.seed(args.seed)
    p = mc.Params()
    t0 = time.time()
    if args.task in ("q1", "all"):
        df = run_q1(p, quick=args.quick)
        print("Q1 rows:", len(df))
    if args.task in ("q2", "all"):
        df = run_q2(p, quick=args.quick)
        print("Q2 rows:", len(df))
    if args.task in ("q3", "all"):
        df = run_q3(p, quick=args.quick)
        print("Q3 rows:", len(df))
    if args.task in ("q4", "all"):
        df = run_q4(p, quick=args.quick)
        print("Q4 rows:", len(df), "Pareto:", int(df["pareto"].sum()))
    if args.task in ("stab", "all"):
        df = run_stability(p, quick=args.quick)
        print(df.to_string(index=False))
    if args.task in ("amap", "all"):
        df = run_annual_map(p, quick=args.quick)
        print(df.to_string(index=False))
    if args.task in ("check", "all"):
        df = run_solver_check(p)
        print(df.to_string(index=False))
    if args.task in ("sens", "all"):
        df = run_sensitivity(p, quick=args.quick)
        print("Sensitivity rows:", len(df))
    print("elapsed %.1f s" % (time.time() - t0))


if __name__ == "__main__":
    main()
