# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
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

import dataclasses
import math

from .bracing import WALL_BRACE_TOP, BracingInput, rafter_depth
from .builtup_frame import BuiltUpSizes, _split, mark
from .secondary import HOLE, Wall, gauge, girt_heights, z_pieces

MAX_WIND_SPACING = 6000.0
# wind column placeholder (user, 2026-11-05): built-up web 300 constant, flanges 150x8, S355; NOT designed
WIND_COLUMN = {"hw": 300.0, "tw": 6.0, "bf": 150.0, "tf": 8.0, "grade": "S355"}
SECTION_KEYS = ("hw", "tw", "bf", "tf")   # a wind-column / end-rafter override (Phase 4 step 9: the sizing loop)


def wind_column_section(over: dict | None = None) -> dict:
    """The wind columns' section: the placeholder, with an override's hw / tw / bf / tf (and grade) on top."""
    return {**WIND_COLUMN, **{k: float(v) for k, v in (over or {}).items() if k in SECTION_KEYS}, **({"grade": over["grade"]} if over and over.get("grade") else {})}


def check_section(name: str, over: dict | None) -> None:
    if not over:
        return
    bad = set(over) - set(SECTION_KEYS) - {"grade"}
    if bad:
        raise ValueError(f"{name}: unknown key(s) {sorted(bad)} (hw, tw, bf, tf, grade)")
    for k in SECTION_KEYS:
        if k in over and not (isinstance(over[k], (int, float)) and over[k] > 0):
            raise ValueError(f"{name}: {k} must be a number above 0")
# its top follows the rafter slope under a cap plate (user); PL10, 20 mm past the column all round (CONFIRMED by the user)
CAP_T = 10.0
CAP_EDGE = 20.0


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
             wall: Wall = Wall(), girt: str = "Z200x65x20x2.0", bolt: str = "M12", top_gap: float = 300.0,
             wc: dict | None = None, er: dict | None = None) -> dict:
    """The end wall at the first (end='first') or last (end='last') frame line x_frame. wc / er: the wind-column and
    end-rafter section overrides {hw, tw, bf, tf} (None: the placeholder / the main rafter's section)."""
    WC = wind_column_section(wc)
    if kind not in ("frame", "rafter"):
        raise ValueError("end wall type must be frame or rafter")
    out_dir = -1.0 if end == "first" else 1.0          # outward along X
    x_face = x_frame + out_dir * z.bf / 2               # the end-wall plane (outer flange faces)
    c = math.sqrt(1 + slope * slope)
    raf_d = z.hw_rafter + 2 * z.tf
    members = []
    ys = wind_column_ys(span, z.bf, kind)
    bi = BracingInput(span=span, eave_height=eave, roof_slope=slope, frames=[x_frame], sizes=z)
    u_sign = 1.0 if end == "first" else -1.0            # a wind column's u (across its flanges) is +Y at the first end, -Y at the last
    wd = WC["hw"] + 2 * WC["tf"]       # its overall depth along X
    for k, y in enumerate(ys):
        under = raf_d if kind == "rafter" else rafter_depth(roof_s(y, span, slope), bi)
        rise = 0.0 if abs(y - span / 2) < 1.0 else (slope if y < span / 2 else -slope)   # dz/dy of the roof over the column
        top = roof_z(y, span, eave, slope) - (under + CAP_T) * c
        seg = dict(length=_r(top), hw_start=WC["hw"], hw_end=WC["hw"], tw=WC["tw"], bf_top=WC["bf"], tf_top=WC["tf"],
                   bf_bot=WC["bf"], tf_bot=WC["tf"], grade=WC["grade"], straight="top")
        members.append(dict(id=f"W{end[0].upper()}{k + 1}", role="wind_column", start=[_r(x_face), _r(y), 0.0], end=[_r(x_face), _r(y), _r(top)],
                            rotation=180.0 if end == "first" else 0.0,
                            section=dict(segments=[seg], cut_start=0.0, cut_end=0.0, cut_end_u=_r(u_sign * rise))))
        # cap plate: PL10, the column + 20 mm all round, lying on the roof slope over the column, its mid-plane 5 mm above the top
        ny, nz = -rise / c, 1.0 / c                      # roof normal (y, z)
        xa, xb = x_face + out_dir * CAP_EDGE, x_face - out_dir * (wd + CAP_EDGE)
        members.append(dict(id=f"W{end[0].upper()}{k + 1}-CAP", role="cap_plate", profile=f"PL{CAP_T:g}x{WC['bf'] + 2 * CAP_EDGE:g}",
                            start=[_r(xa), _r(y + ny * CAP_T / 2), _r(top + nz * CAP_T / 2)], end=[_r(xb), _r(y + ny * CAP_T / 2), _r(top + nz * CAP_T / 2)],
                            width_dir=[0.0, _r(1.0 / c), _r(rise / c)], rotation=0.0, position="middle", material=WC["grade"], designed=False))
    if kind == "rafter":
        apex = [_r(x_frame), _r(span / 2), _r(eave + slope * span / 2)]
        for side, y0 in (("A", 0.0), ("B", span)):
            L = math.hypot(span / 2, slope * span / 2)
            members.append(dict(id=f"E{end[0].upper()}R{side}", role="end_rafter", start=[_r(x_frame), _r(y0), _r(eave)], end=apex, rotation=0.0,
                                section=dict(segments=_er_segments(L, z, er), cut_start=_r(slope), cut_end=_r(slope))))
    for m in members:
        if "section" in m:
            m.update(material=m["section"]["segments"][0]["grade"], designed=False, profile=mark(m["section"]["segments"]))
    supports = sorted(ys) if kind == "rafter" else sorted([z.bf / 2, *ys, span - z.bf / 2])
    return {"members": members, "girts": gable_girts(kind, span, eave, slope, x_face, out_dir, ys, z, wall, girt, bolt, top_gap, end),
            "x_face": _r(x_face), "supports": [_r(s) for s in supports]}


def _er_segments(L: float, z: BuiltUpSizes, er: dict | None) -> list[dict]:
    if not er:
        return _split(L, z.hw_rafter, z)
    ze = dataclasses.replace(z, bf=float(er.get("bf", z.bf)), tf=float(er.get("tf", z.tf)), grade=er.get("grade", z.grade))
    return _split(L, float(er.get("hw", z.hw_rafter)), ze, er.get("tw"))


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


WC_BRACE_EVERY = 2          # default: a flange-brace pair at every second gable girt (user, 2026-11-09); 0 = none
WC_BRACE_PROFILE = "L50x5"


def wind_column_braces(end: str, x_face: float, columns: list[dict], girts: list[dict], every: int = WC_BRACE_EVERY,
                       profile: str = WC_BRACE_PROFILE, wc: dict | None = None) -> list[dict]:
    """Flange braces from the gable girts to each wind column's INNER flange (user decision 2026-11-09), like the main
    columns' (bracing.py): a pair at 45°, horizontal in plan, from the inner flange's mid-thickness to 50 mm into the girt
    on the outer face. Rows: the girt rows a column carries (below its top), the TOP one and then every `every`-th row
    downward (Claude's default count from the top: the upper part of the column, where suction moments are largest,
    is braced first; editable per wall, 0 = none). A brace is made only where a girt piece actually runs past its end
    (openings, wall ends)."""
    if not every:
        return []
    from .bracing import INTO_SECONDARY
    out_dir = -1.0 if end == "first" else 1.0
    WC = wind_column_section(wc)
    wd = WC["hw"] + 2 * WC["tf"]
    x_in = x_face - out_dir * (wd - WC["tf"] / 2)                       # the inner flange's mid-thickness
    x_out = x_face + out_dir * INTO_SECONDARY                           # 50 mm into the girt
    run = wd - WC["tf"] / 2 + INTO_SECONDARY                             # 45° in plan
    out = []
    for c in columns:
        y, top = c["start"][1], c["end"][2]
        rows = sorted({g["z"] for g in girts if g["z"] < top - 1.0}, reverse=True)[::every]
        for zr in sorted(rows):
            for sy in (-1.0, 1.0):
                yb = y + sy * run
                if not any(g["z"] == zr and min(g["start"][1], g["end"][1]) - 1e-6 <= yb <= max(g["start"][1], g["end"][1]) + 1e-6 for g in girts):
                    continue                                             # no girt there (a wall end, an opening)
                out.append({"role": "flange_brace", "host": "wind column " + c["id"], "line": next(g["id"] for g in girts if g["z"] == zr and min(g["start"][1], g["end"][1]) - 1e-6 <= yb <= max(g["start"][1], g["end"][1]) + 1e-6),
                            "profile": profile, "start": [_r(x_in), _r(y), _r(zr)], "end": [_r(x_out), _r(yb), _r(zr)],
                            "length": _r(run * math.sqrt(2)), "wall": end, "designed": False})
    return out


def endwall_braces(end: str, x_face: float, span: float, eave: float, supports: list[float], tops: dict[float, float],
                   bays: tuple[int, ...], profile: str, wc: dict | None = None) -> list[dict]:
    """X-bracing in the end-wall plane (user decision 2026-11-08: the end-rafter frame does NOT rely on sheeting; default
    one braced bay per end-rafter wall). An end-wall bay k (1-based, counted from column line A) lies between supports
    k−1 and k. Set-out (Claude, as the side walls): the diagonals run in the wind columns' centre plane, from a column's
    base to 100 mm below the other column's top (a main-frame corner column: below the eave), one X per bay.
    tops: support y → its top z (wind columns); a support missing there is a main-frame column (eave)."""
    sup = sorted(supports)
    out_dir = -1.0 if end == "first" else 1.0
    WC = wind_column_section(wc)
    wd = WC["hw"] + 2 * WC["tf"]
    x = x_face - out_dir * wd / 2
    out = []
    for k in bays:
        if not (1 <= k < len(sup)):
            raise ValueError(f"end-wall braced bay {k} does not exist (the {end} end wall has {len(sup) - 1} bays)")
        ya, yb = sup[k - 1], sup[k]
        for y0, y1 in ((ya, yb), (yb, ya)):
            z1 = tops.get(round(y1, 3), eave) - WALL_BRACE_TOP
            out.append({"id": f"X{end[0].upper()}{k}{'a' if y0 == ya else 'b'}", "role": "endwall_brace", "wall": end, "bay": k,
                        "profile": profile, "start": [_r(x), _r(y0), 0.0], "end": [_r(x), _r(y1), _r(z1)],
                        "length": _r(math.hypot(y1 - y0, z1)), "designed": False})
    return out
