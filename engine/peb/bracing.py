# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 2 step 4: sag rods, X-bracing, flange braces. Geometry only, NOT designed (Phase 4).

User decisions (2026-11-05):
    sag rods      M12; 1 row at mid-bay for bays ≤ 7.5 m, 2 rows (third points) above; purlin to purlin from the eave strut
                  to the ridge purlin, plus one across the ridge between the two ridge purlins; through the webs at ONE
                  THIRD OF THE DEPTH BELOW THE TOP FLANGE (2H/3 above the roof)
    X-bracing     in the chosen bays, roof and side walls; rods M20 by default, or angles (L75x6); roof nodes near 45°
                  (panels about as long up the roof as the bay is wide, snapped to the nearest purlin line; the eave
                  strut and the ridge purlin always nodes); walls: one X if eave ≤ 1.5 × bay, else two panels with a node
                  at the girt nearest mid-height
    flange braces L50x5, a PAIR (one each side of the frame web) at 45°: roof — every purlin over the haunch plus the next
                  one, at every frame (end frames: the inward brace only — user, 2026-11-08); columns — the top two girts
                  of every column (end columns: the inward brace only)
Claude's detailing defaults (flagged to the user, editable): a sag-rod piece ends in its own hole, adjacent pieces 80 mm
apart along the purlin (two rods cannot share one hole), 50 mm of thread each end; roof brace rods pass through the rafter
web 75 mm below the top flange; wall braces lie in the column web plane at mid-height, from the base to 100 mm below the
eave; a flange brace meets the purlin / girt 50 mm into it from the frame; column flange braces are horizontal in plan.
Axes and roof distance s as in secondary.py.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .builtup_frame import BuiltUpSizes
from .secondary import cf_dims, roof_point

SAG_HOLE_OFFSET = 40.0       # each rod end 40 mm from the row line (adjacent pieces 80 mm apart)
THREAD = 50.0                # per rod end, added to the web-to-web length
ROOF_BRACE_BELOW = 75.0      # below the rafter's top flange
WALL_BRACE_TOP = 100.0       # below the eave
INTO_SECONDARY = 50.0        # flange brace end into the purlin / girt


@dataclass(frozen=True)
class BracingInput:
    span: float
    eave_height: float
    roof_slope: float
    frames: list[float]                     # frame line x, ascending
    sizes: BuiltUpSizes                     # the main frames (column and rafter depths)
    braced_bays: list[int] = field(default_factory=list)   # 0-based bay indices
    brace_type: str = "rod"                 # "rod" or "angle"
    brace_rod: str = "RD20"
    brace_angle: str = "L75x6"
    sag_rod: str = "RD12"
    ridge_tie: str = "rod"                # across the apex between the two ridge purlins: "rod" (the sag rod) or "strap"
    ridge_strap: str = "PL3x50"            # the strap: a flat 3 x 50, one bolt each end (CONFIRMED by the user)
    flange_brace: str = "L50x5"


def _r(v: float) -> float:
    return round(v + 0.0, 3)


def _n(side: str, slope: float) -> tuple[float, float]:
    """Roof normal (y, z), pointing out of the roof."""
    c = 1 / math.sqrt(1 + slope * slope)
    return (-slope * c, c) if side == "A" else (slope * c, c)


def _up(side: str, slope: float) -> tuple[float, float]:
    """Up-slope direction (y, z)."""
    c = 1 / math.sqrt(1 + slope * slope)
    return (c, slope * c) if side == "A" else (-c, slope * c)


def _pt(side, s, h, slope, span, eave, along=0.0):
    """(y, z) of the point s along the roof, h along the roof normal, `along` up-slope."""
    y, z = roof_point(s, side, span, eave, slope)
    ny, nz = _n(side, slope)
    uy, uz = _up(side, slope)
    return (y + h * ny + along * uy, z + h * nz + along * uz)


def rafter_depth(s: float, inp: BracingInput) -> float:
    """Overall rafter depth at roof distance s (built-up frame: haunch from the column's inner face, then constant)."""
    z = inp.sizes
    s0 = (z.hw_knee + 2 * z.tf) * math.sqrt(1 + inp.roof_slope ** 2)
    d = s - s0
    hw = z.hw_rafter if d >= z.haunch_length else z.hw_knee + (z.hw_rafter - z.hw_knee) * max(d, 0) / z.haunch_length
    return hw + 2 * z.tf


def column_depth(zh: float, inp: BracingInput) -> float:
    z = inp.sizes
    return z.hw_base + (z.hw_knee - z.hw_base) * zh / inp.eave_height + 2 * z.tf


def sag_rods(lines: dict, inp: BracingInput) -> dict:
    span, eave, slope = inp.span, inp.eave_height, inp.roof_slope
    rows = []
    for x0, x1 in zip(inp.frames, inp.frames[1:]):
        b = x1 - x0
        rows += [x0 + b / 2] if b <= 7500 else [x0 + b / 3, x0 + 2 * b / 3]
    rod_d = float(inp.sag_rod[2:])
    members, holes = [], []
    by_side = {s: sorted([m for m in lines["roof"] if m["side"] == s], key=lambda m: m["s"]) for s in "AB"}

    def web(m):   # the web line's up-slope offset from the member line (a C's web is at its back)
        d = cf_dims(m["profile"])
        return -(d["B"] / 2 - d["t"] / 2) if d["kind"] == "C" else 0.0

    def h_rod(m):
        return 2 * cf_dims(m["profile"])["H"] / 3

    for xr in rows:
        ends = []   # (side, line, point) chain eave → ridge per side, then the ridge rod
        for side in "AB":
            ls = by_side[side]
            for k in range(len(ls) - 1):
                a, b = ls[k], ls[k + 1]
                xa = xr + (SAG_HOLE_OFFSET if k % 2 else -SAG_HOLE_OFFSET)
                pa = _pt(side, a["s"], h_rod(a), slope, span, eave, web(a))
                pb = _pt(side, b["s"], h_rod(b), slope, span, eave, web(b))
                ends.append((side, a, b, xa, pa, pb))
        ra, rb = by_side["A"][-1], by_side["B"][-1]
        # the ridge rod's holes must miss the last chain hole in BOTH ridge purlins
        oa, ob = (SAG_HOLE_OFFSET if (len(by_side[s]) - 2) % 2 else -SAG_HOLE_OFFSET for s in "AB")
        x_ridge = xr - oa if oa == ob else xr
        ends.append(("ridge", ra, rb, x_ridge, _pt("A", ra["s"], h_rod(ra), slope, span, eave), _pt("B", rb["s"], h_rod(rb), slope, span, eave)))
        for side, a, b, xa, pa, pb in ends:   # the last one is the ridge tie (user, 2026-11-05: ties the ridge purlins so sag forces balance)
            web_len = math.hypot(pa[0] - pb[0], pa[1] - pb[1])
            tie = side == "ridge"
            prof = (inp.ridge_strap if inp.ridge_tie == "strap" else inp.sag_rod) if tie else inp.sag_rod
            members.append({"role": "ridge_tie" if tie else "sag_rod", "side": side, "profile": prof, "start": [_r(xa), _r(pa[0]), _r(pa[1])],
                            "end": [_r(xa), _r(pb[0]), _r(pb[1])], "cut_length": _r(web_len + 2 * THREAD), "designed": False})
            for m in (a, b):
                holes.append({"line": m["id"], "x": _r(xa), "y": _r(h_rod(m) - cf_dims(m["profile"])["H"] / 2), "d": rod_d + 2})
    if inp.ridge_tie not in ("rod", "strap"):
        raise ValueError("ridge tie must be rod or strap")
    straps = sum(1 for m in members if m["role"] == "ridge_tie" and inp.ridge_tie == "strap")
    n = len(members) - straps
    fasteners = [{"item": f"nut M{rod_d:g}", "count": 4 * n}, {"item": f"washer M{rod_d:g}", "count": 4 * n}]
    if straps:
        fasteners.append({"item": f"bolt M{rod_d:g} with nut and washer", "count": 2 * straps})
    return {"members": members, "holes": holes, "rows": [_r(x) for x in rows], "fasteners": fasteners,
            "fastener_rule": "per rod: a nut and a washer each side of each web it ends at (4 + 4); per strap: one bolt each end"}


def roof_nodes(ss: list[float], bay: float) -> list[float]:
    """Node s values near 45°: n panels = max(1, round(run / bay)), each target snapped to the nearest purlin line."""
    run = ss[-1] - ss[0]
    n = max(1, round(run / bay))
    out = [ss[0]]
    for i in range(1, n):
        t = ss[0] + run * i / n
        best = min(ss, key=lambda s: abs(s - t))
        if best not in out and best != ss[-1]:
            out.append(best)
    return out + [ss[-1]]


def x_bracing(lines: dict, girts: dict, inp: BracingInput) -> list[dict]:
    span, eave, slope, z = inp.span, inp.eave_height, inp.roof_slope, inp.sizes
    prof = inp.brace_rod if inp.brace_type == "rod" else inp.brace_angle
    if inp.brace_type not in ("rod", "angle"):
        raise ValueError("brace type must be rod or angle")
    out = []
    nb = len(inp.frames) - 1
    for j in inp.braced_bays:
        if not (0 <= j < nb):
            raise ValueError(f"braced bay {j + 1} does not exist (the building has {nb} bays)")
        x0, x1 = inp.frames[j], inp.frames[j + 1]
        bay = x1 - x0
        for side in "AB":
            ss = sorted(m["s"] for m in lines["roof"] if m["side"] == side)
            nodes = roof_nodes(ss, bay)
            for sa, sb in zip(nodes, nodes[1:]):
                pa = _pt(side, sa, -(z.tf + ROOF_BRACE_BELOW), slope, span, eave)
                pb = _pt(side, sb, -(z.tf + ROOF_BRACE_BELOW), slope, span, eave)
                for (xa, a), (xb, b) in (((x0, pa), (x1, pb)), ((x1, pa), (x0, pb))):
                    out.append({"role": "roof_brace", "side": side, "bay": j, "profile": prof, "start": [_r(xa), _r(a[0]), _r(a[1])],
                                "end": [_r(xb), _r(b[0]), _r(b[1])], "length": _r(math.dist((xa, *a), (xb, *b))), "designed": False})
            # wall of this side
            yw = column_depth(eave / 2, inp) / 2
            y = yw if side == "A" else span - yw
            top = eave - WALL_BRACE_TOP
            zs = [0.0, top]
            if eave > 1.5 * bay:
                gz = [g["z"] for g in girts if g["side"] == side]
                if gz:
                    zs = [0.0, min(gz, key=lambda h: abs(h - eave / 2)), top]
            for za, zb in zip(zs, zs[1:]):
                for xa, xb in ((x0, x1), (x1, x0)):
                    out.append({"role": "wall_brace", "side": side, "bay": j, "profile": prof, "start": [_r(xa), _r(y), _r(za)],
                                "end": [_r(xb), _r(y), _r(zb)], "length": _r(math.hypot(bay, zb - za)), "designed": False})
    return out


def flange_braces(lines: dict, inp: BracingInput) -> list[dict]:
    span, eave, slope, z = inp.span, inp.eave_height, inp.roof_slope, inp.sizes
    out = []
    s0 = (z.hw_knee + 2 * z.tf) * math.sqrt(1 + slope ** 2)
    for side in "AB":
        purl = sorted([m for m in lines["roof"] if m["side"] == side and m["role"] != "eave_strut"], key=lambda m: m["s"])
        zone = [m for m in purl if s0 < m["s"] <= s0 + z.haunch_length]
        nxt = [m for m in purl if m["s"] > s0 + z.haunch_length][:1]
        for xf in inp.frames:                                # every frame line (end frames: user, 2026-11-08)
            for m in zone + nxt:
                d = rafter_depth(m["s"], inp)
                low = _pt(side, m["s"], -(d - z.tf / 2), slope, span, eave)
                high = _pt(side, m["s"], INTO_SECONDARY, slope, span, eave)
                run = d - z.tf / 2 + INTO_SECONDARY          # 45°: the same distance along X
                for sx in (-1, 1):
                    if not (inp.frames[0] <= xf + sx * run <= inp.frames[-1]):
                        continue   # an end frame: only the brace that stays inside the building
                    out.append({"role": "flange_brace", "host": "rafter " + side, "line": m["id"], "profile": inp.flange_brace,
                                "start": [_r(xf), _r(low[0]), _r(low[1])], "end": [_r(xf + sx * run), _r(high[0]), _r(high[1])],
                                "length": _r(run * math.sqrt(2)), "designed": False})
    # columns: the top two girts of every column, horizontal in plan
    for side, sgn, y0 in (("A", 1, 0.0), ("B", -1, span)):
        gs = sorted([g for g in lines["walls"] if g["side"] == side], key=lambda g: g["z"])[-2:]
        for xf in inp.frames:
            for g in gs:
                d = column_depth(g["z"], inp)
                y_in = y0 + sgn * (d - z.tf / 2)
                y_out = y0 - sgn * INTO_SECONDARY
                run = d - z.tf / 2 + INTO_SECONDARY
                for sx in (-1, 1):
                    if not (inp.frames[0] <= xf + sx * run <= inp.frames[-1]) and xf in (inp.frames[0], inp.frames[-1]):
                        continue   # an end column: only the brace that stays inside the building
                    out.append({"role": "flange_brace", "host": "column " + side, "line": g["id"], "profile": inp.flange_brace,
                                "start": [_r(xf), _r(y_in), _r(g["z"])], "end": [_r(xf + sx * run), _r(y_out), _r(g["z"])],
                                "length": _r(run * math.sqrt(2)), "designed": False})
    return out
