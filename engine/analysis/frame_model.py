# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 3 step 2: one Manafe3 frame line → a bimsteelauto FrameLayout (2D, solved by its verified FrameAnalysis).

User decision (2026-11-05): members on their CENTROID LINES, with RIGID links at the knee (and the ridge if needed).
In the frame plane: X = the building's y (across the span), Y = z (up); mm.

    column     from its base centroid (pinned / fixed support) up to the height of the rafter's start centroid; its
               centroid sits d − ȳ inside its line (the outer face: "straight top"), so a tapered column's centroid line
               is inclined; WeldedI gives ȳ (bimsteelauto)
    knee       a horizontal RIGID link from the column's top node to the rafter's start node (the knee panel)
    rafter     the plumb-cut ends' face centroids lie straight below the roof point by e/cos θ (e = centroid depth from the
               top of steel); splice nodes lie e below the roof line along its normal; each segment is one FrameMember
               (a TaperedMember between its end sections)
    ridge      both rafters' plumb end centroids fall on the same point under the apex for a symmetric frame — one node;
               otherwise a rigid link joins them
A splice where the flange THICKNESS changes moves the centroid by a few mm: the node is placed on the left segment's
centroid (noted, not modelled). Rigid links carry no load and no self-weight.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from bimsteelauto.analysis import FrameLayout
from bimsteelauto.analysis.frame import BaseFixity, FrameMember, ModelSettings
from bimsteelauto.sections import TaperedMember, WeldedI
from bimsteelauto.spec import MemberType, PEBGeometry

RIGID = WeldedI(d=1500.0, tw=60.0, bf_top=800.0, tf_top=80.0, bf_bot=800.0, tf_bot=80.0)   # ≥ 100 × a rafter: a stiff arm


@dataclass(frozen=True)
class FrameModelInfo:
    layout: FrameLayout
    marks: dict[str, str]          # FrameLayout mark → the Manafe3 member id (rigid links: "rigid")
    roles: dict[str, str]          # mark → "column A" | "rafter A" | … | "link"


def _wi(seg: dict, hw: float) -> WeldedI:
    return WeldedI(d=hw + seg["tf_top"] + seg["tf_bot"], tw=seg["tw"], bf_top=seg["bf_top"], tf_top=seg["tf_top"],
                   bf_bot=seg["bf_bot"], tf_bot=seg["tf_bot"])


def _depth_below_top(seg: dict, hw: float) -> float:
    """Centroid depth below the top-of-steel face ("straight top": the top flange's outer face is on the line)."""
    w = _wi(seg, hw)
    return w.d - w.y_bar


def frame_line_model(members: list[dict], span: float, eave: float, slope: float, bays: tuple[float, ...],
                     base: str = "pinned", max_taper_step: float = 0.05) -> FrameModelInfo:
    """members: the four built-up members of one frame line in the engine's format (builtup_frame.py): roles column /
    rafter, sides A / B, 3D start / end (x = the frame line), section {segments, cut_start, cut_end}."""
    by = {(m["role"], m["side"]): m for m in members}
    for k in (("column", "A"), ("column", "B"), ("rafter", "A"), ("rafter", "B")):
        if k not in by:
            raise ValueError(f"frame line: no {k[0]} {k[1]}")
    c = math.sqrt(1.0 + slope * slope)
    nodes: dict[str, tuple[float, float]] = {}
    fms: list[FrameMember] = []
    marks: dict[str, str] = {}
    roles: dict[str, str] = {}

    def node(name, p):
        nodes[name] = (round(p[0], 6), round(p[1], 6))
        return nodes[name]

    rafter_start, rafter_end = {}, {}
    for side in "AB":
        r = by[("rafter", side)]
        y0, z0 = r["start"][1], r["start"][2]
        y1, z1 = r["end"][1], r["end"][2]
        L = math.hypot(y1 - y0, z1 - z0)
        dy, dz = (y1 - y0) / L, (z1 - z0) / L
        ny, nz = -dz, dy                                      # the roof normal, pointing up (out of the roof)
        if nz < 0:
            ny, nz = -ny, -nz
        segs = r["section"]["segments"]
        x, pts = 0.0, []
        for i, s in enumerate(segs):
            for end, hw, xx in (("a", s["hw_start"], x), ("b", s["hw_end"], x + s["length"])):
                e = _depth_below_top(s, hw)
                first, last = i == 0 and end == "a", i == len(segs) - 1 and end == "b"
                if first or last:                             # a plumb end: straight down from the roof point
                    py, pz = (y0, z0) if first else (y1, z1)
                    p = (py, pz - e * c)
                else:                                         # a splice: e below the roof line, along its normal
                    p = (y0 + dy * xx - ny * e, z0 + dz * xx - nz * e)
                if end == "a" and i > 0:
                    continue                                  # the splice node is the left segment's end centroid
                pts.append(p)
            x += s["length"]
        names = [f"R{side}0"] + [f"R{side}S{i}" for i in range(1, len(segs))] + ["RIDGE" if side == "A" else "RIDGEB"]
        for nm, p in zip(names, pts):
            node(nm, p)
        rafter_start[side], rafter_end[side] = names[0], names[-1]
        for i, s in enumerate(segs):
            pa, pb = nodes[names[i]], nodes[names[i + 1]]
            ln = math.dist(pa, pb)
            mk = f"R{side}{i + 1}"
            fms.append(FrameMember(mk, MemberType.RAFTER, TaperedMember(_wi(s, s["hw_start"]), _wi(s, s["hw_end"]), ln), pa, pb))
            marks[mk], roles[mk] = r["id"], f"rafter {side}"
    # the ridge: one node when the two plumb ends meet (symmetric frame), else a rigid link
    if math.dist(nodes["RIDGE"], nodes["RIDGEB"]) < 1e-3:
        pB = nodes.pop("RIDGEB")
        fms = [FrameMember(f.mark, f.member_type, f.taper, f.i_point if f.i_point != pB else nodes["RIDGE"],
                           nodes["RIDGE"] if f.j_point == pB else f.j_point) for f in fms]
    else:
        fms.append(FrameMember("KR", MemberType.RAFTER, TaperedMember(RIGID, RIGID, math.dist(nodes["RIDGE"], nodes["RIDGEB"])), nodes["RIDGE"], nodes["RIDGEB"]))
        marks["KR"], roles["KR"] = "rigid", "link"

    base_nodes, eave_nodes = [], []
    for side, sgn in (("A", 1.0), ("B", -1.0)):
        col = by[("column", side)]
        s = col["section"]["segments"][0]
        if len(col["section"]["segments"]) != 1:
            raise ValueError("a frame column in several segments is not modelled yet")
        y_line, H = col["start"][1], col["end"][2] - col["start"][2]
        zk = nodes[rafter_start[side]][1]                      # the column runs up to the rafter's start centroid
        hw_k = s["hw_start"] + (s["hw_end"] - s["hw_start"]) * zk / H
        pb = node(f"B{side}", (y_line + sgn * _depth_below_top(s, s["hw_start"]), 0.0))
        pk = node(f"K{side}", (y_line + sgn * _depth_below_top(s, hw_k), zk))
        mk = f"C{side}"
        fms.append(FrameMember(mk, MemberType.COLUMN, TaperedMember(_wi(s, s["hw_start"]), _wi(s, hw_k), math.dist(pb, pk)), pb, pk))
        marks[mk], roles[mk] = col["id"], f"column {side}"
        pr = nodes[rafter_start[side]]
        fms.append(FrameMember(f"K{side}L", MemberType.RAFTER, TaperedMember(RIGID, RIGID, math.dist(pk, pr)), pk, pr))
        marks[f"K{side}L"], roles[f"K{side}L"] = "rigid", "link"
        base_nodes.append(f"B{side}")
        eave_nodes.append(f"K{side}")

    geom = PEBGeometry(span_widths=(span,), bay_spacings=tuple(bays), eave_height=eave, roof_slope=slope, purlin_spacing=1250.0, girt_spacing=1250.0)
    settings = ModelSettings(base_fixity=BaseFixity.FIXED if base == "fixed" else BaseFixity.PINNED, max_taper_step=max_taper_step)
    layout = FrameLayout(members=tuple(fms), nodes=nodes, base_nodes=tuple(base_nodes), eave_nodes=tuple(eave_nodes),
                         ridge_nodes=("RIDGE",), geometry=geom, settings=settings)
    return FrameModelInfo(layout=layout, marks=marks, roles=roles)
