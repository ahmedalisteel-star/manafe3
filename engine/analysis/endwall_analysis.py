# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 7: the end walls.

1. Wind columns OUT OF PLANE: each a simple beam, pinned at the base and at the top, under the end-wall wind on its
   tributary strip (half-way to the neighbouring supports; the outer strips to the building corners 0 / span).
   Pressure: bimsteelauto's Load Case B, net with ±GCpi — inward = windward wall (zones 5 / 5E), outward = leeward
   (6 / 6E). The E-zone value is used for EVERY column (conservative envelope: the corner-strip layout of Fig. 28.3-1
   is not encoded here). MWFRS pressures (as for the frames): components-and-cladding pressures (Ch. 30), usually
   higher for a wind column, are an OPEN QUESTION for the user. w = p × strip, M = wL²/8, R = wL/2.
2. End-RAFTER frame IN PLANE (end wall type "rafter" only): the constant end rafter on its centroid line, continuous over
   the wind columns, which are pinned at the base and at the top (two-force members, modelled up to the rafter centroid
   line). PyNite directly, first order. ACCEPTED ASSUMPTIONS: the frame's in-plane sway is held by the end-wall bracing /
   sheeting (not modelled) — one horizontal restraint at the eave, side A, whose force is reported; tributary = half the
   end bay (bimsteelauto tributary_width). Loads as the main frames (engine/analysis/frame_loads.py, the same cases and
   combinations, the roof and side-wall wind of the end frame line incl. its end zone).
   With an end wall of type "frame" the main frame carries the roof (step 4) and the wind columns take NO gravity —
   their tops are in vertical slotted holes (Phase 5 note), so they are not in that frame's model.
Units: kN, m, kN·m out; mm inside the PyNite model (N, mm).
"""

from __future__ import annotations

import math

from Pynite import FEModel3D

from bimsteelauto.loads.frame import tributary_width
from bimsteelauto.loads.wind import envelope_pressures
from bimsteelauto.sections import WeldedI
from bimsteelauto.spec import PEBGeometry

from ..peb.builtup_frame import builtup_frame_members, default_sizes
from ..peb.endwall import WIND_COLUMN
from .frame_loads import STEEL_KN_M3, frame_loads
from .frame_model import _wi, frame_line_model

FACTORS = {"case": 1.0, "LRFD": 1.0, "ASD": 0.6}


def _geom(inp: dict) -> PEBGeometry:
    return PEBGeometry(span_widths=(float(inp["span"]),), bay_spacings=(float(inp["bay_spacing"]),) * int(inp["n_bays"]),
                       eave_height=float(inp["eave_height"]), roof_slope=float(inp["roof_slope"]), purlin_spacing=1250.0, girt_spacing=1250.0)


def endwall_pressures(geom, li) -> dict:
    wind = envelope_pressures(geom, li.site())
    cases = [c for c in wind.pressures if c.startswith("W_B")]
    p_in = max(max(wind.pressures[c]["5"], wind.pressures[c]["5E"]) for c in cases)
    p_out = min(min(wind.pressures[c]["6"], wind.pressures[c]["6E"]) for c in cases)
    return {"inward": p_in, "outward": p_out, "qh": wind.qh, "GCpi": wind.GCpi, "gcpf": wind.gcpf["W_B_pi_pos"]}


def wind_columns(out: dict, li) -> dict:
    span = float(out["input"]["span"])
    pr = endwall_pressures(_geom(out["input"]), li)
    cols = []
    for ew in out["end_walls"]:
        sup = sorted(ew["supports"])
        prefix = "WF" if ew["end"] == "first" else "WL"
        for m in out["members"]:
            if m["role"] != "wind_column" or not m["id"].startswith(prefix):
                continue
            y, L = m["start"][1], (m["end"][2] - m["start"][2]) / 1000
            k = min(range(len(sup)), key=lambda i: abs(sup[i] - y))
            left = (sup[k - 1] + y) / 2 if k > 0 else 0.0
            right = (y + sup[k + 1]) / 2 if k < len(sup) - 1 else span
            strip = (right - left) / 1000
            row = {"id": m["id"], "end": ew["end"], "kind": ew["kind"], "y": y, "L_m": round(L, 4), "strip_m": round(strip, 4), "sets": {}}
            for s, f in FACTORS.items():
                d = {}
                for side in ("inward", "outward"):
                    w = f * pr[side] * strip
                    d[side] = {"w": round(w, 4), "M": round(w * L * L / 8, 3), "R_top": round(w * L / 2, 3), "R_base": round(w * L / 2, 3)}
                row["sets"][s] = d
            cols.append(row)
    return {"pressure_kpa": {"inward": round(pr["inward"], 5), "outward": round(pr["outward"], 5)}, "qh": round(pr["qh"], 5),
            "columns": cols, "designed": False,
            "notes": ["MWFRS Load Case B pressures, E-zone value for every column (conservative).",
                      "OPEN: components-and-cladding (Ch. 30) pressures for wind columns — user decision.",
                      "Simple beam, pinned base and top; the strip above a column's top goes to the rafter."]}


def end_rafter_frame(out: dict, end: str, li, roof_secondary_kpa: float = 0.0, wall_secondary_kpa: float = 0.0) -> dict:
    inp = out["input"]
    span, eave, slope = float(inp["span"]), float(inp["eave_height"]), float(inp["roof_slope"])
    nb, bay = int(inp["n_bays"]), float(inp["bay_spacing"])
    ew = next(e for e in out["end_walls"] if e["end"] == end)
    if ew["kind"] != "rafter":
        raise ValueError(f"the {end} end wall is a main frame (step 4 solves it); no end-rafter frame here")
    idx = 0 if end == "first" else nb
    tag = "F" if end == "first" else "L"
    # the loads of this frame line, from the same adapter as the main frames (the sections do not change them)
    ms = builtup_frame_members(span, eave, slope, float(ew["x_frame"]), str(idx + 1), default_sizes(span))
    info = frame_line_model(ms, span, eave, slope, (bay,) * nb)
    fl = frame_loads(info, idx, li, roof_secondary_kpa=roof_secondary_kpa, wall_secondary_kpa=wall_secondary_kpa)
    trib = tributary_width(info.layout.geometry, idx)
    raf = next(m for m in out["members"] if m["role"] == "end_rafter" and m["id"] == f"E{tag}RA")
    seg = raf["section"]["segments"][0]
    rw = _wi(seg, seg["hw_start"])
    cw = WeldedI(d=WIND_COLUMN["hw"] + 2 * WIND_COLUMN["tf"], tw=WIND_COLUMN["tw"], bf_top=WIND_COLUMN["bf"], tf_top=WIND_COLUMN["tf"],
                 bf_bot=WIND_COLUMN["bf"], tf_bot=WIND_COLUMN["tf"])
    c = math.sqrt(1 + slope * slope)
    e = (rw.d - rw.y_bar) * c                              # the rafter's centroid, plumb below the roof line
    zc = lambda y: eave + slope * min(y, span - y) - e
    cols = sorted((m["start"][1], m["id"]) for m in out["members"] if m["role"] == "wind_column" and m["id"].startswith("W" + tag)
                  and not m["id"].endswith("CAP"))
    ys = sorted({0.0, span / 2, span, *[y for y, _ in cols]})
    M = FEModel3D()
    M.add_material("S", 200000.0, 77000.0, 0.3, 7.85e-8)
    M.add_section("raf", rw.A, rw.Iy, rw.Ix, rw.J)
    M.add_section("col", cw.A, cw.Iy, cw.Ix, cw.J)
    names = {}
    for k, y in enumerate(ys):
        n = f"R{k}"
        names[y] = n
        M.add_node(n, y, zc(y), 0.0)
        M.def_support(n, support_DZ=True, support_RX=True, support_RY=True)
    M.def_support(names[0.0], support_DX=True, support_DZ=True, support_RX=True, support_RY=True)   # end-wall bracing (assumed)
    raf_m = []
    for k in range(len(ys) - 1):
        nm = f"RAF{k + 1}"
        M.add_member(nm, names[ys[k]], names[ys[k + 1]], "S", "raf")
        raf_m.append((nm, ys[k], ys[k + 1]))
    bases = {}
    for y, cid in cols:
        b = f"B_{cid}"
        bases[cid] = b
        M.add_node(b, y, 0.0, 0.0)
        M.def_support(b, True, True, True, True, True, False)
        M.add_member(cid, b, names[min(ys, key=lambda v: abs(v - y))], "S", "col")
        M.def_releases(cid, Rzj=True)                       # pinned top
    # loads (kN/m = N/mm), split into global components on each member
    roof_d = li.roof_sheeting + roof_secondary_kpa
    sw_r = rw.A * 1e-6 * STEEL_KN_M3
    sw_c = cw.A * 1e-6 * STEEL_KN_M3
    wind_r = {}                                             # (case, side) → w normal (+ onto the top face)
    wind_c = {}                                             # (case, side) → w toward +X, per m of height
    kcol = {f.mark: abs(f.j_point[1] - f.i_point[1]) / f.length for f in info.layout.members}
    for ld in fl.loads:
        if ld.direction.name == "NORMAL" and ld.member_mark.startswith("R"):
            wind_r[(ld.case, ld.member_mark[1])] = ld.w
        elif ld.direction.name == "GLOBAL_X":
            wind_c[(ld.case, ld.member_mark[1])] = ld.w / kcol[ld.member_mark]
    applied = {cs: [0.0, 0.0] for cs in fl.cases}           # Σ applied (Fx, Fy), kN, for the statics check
    def put(member, case, fx, fy, length_m):
        if fx:
            M.add_member_dist_load(member, "FX", fx, fx, case=case)
        if fy:
            M.add_member_dist_load(member, "FY", fy, fy, case=case)
        applied[case][0] += fx * length_m
        applied[case][1] += fy * length_m
    for nm, ya, yb in raf_m:
        L = math.hypot(yb - ya, zc(yb) - zc(ya)) / 1000
        cos = abs(yb - ya) / 1000 / L
        side = "A" if (ya + yb) / 2 < span / 2 else "B"
        put(nm, "D", 0.0, -(sw_r + roof_d * trib), L)
        put(nm, "C", 0.0, -li.collateral * trib * cos, L)
        put(nm, "Lr", 0.0, -fl.Lr.Lr * trib * cos, L)
        nx, ny = (-slope, 1.0) if side == "A" else (slope, 1.0)
        h = math.hypot(nx, ny)
        for cs in fl.cases:
            if (cs, side) in wind_r:
                w = wind_r[(cs, side)]
                put(nm, cs, -w * nx / h, -w * ny / h, L)
    for y, cid in cols:
        top = M.nodes[M.members[cid].j_node.name]
        L = top.Y / 1000
        put(cid, "D", 0.0, -sw_c, L)
        if cid in (cols[0][1], cols[-1][1]):                # the corner columns take the side-wall wind on half the bay
            side = "A" if y < span / 2 else "B"
            for cs in fl.cases:
                if (cs, side) in wind_c:
                    put(cid, cs, wind_c[(cs, side)], 0.0, L)
    sets = {}
    for cs in fl.cases:
        M.add_load_combo(cs, {cs: 1.0})
        sets[cs] = "case"
    for name, factors, s in fl.combinations:
        M.add_load_combo(name, factors)
        sets[name] = s
    M.analyze_linear(check_statics=False)
    res = {}
    apex = names[span / 2]
    for combo in sets:
        res[combo] = {
            "set": sets[combo],
            "reactions": {cid: [round(M.nodes[b].RxnFX[combo] / 1000, 3), round(M.nodes[b].RxnFY[combo] / 1000, 3)] for cid, b in bases.items()},
            "restraint_H": round(M.nodes[names[0.0]].RxnFX[combo] / 1000, 3),
            "apex": round(M.nodes[apex].DY[combo], 3),
            "rafter_M": round(max(max(abs(M.members[n].max_moment("Mz", combo)), abs(M.members[n].min_moment("Mz", combo))) for n, _, _ in raf_m) / 1e6, 3),
            "column_P": {cid: round(M.members[cid].max_axial(combo) / 1000, 3) for _, cid in cols},
        }
    lrfd = [c for c in sets if sets[c] == "LRFD"]
    asd = [c for c in sets if sets[c] == "ASD"]
    return {
        "end": end, "tributary_m": round(trib, 4), "cases": list(fl.cases), "results": res,
        "applied": {cs: [round(v, 4) for v in a] for cs, a in applied.items()},
        "summary": {"rafter_M_LRFD": max(((c, res[c]["rafter_M"]) for c in lrfd), key=lambda x: x[1]),
                    "column_P_LRFD": max(((c, cid, p) for c in lrfd for cid, p in res[c]["column_P"].items()), key=lambda x: abs(x[2])),
                    "apex_ASD": min(((c, res[c]["apex"]) for c in asd), key=lambda x: x[1])},
        "assumptions": ["in-plane sway held by the end-wall bracing / sheeting: one horizontal restraint at the eave, side A (force reported)",
                        "wind columns pinned top and bottom, modelled up to the rafter centroid line",
                        "first order (the frame is held laterally)"],
        "designed": False,
    }
