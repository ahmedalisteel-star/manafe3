# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 2 step 7: the whole PEB building in one call — main frames (Phase 1), secondary steel (steps 2–4), end walls
(step 5), openings (step 6) and cleats. Geometry only, NOT designed (Phase 4).

Every member carries `gen: "peb"` so the app can replace the generated members when the building is edited, and either
`section` (a built-up member, engine/peb/builtup_frame.py format) or `profile` (+ `holes`).
"""

from __future__ import annotations

import string
from dataclasses import dataclass, field

from .bracing import BracingInput, flange_braces, sag_rods, x_bracing
from .builtup_frame import BuiltUpSizes, builtup_frame_members, default_sizes
from .endwall import end_wall
from .openings import apply_openings
from .secondary import RoofSide, SecondaryInput, Sections, Wall, cf_dims, secondary_lines, secondary_members

ROLE_TYPE = {"column": "column", "rafter": "beam", "wind_column": "column", "end_rafter": "beam", "jamb": "column"}


@dataclass(frozen=True)
class BuildingInput:
    span: float
    eave_height: float
    roof_slope: float
    bay_spacing: float
    n_bays: int
    sizes: BuiltUpSizes | None = None
    roof_a: RoofSide = field(default_factory=RoofSide)
    roof_b: RoofSide = field(default_factory=RoofSide)
    wall_a: Wall = field(default_factory=Wall)
    wall_b: Wall = field(default_factory=Wall)
    gable: Wall = field(default_factory=Wall)
    sections: Sections = field(default_factory=Sections)
    end_first: str = "frame"            # "frame" or "rafter"
    end_last: str = "frame"
    braced_bays: tuple[int, ...] | None = None   # 1-based; None = the first and the last bay
    brace_type: str = "rod"
    bolt: str = "M12"
    fixed_lap: float | None = None
    openings: tuple[dict, ...] = ()

    def check(self) -> None:
        if not (6000 <= self.span <= 90000):
            raise ValueError("span must be 6000 to 90000 mm")
        if not (3000 <= self.eave_height <= 20000):
            raise ValueError("eave height must be 3000 to 20000 mm")
        if not (0.02 <= self.roof_slope <= 0.5):
            raise ValueError("roof slope must be 0.02 to 0.5 (rise/run) for a purlin roof")
        if not (3000 <= self.bay_spacing <= 12000):
            raise ValueError("bay spacing must be 3000 to 12000 mm")
        if not (1 <= self.n_bays <= 40):
            raise ValueError("number of bays must be 1 to 40")


def _r(v: float) -> float:
    return round(v + 0.0, 3)


def peb_building(b: BuildingInput) -> dict:
    b.check()
    z = b.sizes or default_sizes(b.span)
    frames = [i * b.bay_spacing for i in range(b.n_bays + 1)]
    L = frames[-1]
    braced = [i - 1 for i in (b.braced_bays if b.braced_bays is not None else sorted({1, b.n_bays}))]
    members: list[dict] = []

    # main frames (an end line with an end rafter has none)
    for i, x in enumerate(frames):
        if (i == 0 and b.end_first == "rafter") or (i == b.n_bays and b.end_last == "rafter"):
            continue
        for m in builtup_frame_members(b.span, b.eave_height, b.roof_slope, x, str(i + 1), z):
            members.append({**m, "type": ROLE_TYPE[m["role"]]})

    # purlins, girts, eave struts with all their holes; sag rods; bracing; flange braces
    lines = secondary_lines(SecondaryInput(span=b.span, eave_height=b.eave_height, roof_slope=b.roof_slope, length=L,
                                           roof_a=b.roof_a, roof_b=b.roof_b, wall_a=b.wall_a, wall_b=b.wall_b, sections=b.sections))
    bi = BracingInput(span=b.span, eave_height=b.eave_height, roof_slope=b.roof_slope, frames=frames, sizes=z,
                      braced_bays=braced, brace_type=b.brace_type)
    rods = sag_rods(lines, bi)
    overhang = z.bf / 2 + cf_dims(b.sections.girt)["H"]     # to the end-wall girt line
    sec = secondary_members(lines, frames, end_overhang=overhang, bolt=b.bolt, fixed_lap=b.fixed_lap, extra_holes=rods["holes"])
    girts = [m for m in sec["members"] if m["role"] == "girt"]
    others = [m for m in sec["members"] if m["role"] != "girt"]
    rafter_ends = {x for i, x in ((0, frames[0]), (b.n_bays, L)) if (b.end_first if i == 0 else b.end_last) == "rafter"}
    fb = [m for m in flange_braces(lines, bi) if not (m["host"].startswith("column") and m["start"][0] in rafter_ends)]

    # end walls
    for end, kind, x in (("first", b.end_first, frames[0]), ("last", b.end_last, L)):
        w = end_wall(kind, end, b.span, b.eave_height, b.roof_slope, x, z, wall=b.gable, girt=b.sections.girt, bolt=b.bolt)
        members += [{**m, "type": ROLE_TYPE[m["role"]]} for m in w["members"]]
        girts += w["girts"]

    op = apply_openings(girts, list(b.openings), b.eave_height, jamb=b.sections.eave_strut, bolt=b.bolt)
    for m in others + op["girts"] + op["members"]:
        members.append({**m, "type": ROLE_TYPE.get(m["role"], "beam")})
    for m in rods["members"] + x_bracing(lines, lines["walls"], bi) + fb:
        members.append({**m, "type": "brace", "position": "middle", "rotation": 0.0})
    for k, m in enumerate(members):
        m.setdefault("id", f"P{k + 1}")
        m["gen"] = "peb"
        m.setdefault("material", "S350GD" if "profile" in m and m["profile"][:1] in "CZ" and "section" not in m else z.grade)

    labels = list(string.ascii_uppercase)
    return {
        "units": {"length": "mm"}, "section": "builtup", "designed": False,
        "input": {"span": b.span, "eave_height": b.eave_height, "roof_slope": b.roof_slope, "bay_spacing": b.bay_spacing, "n_bays": b.n_bays},
        "grids": {"x": [{"label": str(i + 1), "at": _r(x)} for i, x in enumerate(frames)], "y": [{"label": labels[0], "at": 0.0}, {"label": labels[1], "at": _r(b.span)}]},
        "levels": [{"name": "Ground", "z": 0.0}, {"name": "Eave", "z": _r(b.eave_height)}],
        "members": members, "cleats": sec["cleats"], "fasteners": rods["fasteners"], "bolt": b.bolt,
        "braced_bays": [j + 1 for j in braced], "apex_height": _r(b.eave_height + b.roof_slope * b.span / 2),
        "notes": ["Geometry only: NOT designed (Phase 4). Splices, knee, ridge and brace connections are points only (Phase 5).",
                  "Cold-formed design properties come from the supplier's catalogue (needed before Phase 4)."],
    }
