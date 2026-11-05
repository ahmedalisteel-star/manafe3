# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 2 secondary steel layout. Geometry only, NOT designed (Phase 4).

Step 2 — purlin and girt LINES (continuous along the building; step 3 cuts them into lapped pieces).

Roof (each side A / B on its own settings):
    s = distance ALONG THE ROOF from the eave point (the outer column face on the roof line) to a member's web line, mm
    eave strut (C)   at s = first (default 0)
    ridge purlin (Z) at s = L_slope − apex_gap (default 200 mm from the apex; user range 150–300)
    the purlins between are evenly spaced: n = ceil((s_ridge − s_eave) / spacing), pitch = (s_ridge − s_eave) / n ≤ spacing
    a purlin stands on the roof line (its bottom on the rafter's top flange), tilted with the roof; the Z's top flange
    points up-slope, so side B's purlins run the other way along X (a Z cannot be mirrored)
Walls (each side wall A / B on its own settings):
    girts outside the column outer face, web horizontal (depth pointing out of the building), at
    z = first + k·spacing while z ≤ eave − top_gap (defaults 1250, 1250, 300)
Axes: X along the building, Y across (wall A at y = 0, wall B at y = span), Z up; mm.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field

DEFAULT_SPACING = 1250.0


@dataclass(frozen=True)
class RoofSide:
    spacing: float = DEFAULT_SPACING
    first: float = 0.0          # eave strut, along the roof from the eave point
    apex_gap: float = 200.0     # ridge purlin from the apex, along the roof

    def check(self, label: str) -> None:
        if not (300 <= self.spacing <= 3000):
            raise ValueError(f"{label}: purlin spacing must be 300 to 3000 mm")
        if not (0 <= self.first <= 2000):
            raise ValueError(f"{label}: the eave strut position must be 0 to 2000 mm")
        if not (150 <= self.apex_gap <= 300):
            raise ValueError(f"{label}: the ridge purlin must be 150 to 300 mm from the apex")


@dataclass(frozen=True)
class Wall:
    spacing: float = DEFAULT_SPACING
    first: float = DEFAULT_SPACING
    top_gap: float = 300.0

    def check(self, label: str) -> None:
        if not (300 <= self.spacing <= 3000):
            raise ValueError(f"{label}: girt spacing must be 300 to 3000 mm")
        if not (0 <= self.first <= 5000):
            raise ValueError(f"{label}: the first girt must be 0 to 5000 mm high")
        if not (0 <= self.top_gap <= 3000):
            raise ValueError(f"{label}: the gap under the eave must be 0 to 3000 mm")


@dataclass(frozen=True)
class Sections:
    purlin: str = "Z200x65x20x2.0"
    eave_strut: str = "C200x65x20x2.0"
    girt: str = "Z200x65x20x2.0"


@dataclass(frozen=True)
class SecondaryInput:
    span: float
    eave_height: float
    roof_slope: float
    length: float                       # building length along X (first to last frame line), mm
    roof_a: RoofSide = field(default_factory=RoofSide)
    roof_b: RoofSide = field(default_factory=RoofSide)
    wall_a: Wall = field(default_factory=Wall)
    wall_b: Wall = field(default_factory=Wall)
    sections: Sections = field(default_factory=Sections)


def _r(v: float) -> float:
    return round(v + 0.0, 3)


def roof_slope_length(span: float, slope: float) -> float:
    """Eave point to apex along the roof."""
    return math.hypot(span / 2.0, slope * span / 2.0)


def purlin_positions(span: float, slope: float, side: RoofSide) -> list[float]:
    """s of the eave strut, the purlins and the ridge purlin (in that order)."""
    s_ridge = roof_slope_length(span, slope) - side.apex_gap
    s0 = side.first
    if s_ridge - s0 < 300:
        raise ValueError("the roof is too short for an eave strut and a ridge purlin")
    n = math.ceil((s_ridge - s0) / side.spacing - 1e-9)
    pitch = (s_ridge - s0) / n
    return [s0 + k * pitch for k in range(n + 1)]


def roof_point(s: float, side: str, span: float, eave: float, slope: float) -> tuple[float, float]:
    """(y, z) of the point s along the roof from side A's or B's eave point."""
    c = 1.0 / math.sqrt(1.0 + slope * slope)
    dy, dz = s * c, s * slope * c
    return (dy, eave + dz) if side == "A" else (span - dy, eave + dz)


def girt_heights(eave: float, wall: Wall) -> list[float]:
    out, z = [], wall.first
    while z <= eave - wall.top_gap + 1e-9:
        out.append(z)
        z += wall.spacing
    return out


def secondary_lines(inp: SecondaryInput) -> dict:
    """Purlin and girt lines for the whole building (step 2)."""
    for lab, x in (("roof A", inp.roof_a), ("roof B", inp.roof_b)):
        x.check(lab)
    for lab, x in (("wall A", inp.wall_a), ("wall B", inp.wall_b)):
        x.check(lab)
    span, eave, slope, L = inp.span, inp.eave_height, inp.roof_slope, inp.length
    theta = math.degrees(math.atan(slope))
    roof = []
    for side, cfg in (("A", inp.roof_a), ("B", inp.roof_b)):
        ss = purlin_positions(span, slope, cfg)
        for k, s in enumerate(ss):
            y, z = roof_point(s, side, span, eave, slope)
            role = "eave_strut" if k == 0 else "ridge_purlin" if k == len(ss) - 1 else "purlin"
            x0, x1 = (0.0, L) if side == "A" else (L, 0.0)          # side B runs back along X: Z top flange up-slope
            roof.append(dict(
                id=f"R{side}{k}", role=role, side=side, s=_r(s),
                profile=inp.sections.eave_strut if role == "eave_strut" else inp.sections.purlin,
                start=[_r(x0), _r(y), _r(z)], end=[_r(x1), _r(y), _r(z)],
                # rotation θ on both sides: side A runs +X, side B −X, so geom.js frame() gives v = the roof normal and
                # u = up-slope on each (the Z's top flange and the C's flanges point up-slope)
                rotation=_r(theta), position="bottom",
            ))
    walls = []
    for side, cfg, y in (("A", inp.wall_a, 0.0), ("B", inp.wall_b, span)):
        for k, z in enumerate(girt_heights(eave, cfg)):
            x0, x1 = (0.0, L) if side == "A" else (L, 0.0)
            walls.append(dict(id=f"G{side}{k + 1}", role="girt", side=side, z=_r(z), profile=inp.sections.girt,
                              start=[_r(x0), _r(y), _r(z)], end=[_r(x1), _r(y), _r(z)], rotation=90.0, position="bottom"))
    return {"roof": roof, "walls": walls, "slope_length": _r(roof_slope_length(span, slope)), "designed": False}


# ---- step 3: pieces, laps, holes, cleats ------------------------------------------------------------------------------
"""
Decisions (user, 2026-11-05):
    lap each side of a frame = 10 % of THAT side's bay (6 m → 600) unless the job sets a fixed lap; Z lines lap over every
      interior frame (the piece of bay i runs lap(b_{i-1}) back past frame i, the piece of bay i-1 runs lap(b_i) past it)
    holes: M12 → 14 mm (M16 → 18), 2 in the web at gauge g = H − 2·(lip + 25), centred on the web, at every frame; 2 at
      each lap end, 40 mm from that piece's end, through both lapped pieces
    cleat: PL8 × (H − 20) × 100 welded to the frame flange, standing on it, beside the web (Z: the up-slope / upper side,
      C: the back of the web); its holes match the purlin's
    ends: the pieces run out to the end-wall girt line (end_overhang past the end frame lines)
    eave strut (C): one piece per bay, butt joints with a 10 mm gap at interior frames, 2 holes 25 mm each side of the
      frame line (a 4-hole cleat); at the end frames 2 holes on the frame line
"""

HOLE ={"M12": 14.0, "M16": 18.0}
LAP_END_EDGE = 40.0
BUTT_GAP = 10.0
BUTT_HOLE = 25.0
_CF = re.compile(r"^([CZ])\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)\s*[xX]\s*(\d+(?:\.\d+)?)$")


def cf_dims(name: str) -> dict:
    m = _CF.match(name.strip())
    if not m:
        raise ValueError(f"{name} is not a lipped C or Z name (e.g. Z200x65x20x2.0)")
    return {"kind": m[1].upper(), "H": float(m[2]), "B": float(m[3]), "D": float(m[4]), "t": float(m[5])}


def gauge(name: str) -> float:
    d = cf_dims(name)
    return d["H"] - 2.0 * (d["D"] + 25.0)


def lap_at(bay: float, fixed: float | None) -> float:
    return fixed if fixed is not None else 0.1 * bay


def z_pieces(frames: list[float], overhang: float, fixed_lap: float | None) -> list[dict]:
    """Lapped pieces of one line in line coordinates ℓ (frames ascending from the line's start). Each piece:
    {a, b, holes_l}: its extent and the ℓ of its web-hole pairs (frames, its own lap ends, the neighbour's lap ends)."""
    n = len(frames) - 1
    bays = [frames[i + 1] - frames[i] for i in range(n)]
    out = []
    for j in range(n):
        a = frames[j] - (lap_at(bays[j - 1], fixed_lap) if j > 0 else overhang)
        b = frames[j + 1] + (lap_at(bays[j + 1], fixed_lap) if j < n - 1 else overhang)
        holes = [frames[j], frames[j + 1]]
        if j > 0:     # lap at frame j: own start, the previous piece's end
            holes += [a + LAP_END_EDGE, frames[j] + lap_at(bays[j], fixed_lap) - LAP_END_EDGE]
        if j < n - 1:  # lap at frame j+1: own end, the next piece's start
            holes += [b - LAP_END_EDGE, frames[j + 1] - lap_at(bays[j], fixed_lap) + LAP_END_EDGE]
        out.append({"a": a, "b": b, "holes_l": sorted(holes)})
    return out


def c_pieces(frames: list[float], overhang: float) -> list[dict]:
    """Butt-jointed pieces (eave strut): one per bay, 10 mm gap at interior frames."""
    n = len(frames) - 1
    out = []
    for j in range(n):
        a = frames[j] + BUTT_GAP / 2 if j > 0 else frames[0] - overhang
        b = frames[j + 1] - BUTT_GAP / 2 if j < n - 1 else frames[-1] + overhang
        holes = [frames[j] + BUTT_HOLE if j > 0 else frames[0], frames[j + 1] - BUTT_HOLE if j < n - 1 else frames[-1]]
        out.append({"a": a, "b": b, "holes_l": holes})
    return out


def secondary_members(lines: dict, frames: list[float], end_overhang: float, bolt: str = "M12", fixed_lap: float | None = None,
                      extra_holes: list[dict] | None = None) -> dict:
    """Pieces with their web holes (DetailCraft member holes: face web, x from the piece start, y across the web from the
    section centre) and the cleats, from secondary_lines() and the frame lines' x (ascending)."""
    if bolt not in HOLE:
        raise ValueError("bolt must be M12 or M16")
    if fixed_lap is not None and not (100 <= fixed_lap <= 3000):
        raise ValueError("a fixed lap must be 100 to 3000 mm each side")
    d0 = HOLE[bolt]
    L = frames[-1] - frames[0]
    members, cleats = [], []
    for line in lines["roof"] + lines["walls"]:
        dims = cf_dims(line["profile"])
        g = gauge(line["profile"])
        if g <= 2 * d0:
            raise ValueError(f"{line['profile']}: the gauge {g:g} mm is too small for two {bolt} holes")
        forward = line["end"][0] > line["start"][0]
        x0 = line["start"][0]
        to_l = (lambda x: x - x0) if forward else (lambda x: x0 - x)
        fl = sorted(to_l(x) for x in frames)
        is_c = dims["kind"] == "C"
        pieces = c_pieces(fl, end_overhang) if is_c else z_pieces(fl, end_overhang, fixed_lap)
        sgn = 1.0 if forward else -1.0
        extra = [h for h in (extra_holes or []) if h["line"] == line["id"]]   # e.g. sag-rod holes (bracing.py), world x
        for k, p in enumerate(pieces):
            holes = [{"face": "web", "x": _r(h - p["a"]), "y": _r(sy * g / 2), "d": d0} for h in p["holes_l"] for sy in (-1, 1)]
            for h in extra:
                lx = to_l(h["x"])
                if p["a"] < lx < p["b"]:
                    holes.append({"face": "web", "x": _r(lx - p["a"]), "y": h["y"], "d": h["d"]})
            members.append({
                "id": f"{line['id']}-{k + 1}", "role": line["role"], "side": line["side"], "line": line["id"], "profile": line["profile"],
                "start": [_r(x0 + sgn * p["a"]), line["start"][1], line["start"][2]],
                "end": [_r(x0 + sgn * p["b"]), line["start"][1], line["start"][2]],
                "rotation": line["rotation"], "position": line["position"], "length": _r(p["b"] - p["a"]), "holes": holes, "designed": False,
            })
        h = dims["H"] - 20.0
        # the line's section axes (geom.js frame(): x along the line, v0 = Z, u0 = v0 × x, turned by the rotation)
        a = math.radians(line["rotation"])
        u0 = (0.0, sgn, 0.0)
        u = (0.0, math.cos(a) * u0[1], math.sin(a))
        v = (0.0, -math.sin(a) * u0[1], math.cos(a))
        off = -(dims["B"] / 2 + 4.0) if is_c else dims["t"] / 2 + 4.0     # beside the web: C at its back, Z on its upper side
        for i, xf in enumerate(sorted(frames)):
            interior_c = is_c and 0 < i < len(frames) - 1
            along = [-BUTT_HOLE, BUTT_HOLE] if interior_c else [0.0]
            st = [xf, line["start"][1] + off * u[1], line["start"][2] + off * u[2]]
            cleats.append({
                "start": [_r(c) for c in st], "end": [_r(st[0]), _r(st[1] + h * v[1]), _r(st[2] + h * v[2])], "width_dir": [sgn, 0.0, 0.0],
                "line": line["id"], "frame": i, "x": _r(xf), "base": [_r(xf), line["start"][1], line["start"][2]],
                "rotation": line["rotation"], "profile": f"PL8x100", "height": _r(h), "side": "back" if is_c else "up",
                "holes": [{"along": _r(a), "up": _r(dims["H"] / 2 + sy * g / 2), "d": d0} for a in along for sy in (-1, 1)],
                "host": ("column" if line["role"] in ("girt", "eave_strut") else "rafter") + " " + line["side"],
            })
    return {"members": members, "cleats": cleats, "bolt": bolt, "hole": d0, "length": L, "designed": False}
