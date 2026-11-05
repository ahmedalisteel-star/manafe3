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
