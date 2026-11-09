# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 6: purlins, girts and eave struts — AISI S100-16 (DSM), LRFD strength, ASD deflection. NOT FOR ISSUE.

Lines (from the generated building):
    purlins / ridge purlins  one line each, continuous over every frame; the laps (where two pieces overlap) as two nested
                             sections: 2 EI in the analysis, 2 × the strength (flexure, shear) — the lap ends govern; the
                             overhangs past the end frames as cantilevers
    side-wall girts          the same, on the column lines
    gable girts              one line per row and end wall, continuous over the end-wall supports (wind columns and the
                             end frame's columns), cantilevers out to the side-wall girt line / the roof
    eave struts              butt-jointed C: one simple span per bay; + the bracing's eave-strut force (step 5's
                             longitudinal system, LRFD 1.0 W) in compression
Loads (normal to the roof / wall; + toward the building: gravity, inward pressure):
    D   roof sheeting (kN/m² of slope) × tributary width + self weight, × cos θ (the normal component)
    C   collateral (kN/m² of plan) × tributary width × cos² θ; in the gravity combinations, NOT with uplift (user 2026-11-05)
    Lr  Lo reduced by ASCE 7-16 §4.8 from the member's own tributary plan area (bimsteelauto roof_live_load), × cos² θ
    W   ASCE 7-16 Ch. 30 C&C (bimsteelauto loads.cladding: Figs. 30.3-1 and 30.3-2A, VERIFIED against Struware); each
        SPAN in its own zone at its own effective wind area (span × max(tributary, span / 3), §26.2). Zone layout —
        Claude's reading of Fig. 30.3-2A, VERIFIED False, TO CONFIRM: roof edge strips of width a along the eaves, the
        gable ends AND the ridge (bimsteelauto's reading) → zone 2, where an eave / ridge strip meets a gable strip →
        zone 3, everything else zone 1 (zone 1' — the smaller field suction — is NOT used: conservative); walls: within
        a of a building corner → zone 5, else 4. A span takes the worst zone any part of it (and of its tributary strip)
        touches. Roof slope above 7°: Fig. 30.3-2A does not apply → roof wind NOT evaluated (ratio inf).
    the component of gravity along the slope (to the sag rods) and the girts' self weight (in the wall plane) are not
    checked here (minor-axis bending: a stated gap)
Combinations (ASCE 7-16 §2.3.1 / §2.4.1): LRFD 1.4D; 1.2D + 1.6Lr + 0.5W; 1.2D + 1.0W + 0.5Lr; 0.9D + 1.0W (W inward in
    the first three, outward in the last; D includes C except in 0.9D); girts 1.0W in / out. ASD (deflection) D + Lr,
    D + 0.6W, 0.6D + 0.6W; girts 0.6W. Every combination is checked; the worst ratio governs.
Analysis: my own continuous-beam solver (Euler–Bernoulli, exact for uniform load per element; checked against closed
    forms and bimsteelauto continuous_beam_forces in the tests); simple supports at every frame / support.
Strength (AISI S100-16, DSM, Appendix 1 curves from the vendored direct_strength — bimsteelauto's cfs library):
    M + compresses the SHEETED flange (purlin top, girt outer): continuously braced → Mne = My;
    M − compresses the free flange: braced only at frames, sag-rod rows (roof members; the rods are taken as brace
        points of the section — Claude's assumption, listed) and the line's ends → Mne from Cb · Mcre(Lb), Cb =
        12.5 Mmax / (2.5 Mmax + 3 MA + 4 MB + 3 MC) over the brace segment (F2.1; 1.0 on a cantilever);
    Mn = min(Mnl(Mne), Mnd), φb 0.90; Mcrl, Mcrd, Mcre from cfs_section (geometry, finite strip) or the supplier table.
    Shear: the vendored aisi_s100.shear_strength (kv 5.34, φ 0.90 throughout — its own conservative single pair;
        VERIFIED False against S100-16 G2.1); combined bending and shear (H2): (M / φMnlo)² + (V / φVn)² ≤ 1, Mnlo the
        local strength with Mne = My.
    Eave strut, axial + bending (H1.2): P / φcPn + B1 M / φbMn ≤ 1, Pn by DSM (φc 0.85) with Pcre at the bay length
        (K = 1 about every axis; sag rods not counted for compression — conservative), B1 = 1 / (1 − P / Pex), Cm = 1.
Deflection: ASD, span / limit (ServiceLimits.purlin, default 150), gross Ix (the effective Ix at service stress is not
    computed: slightly unconservative for slender webs — stated); a cantilever against 2 × its length / limit.
Supplier table (overrides, per profile name): A, Ix, Sx, J, Cw, r_inside, Mcrl, Mcrd, Pcrl, Pcrd, Fy, Fu — each overridden
    value is marked "supplier" on the result; everything else stays "geometry".
Units: kN, kN·m, mm.
"""

from __future__ import annotations

import math

import numpy as np

import aisi_s100 as A_
from direct_strength import Mnd_distortional, Mne_global, Mnl_local, Pnd_distortional, Pne_global, Pnl_local
from bimsteelauto.loads.cladding import cladding_pressure, effective_wind_area
from bimsteelauto.loads.gravity import roof_live_load
from bimsteelauto.loads.wind import envelope_pressures

from ..analysis.endwall_analysis import _geom, longitudinal_feed
from ..analysis.bracing_system import longitudinal_bracing
from ..peb.building import BuildingInput, peb_building, resolve
from .cfs_section import KSI, Mcre, Pcre, cfs_section
from .inputs import plate_strength
from .serviceability import ServiceLimits

BANNER = "NOT FOR ISSUE — purlins, girts and eave struts (AISI S100-16 DSM) with open verification flags"
STEEL_KN_M3 = 77.0
PHI_B, PHI_C = 0.90, 0.85
NST = 21
SUPPLIER_KEYS = {"A", "Ix", "Sx", "J", "Cw", "r_inside", "Mcrl", "Mcrd", "Pcrl", "Pcrd", "Fy", "Fu"}
COMBOS_ROOF = {"LRFD": {"1.4D": {"D": 1.4, "C": 1.4}, "1.2D+1.6Lr+0.5W": {"D": 1.2, "C": 1.2, "Lr": 1.6, "Win": 0.5},
                        "1.2D+1.0W+0.5Lr": {"D": 1.2, "C": 1.2, "Lr": 0.5, "Win": 1.0}, "0.9D+1.0W": {"D": 0.9, "Wout": 1.0}},
               "ASD": {"D+Lr": {"D": 1.0, "C": 1.0, "Lr": 1.0}, "D+0.6W": {"D": 1.0, "C": 1.0, "Win": 0.6}, "0.6D+0.6W": {"D": 0.6, "Wout": 0.6}}}
COMBOS_WALL = {"LRFD": {"1.0W inward": {"Win": 1.0}, "1.0W outward": {"Wout": 1.0}},
               "ASD": {"0.6W inward": {"Win": 0.6}, "0.6W outward": {"Wout": 0.6}}}
ASSUMPTIONS = (
    "sag-rod rows are brace points of the purlin section for its free (unsheeted) flange; girts have none",
    "the sheeted flange is continuously braced (Mne = My); distortional buckling without the sheeting's rotational "
    "restraint (k_phi = 0) at its own critical half-wavelength — conservative",
    "lapped Z lines: continuous beams with the lap (two nested sections) at 2 x EI, 2 x the strength in flexure and "
    "shear; the critical points are then the lap ends",
    "roof C&C zone layout: Claude's reading of ASCE 7-16 Fig. 30.3-2A (edge strips a along eaves, gable ends and ridge; "
    "corners zone 3; zone 1 elsewhere, 1' not used) — TO CONFIRM",
    "eave strut: the bracing force at its bay in every combination with wind (the LRFD 1.0W value, 0.5 of it with "
    "0.5W), together with the C&C bending — an envelope",
)


# ----------------------------------------------------------------------------------------------- the beam

def beam_line(nodes: list[float], supports: list[float], q: list[float], EI, n: int = NST) -> list[tuple[float, float, float, float]]:
    """A straight beam on simple supports. nodes: ascending x (mm) incl. the supports and the free ends; q: N/mm on each
    element (+ in the +v direction); EI N·mm², one value or one per element. Returns stations (x, M N·mm (+ = sagging under + load), V N, v mm (+ along q))."""
    m = len(nodes)
    K = np.zeros((2 * m, 2 * m))
    F = np.zeros(2 * m)
    els = []
    EIs = list(EI) if isinstance(EI, (list, tuple)) else [EI] * (m - 1)
    for i in range(m - 1):
        L = nodes[i + 1] - nodes[i]
        k = EIs[i] / L ** 3 * np.array([[12, 6 * L, -12, 6 * L], [6 * L, 4 * L * L, -6 * L, 2 * L * L],
                                     [-12, -6 * L, 12, -6 * L], [6 * L, 2 * L * L, -6 * L, 4 * L * L]])
        p = q[i]
        fe = np.array([p * L / 2, p * L * L / 12, p * L / 2, -p * L * L / 12])
        idx = [2 * i, 2 * i + 1, 2 * i + 2, 2 * i + 3]
        K[np.ix_(idx, idx)] += k
        F[idx] += fe
        els.append((L, k, fe, idx, p, EIs[i]))
    fixed = {2 * nodes.index(s) for s in supports}
    free = [i for i in range(2 * m) if i not in fixed]
    d = np.zeros(2 * m)
    d[free] = np.linalg.solve(K[np.ix_(free, free)], F[free])
    out = []
    for i, (L, k, fe, idx, p, EIi) in enumerate(els):
        de = d[idx]
        f = k @ de - fe                                           # end forces on the element (v up = +q direction)
        F1, M1 = f[0], f[1]
        for j in range(n):
            x = L * j / (n - 1)
            xi = x / L
            H = np.array([1 - 3 * xi ** 2 + 2 * xi ** 3, L * (xi - 2 * xi ** 2 + xi ** 3), 3 * xi ** 2 - 2 * xi ** 3, L * (-xi ** 2 + xi ** 3)])
            v = float(H @ de + p * x * x * (L - x) ** 2 / (24 * EIi))
            # the usual sagging moment (v and p the same way) is −M1 + F1 x + p x²/2; here + = compression on the face the
            # load comes from (a simple span under + load: + p x (L − x) / 2)
            Mx = M1 - F1 * x - p * x * x / 2
            Vx = F1 + p * x
            out.append((nodes[i] + x, float(Mx), float(Vx), v))
    return out


# ----------------------------------------------------------------------------------------------- section data

def section_data(profile: str, grade: str, supplier: dict | None = None) -> dict:
    """Design data of one profile: geometry (cfs_section) with any supplier overrides. N, mm."""
    sup = dict((supplier or {}).get(profile, {}))
    bad = set(sup) - SUPPLIER_KEYS
    if bad:
        raise ValueError(f"supplier table for {profile}: unknown key(s) {sorted(bad)}; allowed {sorted(SUPPLIER_KEYS)}")
    from .cfs_section import parse_name
    t = parse_name(profile)["t"]
    st = plate_strength(grade, t)
    Fy, Fu = float(sup.get("Fy", st["Fy"])), float(sup.get("Fu", st["Fu"]))
    r = sup.get("r_inside")
    s = cfs_section(profile, Fy, None if r is None else float(r))
    p = s["props"]
    src = {}
    val = {}
    for k, v in (("A", p["A"]), ("Ix", p["Ix"]), ("Sx", p["Sx"]), ("J", p["J"]), ("Cw", p["Cw"])):
        val[k], src[k] = (float(sup[k]), "supplier") if k in sup else (v, "geometry")
    for k, key, mode in (("Mcrl", "bending", "local"), ("Mcrd", "bending", "distortional"), ("Pcrl", "compression", "local"),
                         ("Pcrd", "compression", "distortional")):
        if k in sup:
            val[k], src[k] = float(sup[k]), "supplier"
        else:
            m = s[key][mode]
            val[k], src[k] = (m["value"] if m else None), ("geometry (finite strip)" if m else "NOT IDENTIFIED")
    src["Fy"] = "supplier" if "Fy" in sup else st.get("source", grade)
    My, Py = val["Sx"] * Fy, val["A"] * Fy
    h_flat = s["H"] - 2 * (t + s["r_inside"])
    return {"profile": profile, "grade": grade, "kind": s["kind"], "H": s["H"], "t": t, "r_inside": s["r_inside"], "Fy": Fy, "Fu": Fu,
            **val, "My": My, "Py": Py, "h_flat": h_flat, "source": src, "a_local": s["bending"]["local"]["a"] if s["bending"]["local"] else None,
            "a_distortional": s["bending"]["distortional"]["a"] if s["bending"]["distortional"] else None,
            "note": s["bending"]["note"], "assumptions": s["assumptions"], "_r": None if r is None else float(r)}


def _shear_capacity(sd: dict) -> float:
    """φVn, N (vendored aisi_s100, kips / in inside)."""
    sec = A_.CFSSection(name=sd["profile"], t=sd["t"] / 25.4, Aw=sd["h_flat"] * sd["t"] / 25.4 ** 2, h_flat=sd["h_flat"] / 25.4)
    steel = A_.Steel(name=sd["grade"], Fy=sd["Fy"] / KSI, Fu=sd["Fu"] / KSI)
    r = A_.shear_strength(sec, steel)
    return r.design("LRFD") * 4448.2216152605


def flexure_capacity(sd: dict, M: float, Lb: float | None, Cb: float = 1.0, n: int = 1) -> dict:
    """φMn (N·mm) of n nested sections (a lap: 2) for a moment M at a station: M ≥ 0 → the sheeted flange in compression
    (Mne = My); M < 0 → the free flange, unbraced over Lb, Mcre × Cb (AISI S100-16 F2.1)."""
    My = sd["My"]
    if M >= 0 or Lb is None:
        mcre, Mne = math.inf, My
    else:
        mcre = Cb * Mcre(sd["profile"], sd["Fy"], Lb, sd["_r"]) * (sd["Sx"] / cfs_section(sd["profile"], sd["Fy"], sd["_r"])["props"]["Sx"])
        Mne = Mne_global(My, mcre)
    if sd["Mcrl"] is None or sd["Mcrd"] is None:
        return {"phiMn": 0.0, "Mne": Mne, "Mnl": None, "Mnd": None, "Mcre": mcre, "note": "local or distortional buckling not identified — NOT EVALUATED"}
    Mnl = Mnl_local(Mne, sd["Mcrl"])
    Mnd = Mnd_distortional(My, sd["Mcrd"])
    return {"phiMn": n * PHI_B * min(Mnl, Mnd), "Mne": Mne, "Mnl": Mnl, "Mnd": Mnd, "Mcre": mcre, "Cb": Cb, "n": n,
            "mode": "local-global" if Mnl <= Mnd else "distortional", "note": ""}


def axial_capacity(sd: dict, L: float) -> dict:
    Py = sd["Py"]
    pcre = Pcre(sd["profile"], sd["Fy"], L, sd["_r"])
    Pne = Pne_global(Py, pcre)
    if sd["Pcrl"] is None or sd["Pcrd"] is None:
        return {"phiPn": 0.0, "Pcre": pcre, "note": "local or distortional buckling not identified — NOT EVALUATED"}
    Pnl, Pnd = Pnl_local(Pne, sd["Pcrl"]), Pnd_distortional(Py, sd["Pcrd"])
    return {"phiPn": PHI_C * min(Pnl, Pnd), "Pcre": pcre, "Pne": Pne, "Pnl": Pnl, "Pnd": Pnd, "note": ""}


# ----------------------------------------------------------------------------------------------- one line

def _row(name, ref, demand, capacity, unit, note=""):
    r = demand / capacity if capacity > 0 else math.inf
    return {"name": name, "reference": ref, "demand": round(float(demand), 3), "capacity": round(float(capacity), 3),
            "ratio": round(r, 4) if math.isfinite(r) else math.inf, "unit": unit, "note": note}


def check_line(line: dict, sd: dict, combos: dict, deflection_limit: float) -> dict:
    """line: {id, kind, nodes, supports, braces, cases: {D, C, Lr, Win, Wout: [q per element, kN/m]}, P (eave strut, kN)}."""
    nodes, sup, br = line["nodes"], line["supports"], sorted(line["braces"])
    laps = line.get("laps", [])
    nsec = [2 if any(l0 - 1e-6 <= (nodes[i] + nodes[i + 1]) / 2 <= l1 + 1e-6 for l0, l1 in laps) else 1 for i in range(len(nodes) - 1)]
    EI = [203395.3 * sd["Ix"] * k for k in nsec]
    phiV = _shear_capacity(sd)
    Mnlo = Mnl_local(sd["My"], sd["Mcrl"]) if sd["Mcrl"] else None
    worst = None
    defl = None
    ax = axial_capacity(sd, max(b - a for a, b in zip(sup, sup[1:]))) if line.get("P") else None
    Pex = math.pi ** 2 * 203395.3 * sd["Ix"] / max(b - a for a, b in zip(sup, sup[1:])) ** 2 if line.get("P") else None
    for setname, cs in combos.items():
        for cname, fac in cs.items():
            q = [sum(f * line["cases"].get(c, [0.0] * (len(nodes) - 1))[i] for c, f in fac.items()) for i in range(len(nodes) - 1)]
            if any(not math.isfinite(v) for v in q):
                return {**_meta(line, sd), "ratio": math.inf, "passed": False, "combo": cname, "governing": "wind not evaluated",
                        "checks": [_row("C&C wind — NOT EVALUATED", "ASCE 7-16 Fig. 30.3-2A", 1.0, 0.0, "-", line.get("wind_note", ""))]}
            st = beam_line(nodes, sup, q, EI)
            if setname == "ASD":
                for i in range(len(nodes) - 1):
                    L = nodes[i + 1] - nodes[i]
                    cant = (nodes[i] not in sup) or (nodes[i + 1] not in sup)
                    lim = (2 * L if cant else L) / deflection_limit
                    seg = st[i * NST:(i + 1) * NST]
                    dmax = max(abs(s[3]) for s in seg)
                    if defl is None or dmax / lim > defl["ratio"]:
                        defl = {**_row(f"Deflection ({'2 × cantilever' if cant else 'span'} / {deflection_limit:g})", "Serviceability (user limit, ASD)", dmax, lim, "mm",
                                       f"{cname}, span {L:.0f} mm, gross Ix"), "combo": cname}
                continue
            Pk = 0.0
            if line.get("P"):
                Pk = line["P"] * max(fac.get("Win", 0.0), fac.get("Wout", 0.0))
            xs_ = np.array([s[0] for s in st])
            Ms_ = np.array([abs(s[1]) for s in st])
            cbs = {}
            for si, (x, M, V, _) in enumerate(st):
                ne = nsec[si // NST]
                k = next((j for j in range(len(br) - 1) if br[j] - 1e-6 <= x <= br[j + 1] + 1e-6), None)
                Lb = br[k + 1] - br[k] if k is not None else None
                if k is not None and k not in cbs:
                    a_, b_ = br[k], br[k + 1]
                    inside = (xs_ >= a_ - 1e-6) & (xs_ <= b_ + 1e-6)
                    Mmax = float(Ms_[inside].max()) if inside.any() else 0.0
                    MA, MB, MC = (float(np.interp(a_ + f * (b_ - a_), xs_, Ms_)) for f in (0.25, 0.5, 0.75))
                    cant = a_ < sup[0] - 1e-6 or b_ > sup[-1] + 1e-6
                    cbs[k] = 1.0 if cant or Mmax <= 0 else 12.5 * Mmax / (2.5 * Mmax + 3 * MA + 4 * MB + 3 * MC)
                fc = flexure_capacity(sd, M, Lb, cbs.get(k, 1.0), ne)
                rows = []
                B1 = 1.0
                if Pk > 0 and ax:
                    B1 = 1.0 / (1.0 - Pk * 1e3 / Pex) if Pk * 1e3 < Pex else math.inf
                    r_int = (Pk * 1e3 / ax["phiPn"] if ax["phiPn"] > 0 else math.inf) + (B1 * abs(M) / fc["phiMn"] if fc["phiMn"] > 0 else math.inf)
                    rows.append({**_row("Axial + bending (H1.2, B1 · M)", "AISI S100-16 H1.2, App. 1 (DSM)", r_int, 1.0, "-",
                                        f"P {Pk:.2f} kN, φPn {ax['phiPn'] / 1e3:.2f} kN (Pcre at the bay), B1 {B1:.3f}")})
                rows.append(_row("Flexure (DSM)", "AISI S100-16 App. 1 1.2.2 (F)", abs(M) / 1e6, fc["phiMn"] / 1e6, "kN·m",
                                 ("sheeted flange in compression, Mne = My" if M >= 0 else f"free flange in compression, Lb {Lb:.0f} mm, Cb {fc['Cb']:.2f}")
                                 + (", lap: 2 sections" if ne == 2 else "") + (" — " + fc["note"] if fc["note"] else "")))
                rows.append(_row("Shear", "AISI S100-16 G2 (vendored, φ 0.90)", abs(V) / 1e3, ne * phiV / 1e3, "kN"))
                if Mnlo:
                    ri = (abs(M) / (ne * PHI_B * Mnlo)) ** 2 + (abs(V) / (ne * phiV)) ** 2
                    rows.append(_row("Bending + shear (H2)", "AISI S100-16 H2", ri, 1.0, "-"))
                r = max(rw["ratio"] for rw in rows)
                if worst is None or r > worst["ratio"]:
                    worst = {"ratio": r, "combo": cname, "x": x, "M": M / 1e6, "V": V / 1e3, "P": Pk, "Lb": Lb, "checks": rows}
    checks = list(worst["checks"]) + ([defl] if defl else [])
    gov = max(checks, key=lambda c: c["ratio"])
    return {**_meta(line, sd), "ratio": gov["ratio"], "passed": all(c["ratio"] <= 1.0 for c in checks), "governing": gov["name"],
            "combo": worst["combo"] if gov is not defl else defl["combo"], "x": round(worst["x"], 1),
            "forces": {"M": round(worst["M"], 3), "V": round(worst["V"], 3), "P": round(worst["P"], 3), "Lb": worst["Lb"]},
            "checks": checks}


def _span_zones(line):
    """The worst C&C zone of each supported span (its cantilevers and lap elements folded in)."""
    if not line.get("zones"):
        return None
    sups, nodes = line["supports"], line["nodes"]
    spans = list(zip(sups, sups[1:]))
    worst = {}
    for i, z in enumerate(line["zones"]):
        j = spans.index(_span_of(nodes, sups, i))
        worst[j] = max(worst.get(j, z), z)
    return [worst[j] for j in range(len(spans))]


def _meta(line, sd):
    return {"id": line["id"], "kind": line["kind"], "profile": sd["profile"], "grade": sd["grade"], "spans": [round(b - a, 1) for a, b in zip(line["supports"], line["supports"][1:])],
            "tributary": round(line["trib"], 1), "zones": _span_zones(line), "loads_kN_m": line.get("loads"),
            "section": {k: (round(sd[k], 1) if isinstance(sd[k], float) else sd[k]) for k in ("A", "Ix", "Sx", "J", "Fy")} |
                       {"My_kNm": round(sd["My"] / 1e6, 3), "Mcrl_kNm": round(sd["Mcrl"] / 1e6, 3) if sd["Mcrl"] else None,
                        "Mcrd_kNm": round(sd["Mcrd"] / 1e6, 3) if sd["Mcrd"] else None, "source": sd["source"]}}


# ----------------------------------------------------------------------------------------------- the building

def _cluster(xs, tol=150.0):
    out = []
    for x in sorted(xs):
        if out and x - out[-1][-1] <= tol:
            out[-1].append(x)
        else:
            out.append([x])
    return [sum(c) / len(c) for c in out]


def _roof_zone(x0, x1, y0, y1, Lb, span, a):
    end = x0 < a or x1 > Lb - a
    edge = y0 < a or y1 > span - a or (y0 < span / 2 + a and y1 > span / 2 - a)
    return "3" if end and edge else "2" if end or edge else "1"


def _wind(wind, zone, span_mm, trib_mm, theta):
    try:
        cp = cladding_pressure(wind, zone, effective_wind_area(span_mm, trib_mm), theta_deg=theta)
        return cp.inward, cp.outward, None
    except Exception as e:            # bimsteelauto refuses a roof above 7° (Fig. 30.3-2A)
        return math.nan, math.nan, str(e)


def building_lines(out: dict, li) -> list[dict]:
    """Every purlin, eave strut, girt and gable-girt line of a generated building with its loads per element (kN/m)."""
    inp = out["input"]
    span, eave, slope = float(inp["span"]), float(inp["eave_height"]), float(inp["roof_slope"])
    c = 1 / math.sqrt(1 + slope * slope)
    theta = math.degrees(math.atan(slope))
    frames = sorted(g["at"] for g in out["grids"]["x"])
    Lb_ = frames[-1] - frames[0]
    wind = envelope_pressures(_geom(inp), li.site())
    a = wind.end_zone_a
    rows = _cluster([m["start"][0] for m in out["members"] if m["role"] == "sag_rod"])
    ms = out["members"]
    lines = []

    def pieces(role_set, key):
        g = {}
        for m in ms:
            if m["role"] in role_set:
                g.setdefault(key(m), []).append(m)
        return g

    # ---- roof
    roof = pieces({"purlin", "ridge_purlin", "eave_strut"}, lambda m: m["line"])
    for side in "AB":
        ids = sorted((k for k in roof if k[1] == side), key=lambda k: int(k[2:]))
        ss = [(roof[k][0]["start"][1] / c) if side == "A" else ((span - roof[k][0]["start"][1]) / c) for k in ids]
        L_slope = (span / 2) / c
        for n, k in enumerate(ids):
            lo = (ss[n] - ss[n - 1]) / 2 if n > 0 else ss[0]
            hi = (ss[n + 1] - ss[n]) / 2 if n < len(ids) - 1 else (L_slope - ss[n])
            trib = lo + hi
            ps = roof[k]
            role = ps[0]["role"]
            xa = min(min(p["start"][0], p["end"][0]) for p in ps)
            xb = max(max(p["start"][0], p["end"][0]) for p in ps)
            y = ps[0]["start"][1]
            ys = sorted([y - lo * c, y + hi * c] if side == "A" else [y - hi * c, y + lo * c])
            sd_prof = ps[0]["profile"]
            if role == "eave_strut":                               # butt-jointed: one simple span per bay
                spans = [(frames[j], frames[j + 1], [xa] if j == 0 else [], [xb] if j == len(frames) - 2 else []) for j in range(len(frames) - 1)]
            else:
                spans = [(frames[0], frames[-1], [xa], [xb])]
            laps = [] if role == "eave_strut" else _laps(ps, 0)
            for sp in spans:
                x0, x1, left, right = sp
                sups = [x for x in frames if x0 - 1e-6 <= x <= x1 + 1e-6]
                nodes = sorted(set(left + sups + right + [v for l in laps for v in l]))
                lines.append(_roof_line(f"{k}" + (f"-{frames.index(x0) + 1}" if role == "eave_strut" else ""), role, sd_prof, ps[0].get("material", "S350GD"),
                                        nodes, sups, [x for x in rows if x0 < x < x1] + [nodes[0], nodes[-1]] + sups, trib, ys, c, theta, span, Lb_, a, wind, li))
                lines[-1]["laps"] = laps
    # ---- side-wall girts
    walls = pieces({"girt"}, lambda m: m["line"])
    for side in "AB":
        ids = sorted((k for k in walls if k[1] == side), key=lambda k: int(k[2:]))
        zs = [walls[k][0]["start"][2] for k in ids]
        for n, k in enumerate(ids):
            lo = (zs[n] - zs[n - 1]) / 2 if n > 0 else zs[0] / 2
            hi = (zs[n + 1] - zs[n]) / 2 if n < len(ids) - 1 else (eave - zs[n]) / 2
            ps = walls[k]
            xa = min(min(p["start"][0], p["end"][0]) for p in ps)
            xb = max(max(p["start"][0], p["end"][0]) for p in ps)
            laps = _laps(ps, 0)
            nodes = sorted(set([xa, xb] + frames + [v for l in laps for v in l]))
            lines.append(_wall_line(k, "girt", ps[0]["profile"], ps[0].get("material", "S350GD"), nodes, frames, [xa, xb] + frames,
                                    lo + hi, lambda u0, u1: u0 < a or u1 > Lb_ - a, theta, wind))
            lines[-1]["laps"] = laps
    # ---- gable girts
    for ew in out["end_walls"]:
        tag = "G" + ew["end"][0].upper()
        gg = pieces({"gable_girt"}, lambda m: (m["id"].split("-")[0]))
        ids = sorted((k for k in gg if k.startswith(tag)), key=lambda k: int(k[2:]))
        zs = [gg[k][0]["start"][2] for k in ids]
        for n, k in enumerate(ids):
            lo = (zs[n] - zs[n - 1]) / 2 if n > 0 else zs[0] / 2
            hi = (zs[n + 1] - zs[n]) / 2 if n < len(ids) - 1 else (zs[n] - zs[n - 1]) / 2 if n else zs[0] / 2
            ps = gg[k]
            ya = min(min(p["start"][1], p["end"][1]) for p in ps)
            yb = max(max(p["start"][1], p["end"][1]) for p in ps)
            sups = [y for y in sorted(ew["supports"]) if ya < y < yb]
            if len(sups) < 2:
                continue
            laps = _laps(ps, 1)
            nodes = sorted(set([ya, yb] + sups + [v for l in laps for v in l]))
            lines.append(_wall_line(k, "gable_girt", ps[0]["profile"], ps[0].get("material", "S350GD"), nodes, sups, [ya, yb] + sups,
                                    lo + hi, lambda u0, u1: u0 < a or u1 > span - a, theta, wind))
            lines[-1]["laps"] = laps
    return lines


def _laps(ps, axis):
    """Overlaps of consecutive pieces of one line along an axis (0 = x, 1 = y): the nested-Z laps."""
    iv = sorted((min(p["start"][axis], p["end"][axis]), max(p["start"][axis], p["end"][axis])) for p in ps)
    return [(b0, a1) for (a0, a1), (b0, b1) in zip(iv, iv[1:]) if b0 < a1 - 1e-6]


def _span_of(nodes, sups, i):
    """The supported span an element belongs to (a cantilever: its neighbouring span)."""
    x0, x1 = nodes[i], nodes[i + 1]
    inside = [(sups[j], sups[j + 1]) for j in range(len(sups) - 1) if sups[j] - 1e-6 <= x0 and x1 <= sups[j + 1] + 1e-6]
    if inside:
        return inside[0]
    return (sups[0], sups[1]) if x1 <= sups[0] + 1e-6 else (sups[-2], sups[-1])


def _roof_line(lid, role, profile, grade, nodes, sups, braces, trib, ys, c, theta, span, Lb_, a, wind, li):
    sd_A = cfs_section(profile, 350.0)["props"]["A"]          # self weight only (independent of Fy)
    sw = sd_A * 1e-6 * STEEL_KN_M3
    D = (li.roof_sheeting * trib / 1000 + sw) * c
    C = li.collateral * trib / 1000 * c * c
    maxspan = max(b - a_ for a_, b in zip(sups, sups[1:]))
    lr = roof_live_load(trib * c * maxspan / 1e6, math.tan(math.radians(theta)), Lo=li.Lo)
    Lr = lr.Lr * trib / 1000 * c * c
    win, wout, zones, notes = [], [], [], set()
    for i in range(len(nodes) - 1):
        s0, s1 = _span_of(nodes, sups, i)
        x0, x1 = min(nodes[i], s0), max(nodes[i + 1], s1)
        z = _roof_zone(x0, x1, ys[0], ys[1], Lb_, span, a)
        pi_, po, note = _wind(wind, z, s1 - s0, trib, theta)
        if note:
            notes.add(note)
        win.append(pi_ * trib / 1000)
        wout.append(po * trib / 1000)
        zones.append(z)
    n = len(nodes) - 1
    return {"id": lid, "kind": role, "profile": profile, "grade": grade, "nodes": nodes, "supports": sups, "braces": sorted(set(braces)),
            "trib": trib, "zones": zones, "wind_note": "; ".join(sorted(notes)),
            "cases": {"D": [D] * n, "C": [C] * n, "Lr": [Lr] * n, "Win": win, "Wout": wout},
            "loads": {"D": round(D, 4), "C": round(C, 4), "Lr": round(Lr, 4), "Lr_kPa": round(lr.Lr, 4),
                      "W_in": [round(v, 4) for v in win], "W_out": [round(v, 4) for v in wout]}, "combos": COMBOS_ROOF}


def _wall_line(lid, role, profile, grade, nodes, sups, braces, trib, corner, theta, wind):
    win, wout, zones = [], [], []
    for i in range(len(nodes) - 1):
        s0, s1 = _span_of(nodes, sups, i)
        z = "5" if corner(min(nodes[i], s0), max(nodes[i + 1], s1)) else "4"
        pi_, po, _ = _wind(wind, z, s1 - s0, trib, theta)
        win.append(pi_ * trib / 1000)
        wout.append(po * trib / 1000)
        zones.append(z)
    return {"id": lid, "kind": role, "profile": profile, "grade": grade, "nodes": nodes, "supports": sups, "braces": sorted(set(braces)),
            "trib": trib, "zones": zones, "cases": {"Win": win, "Wout": wout},
            "loads": {"W_in": [round(v, 4) for v in win], "W_out": [round(v, 4) for v in wout]}, "combos": COMBOS_WALL}


def cfs_checks(b: BuildingInput, li, *, supplier: dict | None = None, limits: ServiceLimits | None = None, out: dict | None = None) -> dict:
    """Step 6 for a building: every purlin, girt, gable-girt and eave-strut line."""
    limits = limits or ServiceLimits()
    if out is None:
        b, _ = resolve(b)
        out = peb_building(b)
    lines = building_lines(out, li)
    braces = [m for m in out["members"] if m["role"] in ("roof_brace", "wall_brace")]
    struts = {}
    if braces and out.get("braced_bays"):
        bs = longitudinal_bracing(_geom(out["input"]), braces, [j - 1 for j in out["braced_bays"]], longitudinal_feed(out, li))["sets"]["LRFD"]
        struts = {j: abs(v) for j, v in bs["strut"]}
    res = {"purlins": [], "eave_struts": [], "girts": [], "gable_girts": []}
    cache = {}
    for ln in lines:
        key = (ln["profile"], ln["grade"])
        if key not in cache:
            cache[key] = section_data(*key, supplier)
        if ln["kind"] == "eave_strut":
            bay = int(ln["id"].rsplit("-", 1)[1])
            ln["P"] = struts.get(bay, 0.0)
        r = check_line(ln, cache[key], ln["combos"], limits.purlin)
        if ln["kind"] == "eave_strut":
            r["P_strut_kN"] = ln.get("P", 0.0)
        res[{"purlin": "purlins", "ridge_purlin": "purlins", "eave_strut": "eave_struts", "girt": "girts", "gable_girt": "gable_girts"}[ln["kind"]]].append(r)
    allr = [r["ratio"] for v in res.values() for r in v]
    sections = {f"{k[0]} {k[1]}": {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in cache.items()}
    return {"banner": BANNER, "code": "AISI S100-16 (DSM), LRFD; deflection ASD", **res, "sections": sections,
            "max_ratio": max(allr) if allr else None, "assumptions": list(ASSUMPTIONS), "deflection_limit": limits.purlin,
            "designed": False, "VERIFIED": False}
