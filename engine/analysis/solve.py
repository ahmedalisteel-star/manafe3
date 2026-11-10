# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 3 step 4 / Phase 4 step 2: solve one frame line (bimsteelauto FrameAnalysis, PyNite, P-Delta) and shape the results.

Every load case is ALSO solved on its own, unfactored (user decision: the foundation designer applies their own factors),
next to every LRFD and ASD combination. Each result carries its set: "case" | "LRFD" | "ASD". Strength values (member
forces, governing moments) are reported from LRFD; deflection and drift from ASD (user decision).

Direct Analysis Method (AISC 360-16 Chapter C, user decision 2026-11-08) — for the STRENGTH (LRFD) combinations only:
    stiffness   0.8 × every stiffness (C2.3(a): applying it to all members is permitted) — bimsteelauto 0.14.2
                ModelSettings.stiffness_factor = 0.8 (E and G, so EI and EA); τb = 1, CHECKED: αPr/Pns ≤ 0.5 at every station (α = 1.0 LRFD;
                Pns = Fy·A — the gross cross-section strength; for a slender section Pns is lower, refined with E7 in step 3)
    τb > ...    if αPr/Pns > 0.5 anywhere: C2.3(c) — keep τb = 1 and add 0.001·α·Yi to the notional loads (0.003 in all)
    notional    C2.2b: Ni = 0.002·α·Yi, applied where the gravity load is: each D / C / Lr line load gets a horizontal twin
                0.002 × its vertical intensity (per metre of member) — cases "ND", "NC", "NLr" — in EVERY LRFD combination
                (conservative: the C2.2b(4) exemption for lateral combinations is not used), in the direction of that
                combination's net lateral load (it adds to it); a gravity-only combination is solved in BOTH directions
                ("… [+N]", "… [-N]")
    P-δ         C2.1 needs P-Δ AND P-δ: every member — constant rafter segments and rigid arms too — is split into at
                least DAM_MIN_SEGMENTS = 4 elements (ModelSettings.min_segments); PyNite's P-Delta solution then carries
                the members' own curvature (4 elements: within 1 % of the exact braced beam-column — test_dam.py)
The service set (unfactored cases and ASD) uses the nominal stiffness and no notional loads (deflections and drift are
judged on the real frame). Both sets run P-Delta.
Units: kN, kN·m, mm. Reactions (H, V, M) are the forces the support gives the frame; P is positive in compression;
M is positive when the member's TOP flange is in compression (rafter: top flange; column: outer flange) — bimsteelauto
0.14.1's design sign.
Drift is the largest |horizontal movement| of the eave (knee) nodes. Note: bimsteelauto's Envelope.eave_drift looks for
nodes named "E…" (its own layouts) and would return 0 here — not used.
"""

from __future__ import annotations

import dataclasses
import math

from bimsteelauto.analysis import FrameAnalysis, LoadDirection

from .frame_loads import Load

DAM_STIFFNESS = 0.8
NOTIONAL = 0.002            # × α (1.0 for LRFD) × Yi
NOTIONAL_TAU = 0.001        # the C2.3(c) addition when αPr/Pns > 0.5
ALPHA_LRFD = 1.0
DAM_MIN_SEGMENTS = 4
GRAVITY_CASES = ("D", "C", "Lr")


def strength_layout(layout):
    """The same frame for the strength (DAM) solve: stiffness × 0.8, at least 4 elements per member (P-δ)."""
    return dataclasses.replace(layout, settings=dataclasses.replace(layout.settings, stiffness_factor=DAM_STIFFNESS,
                                                                    min_segments=DAM_MIN_SEGMENTS))


def _geom(info):
    return {m.mark: m for m in info.layout.members}


def _fx_per_length(m, ld: Load, w: float) -> float:
    """Horizontal force per mm of member of one line load (kN/m), + toward +X (bimsteelauto's conventions)."""
    (xi, yi), (xj, yj) = m.i_point, m.j_point
    if ld.direction is LoadDirection.GLOBAL_X:
        return w
    if ld.direction is LoadDirection.NORMAL and not abs(xj - xi) < 1e-9:   # a roof pressure: + onto the top face
        nx, ny = -(yj - yi), (xj - xi)
        if ny < 0:
            nx, ny = -nx, -ny
        return -w * nx / math.hypot(nx, ny)
    return 0.0


def notional_loads(info, fl, ratio: float) -> list[Load]:
    """A horizontal twin (+X) of every gravity line load: ratio × its vertical intensity per metre of member."""
    g = _geom(info)
    out = []
    for ld in fl.loads:
        if ld.case not in GRAVITY_CASES:
            continue
        m = g[ld.member_mark]
        if ld.direction is LoadDirection.GLOBAL_Y:
            k = 1.0
        elif ld.direction is LoadDirection.GLOBAL_Y_PROJECTED:
            k = abs(m.j_point[0] - m.i_point[0]) / m.length            # per metre of plan → per metre of member
        else:
            raise ValueError(f"gravity case {ld.case} has a {ld.direction.name} load — no notional rule for it")
        w0 = ratio * ld.w * k
        w1 = None if ld.w_end is None else ratio * ld.w_end * k
        out.append(Load("N" + ld.case, ld.member_mark, w0, LoadDirection.GLOBAL_X,
                        f"notional {ratio:g} x Yi (AISC 360-16 C2.2b) of {ld.case}: {ld.origin}", w_end=w1))
    return out


def net_lateral(info, fl, factors: dict) -> float:
    """Σ factor × horizontal force of a combination's loads, kN (+ toward +X)."""
    g = _geom(info)
    tot = 0.0
    for ld in fl.loads:
        f = factors.get(ld.case, 0.0)
        if not f:
            continue
        m = g[ld.member_mark]
        w = (ld.w + (ld.w if ld.w_end is None else ld.w_end)) / 2
        tot += f * _fx_per_length(m, ld, w) * m.length / 1000
    return tot


def strength_combinations(info, fl) -> list[tuple[str, dict, str]]:
    """The LRFD combinations with the notional cases added (direction: the combination's net lateral load)."""
    out = []
    for name, factors, s in fl.combinations:
        if s != "LRFD":
            continue
        grav = {c: f for c, f in factors.items() if c in GRAVITY_CASES}
        if not grav:
            out.append((name, dict(factors), s))
            continue
        h = net_lateral(info, fl, factors)
        signs = [1.0, -1.0] if abs(h) < 1e-6 else [math.copysign(1.0, h)]
        for sg in signs:
            f = dict(factors)
            f.update({"N" + c: fc * ALPHA_LRFD * sg for c, fc in grav.items()})
            out.append((f"{name} [{'+' if sg > 0 else '-'}N]" if len(signs) == 2 else name, f, s))
    return out


def _solve(layout, loads, combos, p_delta):
    fa = FrameAnalysis(layout)
    for ld in loads:
        fa.add_line_load(ld.case, ld.member_mark, ld.w, ld.direction, w_end=ld.w_end)
    for name, factors in combos:
        fa.add_combination(name, factors)
    return fa.solve(p_delta=p_delta)


def _tau_check(info, env, combos, fy: dict | None) -> dict:
    """max αPr/Pns over the LRFD stations; Pns = Fy·A(x)."""
    if not fy:
        return {"checked": False, "note": "no Fy given: τb not checked"}
    worst = (0.0, None, None, None)
    for m in info.layout.members:
        if info.roles[m.mark] == "link":
            continue
        for c in combos:
            for s in env.stations[m.mark][c]:
                if s.P <= 0:
                    continue
                r = ALPHA_LRFD * s.P * 1000 / (fy[m.mark] * m.taper.at(min(max(s.x, 0.0), m.length)).A)
                if r > worst[0]:
                    worst = (r, m.mark, c, s.x)
    r = float(worst[0])
    return {"checked": True, "alpha_Pr_Pns": round(r, 5), "member": worst[1], "combo": worst[2], "x": None if worst[3] is None else round(float(worst[3]), 1),
            "tau_b": 1.0, "ok": bool(r <= 0.5)}


def analyse_frame_line(info, fl, *, p_delta: bool = True, label: str = "", dam: bool = True, fy: dict | None = None) -> dict:
    """fy: {analysis member mark: Fy MPa} for the τb check (the lowest plate Fy of each member)."""
    lay = info.layout
    sets: dict[str, str] = {}
    envs: dict[str, object] = {}
    dam_info = {"used": dam}
    service = [(c, {c: 1.0}) for c in fl.cases] + [(n, f) for n, f, s in fl.combinations if not (dam and s == "LRFD")]
    for c in fl.cases:
        sets[c] = "case"
    for n, f, s in fl.combinations:
        if not (dam and s == "LRFD"):
            sets[n] = s
    env_s = _solve(lay, fl.loads, service, p_delta)
    for c, _ in service:
        envs[c] = env_s
    strength = strength_combinations(info, fl) if dam else []
    if dam and not strength:
        dam_info.update({"note": "no LRFD combinations: nothing to solve with the DAM"})
    if strength:
        ratio = NOTIONAL
        env_r = _solve(strength_layout(lay), list(fl.loads) + notional_loads(info, fl, ratio * ALPHA_LRFD),
                       [(n, f) for n, f, _ in strength], p_delta)
        tau = _tau_check(info, env_r, [n for n, _, _ in strength], fy)
        if tau.get("checked") and not tau["ok"]:
            ratio = NOTIONAL + NOTIONAL_TAU                                   # C2.3(c)
            env_r = _solve(strength_layout(lay), list(fl.loads) + notional_loads(info, fl, ratio * ALPHA_LRFD),
                           [(n, f) for n, f, _ in strength], p_delta)
            tau["route"] = "C2.3(c): τb = 1 with an additional notional load 0.001·α·Yi"
        for n, _, s in strength:
            sets[n] = s
            envs[n] = env_r
        dam_info.update({"stiffness": DAM_STIFFNESS, "min_segments": DAM_MIN_SEGMENTS, "notional": ratio, "alpha": ALPHA_LRFD, "tau": tau,
                         "notional_in": "every LRFD combination, along its net lateral load; gravity-only: both directions"})
    order = [c for c, _ in service if sets[c] == "case"] + [n for n in sets if sets[n] not in ("case", "ASD")] + [n for n in sets if sets[n] == "ASD"]
    eaves, ridge = lay.eave_nodes, lay.ridge_nodes[0]
    results = {}
    for combo in order:
        env = envs[combo]
        results[combo] = {
            "set": sets[combo],
            "reactions": {b: [round(v, 3) for v in env.reactions[b][combo]] for b in lay.base_nodes},
            "drift": round(max(abs(env.displacements[n][combo][0]) for n in eaves), 3),
            # sway = the frame's sideways movement (mean of the eaves); drift above also holds the knees' spread under gravity
            "sway": round(sum(env.displacements[n][combo][0] for n in eaves) / len(eaves), 3),
            "apex": round(env.displacements[ridge][combo][1], 3),
            "displacements": {n: [round(v, 3) for v in env.displacements[n][combo]] for n in lay.nodes},
            "members": {m.mark: [[round(s.x, 1), round(s.P, 3), round(s.V, 3), round(s.M, 3)] for s in env.stations[m.mark][combo]]
                        for m in lay.members if info.roles[m.mark] != "link"},
        }
    strength_c = [c for c in order if sets[c] == "LRFD"]
    service_c = [c for c in order if sets[c] == "ASD"]

    def gov(attr, combos):
        out = {}
        for m in lay.members:
            if info.roles[m.mark] == "link" or not combos:
                continue
            best = max(((c, s) for c in combos for s in envs[c].stations[m.mark][c]), key=lambda cs: abs(getattr(cs[1], attr)))
            out[m.mark] = {"combo": best[0], "x": round(best[1].x, 1), attr: round(getattr(best[1], attr), 3), "set": "LRFD"}
        return out
    summary = {
        "max_M_LRFD": gov("M", strength_c), "max_P_LRFD": gov("P", strength_c),
        "drift_ASD": max(((c, results[c]["drift"]) for c in service_c), key=lambda x: x[1], default=None),
        "apex_ASD": min(((c, results[c]["apex"]) for c in service_c), key=lambda x: x[1], default=None),
        "sway_ASD": max(((c, results[c]["sway"]) for c in service_c), key=lambda x: abs(x[1]), default=None),
        "uplift": max(((c, b, -results[c]["reactions"][b][1]) for c in results for b in lay.base_nodes), key=lambda x: x[2]),
    }
    return {
        "label": label, "p_delta": p_delta, "dam": dam_info, "cases": list(fl.cases), "combos": [[c, sets[c]] for c in order],
        "factors": {**{c: {c: 1.0} for c in fl.cases}, **{n: dict(f) for n, f, _ in fl.combinations},
                    **{n: dict(f) for n, f, _ in strength}},
        "nodes": {n: list(p) for n, p in lay.nodes.items()}, "base_nodes": list(lay.base_nodes),
        "members": [{"mark": m.mark, "role": info.roles[m.mark], "id": info.marks[m.mark], "i": list(m.i_point), "j": list(m.j_point),
                     "length": round(m.length, 1)} for m in lay.members],
        "results": results, "summary": summary, "tributary_m": fl.tributary_m,
        "Lr": {"At": round(fl.Lr.At, 3), "R1": round(fl.Lr.R1, 4), "R2": round(fl.Lr.R2, 4), "Lr": round(fl.Lr.Lr, 4)},
        "wind": {"qh": round(fl.wind.qh, 5), "Kz": round(fl.wind.Kz, 5), "a_mm": round(fl.wind.end_zone_a, 1), "GCpi": list(fl.wind.GCpi)},
        "loads": [{"case": ld.case, "mark": ld.member_mark, "w": round(ld.w, 4), "w_end": None if ld.w_end is None else round(ld.w_end, 4),
                   "direction": ld.direction.name, "origin": ld.origin} for ld in fl.loads],
        "designed": False,
    }
