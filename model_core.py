"""Core model: seasonally forced, two-timescale agro-ecosystem food web.

States (fast): C, W, V, SN, L, H, A, P, B, R, XH, XP
Slow: E (edge maturity), SOM (soil organic carbon)

All biomass in g C m^-2, nitrogen in g N m^-2, residues in mg a.i. kg^-1.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, asdict

import numpy as np

# state order
C, W, V, SN, L, H, A, P, B, R, XH, XP = range(12)
N_FAST = 12

DAY = 1.0
YEAR = 365.0


@dataclass
class Params:
    # climate / phenology
    Tbar: float = 15.0
    dT: float = 10.0
    Topt: float = 22.0
    sigT: float = 12.0
    tpeak: float = 200.0
    tp: float = 100.0
    th: float = 280.0
    tau_s: float = 3.0
    tfl1: float = 180.0
    tfl2: float = 215.0
    ta1: float = 90.0
    ta2: float = 310.0
    tb1: float = 100.0
    tb2: float = 300.0
    sov: float = 0.15
    deltaB: float = 0.25
    # crops and weeds
    gseed: float = 0.050
    gamma0: float = 0.90
    chiE: float = 0.80
    bat_t0: float = 120.0
    bat_width: float = 6.0
    rC: float = 0.09
    KC: float = 600.0
    mC: float = 0.003
    rW: float = 0.08
    KW: float = 150.0
    mW: float = 0.012
    betaCW: float = 0.5
    betaWC: float = 0.4
    rV: float = 0.03
    KV0: float = 250.0
    mV: float = 0.006
    cV: float = 0.0008
    Sseed: float = 4.0
    Dp: float = 5.0
    Dh: float = 6.0
    eta: float = 0.30
    HI: float = 0.50
    fC: float = 0.45
    # nutrients / litter
    phiCN: float = 15.0
    KN: float = 1.0
    kappalit: float = 0.012
    epsL: float = 0.12
    kappaSOM: float = 0.03
    kappamow: float = 0.01
    lS: float = 0.0015
    thetaC: float = 0.020
    thetaW: float = 0.020
    Fsyn: float = 5.0
    Forg: float = 5.0
    Df: float = 3.0
    # insects / predators
    aHC: float = 0.004
    hHC: float = 1.00
    eH: float = 0.25
    aHW: float = 0.004
    hHW: float = 1.00
    eHW: float = 0.15
    mH: float = 0.030
    KH: float = 40.0
    cH: float = 0.0008
    aAH: float = 0.060
    hAH: float = 0.50
    eA: float = 0.25
    mA: float = 0.012
    KA: float = 2.0
    cA: float = 0.0004
    # pollinators
    psiC: float = 0.0010
    psiV: float = 0.0015
    eP: float = 0.20
    mP: float = 0.025
    KP: float = 1.0
    cP: float = 0.0005
    lam0: float = 0.60
    Pref: float = 0.5
    omegaB: float = 0.30
    nuB: float = 50.0
    # bats / birds
    aBH: float = 4.000
    hBH: float = 0.20
    eB: float = 0.35
    mB: float = 0.004
    KB: float = 0.020
    cB: float = 0.00040
    psiB: float = 0.0003
    aRH: float = 0.500
    aRA: float = 0.020
    aRP: float = 0.010
    hRH: float = 0.20
    hRA: float = 0.5
    hRP: float = 0.5
    eR: float = 0.30
    mR: float = 0.006
    KR: float = 0.010
    cR: float = 0.00010
    # parasitoid
    aQH: float = 0.100
    hQH: float = 0.5
    eQ: float = 0.22
    mQ: float = 0.025
    KQ: float = 2.0
    cQ: float = 0.0003
    # earthworm decomposer
    aDL: float = 0.050
    hDL: float = 0.20
    eD: float = 0.20
    mD: float = 0.004
    KD: float = 12.0
    cD: float = 0.0008
    kappaD: float = 0.0005
    kw: float = 0.50
    # raptor
    aOR: float = 0.200
    aOB: float = 1.500
    N_rod: float = 20.0
    aON: float = 0.010
    hON: float = 0.5
    hOR: float = 0.5
    hOB: float = 0.5
    eO: float = 0.22
    mO: float = 0.0012
    KO: float = 0.010
    cO: float = 0.00002
    # chemicals
    phiC: float = 0.0005
    phiW: float = 0.080
    phiH: float = 0.60
    phiA: float = 0.25
    phiP: float = 0.05
    phiB: float = 0.010
    phiR: float = 0.010
    phiQ: float = 0.25
    phiD: float = 0.010
    phiO: float = 0.004
    H50C: float = 3.0
    H50W: float = 1.0
    H50H: float = 1.0
    H50A: float = 1.0
    H50P: float = 1.0
    H50B: float = 6.0
    H50R: float = 6.0
    H50Q: float = 1.0
    H50D: float = 6.0
    H50O: float = 6.0
    DT50H: float = 20.0
    DT50P: float = 8.0
    DoseH: float = 1.0
    DoseP: float = 0.5
    happ_H: tuple = (95.0, 130.0)
    happ_P: tuple = (160.0, 205.0)
    dapp: float = 2.0
    rho_b: float = 1250.0
    d_s: float = 0.2
    # slow
    E0: float = 0.20
    SOM0: float = 1700.0
    gammaE: float = 0.35
    mmow: float = 0.10
    # economics (used downstream)
    pC: float = 2.0
    kH: float = 260.0
    kP: float = 420.0
    kbat: float = 120.0
    kland: float = 900.0
    r_d: float = 0.05
    k_mow: float = 156.0
    k_org: float = 40.0
    bat_input: float = 0.00008


def default_state() -> np.ndarray:
    y = np.zeros(N_FAST)
    y[C] = 0.0
    y[W] = 25.0
    y[V] = 120.0
    y[SN] = 8.0
    y[L] = 60.0
    y[H] = 0.4
    y[A] = 0.25
    y[P] = 0.4
    y[B] = 0.0020
    y[R] = 0.0020
    y[XH] = 0.0
    y[XP] = 0.0
    return y


def default_scenario() -> dict:
    return {
        "uH": 1.0,
        "uP": 1.0,
        "uF": 0.0,
        "uM": 1.0,
        "uE": 0.0,
        "bat": 0.0,
        "uorg": 0.0,
        "chiQ4": 0.0,
        "useD": 0,
        "useO": 0,
        "useQ": 0,
        "remove_herbicide_from": None,  # year index for ramp
        "release_Q_from": None,
        "bat_mult": 1.0,
    }


def _gate(t, t0, t1, tau):
    return (1.0 / (1.0 + math.exp(-(t - t0) / tau))) * (
        1.0 - 1.0 / (1.0 + math.exp(-(t - t1) / tau))
    )


def _pulse_sum(t, days, width):
    s = 0.0
    for d in days:
        if d <= t <= d + width:
            s += 1.0 / width
    return s


def make_rhs(p: Params, sc: dict, E: float, SOM: float):
    """Return rhs(t, y) with fixed slow variables for the current year."""
    KV = p.KV0 * (1.0 + p.chiE * sc["uE"])
    cscale = 1.0 + p.chiE * sc["uE"]
    Msoil = p.rho_b * p.d_s * 1.0e4

    useD = sc["useD"]
    useO = sc["useO"]
    useQ = sc["useQ"]
    chiQ4 = sc["chiQ4"]
    bat_on = sc["bat"]
    D_const = 0.0 if sc.get("D_Q3") is None else sc["D_Q3"]

    def rhs(t, y):
        c, w, v, sn, lit, h, a, pp, b, r, xh, xp = [max(0.0, z) for z in y[:12]]

        tt = t % YEAR
        Ta = p.Tbar + p.dT * math.cos(2.0 * math.pi * (tt - p.tpeak) / YEAR)
        fT = math.exp(-((Ta - p.Topt) / p.sigT) ** 2)
        sigC = _gate(tt, p.tp, p.th, p.tau_s)
        sigFl = _gate(tt, p.tfl1, p.tfl2, p.tau_s)
        sigAct = _gate(tt, p.ta1, p.ta2, p.tau_s)
        sigB = _gate(tt, p.tb1, p.tb2, p.tau_s)
        fAct = p.sov + (1.0 - p.sov) * sigAct
        fB = p.deltaB + (1.0 - p.deltaB) * sigB
        Cfl = sigFl * c

        uH_eff = (1.0 - sc["uorg"]) * sc["uH"]
        uP_eff = (1.0 - sc["uorg"]) * sc["uP"]
        if sc.get("uH_t") is not None:
            uH_eff = (1.0 - sc["uorg"]) * sc["uH_t"](t)
        if sc.get("uP_t") is not None:
            uP_eff = (1.0 - sc["uorg"]) * sc["uP_t"](t)

        UH = uH_eff * p.DoseH * _pulse_sum(tt, p.happ_H, p.dapp)
        UP = uP_eff * p.DoseP * _pulse_sum(tt, p.happ_P, p.dapp)
        Ffert = (sc["uF"] * p.Forg + (1.0 - sc["uF"]) * p.Fsyn) * _pulse_sum(
            tt, (110.0, 160.0), p.Df
        )
        iotaC = p.Sseed / p.Dp if (p.tp <= tt <= p.tp + p.Dp) else 0.0
        eta = p.eta if (p.th <= tt <= p.th + p.Dh) else 0.0
        gamma_mow = sc["uM"] * p.gamma0 * _pulse_sum(tt, (300.0,), 3.0)

        def g(att, hand, x):
            return att * x / (1.0 + att * hand * x)

        fN = sn / (sn + p.KN) if p.KN > 0 else 1.0
        gHC = g(p.aHC, p.hHC, c)
        gHW = g(p.aHW, p.hHW, w)
        gAH = g(p.aAH, p.hAH, h)
        gBH = g(p.aBH, p.hBH, h)
        gQH = g(p.aQH, p.hQH, h)
        gDL = g(p.aDL, p.hDL, lit)
        gRA = g(p.aRA, p.hRA, a)
        gRP = g(p.aRP, p.hRP, pp)
        discR = (p.aRH * h + p.aRA * a + p.aRP * pp) / (
            1.0 + p.aRH * p.hRH * h + p.aRA * p.hRA * a + p.aRP * p.hRP * pp
        )
        discO = (p.aOR * r + p.aOB * b + p.aON * p.N_rod) / (
            1.0 + p.aOR * p.hOR * r + p.aOB * p.hOB * b + p.aON * p.hON * p.N_rod
        )

        tox = lambda phi, H50, x: phi * x / (x + H50)

        dC = (
            c
            * (
                p.rC * fN * fT * sigC * (1.0 - (c + p.betaCW * w) / p.KC)
                - p.mC
                - tox(p.phiC, p.H50C, xh)
            )
            - h * gHC
            + iotaC
            - eta * c
        )
        dW = (
            w
            * (
                p.rW * fN * fT * (1.0 - (w + p.betaWC * c) / p.KW)
                - p.mW
                - tox(p.phiW, p.H50W, xh)
                - gamma_mow
            )
            - h * gHW
            + p.gseed * (1.0 - w / p.KW)
        )
        dV = v * (p.rV * fT * (1.0 - v / KV) - p.mV - gamma_mow)
        dV += cscale * p.cV * E * (1.0 - v / KV)

        d_state = y[12] if useD else D_const
        Ilit = (
            p.mC * c
            + p.mW * w
            + p.mV * v
            + p.mH * h
            + p.mA * a
            + p.mP * pp
            + p.mB * b
            + p.mR * r
        )
        Ilit += p.mD * d_state
        if useQ:
            Ilit += p.mQ * y[13] if len(y) > 13 else 0.0
        if useO:
            Ilit += p.mO * y[14] if len(y) > 14 else 0.0

        dL = (1.0 - p.epsL) * Ilit - p.kappalit * lit - d_state * gDL

        dSN = (
            Ffert
            + p.kappalit * lit / p.phiCN
            + p.kappaD * d_state + p.kw * d_state * gDL / p.phiCN
            + chiQ4 * p.kappaSOM * SOM / (365.0 * p.phiCN)
            - (
                p.thetaC * p.rC * fN * fT * sigC * (1.0 - (c + p.betaCW * w) / p.KC) * c
                + p.thetaW * p.rW * fN * fT * (1.0 - (w + p.betaWC * c) / p.KW) * w
            )
            - p.lS * sn
        )

        dH = (
            h
            * (
                fAct * (p.eH * gHC + p.eHW * gHW) * (1.0 - h / p.KH)
                - p.mH
                - tox(p.phiH, p.H50H, xp)
            )
            - a * gAH
            - b * gBH
            - r * g(p.aRH, p.hRH, h)
            + cscale * p.cH * E * (1.0 - h / p.KH)
        )

        dA = (
            a * (p.eA * fAct * gAH * (1.0 - a / p.KA) - p.mA - tox(p.phiA, p.H50A, xp))
            - r * gRA
            + cscale * p.cA * E * (1.0 - a / p.KA)
        )

        dP = (
            pp
            * (
                p.eP * fAct * (p.psiC * Cfl + p.psiV * v) * (1.0 - pp / p.KP)
                - p.mP
                - tox(p.phiP, p.H50P, xp)
            )
            - r * gRP
            + cscale * p.cP * E * (1.0 - pp / p.KP)
        )

        dB = (
            b
            * (
                p.eB * fB * (gBH + p.psiB * Cfl) * (1.0 - b / p.KB)
                - p.mB
                - tox(p.phiB, p.H50B, xp)
            )
            + cscale * p.cB * sc.get("bat_mult", 1.0) * E * (1.0 - b / p.KB)
        )
        if useO:
            dB -= y[14] * g(p.aOB, p.hOB, b)
        if bat_on > 0 and p.bat_t0 <= tt <= p.bat_t0 + p.bat_width:
            dB += bat_on * p.bat_input
        if sc.get("bat_mult", 1.0) <= 0.0:
            dB = 0.0

        dR = (
            r
            * (p.eR * fB * discR * (1.0 - r / p.KR) - p.mR - tox(p.phiR, p.H50R, xp))
            + cscale * p.cR * E * (1.0 - r / p.KR)
        )
        if useO:
            dR -= y[14] * g(p.aOR, p.hOR, r)

        dXH = 1.0e6 / Msoil * UH - math.log(2.0) / p.DT50H * xh
        dXP = 1.0e6 / Msoil * UP - math.log(2.0) / p.DT50P * xp

        out = [dC, dW, dV, dSN, dL, dH, dA, dP, dB, dR, dXH, dXP]

        if useD:
            dd = y[12]
            out.append(
                dd * (p.eD * fAct * gDL * (1.0 - dd / p.KD) - p.mD - tox(p.phiD, p.H50D, xp))
                + cscale * p.cD * E * (1.0 - dd / p.KD)
            )
        else:
            out.append(0.0)

        if useQ:
            q = y[13]
            out.append(
                q * (p.eQ * fAct * gQH * (1.0 - q / p.KQ) - p.mQ - tox(p.phiQ, p.H50Q, xp))
                + cscale * p.cQ * E * (1.0 - q / p.KQ)
            )
        else:
            out.append(0.0)

        if useO:
            o = y[14]
            out.append(
                o * (p.eO * discO * (1.0 - o / p.KO) - p.mO - tox(p.phiO, p.H50O, xp))
                + cscale * p.cO * E * (1.0 - o / p.KO)
            )
        else:
            out.append(0.0)

        return out

    return rhs


def full_state(y12, sc, p):
    """Assemble full state vector; slots 12/13/14 are D/Q/O (unused slots stay 0)."""
    ys = list(y12)
    ys.append(1.0 if sc["useD"] else 0.0)   # 12: D
    ys.append(0.05 if sc["useQ"] else 0.0)  # 13: Q
    ys.append(0.0006 if sc["useO"] else 0.0)  # 14: O
    return ys


def _split(yfull, sc):
    y12 = list(yfull[:12])
    d = yfull[12] if sc["useD"] else float(sc.get("D_Q3", 0.0) or 0.0)
    q = yfull[13] if sc["useQ"] else 0.0
    o = yfull[14] if sc["useO"] else 0.0
    return y12, q, d, o


def simulate(
    p: Params,
    sc: dict | None = None,
    years: float = 6.0,
    dt: float = 0.05,
    record: bool = True,
    y0=None,
    E0=None,
    SOM0=None,
):
    sc = default_scenario() if sc is None else sc
    yfull = full_state(default_state(), sc, p) if y0 is None else list(y0)
    if y0 is None:
        yfull[B] = yfull[B] * float(sc.get("bat_mult", 1.0))
    E = p.E0 if E0 is None else E0
    SOM = p.SOM0 if SOM0 is None else SOM0

    n_days = int(round(years * YEAR))
    n_sub = max(1, int(round(1.0 / dt)))
    steps = n_days * n_sub

    rec = {
        "t": np.empty(steps + 1),
        "y": np.empty((steps + 1, len(yfull))),
        "E": np.empty(steps + 1),
        "SOM": np.empty(steps + 1),
    }
    harvest = 0.0
    Ilit_int = 0.0
    lam_poll = 1.0
    n_lam = 0

    k = 0
    rec["t"][0] = 0.0
    rec["y"][0] = yfull
    rec["E"][0] = E
    rec["SOM"][0] = SOM

    for day in range(n_days):
        rhs = make_rhs(p, sc, E, SOM)
        for sub in range(n_sub):
            t = day + sub * dt
            k1 = rhs(t, yfull)
            y2 = [yfull[i] + 0.5 * dt * k1[i] for i in range(len(yfull))]
            k2 = rhs(t + 0.5 * dt, y2)
            y3 = [yfull[i] + 0.5 * dt * k2[i] for i in range(len(yfull))]
            k3 = rhs(t + 0.5 * dt, y3)
            y4 = [yfull[i] + dt * k3[i] for i in range(len(yfull))]
            k4 = rhs(t + dt, y4)
            for i in range(len(yfull)):
                yfull[i] += dt / 6.0 * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i])
                if yfull[i] < 1e-12:
                    yfull[i] = 1e-12 if yfull[i] >= 0.0 else 0.0
            # accumulate diagnostics
            tt = t % YEAR
            if p.th <= tt <= p.th + p.Dh:
                harvest += p.eta * yfull[C] * dt
            y12, q, d, o = _split(yfull, sc)
            Ilit = (
                p.mC * y12[C]
                + p.mW * y12[W]
                + p.mV * y12[V]
                + p.mH * y12[H]
                + p.mA * y12[A]
                + p.mP * y12[P]
                + p.mB * y12[B]
                + p.mR * y12[R]
                + p.mD * d
                + (p.mQ * q if sc["useQ"] else 0.0)
                + (p.mO * o if sc["useO"] else 0.0)
            )
            Ilit_int += Ilit * dt
            if p.tfl1 <= tt <= p.tfl2:
                lam_now = p.lam0 + (1.0 - p.lam0) * min(
                    1.0, (y12[P] + p.omegaB * p.nuB * y12[B]) / p.Pref
                )
                lam_poll = (lam_poll * n_lam + lam_now) / (n_lam + 1)
                n_lam += 1
            k += 1
            rec["t"][k] = t + dt
            rec["y"][k] = yfull
            rec["E"][k] = E
            rec["SOM"][k] = SOM

        # end of day: slow variables
        # (updated at year boundaries below)
        if (day + 1) % 365 == 0:
            E = min(1.0, max(0.0, E + p.gammaE * E * (1.0 - E) - p.mmow * E))
            SOM = max(
                0.0,
                SOM + p.epsL * Ilit_int
                - p.kappaSOM * SOM
                - p.kappamow * sc["uM"] * SOM,
            )
            Ilit_int = 0.0
            harvest_year = harvest
            harvest = 0.0
            rec.setdefault("harvest_year", []).append(harvest_year)
            rec["E"][k] = E
            rec["SOM"][k] = SOM

    if not record:
        rec["t"] = rec["t"][: k + 1]
        rec["y"] = rec["y"][: k + 1]
        rec["E"] = rec["E"][: k + 1]
        rec["SOM"] = rec["SOM"][: k + 1]

    return {
        "t": rec["t"][: k + 1],
        "y": rec["y"][: k + 1],
        "E": rec["E"][: k + 1],
        "SOM": rec["SOM"][: k + 1],
        "yield": (float(np.mean(rec["harvest_year"])) if rec.get("harvest_year") else harvest) * lam_poll,
        "harvest_series": rec.get("harvest_year", []),
        "lam_poll": lam_poll,
        "HI": p.HI,
        "fC": p.fC,
        "scenario": sc,
    }


def annual_metrics(res, sc):
    y = res["y"]
    t = res["t"]
    n = len(t)
    out = {}
    names = ["C", "W", "V", "SN", "L", "H", "A", "P", "B", "R", "XH", "XP"]
    for i, nm in enumerate(names):
        x = y[:, i]
        out[f"mean_{nm}"] = float(np.mean(x))
        out[f"min_{nm}"] = float(np.min(x))
        out[f"cv_{nm}"] = float(np.std(x) / max(np.mean(x), 1e-12))
    if y.shape[1] > 12:
        extra = ["D", "Q", "O"]
        for j, nm in enumerate(extra):
            if 12 + j < y.shape[1]:
                x = y[:, 12 + j]
                out[f"mean_{nm}"] = float(np.mean(x))
    out["E_final"] = float(res["E"][-1])
    out["SOM_final"] = float(res["SOM"][-1])
    out["yield_grain"] = float(10.0 * res.get("HI", 0.5) * res["yield"] / res.get("fC", 0.45))
    out["lam_poll"] = float(res["lam_poll"])
    return out


def monodromy(p, sc, years_warm=12, eps=1e-5, dt=0.05):
    """Finite-difference monodromy of the fast subsystem with fixed E, SOM."""
    sc = dict(sc)
    base = simulate(p, sc, years=years_warm + 1, dt=dt, record=True)
    # take state at the start of the last year
    n_steps = int(round(YEAR / dt))
    y_end = np.array(base["y"][-1], dtype=float)
    y_start = np.array(base["y"][-1 - n_steps], dtype=float)
    E = base["E"][-1]
    SOM = base["SOM"][-1]

    def one_year(y0):
        r = simulate(p, sc, years=1.0, dt=dt, record=True, y0=list(y0), E0=E, SOM0=SOM)
        return np.array(r["y"][-1], dtype=float)

    active = list(range(12))
    if sc.get("useD", 0):
        active.append(12)
    if sc.get("useQ", 0):
        active.append(13)
    if sc.get("useO", 0):
        active.append(14)

    # converge the one-year map to a fixed point (slow variables frozen)
    y_star = y_start.copy()
    n_iter = 0
    for n_iter in range(40):
        y_next = one_year(y_star)
        if np.max(np.abs(y_next - y_star)) < 1e-7:
            y_star = y_next
            break
        y_star = y_next
    y_start = y_star

    n = len(active)
    M = np.zeros((n, n))
    f0 = one_year(y_start)
    for jj, j in enumerate(active):
        yp = y_start.copy()
        yp[j] += eps
        fj = one_year(yp)
        M[:, jj] = (fj[active] - f0[active]) / eps
    mu = np.linalg.eigvals(M)
    rho = float(np.max(np.abs(mu)))
    return {
        "M": M,
        "mu": mu,
        "rho": rho,
        "Lambda": math.log(max(rho, 1e-300)) / YEAR,
        "TR": (-YEAR / math.log(max(rho, 1e-300))) if rho < 1 else float("nan"),
        "y_start": y_start,
        "y_end": f0,
        "residual": float(np.max(np.abs(f0 - y_start))),
        "n_iter": n_iter,
    }

def _year_step(p, sc, y, E, SOM, dt=0.05):
    """One-year advance of the full (fast + slow) system."""
    r = simulate(p, sc, years=1.0, dt=dt, record=False, y0=list(y), E0=E, SOM0=SOM)
    return np.array(r["y"][-1], dtype=float), float(r["E"][-1]), float(r["SOM"][-1])


def _active_idx(sc):
    idx = list(range(12))
    if sc.get("useD", 0):
        idx.append(12)
    if sc.get("useQ", 0):
        idx.append(13)
    if sc.get("useO", 0):
        idx.append(14)
    return idx


def annual_map_spectral_radius(p, sc, years_warm=8, eps=1e-5, dt=0.05):
    """Spectral radius of the annual map G:(x,E,SOM)->(x',E',SOM')."""
    sc = dict(sc)
    y = np.array(full_state(default_state(), sc, p), dtype=float)
    # slow-variable fixed points: E is analytic; SOM follows from the annual litter input
    E = min(1.0, max(0.0, 1.0 - p.mmow / p.gammaE))
    S = p.SOM0
    y1, E1, S1 = _year_step(p, sc, y, E, S, dt)
    k_tot = p.kappaSOM + p.kappamow * sc["uM"]
    influx = max(0.0, (S1 - S + k_tot * S) / p.epsL)
    S = max(1.0, p.epsL * influx / k_tot)
    y = y1

    for _ in range(max(0, years_warm)):
        y, E, S = _year_step(p, sc, y, E, S, dt)

    # converge to the annual fixed point, then linearise
    residual = float("inf")
    converged = False
    for _ in range(120):
        S_prev = S
        y2, E2, S2 = _year_step(p, sc, y, E, S, dt)
        dfast = float(np.max(np.abs(y2 - y)))
        y, E, S = y2, E2, S2
        # once the fast states settle, jump SOM to its exact fixed point
        if dfast < 1e-9 and k_tot > 0:
            S = S + (S2 - S_prev) / k_tot
        residual = float(max(dfast, abs(E2 - E), abs(S - S_prev)))
        if residual < 1e-8:
            converged = True
            break
    if not converged:
        raise RuntimeError(f"annual map fixed point not converged (residual={residual:.3e})")

    idx = _active_idx(sc)
    n = len(idx)
    base = np.concatenate([y[idx], [E, S]])
    dim = n + 2

    def step_z(z):
        yz = y.copy()
        yz[idx] = z[:n]
        y2, E2, S2 = _year_step(p, sc, yz, z[n], z[n + 1], dt)
        return np.concatenate([y2[idx], [E2, S2]])

    f0 = step_z(base)
    J = np.zeros((dim, dim))
    for j in range(dim):
        zp = base.copy()
        step = eps
        if j == n and base[j] + eps > 1.0:   # E upper bound
            step = -eps
        zp[j] += step
        J[:, j] = (step_z(zp) - f0) / step
    rho = float(np.max(np.abs(np.linalg.eigvals(J))))
    return {"J": J, "rho_y": rho, "dim": dim, "state": base, "residual": residual, "converged": converged, "eps": eps}


def maturity_contraction(p, sc, years=20, eps=1e-6, dt=0.05):
    """Year-by-year finite-time contraction rate during habitat maturation."""
    sc = dict(sc)
    y = np.array(full_state(default_state(), sc, p), dtype=float)
    E, S = p.E0, p.SOM0
    idx = _active_idx(sc)
    n = len(idx)
    v = np.ones(n + 2)
    v /= np.linalg.norm(v)
    rows = []
    for yr in range(1, years + 1):
        base = np.concatenate([y[idx], [E, S]])
        scale = 1.0 + np.abs(base)
        delta = eps * scale * v
        y1, E1, S1 = _year_step(p, sc, y, E, S, dt)
        yp = y.copy()
        yp[idx] += delta[:n]
        yp2, Ep2, Sp2 = _year_step(p, sc, yp, E + delta[n], S + delta[n + 1], dt)
        dz = np.concatenate([(yp2 - y1)[idx], [Ep2 - E1, Sp2 - S1]])
        ratio = max(np.linalg.norm(dz / scale) / max(np.linalg.norm(delta / scale), 1e-300), 1e-300)
        rows.append(
            {
                "year": yr,
                "E": E1,
                "dE": E1 - E,
                "Lambda_y": float(np.log(ratio) / YEAR),
                "ratio": float(ratio),
            }
        )
        y, E, S = y1, E1, S1
    return rows


def solver_check(p, sc=None, dt=0.05, days=365):
    """Compare daily-mean states across RK4 (dt and dt/2) and scipy Radau."""
    import time
    from scipy.integrate import solve_ivp

    sc = default_scenario() if sc is None else sc
    y0 = np.array(full_state(default_state(), sc, p), dtype=float)
    E, S = p.E0, p.SOM0
    rhs = make_rhs(p, sc, E, S)
    names = ["C", "W", "V", "SN", "L", "H", "A", "P", "B", "R", "XH", "XP", "D", "Q", "O"]
    key = [0, 1, 2, 5, 6, 7, 8, 9]

    t0 = time.time()
    rk = simulate(p, sc, years=days / YEAR, dt=dt, record=False, y0=list(y0), E0=E, SOM0=S)
    wall_rk = time.time() - t0
    y_rk = np.array(rk["y"], dtype=float)

    t0 = time.time()
    rk2 = simulate(p, sc, years=days / YEAR, dt=dt / 2, record=False, y0=list(y0), E0=E, SOM0=S)
    wall_rk2 = time.time() - t0
    y_rk2 = np.array(rk2["y"], dtype=float)

    t0 = time.time()
    sol = solve_ivp(rhs, (0.0, float(days)), y0, method="Radau",
                    rtol=1e-10, atol=1e-12, max_step=0.05,
                    t_eval=np.arange(0.0, float(days) + 1e-9, 1.0))
    wall_radau = time.time() - t0
    y_rad = sol.y.T  # days x states

    mean_rk = y_rk.mean(axis=0)
    mean_rk2 = y_rk2.mean(axis=0)
    mean_rad = y_rad.mean(axis=0)

    def rel(a, b):
        denom = np.maximum(np.maximum(np.abs(a), np.abs(b)), 1e-10)
        return np.abs(a - b) / denom

    r_rad = rel(mean_rk[key], mean_rad[key])
    r_half = rel(mean_rk[key], mean_rk2[key])
    jmax = int(np.argmax(r_rad))
    return {
        "success": bool(sol.success),
        "n_steps_radau": int(sol.t.size),
        "max_rel_diff_key": float(r_rad[jmax]),
        "median_rel_diff_key": float(np.median(r_rad)),
        "max_state": names[key[jmax]],
        "mean_rk_at_max": float(mean_rk[key[jmax]]),
        "mean_radau_at_max": float(mean_rad[key[jmax]]),
        "step_halving_max_rel": float(np.max(r_half)),
        "step_halving_median_rel": float(np.median(r_half)),
        "wall_rk_s": float(wall_rk),
        "wall_rk_half_s": float(wall_rk2),
        "wall_radau_s": float(wall_radau),
        "y_rk": mean_rk,
        "y_radau": mean_rad,
    }

