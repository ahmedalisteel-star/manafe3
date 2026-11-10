# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 3 step 7: the end walls.

1. Wind columns OUT OF PLANE (wind_columns): each a simple beam, pinned at the base and at the top, under the end-wall
   wind on its tributary strip (half-way to the neighbouring supports; the outer strips to the building corners).
   DESIGN pressure: components and cladding, ASCE 7-16 Ch. 30 (cc_wind.py, user decision 2026-11-08; VERIFIED False),
   zone 5 where the strip comes within a of a corner, else zone 4. w = p × strip, M = wL²/8, R = wL/2.
   longitudinal_feed: the same simple beams under MWFRS end-wall pressure give the ACTUAL top reactions that drive the
   longitudinal bracing (step 6).
2. End-RAFTER frame IN PLANE (end wall type "rafter" only): the constant end rafter on its centroid line, continuous over
   the wind columns, which are pinned at the base and at the top (two-force members, modelled up to the rafter centroid
   line). PyNite directly, first order. The frame's in-plane sway is carried by the end-wall X-bracing
   (user decision 2026-11-08: no reliance on sheeting; tension-only diagonals in the braced bays — refused without);
   tributary = half the
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
from bimsteelauto.loads.wind import envelope_pressures, longitudinal_endwall_pressure
from bimsteelauto.sections import WeldedI
from bimsteelauto.spec import PEBGeometry

from ..peb.builtup_frame import builtup_frame_members, default_sizes
from ..peb.endwall import WIND_COLUMN
from .cc_wind import cc_wall_pressure, effective_area
from .frame_loads import STEEL_KN_M3, frame_loads
from .solve import ALPHA_LRFD, DAM_MIN_SEGMENTS, DAM_STIFFNESS, GRAVITY_CASES, NOTIONAL, NOTIONAL_TAU
from ..design.inputs import section_strength
from .frame_model import _wi, frame_line_model
from .secondary_weight import area_mm2

FACTORS = {"case": 1.0, "LRFD": 1.0, "ASD": 0.6}


def bays_of(inp: dict) -> tuple[float, ...]:
    """The bays of a building's "input": the list (field fix 6), else n_bays x bay_spacing (older outputs)."""
    return tuple(float(v) for v in inp["bays"]) if inp.get("bays") else (float(inp["bay_spacing"]),) * int(inp["n_bays"])


def _geom(inp: dict) -> PEBGeometry:
    return PEBGeometry(span_widths=(float(inp["span"]),), bay_spacings=bays_of(inp),
                       eave_height=float(inp["eave_height"]), roof_slope=float(inp["roof_slope"]), purlin_spacing=1250.0, girt_spacing=1250.0)


def _strips(sup: list[float], span: float) -> list[tuple[float, float, float]]:
    """(y, left, right) of every support's tributary strip: half-way to its neighbours, the outer ones to the corners."""
    out = []
    for k, y in enumerate(sup):
        left = (sup[k - 1] + y) / 2 if k > 0 else 0.0
        right = (y + sup[k + 1]) / 2 if k < len(sup) - 1 else span
        out.append((y, left, right))
    return out


def _wall_area(left: float, right: float, span: float, eave: float, slope: float) -> float:
    """mm² of end wall between y = left and right, from the floor to the roof line (exact: the roof is linear each side of
    the apex)."""
    a = 0.0
    for lo, hi in ((left, min(right, span / 2)), (max(left, span / 2), right)):
        if hi > lo:
            z0, z1 = eave + slope * min(lo, span - lo), eave + slope * min(hi, span - hi)
            a += (z0 + z1) / 2 * (hi - lo)
    return a


def wind_columns(out: dict, li) -> dict:
    """The wind columns' DESIGN loads: C&C (ASCE 7-16 Ch. 30, cc_wind.py — VERIFIED False), simple beams."""
    inp = out["input"]
    span = float(inp["span"])
    geom = _geom(inp)
    wind = envelope_pressures(geom, li.site())
    a = wind.end_zone_a
    theta = math.degrees(math.atan(float(inp["roof_slope"])))
    cols = []
    for ew in out["end_walls"]:
        strips = {round(y, 3): (lft, rgt) for y, lft, rgt in _strips(sorted(ew["supports"]), span)}
        prefix = "WF" if ew["end"] == "first" else "WL"
        for m in out["members"]:
            if m["role"] != "wind_column" or not m["id"].startswith(prefix):
                continue
            y, L = m["start"][1], (m["end"][2] - m["start"][2]) / 1000
            lft, rgt = strips[min(strips, key=lambda v: abs(v - y))]
            strip = (rgt - lft) / 1000
            zone = "5" if lft < a or rgt > span - a else "4"          # any part of its strip within a of a corner
            cc = cc_wall_pressure(wind.qh, zone, effective_area(L, strip), theta, wind.GCpi)
            row = {"id": m["id"], "end": ew["end"], "kind": ew["kind"], "y": y, "L_m": round(L, 4), "strip_m": round(strip, 4),
                   "cc": {k: (round(v, 5) if isinstance(v, float) else v) for k, v in cc.items()}, "sets": {}}
            for s, f in FACTORS.items():
                d = {}
                for side in ("inward", "outward"):
                    w = f * cc[side] * strip
                    d[side] = {"w": round(w, 4), "M": round(w * L * L / 8, 3), "R_top": round(w * L / 2, 3), "R_base": round(w * L / 2, 3)}
                row["sets"][s] = d
            cols.append(row)
    return {"qh": round(wind.qh, 5), "a_mm": round(a, 1), "theta_deg": round(theta, 3), "columns": cols, "designed": False, "VERIFIED": False,
            "notes": ["Components and cladding, ASCE 7-16 Ch. 30 Part 1, walls zones 4 / 5; effective area = span x max(spacing, span/3).",
                      "VERIFIED False: new code, the GCp values transcribed from Fig. 30.3-1 (hand-checked arithmetic, not the figure).",
                      "Simple beam, pinned base and top; the strip above a column's top goes to the rafter."]}


def longitudinal_feed(out: dict, li) -> dict:
    """What the end walls deliver to the longitudinal bracing — the ACTUAL top reactions (user decision 2026-11-08):
    every support of each end wall (wind columns; corner main-frame columns, held at the eave) is a simple beam under
    MWFRS end-wall pressure on its strip; its top reaction plus the wall above its top (up to the roof line, carried by
    the rafter) arrive at roof level, the rest at the base. Summed per end wall (side).
    Pressure: bimsteelauto's Load Case B interior zones, windward 5 and leeward 6, GCpi of the + case (it cancels in the
    sum), scaled by the §28.3.4 minimum exactly as bimsteelauto longitudinal_endwall_pressure does — so the TOTAL equals
    bimsteelauto's net pressure × end-wall area; only its eave / base split is now the real one, not a blanket half.
    MWFRS, not C&C: the bracing is part of the main wind-force resisting system."""
    inp = out["input"]
    span, eave, slope = float(inp["span"]), float(inp["eave_height"]), float(inp["roof_slope"])
    geom = _geom(inp)
    wind = envelope_pressures(geom, li.site())
    p_net, minimum = longitudinal_endwall_pressure(geom, wind)
    g = wind.gcpf["W_B_pi_pos"]
    k = p_net / (wind.qh * (g["5"] - g["6"]))
    gi = wind.GCpi[0]
    side_p = {"windward": k * wind.qh * (g["5"] - gi), "leeward": k * wind.qh * (g["6"] - gi)}     # + toward the wall
    tops = {}
    for m in out["members"]:
        if m["role"] == "wind_column":
            tops[(m["id"][1], round(m["start"][1], 3))] = m["end"][2] - m["start"][2]
    walls = {}
    for ew in out["end_walls"]:
        tag = "F" if ew["end"] == "first" else "L"
        rows = []
        for y, lft, rgt in _strips(sorted(ew["supports"]), span):
            h = tops.get((tag, round(y, 3)), eave)                    # a main-frame corner column: held at the eave
            area = _wall_area(lft, rgt, span, eave, slope) * 1e-6      # m²
            strip = (rgt - lft) / 1000
            rows.append({"y": y, "height_m": round(h / 1000, 4), "strip_m": round(strip, 4), "area_m2": round(area, 5),
                         "top_m2": strip * h / 2000 + (area - strip * h / 1000), "base_m2": strip * h / 2000})
        walls[ew["end"]] = {"kind": ew["kind"], "supports": rows,
                            "top_m2": sum(r["top_m2"] for r in rows), "base_m2": sum(r["base_m2"] for r in rows)}
    directions = {}
    for ww, lw in (("first", "last"), ("last", "first")):
        wt, lt = abs(side_p["windward"]) * walls[ww]["top_m2"], abs(side_p["leeward"]) * walls[lw]["top_m2"]
        directions[f"from {ww}"] = {"F_eave": wt + lt, "windward_top": wt, "leeward_top": lt,
                                    "F_base": abs(side_p["windward"]) * walls[ww]["base_m2"] + abs(side_p["leeward"]) * walls[lw]["base_m2"]}
    gov = max(directions, key=lambda d: directions[d]["F_eave"])
    return {"p_side_kpa": {s: round(v, 5) for s, v in side_p.items()}, "p_net_kpa": round(p_net, 5), "minimum_scale": round(k, 5),
            "minimum": None if minimum is None else {"governs": bool(minimum.governs)},
            "walls": walls, "directions": directions, "governing": gov, "F_eave": directions[gov]["F_eave"], "F_base": directions[gov]["F_base"]}


def end_rafter_frame(out: dict, end: str, li, roof_secondary_kpa: float = 0.0, wall_secondary_kpa: float = 0.0) -> dict:
    inp = out["input"]
    span, eave, slope = float(inp["span"]), float(inp["eave_height"]), float(inp["roof_slope"])
    bays = bays_of(inp)
    nb = len(bays)
    ew = next(e for e in out["end_walls"] if e["end"] == end)
    if ew["kind"] != "rafter":
        raise ValueError(f"the {end} end wall is a main frame (step 4 solves it); no end-rafter frame here")
    idx = 0 if end == "first" else nb
    tag = "F" if end == "first" else "L"
    # the loads of this frame line, from the same adapter as the main frames (the sections do not change them)
    ms = builtup_frame_members(span, eave, slope, float(ew["x_frame"]), str(idx + 1), default_sizes(span))
    info = frame_line_model(ms, span, eave, slope, bays)
    fl = frame_loads(info, idx, li, roof_secondary_kpa=roof_secondary_kpa, wall_secondary_kpa=wall_secondary_kpa)
    trib = tributary_width(info.layout.geometry, idx)
    raf = next(m for m in out["members"] if m["role"] == "end_rafter" and m["id"] == f"E{tag}RA")
    seg = raf["section"]["segments"][0]
    rw = _wi(seg, seg["hw_start"])
    wcm = next(m for m in out["members"] if m["role"] == "wind_column" and m["id"].startswith("W" + tag))   # the generated section
    wseg = wcm["section"]["segments"][0]
    cw = _wi(wseg, wseg["hw_start"])
    c = math.sqrt(1 + slope * slope)
    e = (rw.d - rw.y_bar) * c                              # the rafter's centroid, plumb below the roof line
    zc = lambda y: eave + slope * min(y, span - y) - e
    cols = sorted((m["start"][1], m["id"]) for m in out["members"] if m["role"] == "wind_column" and m["id"].startswith("W" + tag)
                  and not m["id"].endswith("CAP"))
    ys = sorted({0.0, span / 2, span, *[y for y, _ in cols]})
    braces = [m for m in out["members"] if m["role"] == "endwall_brace" and m.get("wall") == end]
    if not braces:
        raise ValueError(f"the {end} end wall is an end-rafter wall with no X-bracing: its frame has no in-plane stability "
                         "(set end-wall braced bays; the default is bay 1)")
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
    fy_col = section_strength(wseg)["Fy"]

    def build(k: float, nseg: int, notional: float, combos: list[tuple[str, dict]], second_order: bool, diagonals=None):
        """The end frame in PyNite: stiffness × k, every rafter span and column in nseg elements, notional twins
        (cases "ND" / "NC" / "NLr", + toward +X) of the gravity loads at `notional` × their vertical intensity."""
        M = FEModel3D()
        M.add_material("S", k * 200000.0, k * 77000.0, 0.3, 7.85e-8)
        M.add_section("raf", rw.A, rw.Iy, rw.Ix, rw.J)
        M.add_section("col", cw.A, cw.Iy, cw.Ix, cw.J)
        names = {}
        for i, y in enumerate(ys):
            names[y] = f"R{i}"
            M.add_node(names[y], y, zc(y), 0.0)
            M.def_support(names[y], support_DZ=True, support_RX=True, support_RY=True)
        elems: dict[str, list[str]] = {}

        def chain(key, n0, n1, p0, p1, sec):
            out_ = []
            prev = n0
            for s in range(nseg):
                nxt = n1 if s == nseg - 1 else f"{key}_n{s + 1}"
                if s < nseg - 1:
                    f = (s + 1) / nseg
                    M.add_node(nxt, p0[0] + (p1[0] - p0[0]) * f, p0[1] + (p1[1] - p0[1]) * f, 0.0)
                    M.def_support(nxt, support_DZ=True, support_RX=True, support_RY=True)
                nm = f"{key}_e{s + 1}"
                M.add_member(nm, prev, nxt, "S", sec)
                out_.append(nm)
                prev = nxt
            elems[key] = out_
        raf_m = []
        for i in range(len(ys) - 1):
            key = f"RAF{i + 1}"
            chain(key, names[ys[i]], names[ys[i + 1]], (ys[i], zc(ys[i])), (ys[i + 1], zc(ys[i + 1])), "raf")
            raf_m.append((key, ys[i], ys[i + 1]))
        bases = {}
        for y, cid in cols:
            b = f"B_{cid}"
            bases[cid] = b
            M.add_node(b, y, 0.0, 0.0)
            M.def_support(b, True, True, True, True, True, False)
            top = names[min(ys, key=lambda v: abs(v - y))]
            chain(cid, b, top, (y, 0.0), (y, M.nodes[top].Y), "col")
            M.def_releases(elems[cid][-1], Rzj=True)                 # pinned top
        # the end-wall X-bracing (user decision 2026-11-08 — no reliance on sheeting): tension-only, pinned, from a
        # column's base to the rafter node over the other column (the real brace stops 100 below the column top)
        col_at = {round(y, 3): cid for y, cid in cols}
        brace_cos = {}
        for bm in braces:
            if diagonals is not None and bm["id"] not in diagonals:
                continue
            y0, y1 = round(bm["start"][1], 3), round(bm["end"][1], 3)
            sec = "brace_" + bm["profile"]
            if sec not in M.sections:
                M.add_section(sec, area_mm2(bm["profile"]), 1.0, 1.0, 1.0)
            top = names[min(ys, key=lambda v: abs(v - y1))]
            # diagonals=None: PyNite's tension-only switch (the service set); a chosen set: ordinary axial members
            M.add_member(bm["id"], bases[col_at[y0]], top, "S", sec, tension_only=diagonals is None)
            M.def_releases(bm["id"], Ryi=True, Rzi=True, Ryj=True, Rzj=True)
            dx, dy = M.nodes[top].X - y0, M.nodes[top].Y
            brace_cos[bm["id"]] = abs(dx) / math.hypot(dx, dy)
        applied = {}                                                 # case → [Σ Fx, Σ Fy], kN
        roof_H = {}                                                  # case → horizontal load arriving at rafter level

        def put(key, case, fx, fy, length_m, top_share=1.0):
            for nm in elems[key]:
                if fx:
                    M.add_member_dist_load(nm, "FX", fx, fx, case=case)
                if fy:
                    M.add_member_dist_load(nm, "FY", fy, fy, case=case)
            a_ = applied.setdefault(case, [0.0, 0.0])
            a_[0] += fx * length_m
            a_[1] += fy * length_m
            roof_H[case] = roof_H.get(case, 0.0) + fx * length_m * top_share
            if notional and case in GRAVITY_CASES and fy:
                put(key, "N" + case, -notional * fy, 0.0, length_m, top_share)   # the horizontal twin, + toward +X
        for key, ya, yb in raf_m:
            L = math.hypot(yb - ya, zc(yb) - zc(ya)) / 1000
            cos = abs(yb - ya) / 1000 / L
            side = "A" if (ya + yb) / 2 < span / 2 else "B"
            put(key, "D", 0.0, -(sw_r + roof_d * trib), L)
            put(key, "C", 0.0, -li.collateral * trib * cos, L)
            put(key, "Lr", 0.0, -fl.Lr.Lr * trib * cos, L)
            nx, ny = (-slope, 1.0) if side == "A" else (slope, 1.0)
            h = math.hypot(nx, ny)
            for cs in fl.cases:
                if (cs, side) in wind_r:
                    w = wind_r[(cs, side)]
                    put(key, cs, -w * nx / h, -w * ny / h, L)
        for y, cid in cols:
            L = M.nodes[M.members[elems[cid][-1]].j_node.name].Y / 1000
            put(cid, "D", 0.0, -sw_c, L, top_share=0.5)
            if cid in (cols[0][1], cols[-1][1]):                    # the corner columns take the side-wall wind on half the bay
                side = "A" if y < span / 2 else "B"
                for cs in fl.cases:
                    if (cs, side) in wind_c:
                        put(cid, cs, wind_c[(cs, side)], 0.0, L, top_share=0.5)   # pinned-pinned: half to the top
        for name, factors in combos:
            M.add_load_combo(name, {c: f for c, f in factors.items() if c in applied})
        if second_order:
            M.analyze_PDelta(log=False)                              # iterates the tension-only diagonals too
        else:
            M.analyze(check_statics=False)                           # non-linear only for the tension-only diagonals
        return M, names, raf_m, bases, elems, brace_cos, applied, roof_H

    # the service set (cases, ASD): nominal stiffness, one element per span, no notional loads, FIRST order (a braced
    # frame: its drift is not judged; the statics of each case stay exact)
    sets: dict[str, str] = {c: "case" for c in fl.cases}
    service = [(c, {c: 1.0}) for c in fl.cases] + [(n, f) for n, f, s in fl.combinations if s != "LRFD"]
    for n, f, s in fl.combinations:
        if s != "LRFD":
            sets[n] = s
    Ms, names, raf_s, bases, el_s, brace_cos, applied, roof_H = build(1.0, 1, 0.0, service, False)
    # the strength set (LRFD): Direct Analysis Method — 0.8 stiffness, 4 elements per member (P-δ), notional loads in
    # every LRFD combination along its net lateral load (gravity-only: both ways); τb checked on the wind columns
    lrfd = []
    for n, f, s in fl.combinations:
        if s != "LRFD":
            continue
        grav = {c: v for c, v in f.items() if c in GRAVITY_CASES}
        h = sum(v * applied.get(c, [0.0, 0.0])[0] for c, v in f.items())
        signs = [1.0, -1.0] if (grav and abs(h) < 1e-6) else [math.copysign(1.0, h) if grav else 1.0]
        for sg in signs:
            ff = dict(f)
            ff.update({"N" + c: v * ALPHA_LRFD * sg for c, v in grav.items()})
            lrfd.append((f"{n} [{'+' if sg > 0 else '-'}N]" if len(signs) == 2 else n, ff))
    # PyNite never re-activates a tension-only member it has switched off (Analysis._check_TC_convergence): under a
    # gravity-heavy combination the columns' shortening puts BOTH diagonals in compression first, both are switched off
    # for good and the frame is left a mechanism, silently. So for strength: one model per sway direction with only the
    # diagonal that LENGTHENS under it (+X: the one whose top is further +X), as an ordinary axial member; each
    # combination takes the model of the sign of its factored horizontal load at rafter level (notional twins included).
    # The rod's design tension = max(the model's tension, H / cos θ) — H / cos θ is statics (the pinned columns take no
    # shear); a model compression (column shortening exceeding a tiny lateral) is flagged "slack".
    plus = [b["id"] for b in braces if b["end"][1] > b["start"][1]]
    minus = [b["id"] for b in braces if b["end"][1] < b["start"][1]]

    def strength(ratio):
        mp = build(DAM_STIFFNESS, DAM_MIN_SEGMENTS, ratio, lrfd, True, plus)
        mm = build(DAM_STIFFNESS, DAM_MIN_SEGMENTS, ratio, lrfd, True, minus)
        rh = mp[7]
        pick = {}
        for n, f in lrfd:
            h = sum(v * rh.get(c, 0.0) for c, v in f.items())
            pick[n] = (mp if h >= 0 else mm, h)
        return pick
    ratio = NOTIONAL
    pick = strength(ratio)
    tau = max(((max(0.0, pick[c][0][0].members[pick[c][0][4][cid][0]].max_axial(c)) / (fy_col * cw.A), cid, c) for _, cid in cols for c, _ in lrfd),
              key=lambda x: x[0])
    if tau[0] > 0.5:                                                 # C2.3(c)
        ratio = NOTIONAL + NOTIONAL_TAU
        pick = strength(ratio)
    for n, _ in lrfd:
        sets[n] = "LRFD"
    res = {}
    for combo, kind in sets.items():
        if kind == "LRFD":
            (M_, nm_, raf_, bas_, el_, bcos, _, _), h = pick[combo]
            braces_out, slack = {}, []
            for bid in brace_cos:
                if bid not in bcos:
                    braces_out[bid] = 0.0
                    continue
                ax = -M_.members[bid].min_axial(combo) / 1000              # tension +
                statics = abs(h) / bcos[bid]
                if ax < 0:
                    slack.append(bid)
                braces_out[bid] = round(max(ax, statics), 3)
        else:
            M_, nm_, raf_, bas_, el_ = Ms, names, raf_s, bases, el_s
            braces_out = {bid: round(max(0.0, -M_.members[bid].min_axial(combo)) / 1000, 3) for bid in brace_cos}
            slack, h = [], None
        stations = None
        if kind == "LRFD":
            # Phase 4 step 5: the rafter's forces at every element end, for the member checks — [y, P, V, M], kN / kN·m.
            # Every rafter element runs toward +y (ys ascending) with PyNite's local y up, so its Mz + is tension on the
            # TOP face; M here is the design sign of bimsteelauto 0.14.1 (+ = top flange in compression) = −Mz. P + =
            # compression (PyNite's axial sign).
            stations = []
            for key, _, _ in raf_:
                for e_ in el_[key]:
                    mem = M_.members[e_]
                    Lm = mem.L()
                    for xx, nd in ((0.0, mem.i_node), (Lm, mem.j_node)):
                        stations.append([round(nd.X, 3), round(mem.axial(xx, combo) / 1000, 4), round(mem.shear("Fy", xx, combo) / 1000, 4),
                                         round(-mem.moment("Mz", xx, combo) / 1e6, 4)])
        res[combo] = {
            "set": kind, "rafter_stations": stations,
            "reactions": {cid: [round(M_.nodes[b].RxnFX[combo] / 1000, 3), round(M_.nodes[b].RxnFY[combo] / 1000, 3)] for cid, b in bas_.items()},
            "braces": braces_out,                                             # tension, kN
            "slack": slack, "roof_H": None if h is None else round(h, 4),
            "apex": round(M_.nodes[nm_[span / 2]].DY[combo], 3),
            "rafter_M": round(max(max(abs(M_.members[e_].max_moment("Mz", combo)), abs(M_.members[e_].min_moment("Mz", combo)))
                                  for key, _, _ in raf_ for e_ in el_[key]) / 1e6, 3),
            "column_P": {cid: round(max(M_.members[e_].max_axial(combo) for e_ in el_[cid]) / 1000, 3) for _, cid in cols},
        }
    lrfd_n = [c for c in sets if sets[c] == "LRFD"]
    asd = [c for c in sets if sets[c] == "ASD"]
    return {
        "end": end, "tributary_m": round(trib, 4), "cases": list(fl.cases), "results": res,
        "applied": {cs: [round(v, 4) for v in a_] for cs, a_ in applied.items() if not cs.startswith("N")},
        "roof_H": {cs: round(v, 4) for cs, v in roof_H.items() if not cs.startswith("N")}, "brace_cos": {k_: round(v, 6) for k_, v in brace_cos.items()},
        "dam": {"stiffness": DAM_STIFFNESS, "min_segments": DAM_MIN_SEGMENTS, "notional": ratio,
                "tau": {"alpha_Pr_Pns": round(float(tau[0]), 5), "member": tau[1], "combo": tau[2], "ok": bool(tau[0] <= 0.5)}},
        "summary": {"rafter_M_LRFD": max(((c, res[c]["rafter_M"]) for c in lrfd_n), key=lambda x: x[1]),
                    "column_P_LRFD": max(((c, cid, p_) for c in lrfd_n for cid, p_ in res[c]["column_P"].items()), key=lambda x: abs(x[2])),
                    "apex_ASD": min(((c, res[c]["apex"]) for c in asd), key=lambda x: x[1]),
                    "brace_T_LRFD": max(((c, b, v) for c in lrfd_n for b, v in res[c]["braces"].items()), key=lambda x: x[2])},
        "assumptions": ["in-plane sway held by the end-wall X-bracing (tension-only diagonals, modelled from a column base to the rafter node over the next column); no reliance on sheeting",
                        "wind columns pinned top and bottom, modelled up to the rafter centroid line",
                        "strength (LRFD): Direct Analysis Method — second order, 0.8 stiffness, notional loads, 4 elements per member (P-delta); cases and ASD first order on the nominal stiffness"],
        "designed": False,
    }
