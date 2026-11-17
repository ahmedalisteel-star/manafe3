# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Open item 7 (user decisions 2026-11-17): the longitudinal bracing's axial forces in the frame lines and the cold-formed
struts. NOT FOR ISSUE.

Forces (the same split as open item 6, `connections.longitudinal.brace_forces`, so the base plates and the columns use ONE
ΔP): the wall diagonal T (LRFD 1.0 W) = minimum_scale × T_caseB; T_min = T_caseB × minimum_ratio. The roof X carries
V = per_braced_bay / 2 per slope (bimsteelauto's rule: the same shear in every panel), V_caseB and V_min split the same way.

    columns (2a)  the vertical component of the TENSION wall diagonal, ΔP = T sin α, a point load on the column at the
                  diagonal's top end (clamped to the column's top node when the brace meets the column above it). The
                  tension diagonal for wind along +x runs from the base at the lower x up to the top at the higher x
                  (and the other way for −x). Its lower end at a base goes straight into the anchors (−ΔP, open item 6,
                  `longitudinal.braced_base`); a lower end ABOVE the base is an upward point load on that column.
    rafters (1a)  the roof X is a truss in the roof plane between two frame lines, spanning eave node to eave node,
                  loaded at the ridge (constant shear V, as bimsteelauto sizes the diagonals): the rafters are its
                  chords. Chord force at a roof-X node = V × s / b (s along the slope from the eave node, b the bay);
                  in a panel the larger end's value (conservative); zero between the knee and the eave node; constant
                  from the ridge-purlin node to the ridge. Wind along +x compresses the lower-x chord and stretches the
                  higher-x one. Applied as point loads ALONG the rafter at the roof-X nodes, in the same combinations as
                  the frame loads (they then reach the member checks, the joints, ECP and the base reactions alike).
    load cases    per frame line: "BRA" = the wind direction in which this line's columns take a diagonal's compression
                  (if none or both: +x), "BRB" = the other direction; "BRminA" / "BRminB" with the §28.3.4 minimum.
                  Combinations (LRFD only): every LRFD combination with WB± once more per direction, + BRA / BRB at that
                  combination's wind factor (the original combinations stay: the frame alone); and 0.9D / 1.2D + 1.0
                  BRmin (dead load only — open item 6's minimum family).
    struts        eave strut in a braced bay = the wall-panel shear per side (upper bound, decision 3a); purlins at the
                  roof-X nodes in a braced bay = V per slope (TO CONFIRM: every node purlin, ridge and eave node included);
                  an eave strut in a bay BETWEEN two braced bays (user decision 1c, 2026-11-17; engineering judgement,
                  VERIFIED False): the larger of (i) the longitudinal force passing through the bay (bimsteelauto's drag;
                  0 between two braced bays) and (ii) AISC 360-16 App. 6 panel bracing of the columns it braces, 0.005 x
                  sum Pr from the same combination — never NOT EVALUATED. "The columns it braces" = the frame columns on
                  that side at the frame lines inside the run of unbraced bays holding this bay (their bracing force may
                  pass through it either way; conservative). Computed in design/cfs_checks.py.
"""

from __future__ import annotations

import math

NODE_TOL = 150.0         # mm: a roof-X node within this of a purlin line (plan, along the slope) is on that purlin (TO CONFIRM)
PANEL_BRACE = 0.005      # AISC 360-16 App. 6.2.1 panel bracing: Vbr = 0.005 Pr (user 1c, 2026-11-17)
VERIFIED = {"chord_rule": False, "strut_rule": False, "column_rule": False, "panel_bracing_strut": False}


def split(value: float, k: float | None, r: float | None) -> dict | None:
    """value (LRFD, governing) → Case B alone and the §28.3.4 minimum alone (open item 6's split)."""
    if value is None or k is None or r is None:
        return None
    vb = value / k
    return {"governing": value, "caseB": vb, "minimum": vb * r}


def _dir_of(b: dict) -> int:
    """+1 when the brace is in tension for wind along +x (its top end at the higher x)."""
    lo, hi = (b["start"], b["end"]) if b["start"][2] < b["end"][2] else (b["end"], b["start"])
    return 1 if hi[0] > lo[0] else -1


def brace_loads(out: dict, bracing: dict) -> dict:
    """{frame index: line record} + "struts" for the cold-formed checks. bracing: bracing_system.longitudinal_bracing."""
    frames = sorted(g["at"] for g in out["grids"]["x"])
    sl = float(out["input"]["roof_slope"])
    cos_t = 1.0 / math.sqrt(1.0 + sl * sl)
    lrfd = (bracing or {}).get("sets", {}).get("LRFD", {})
    k, r = (bracing or {}).get("minimum_scale"), (bracing or {}).get("minimum_ratio")
    T = split(lrfd.get("wall_diagonal"), k, r)
    V = split(lrfd.get("per_braced_bay") / 2.0 if lrfd.get("per_braced_bay") is not None else None, k, r)
    res = {"T": T, "V": V, "lines": {}, "struts": {}, "verified": dict(VERIFIED)}
    if T is None or V is None:
        res["why"] = "the bracing result has no Case B / minimum split (re-run the analysis)"
        return res
    ms = out["members"]
    braced = [j - 1 for j in out.get("braced_bays", [])]
    # ---- per frame line and direction: column point loads and chord signs
    raw = {i: {1: {"columns": [], "chord": 0}, -1: {"columns": [], "chord": 0}} for i in range(len(frames))}
    for b in ms:
        if b.get("role") != "wall_brace":
            continue
        lo, hi = (b["start"], b["end"]) if b["start"][2] < b["end"][2] else (b["end"], b["start"])
        d = _dir_of(b)
        sin_a = abs(hi[2] - lo[2]) / math.dist(lo, hi)
        for i, x in enumerate(frames):
            if abs(hi[0] - x) < 1.0:
                raw[i][d]["columns"].append({"side": b["side"], "z": hi[2], "sin_a": sin_a, "sign": 1, "brace": b.get("id")})
            if abs(lo[0] - x) < 1.0 and lo[2] > 1.0:          # a lower end above the base: an upward load on that column
                raw[i][d]["columns"].append({"side": b["side"], "z": lo[2], "sin_a": sin_a, "sign": -1, "brace": b.get("id")})
    nodes = {}
    for j in braced:
        for side in "AB":
            ys = sorted({round(p[1], 3) for b in ms if b.get("role") == "roof_brace" and b.get("bay") == j and b.get("side") == side
                         for p in (b["start"], b["end"])}, key=lambda y: y if side == "A" else -y)
            if len(ys) >= 2:
                nodes[(j, side)] = ys
        lo_i, hi_i = j, j + 1
        for i, sg in ((lo_i, 1), (hi_i, -1)):              # +x compresses the lower-x chord
            if i in raw:
                raw[i][1]["chord"] += sg
                raw[i][-1]["chord"] -= sg
    for i, x in enumerate(frames):
        dirs = raw[i]
        if not any(dirs[d]["columns"] or dirs[d]["chord"] for d in (1, -1)):
            continue
        with_cols = [d for d in (1, -1) if dirs[d]["columns"]]
        dA = with_cols[0] if len(with_cols) == 1 else 1
        bays = [j for j in braced if i in (j, j + 1)]
        chord_nodes = {side: nodes[(bays[0], side)] for side in "AB" if bays and (bays[0], side) in nodes}
        bw = abs(frames[bays[0] + 1] - frames[bays[0]]) if bays else None
        line = {"x": x, "cases": {}, "points": [], "bay_width": bw, "chord_nodes": chord_nodes}
        for lab, d in (("A", dA), ("B", -dA)):
            for fam, case in (("caseB", "BR" + lab), ("minimum", "BRmin" + lab)):
                line["cases"][case] = {"direction": "+x" if d > 0 else "-x", "family": fam, "chord_sign": dirs[d]["chord"]}
                for c in dirs[d]["columns"]:
                    line["points"].append({"case": case, "kind": "column", "side": c["side"], "z": c["z"],
                                           "dP": round(c["sign"] * T[fam] * c["sin_a"], 6), "brace": c["brace"], "sin_a": c["sin_a"]})
                if dirs[d]["chord"] and bw:
                    for side, ys in chord_nodes.items():
                        s = [abs(y - ys[0]) / cos_t for y in ys]
                        for n in range(len(ys) - 1):        # node n carries the step to the next node's value
                            dN = dirs[d]["chord"] * V[fam] * (s[n + 1] - s[n]) / bw
                            line["points"].append({"case": case, "kind": "chord", "side": side, "y": ys[n], "dN": round(dN, 6)})
        res["lines"][i] = line
    # ---- cold-formed struts
    n_bays = len(frames) - 1
    eave = {}
    for j in range(n_bays):
        if j in braced:
            eave[j + 1] = {"P": lrfd.get("wall_base_shear"), "rule": "braced bay: the wall-panel shear per side (upper bound)"}
        elif braced and min(braced) < j < max(braced):
            lo = max(k for k in braced if k < j)
            hi = min(k for k in braced if k > j)
            eave[j + 1] = {"P": None, "between": True, "panel_lines": list(range(lo + 3, hi + 1)),   # 1-based lines strictly between the braced bays
                           "rule": f"between two braced bays: max(longitudinal force through the bay, App. 6 panel bracing "
                                   f"{PANEL_BRACE:g} x sum Pr of the columns it braces, same combination) - user 1c, VERIFIED False"}
    purl = []
    for (j, side), ys in nodes.items():
        purl.append({"bay": j + 1, "side": side, "x0": frames[j], "x1": frames[j + 1], "node_ys": ys, "P": V["governing"]})
    res["struts"] = {"eave": eave, "purlin_nodes": purl, "node_tol": NODE_TOL}
    return res
