# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 4: solve one frame line (bimsteelauto FrameAnalysis, PyNite, P-Delta) and shape the results.

Every load case is ALSO solved on its own, unfactored (user decision: the foundation designer applies his own factors),
next to every LRFD and ASD combination. Each result carries its set: "case" | "LRFD" | "ASD". Strength values (member
forces, governing moments) are reported from LRFD; deflection and drift from ASD (user decision).
Units: kN, kN·m, mm. Reactions (H, V, M) are the forces the support gives the frame; P is positive in compression;
M is positive when the member's TOP flange is in compression (rafter: top flange; column: outer flange) — bimsteelauto
0.14.1's design sign.
Drift is the largest |horizontal movement| of the eave (knee) nodes. Note: bimsteelauto's Envelope.eave_drift looks for
nodes named "E…" (its own layouts) and would return 0 here — not used.
"""

from __future__ import annotations

from bimsteelauto.analysis import FrameAnalysis


def analyse_frame_line(info, fl, *, p_delta: bool = True, label: str = "") -> dict:
    fa = FrameAnalysis(info.layout)
    for ld in fl.loads:
        fa.add_line_load(ld.case, ld.member_mark, ld.w, ld.direction, w_end=ld.w_end)
    sets: dict[str, str] = {}
    for c in fl.cases:
        fa.add_combination(c, {c: 1.0})
        sets[c] = "case"
    for name, factors, s in fl.combinations:
        fa.add_combination(name, factors)
        sets[name] = s
    env = fa.solve(p_delta=p_delta)
    lay = info.layout
    eaves, ridge = lay.eave_nodes, lay.ridge_nodes[0]
    results = {}
    for combo in env.combos:
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
    strength = [c for c in env.combos if sets[c] == "LRFD"]
    service = [c for c in env.combos if sets[c] == "ASD"]
    def gov(attr, combos):
        out = {}
        for m in lay.members:
            if info.roles[m.mark] == "link" or not combos:
                continue
            best = max(((c, s) for c in combos for s in env.stations[m.mark][c]), key=lambda cs: abs(getattr(cs[1], attr)))
            out[m.mark] = {"combo": best[0], "x": round(best[1].x, 1), attr: round(getattr(best[1], attr), 3), "set": "LRFD"}
        return out
    summary = {
        "max_M_LRFD": gov("M", strength), "max_P_LRFD": gov("P", strength),
        "drift_ASD": max(((c, results[c]["drift"]) for c in service), key=lambda x: x[1], default=None),
        "apex_ASD": min(((c, results[c]["apex"]) for c in service), key=lambda x: x[1], default=None),
        "sway_ASD": max(((c, results[c]["sway"]) for c in service), key=lambda x: abs(x[1]), default=None),
        "uplift": max(((c, b, -results[c]["reactions"][b][1]) for c in results for b in lay.base_nodes), key=lambda x: x[2]),
    }
    return {
        "label": label, "p_delta": p_delta, "cases": list(fl.cases), "combos": [[c, sets[c]] for c in env.combos],
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
