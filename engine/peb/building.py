# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 2 step 7: the whole PEB building in one call — main frames (Phase 1), secondary steel (steps 2–4), end walls
(step 5), openings (step 6) and cleats. Geometry only, NOT designed (Phase 4).

Every member carries `gen: "peb"` so the app can replace the generated members when the building is edited, and either
`section` (a built-up member, engine/peb/builtup_frame.py format) or `profile` (+ `holes`).
"""

from __future__ import annotations

import dataclasses
import math
import string
from dataclasses import dataclass, field

from .bracing import BracingInput, flange_braces, sag_rods, x_bracing
from .builtup_frame import BuiltUpSizes, builtup_frame_members, default_sizes
from .endwall import check_section, end_wall, endwall_braces, wind_column_braces
from .openings import apply_openings
from .secondary import HOLE, RoofSide, SecondaryInput, Sections, Wall, cf_dims, gauge, secondary_lines, secondary_members

SPAN_REFS = ("outside", "centreline", "grid")
ROLE_TYPE = {"column": "column", "rafter": "beam", "wind_column": "column", "end_rafter": "beam", "jamb": "column", "cap_plate": "plate"}


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
    end_braced_bays: tuple[int, ...] | None = None   # end-wall bays (1-based from line A); None = (1,) on an end-rafter wall, none on a main-frame wall
    brace_type: str = "rod"
    ridge_tie: str = "rod"              # "rod" or "strap" across the apex
    bolt: str = "M12"
    fixed_lap: float | None = None
    openings: tuple[dict, ...] = ()
    bays: tuple[float, ...] | None = None   # field fix 6: uneven bays, frame line to frame line; None = n_bays x bay_spacing
    span_ref: str = "outside"               # field fix 7: what `span` measures — outside (of steel: the columns' outer
                                            # faces), centreline (of the columns at the base) or grid (grid_inset outside steel)
    grid_inset: float = 0.0                 # span_ref "grid": from a grid line in to the columns' outer face, mm
    wc_braces_first: int = 2                # wind-column flange braces at every n-th gable girt (from the top), end wall at
    wc_braces_last: int = 2                 # the first / last frame line; 0 = none (user, 2026-11-09)
    wind_column: dict | None = None         # Phase 4 step 9: the wind columns' section {hw, tw, bf, tf}; None = the placeholder
    end_rafter: dict | None = None          # the end rafters' section {hw, tw, bf, tf}; None = the main rafter's

    def bay_list(self) -> tuple[float, ...]:
        return tuple(float(v) for v in self.bays) if self.bays else (float(self.bay_spacing),) * int(self.n_bays)

    def frame_xs(self) -> list[float]:
        xs = [0.0]
        for v in self.bay_list():
            xs.append(xs[-1] + v)
        return xs

    def check(self) -> None:
        if not (6000 <= self.span <= 90000):
            raise ValueError("span must be 6000 to 90000 mm")
        if not (3000 <= self.eave_height <= 20000):
            raise ValueError("eave height must be 3000 to 20000 mm")
        if not (0.02 <= self.roof_slope <= 0.5):
            raise ValueError("roof slope must be 0.02 to 0.5 (rise/run) for a purlin roof")
        bays = self.bay_list()
        if not (1 <= len(bays) <= 40):
            raise ValueError("number of bays must be 1 to 40")
        for k, v in enumerate(bays):
            if not (3000 <= v <= 12000):
                raise ValueError(f"bay {k + 1}: spacing {v:g} mm - must be 3000 to 12000 mm")
        if self.span_ref not in SPAN_REFS:
            raise ValueError(f"span reference must be one of {', '.join(SPAN_REFS)}")
        for k in ("wc_braces_first", "wc_braces_last"):
            if not (isinstance(getattr(self, k), int) and 0 <= getattr(self, k) <= 10):
                raise ValueError("wind-column flange braces: every n-th girt, n a whole number 0 (none) to 10")
        check_section("wind column section", self.wind_column)
        check_section("end rafter section", self.end_rafter)


def resolve(b: BuildingInput) -> tuple[BuildingInput, float]:
    """The steel geometry of a building input (field fixes 6, 7) and the shift y0 that puts it on its reference lines.

    The generator and the analysis work on the STEEL span (the columns' outer faces at y = 0 and y = span) and an explicit
    list of bays. `span` as typed may be measured to the column centrelines (at the base: outer face + d_base / 2,
    d_base = hw_base + 2 tf) or to grid lines grid_inset outside the outer faces:
        outside      steel span = span                     y0 = 0
        centreline   steel span = span + d_base            y0 = -d_base / 2  (centrelines land on y = 0 and y = span)
        grid         steel span = span - 2 grid_inset      y0 = +grid_inset  (grid lines on y = 0 and y = span)
    The sizes are fixed from the TYPED span (default_sizes(span)) so the steel span cannot change them. Idempotent."""
    if b.span_ref not in SPAN_REFS:
        raise ValueError(f"span reference must be one of {', '.join(SPAN_REFS)}")
    z = b.sizes or default_sizes(b.span)
    if b.span_ref == "centreline":
        d = z.hw_base + 2 * z.tf
        span, y0 = b.span + d, -d / 2
    elif b.span_ref == "grid":
        if not (0 <= b.grid_inset <= 2000):
            raise ValueError("grid inset (grid line to the columns' outer face) must be 0 to 2000 mm")
        span, y0 = b.span - 2 * b.grid_inset, b.grid_inset
    else:
        span, y0 = b.span, 0.0
    bays = b.bay_list()
    r = dataclasses.replace(b, span=span, sizes=z, span_ref="outside", grid_inset=0.0, bays=bays, bay_spacing=bays[0], n_bays=len(bays))
    return r, y0


def _r(v: float) -> float:
    return round(v + 0.0, 3)


def peb_building(b: BuildingInput) -> dict:
    b.check()
    typed = b
    b, y0 = resolve(b)
    b.check()
    z = b.sizes
    frames = b.frame_xs()
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
                      braced_bays=braced, brace_type=b.brace_type, ridge_tie=b.ridge_tie)
    rods = sag_rods(lines, bi)
    overhang = z.bf / 2 + cf_dims(b.sections.girt)["H"]     # to the end-wall girt line
    sec = secondary_members(lines, frames, end_overhang=overhang, bolt=b.bolt, fixed_lap=b.fixed_lap, extra_holes=rods["holes"])
    girts = [m for m in sec["members"] if m["role"] == "girt"]
    others = [m for m in sec["members"] if m["role"] != "girt"]
    rafter_ends = {x for i, x in ((0, frames[0]), (b.n_bays, L)) if (b.end_first if i == 0 else b.end_last) == "rafter"}
    fb = [m for m in flange_braces(lines, bi) if m["start"][0] not in rafter_ends]   # an end-rafter wall has no main frame

    # end walls
    gable_sets = []
    end_walls = []
    for end, kind, x in (("first", b.end_first, frames[0]), ("last", b.end_last, L)):
        w = end_wall(kind, end, b.span, b.eave_height, b.roof_slope, x, z, wall=b.gable, girt=b.sections.girt, bolt=b.bolt,
                     wc=b.wind_column, er=b.end_rafter)
        members += [{**m, "type": ROLE_TYPE[m["role"]]} for m in w["members"]]
        girts += w["girts"]
        gable_sets.append((end, w["supports"]))
        eb = b.end_braced_bays if b.end_braced_bays is not None else ((1,) if kind == "rafter" else ())
        tops = {round(m["start"][1], 3): m["end"][2] for m in w["members"] if m["role"] == "wind_column"}
        prof = "RD20" if b.brace_type == "rod" else "L75x6"
        for m in endwall_braces(end, w["x_face"], b.span, b.eave_height, w["supports"], tops, tuple(eb), prof, wc=b.wind_column):
            members.append({**m, "type": "brace", "position": "middle", "rotation": 0.0})
        end_walls.append({"end": end, "kind": kind, "x_frame": _r(x), "x_face": w["x_face"], "supports": w["supports"]})

    op = apply_openings(girts, list(b.openings), b.eave_height, jamb=b.sections.eave_strut, bolt=b.bolt)
    # wind-column flange braces from the gable girts (after the openings: only where a girt piece runs)
    for ew in end_walls:
        tag = "W" + ew["end"][0].upper()
        cols = [m for m in members if m["role"] == "wind_column" and m["id"].startswith(tag)]
        gg = [g for g in op["girts"] if g.get("role") == "gable_girt" and g["id"].startswith("G" + ew["end"][0].upper())]
        every = b.wc_braces_first if ew["end"] == "first" else b.wc_braces_last
        for m in wind_column_braces(ew["end"], ew["x_face"], cols, gg, every, wc=b.wind_column):
            members.append({**m, "type": "brace", "position": "middle", "rotation": 0.0})
    cleats = sec["cleats"] + [c for end, sup in gable_sets for c in gable_cleats(op["girts"], end, sup, b.bolt)]
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
        "input": {"span": b.span, "eave_height": b.eave_height, "roof_slope": b.roof_slope, "bay_spacing": b.bay_spacing, "n_bays": b.n_bays,
                  "bays": list(b.bay_list()), "span_typed": typed.span, "span_ref": typed.span_ref, "grid_inset": typed.grid_inset,
                  "wc_braces_first": b.wc_braces_first, "wc_braces_last": b.wc_braces_last,
                  "wind_column": b.wind_column, "end_rafter": b.end_rafter},
        # the members are in STEEL coordinates (column A's outer face on y = 0); y_shift moves them onto the reference
        # lines, where the grids are — the app applies it together with the placement (field fixes 5, 7)
        "y_shift": _r(y0),
        "grids": {"x": [{"label": str(i + 1), "at": _r(x)} for i, x in enumerate(frames)], "y": [{"label": labels[0], "at": 0.0}, {"label": labels[1], "at": _r(typed.span)}]},
        "levels": [{"name": "Ground", "z": 0.0}, {"name": "Eave", "z": _r(b.eave_height)}],
        "members": members, "cleats": cleats, "fasteners": rods["fasteners"], "bolt": b.bolt,
        "braced_bays": [j + 1 for j in braced], "end_walls": end_walls, "apex_height": _r(b.eave_height + b.roof_slope * b.span / 2),
        "notes": ["Geometry only: NOT designed (Phase 4). Splices, knee, ridge and brace connections are points only (Phase 5).",
                  "Cold-formed design properties come from the supplier's catalogue (needed before Phase 4)."],
    }


def gable_cleats(girts: list[dict], end: str, supports: list[float], bolt: str) -> list[dict]:
    """Cleats for the gable girts on the wind columns (user, 2026-11-05), after openings: one per girt row per support that a
    girt piece of that row actually spans. Same rule as the side-girt cleats (secondary.py): PL8 x (depth - 20) x 100 beside
    the web on the girt's +u side, 2 holes at gauge depth - 2(lip + 25), centred on the web."""
    tag = "G" + end[0].upper()
    rows: dict[float, list[dict]] = {}
    for g in girts:
        if g.get("role") == "gable_girt" and g["id"].startswith(tag):
            rows.setdefault(g["z"], []).append(g)
    out = []
    for zr, ps in sorted(rows.items()):
        d = cf_dims(ps[0]["profile"])
        g, h = gauge(ps[0]["profile"]), d["H"] - 20.0
        a = math.radians(ps[0]["rotation"])
        u = (-math.cos(a), 0.0, math.sin(a))       # a gable girt runs +Y: geom.js frame() u0 = (-1, 0, 0), v0 = Z
        v = (math.sin(a), 0.0, math.cos(a))
        off = d["t"] / 2 + 4.0
        x0 = ps[0]["start"][0]
        for y in supports:
            if not any(min(p["start"][1], p["end"][1]) < y < max(p["start"][1], p["end"][1]) for p in ps):
                continue
            st = [x0 + off * u[0], y, zr + off * u[2]]
            out.append({"start": [round(c, 3) for c in st], "end": [round(st[0] + h * v[0], 3), round(y, 3), round(st[2] + h * v[2], 3)],
                        "width_dir": [0.0, 1.0, 0.0], "line": f"{tag}{zr:g}", "frame": None, "x": round(y, 3), "base": [x0, round(y, 3), zr],
                        "rotation": ps[0]["rotation"], "profile": "PL8x100", "height": h, "side": "up",
                        "holes": [{"along": 0.0, "up": round(d["H"] / 2 + sy * g / 2, 3), "d": HOLE[bolt]} for sy in (-1, 1)],
                        "host": "wind column " + end})
    return out