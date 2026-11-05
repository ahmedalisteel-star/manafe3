# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 2 step 5: end walls (gables). Geometry only, NOT designed (Phase 4).

User decisions (2026-11-05): an end wall is either the main frame, or an END RAFTER + WIND COLUMNS; built-up, wind columns
equally spaced at most 6 m, end rafter and wind columns constant built-up sections from the span rules.
Claude's set-out (flagged to the user, editable):
    * BOTH types get wind columns — gable girts cannot span between the two main columns (24 m and more): "main frame"
      = the portal frame + interior wind columns under its rafter; "rafter" = an end rafter on corner columns + interior
      wind columns (corner columns at y = bf/2 and span − bf/2, inside the side-wall girt lines)
    * wind column section: web plate = the span rules' rafter depth, flanges and web thickness by the rules, constant;
      depth along X (they bend under wind on the gable), outer flange on the end-wall plane = the main columns' outer face
      (x = −bf/2 at the first frame, L + bf/2 at the last) so the end-wall girt line is the same for both types
    * a wind column's top stops under the rafter's bottom flange at the column's centre line, cut square (the roof slope
      across its flange width, ≤ slope × bf, is not cut)
    * end rafter: constant built-up (the rafter section), from the eave point (y = 0) to the apex, cut plumb at both ends,
      split at 12 m for transport like the main rafters
    * gable girts: lapped Z over the wind columns (laps 10 % of each side's spacing), out to the side-wall girt lines;
      rows as the side walls (first 1 250, every 1 250); above the eave a row runs where it stays 300 mm under the roof
"""

from __future__ import annotations

import math

from .bracing import BracingInput, rafter_depth
from .builtup_frame import BuiltUpSizes, _seg, _split, mark
from .secondary import HOLE, Wall, gauge, girt_heights, z_pieces

MAX_WIND_SPACING = 6000.0


def _r(v: float) -> float:
    return round(v + 0.0, 3)


def wind_column_ys(span: float, bf: float, kind: str) -> list[float]:
    n = max(1, math.ceil(span / MAX_WIND_SPACING - 1e-9))
    ys = [span * k / n for k in range(n + 1)]
    if kind == "rafter":
        ys[0], ys[-1] = bf / 2, span - bf / 2         # corner columns inside the side-wall girt lines
        return ys
    return ys[1:-1]                                   # main frame: its own columns stand at the corners


def roof_z(y: float, span: float, eave: float, slope: float) -> float:
    return eave + slope * min(y, span - y)


def end_wall(kind: str, end: str, span: float, eave: float, slope: float, x_frame: float, z: BuiltUpSizes,
             wall: Wall = Wall(), girt: str = "Z200x65x20x2.0", bolt: str = "M12", top_gap: float = 300.0) -> dict:
    """The end wall at the first (end='first') or last (end='last') frame line x_frame."""
    if kind not in ("frame", "rafter"):
        raise ValueError("end wall type must be frame or rafter")
    out_dir = -1.0 if end == "first" else 1.0          # outward along X
    x_face = x_frame + out_dir * z.bf / 2               # the end-wall plane (outer flange faces)
    c = math.sqrt(1 + slope * slope)
    raf_d = z.hw_rafter + 2 * z.tf
    members = []
    ys = wind_column_ys(span, z.bf, kind)
    bi = BracingInput(span=span, eave_height=eave, roof_slope=slope, frames=[x_frame], sizes=z)
    for k, y in enumerate(ys):
        under = raf_d if kind == "rafter" else rafter_depth(roof_s(y, span, slope), bi)
        top = roof_z(y, span, eave, slope) - under * c
        seg = _seg(top, z.hw_rafter, z.hw_rafter, z)
        members.append(dict(id=f"W{end[0].upper()}{k + 1}", role="wind_column", start=[_r(x_face), _r(y), 0.0], end=[_r(x_face), _r(y), _r(top)],
                            rotation=180.0 if end == "first" else 0.0, section=dict(segments=[seg], cut_start=0.0, cut_end=0.0)))
    if kind == "rafter":
        apex = [_r(x_frame), _r(span / 2), _r(eave + slope * span / 2)]
        for side, y0 in (("A", 0.0), ("B", span)):
            L = math.hypot(span / 2, slope * span / 2)
            members.append(dict(id=f"E{end[0].upper()}R{side}", role="end_rafter", start=[_r(x_frame), _r(y0), _r(eave)], end=apex, rotation=0.0,
                                section=dict(segments=_split(L, z.hw_rafter, z), cut_start=_r(slope), cut_end=_r(slope))))
    for m in members:
        m.update(material=z.grade, designed=False, profile=mark(m["section"]["segments"]))
    return {"members": members, "girts": gable_girts(kind, span, eave, slope, x_face, out_dir, ys, z, wall, girt, bolt, top_gap, end), "x_face": _r(x_face)}


def roof_s(y: float, span: float, slope: float) -> float:
    """Distance along the roof from the nearer eave point to the point above y."""
    return min(y, span - y) * math.sqrt(1 + slope * slope)


def gable_girts(kind, span, eave, slope, x_face, out_dir, ys, z, wall, girt, bolt, top_gap, end) -> list[dict]:
    supports = sorted(ys) if kind == "rafter" else sorted([z.bf / 2, *ys, span - z.bf / 2])   # main frame: its columns too
    side_line = 200.0                                    # the side-wall girts' depth: the girt line is −200 / span + 200
    g, d0 = gauge(girt), HOLE[bolt]
    rows = list(girt_heights(eave, wall))
    zz = rows[-1] + wall.spacing if rows else wall.first
    while zz <= eave + slope * span / 2 - top_gap + 1e-9:   # gable rows above the eave
        rows.append(zz)
        zz += wall.spacing
    out = []
    for i, zr in enumerate(rows):
        if zr <= eave - top_gap + 1e-9:
            a, b = -side_line, span + side_line
        else:
            reach = (zr + top_gap - eave) / slope        # min(y, span − y) must be at least this
            a, b = reach, span - reach
        sup = [y for y in supports if a < y < b]
        if not sup:
            continue
        pieces = z_pieces(sup, 0.0, None) if len(sup) > 1 else [{"a": sup[0], "b": sup[0], "holes_l": [sup[0]]}]
        pieces[0]["a"], pieces[-1]["b"] = a, b            # run out to the side-wall girt lines / the roof
        for k, p in enumerate(pieces):
            out.append(dict(id=f"G{end[0].upper()}{i + 1}-{k + 1}", role="gable_girt", z=_r(zr), profile=girt,
                            start=[_r(x_face), _r(p["a"]), _r(zr)], end=[_r(x_face), _r(p["b"]), _r(zr)],
                            rotation=270.0 if out_dir < 0 else 90.0, position="bottom", length=_r(p["b"] - p["a"]),
                            holes=[{"face": "web", "x": _r(h - p["a"]), "y": _r(sy * g / 2), "d": d0} for h in p["holes_l"] for sy in (-1, 1)],
                            designed=False))
    return out
