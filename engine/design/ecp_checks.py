# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 4 step 7: main-frame members to ECP 205-LRFD (2008), side by side with AISC 360-16. NOT FOR ISSUE.

Decisions (user, 2026-11-09):
    loads      the SAME ASCE 7-16 LRFD combinations as the AISC side (ECP 205 checks the resistance side only: φ,
               classification, buckling curves, its clauses). ECP 201 stays refused.
    analysis   its own second-order (P-Δ) solve at NOMINAL stiffness, no notional loads (no B2 double count), every
               member in ≥ 4 elements (P-δ) — `ecp_solve`
    K          in plane: the sway alignment chart (cl. 2.2.1.3; Jackson–Mooreland, solved from its equation
                   (GA GB (π/K)² − 36) / (6 (GA + GB)) = (π/K) / tan(π/K))
               with G at the knee = (Ic / Lc) / (Ir / Lr): Ic the column's LARGEST I (at the knee), Lc its length, Ir
               the rafter's SMALLEST I, Lr the whole sloping rafter (both halves: in symmetric sway the rafter bends
               in double curvature), G base 10 pinned / 1 fixed — the chart, the G rules and the base values are
               Claude's reading, VERIFIED False, TO CONFIRM with the user from the printed code; rafters K = 1 over
               the half length (knee to ridge); out of plane K = 1 between FULL brace points (both flanges held:
               a girt / purlin with a flange brace at the same point, and the member ends)
    slender    class 3 sections (Table 2.12), unequal flanges and h/tw > 260 are NOT EVALUATED (ratio inf) until
               ch. 6 and mono-symmetric flexure are added to ecp205-lrfd and confirmed by the user
Checks, through the user's ecp205-lrfd library (ton / cm / t/cm² inside — ONE boundary here, `_cm`, `_t`, `_tcm`):
    classification Table 2.12 (welded: rolled=False); compression cl. 4.2 (φ 0.80, Q for slender elements), the
    member's φPn = the smallest over its stations (a tapered member: conservative, stated); flexure cl. 5.1.3 (φ 0.85)
    with Lb = the compression flange's brace segment at the station (M + top / outer flange, as the AISC side), Cb from
    the quarter-point moments of that segment (eq. 5.2); shear cl. 5.2.2 (φ 0.85, Aw = d tw); beam-column cl. 7.1
    (eq. 7.1a / 7.1b; tension cl. 7.3 with cl. 3.1 tension, Ae = Ag — no holes at the stations). Mu from the
    second-order solve (cl. 2.2.2: no B1 / B2 on top).
Fy / Fu: the same plates as the AISC side (the lowest plate of the design member); an EN grade's Fy goes into the ECP
equations as it is — the ECP grades St 37 / 44 / 52 are confirmed, EN values VERIFIED False (inputs.py).
"""

from __future__ import annotations

import dataclasses
import math

import numpy as np

from scipy.optimize import brentq

import ecp205
from ecp205 import ISection, Q_factor, beam_column, classify, compression, flexure_I, shear_web, tension
from ecp205.core import PHI as ECP_PHI

from ..analysis.solve import DAM_MIN_SEGMENTS, analyse_frame_line
from .frame_checks import ChainTaper, EPS
from .inputs import design_members, restraints

BANNER = "NOT FOR ISSUE — ECP 205-LRFD member checks (resistance side only, ASCE 7-16 LRFD forces) with open verification flags"
KN_PER_T = 9.80665
G_BASE = {"pinned": 10.0, "fixed": 1.0}
VERIFIED = {"alignment_chart": False, "G_rules": False, "G_base": False, "tapered_min_section": False, "full_brace_points": False}
NOT_EVALUATED = "NOT EVALUATED"


def _cm(mm):
    return mm / 10.0


def _t(kN):
    return kN / KN_PER_T


def _tcm(kNm):
    return kNm * 100.0 / KN_PER_T


def _kN(t):
    return t * KN_PER_T


def _kNm(tcm):
    return tcm * KN_PER_T / 100.0


def _tcm2(MPa):
    return MPa / 98.0665


# --------------------------------------------------------------------------------------------- analysis and K

def ecp_layout(layout):
    """Nominal stiffness (1.0), ≥ 4 elements per member, no notional loads."""
    return dataclasses.replace(layout, settings=dataclasses.replace(layout.settings, stiffness_factor=1.0, min_segments=DAM_MIN_SEGMENTS))


def ecp_solve(info, fl, *, label: str = "") -> dict:
    """The ECP side's own solve: every combination at nominal stiffness, P-Δ, no notional loads."""
    info2 = dataclasses.replace(info, layout=ecp_layout(info.layout))
    r = analyse_frame_line(info2, fl, p_delta=True, label=label, dam=False)
    r["ecp_solve"] = {"stiffness": 1.0, "min_segments": DAM_MIN_SEGMENTS, "notional": 0.0, "p_delta": True}
    return r


def k_sway(GA: float, GB: float) -> float:
    """Effective length factor of a sway column from the alignment chart's equation (VERIFIED False)."""
    if GA <= 0 or GB <= 0:
        raise ValueError("G must be positive")
    f = lambda x: (GA * GB * x * x - 36.0) / (6.0 * (GA + GB)) - x * math.cos(x) / math.sin(x)
    x = brentq(f, 1e-6, math.pi - 1e-9)
    return math.pi / x


def column_K(info, base: str) -> dict:
    """In-plane K of each column of a frame line (the sway chart, G at the knee from the analysis members)."""
    lay = {m.mark: m for m in info.layout.members}
    dms = {d["name"]: d for d in design_members(info)}
    out = {}
    for side in ("A", "B"):
        col = dms[f"column {side}"]
        raf_a, raf_b = dms["rafter A"], dms["rafter B"]
        tc = ChainTaper("c", [(c["s0"], lay[c["mark"]].taper) for c in col["chain"]])
        Ic = max(tc.at(s).Ix for s in (0.0, tc.length / 2, tc.length - EPS))
        Ir, Lr = math.inf, 0.0
        for raf in (raf_a, raf_b):
            tr = ChainTaper("r", [(c["s0"], lay[c["mark"]].taper) for c in raf["chain"]])
            Ir = min(Ir, min(tr.at(tr.length * k / 20).Ix for k in range(20)))
            Lr += tr.length
        G_top = (Ic / tc.length) / (Ir / Lr)
        G_bot = G_BASE[base]
        out[f"column {side}"] = {"K": k_sway(G_top, G_bot), "G_top": G_top, "G_base": G_bot, "Ic_mm4": Ic, "Ir_mm4": Ir, "Lc": tc.length, "Lr": Lr}
    return out


# --------------------------------------------------------------------------------------------- one design member

def _isec(w, name="BU") -> ISection | None:
    if abs(w.bf_top - w.bf_bot) > 1e-6 or abs(w.tf_top - w.tf_bot) > 1e-6:
        return None
    return ISection(name, d=_cm(w.d), bf=_cm(w.bf_top), tf=_cm(w.tf_top), tw=_cm(w.tw), r=0.0, rolled=False)


def _row(name, clause, demand, capacity, unit, governing="", note=""):
    r = float(abs(demand) / capacity) if capacity > 0 else math.inf
    return {"name": name, "reference": f"ECP 205-LRFD cl. {clause}", "demand": round(float(demand), 3), "capacity": round(float(capacity), 3),
            "ratio": round(r, 4) if math.isfinite(r) else math.inf, "unit": unit, "governing": governing, "note": note}


def _segment(points, s):
    for a, b in zip(points, points[1:]):
        if a - 1e-6 <= s <= b + 1e-6:
            return a, b
    return points[0], points[-1]


def check_member_ecp(dm, info, result, rs, strength, K_in, lrfd) -> dict:
    lay = {m.mark: m for m in info.layout.members}
    taper = ChainTaper(dm["name"], [(c["s0"], lay[c["mark"]].taper) for c in dm["chain"]])
    L = taper.length
    Fy, Fu = _tcm2(strength["Fy"]), _tcm2(strength["Fu"])
    top = [0.0] + list(rs["top"]) + [L]
    bot = [0.0] + list(rs["bottom"]) + [L]
    full = [0.0] + sorted(s for s in rs["top"] if any(abs(s - q) <= 50.0 for q in rs["bottom"])) + [L]
    KLy = max(b - a for a, b in zip(full, full[1:]))
    KLx = K_in * L
    # member compression capacity: the smallest over the stations (tapered: conservative)
    phiPn, pn_note, ne = math.inf, "", None
    for k in range(21):
        s = min(max(L * k / 20, EPS), L - EPS)
        w = taper.at(s)
        sec = _isec(w)
        if sec is None:
            ne = "unequal flanges: mono-symmetric I not in ecp205-lrfd (ch. 6 / mono-symmetric flexure to be added)"
            break
        Q = Q_factor(sec, Fy)
        cx = compression(sec.A, sec.rx, _cm(KLx), Fy, Q)
        cy = compression(sec.A, sec.ry, _cm(KLy), Fy, Q)
        c = min((cx, "in plane"), (cy, "out of plane"), key=lambda v: v[0].capacity)
        if c[0].capacity < phiPn:
            phiPn, pn_note = c[0].capacity, f"{c[1]}, {c[0].governing}, Q {Q:.3f}, at s {s:.0f}"
    worst = None
    for combo in lrfd:
        sts = []
        for c in dm["chain"]:
            Lc = c["length"]
            for x, P, V, M in result["results"][combo]["members"][c["mark"]]:
                sts.append((c["s0"] + min(max(x, EPS), Lc - EPS), float(P), float(V), float(M)))
        sts.sort()
        xs = [s[0] for s in sts]
        Ms = [abs(s[3]) for s in sts]

        def m_at(v):
            return float(np.interp(v, xs, Ms))

        for s, P, V, M in sts:
            w = taper.at(s)
            sec = _isec(w)
            rows = []
            if ne or sec is None:
                rows.append(_row(f"Member — {NOT_EVALUATED}", "2.3.1 / ch. 6", 1.0, 0.0, "-", note=ne or "unequal flanges"))
            else:
                cl = classify(sec, Fy, "bending")
                pts = top if M >= 0 else bot
                a, b = _segment(pts, s)
                inside = [abs(q[3]) for q in sts if a - 1e-6 <= q[0] <= b + 1e-6]
                Mmax = max(inside) if inside else abs(M)
                Cb = ecp205.Cb_quarter(Mmax, m_at(a + (b - a) / 4), m_at((a + b) / 2), m_at(a + 3 * (b - a) / 4)) if Mmax > 0 else 1.0
                if cl["class"] == 3:
                    rows.append(_row(f"Flexure — {NOT_EVALUATED} (class 3)", "2.3.1, Table 2.12", 1.0, 0.0, "-",
                                     note=f"web dw/tw {cl['web']['lambda']:.1f} (λr {cl['web']['lr']:.1f}), flange c/tf {cl['flange']['lambda']:.1f} "
                                          f"(λr {cl['flange']['lr']:.1f}): effective properties / ch. 6 not yet in ecp205-lrfd"))
                else:
                    fx = flexure_I(sec, Fy, Lb=_cm(b - a), Cb=Cb, Mu=_tcm(abs(M)))
                    phiMn = fx.capacity
                    rows.append(_row("Flexure Mx", "5.1.3", abs(M), _kNm(phiMn), "kN·m", fx.governing,
                                     f"class {cl['class']}, Lb {b - a:.0f} mm ({'top/outer' if M >= 0 else 'bottom/inner'} flange), Cb {Cb:.2f}"))
                    if P > 0:
                        bc = beam_column(_t(P), phiPn, _tcm(abs(M)), phiMn)
                        rows.append(_row("Beam-column", "7.1", bc.demand, 1.0, "-", bc.governing, f"φPn {_kN(phiPn):.1f} kN ({pn_note})"))
                    elif P < 0:
                        tc = tension(sec.A, sec.A, Fy, Fu, _t(-P))
                        bc = beam_column(_t(-P), tc.capacity, _tcm(abs(M)), phiMn)
                        rows.append(_row("Beam-column (tension)", "7.3", bc.demand, 1.0, "-", bc.governing, f"φTn {_kN(tc.capacity):.1f} kN"))
                try:
                    sv = shear_web(sec, Fy, Vu=_t(abs(V)), h=_cm(w.d - w.tf_top - w.tf_bot))
                    rows.append(_row("Shear Vy", "5.2.2", abs(V), _kN(sv.capacity), "kN", sv.governing))
                except ValueError as e:
                    rows.append(_row(f"Shear — {NOT_EVALUATED}", "5.2.2 / 6.3", 1.0, 0.0, "-", note=str(e)))
            r = max(x["ratio"] for x in rows)
            if worst is None or r > worst["ratio"]:
                worst = {"ratio": r, "combo": combo, "x": s, "P": P, "V": V, "M": M, "checks": rows}
    gov = max(worst["checks"], key=lambda c: c["ratio"])
    return {"name": dm["name"], "id": dm["id"], "length": round(L, 1), "Fy": strength["Fy"], "ratio": worst["ratio"], "passed": worst["ratio"] <= 1.0,
            "governing": gov["name"], "combo": worst["combo"], "x": round(worst["x"], 1),
            "forces": {"P": round(worst["P"], 3), "V": round(worst["V"], 3), "M": round(worst["M"], 3)},
            "K_in_plane": round(K_in, 4), "KL_in_plane": round(KLx, 1), "KL_out_of_plane": round(KLy, 1),
            "phiPn_kN": round(_kN(phiPn), 3) if math.isfinite(phiPn) else None, "checks": worst["checks"]}


def ecp_frame_line(info, result: dict, out: dict, x_frame: float, strengths: dict, base: str = "pinned") -> dict:
    """ECP 205-LRFD checks of every design member of one frame line, from the ECP solve's result."""
    lrfd = [c for c, s in result["combos"] if s == "LRFD"]
    if not lrfd:
        raise ValueError("no LRFD combinations in the analysis result: nothing to check")
    rs = restraints(out, info, x_frame)
    Ks = column_K(info, base)
    members = []
    for dm in design_members(info):
        st = [strengths[c["mark"]] for c in dm["chain"]]
        strength = {"Fy": min(r["Fy"] for r in st), "Fu": min(r["Fu"] for r in st)}
        K = Ks[dm["name"]]["K"] if dm["kind"] == "column" else 1.0
        members.append(check_member_ecp(dm, info, result, rs[dm["name"]], strength, K, lrfd))
    return {"banner": BANNER, "code": "ECP 205-LRFD (2008)", "loads": "ASCE 7-16 LRFD combinations (user decision 2026-11-09)",
            "members": members, "K": {k: {kk: round(vv, 4) for kk, vv in v.items()} for k, v in Ks.items()},
            "max_ratio": max(m["ratio"] for m in members), "open_flags": sorted(f"engine.design.ecp_checks.{k}" for k, v in VERIFIED.items() if not v),
            "phi": {k: ECP_PHI[k] for k in ("compression", "flexure", "shear", "tension_yield")}, "designed": False}


def side_by_side(aisc: dict, ecp: dict, governing: str = "AISC") -> dict:
    """Per design member: both ratios, and the governing code's (a project setting: "AISC" default, "ECP")."""
    if governing not in ("AISC", "ECP"):
        raise ValueError("governing code must be AISC or ECP")
    e = {m["name"]: m for m in ecp["members"]}
    rows = []
    for m in aisc["members"]:
        em = e[m["name"]]
        rows.append({"name": m["name"], "id": m["id"], "AISC": m["ratio"], "AISC_governing": m["governing"], "ECP": em["ratio"],
                     "ECP_governing": em["governing"], "ratio": m["ratio"] if governing == "AISC" else em["ratio"]})
    return {"governing_code": governing, "members": rows, "max_ratio": max(r["ratio"] for r in rows),
            "banner": "NOT FOR ISSUE — two codes side by side; the governing one by the project setting"}


def frame_line_both(b, li, i: int, *, governing: str = "AISC", step: float = 0.10, stability: str = "dg25") -> dict:
    """Frame line i (0-based) of a building: the AISC 360-16 check (DAM solve) and the ECP 205 check (its own solve),
    side by side."""
    from ..analysis.building_analysis import _line_setup
    from ..analysis.secondary_weight import secondary_kpa
    from ..peb.building import peb_building, resolve
    from ..peb.builtup_frame import builtup_frame_members
    from .frame_checks import check_frame_line, strengths_by_mark

    b, _ = resolve(b)
    out = peb_building(b)
    x = b.frame_xs()[i]
    ms = builtup_frame_members(b.span, b.eave_height, b.roof_slope, x, str(i + 1), b.sizes)
    info, fl, fy = _line_setup(b, li, i, secondary_kpa(out), step, with_fy=True)
    st = strengths_by_mark(ms)
    aisc = check_frame_line(info, analyse_frame_line(info, fl, fy=fy, label=f"Frame line {i + 1}"), out, x, st, stability=stability)
    ecp = ecp_frame_line(info, ecp_solve(info, fl, label=f"Frame line {i + 1} (ECP)"), out, x, st, base=li.base)
    return {"line": i + 1, "x": x, "AISC": aisc, "ECP": ecp, "side_by_side": side_by_side(aisc, ecp, governing)}
