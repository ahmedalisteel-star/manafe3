# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""The model's own secondary steel as a dead load per m² (feeds case D of the frames: engine/analysis/frame_loads.py).

Weighed from the generated members (not typed): steel 7850 kg/m³ → 76.982 kN/m³.
    lipped C / Z   centre-line area t·(H + 2B + 2D − 4t), square corners (the corner radii are ignored: within ~1 %)
    rod RDd        π d² / 4;  angle LbxT  (2b − t)·t;  plate PLtxw  t·w (a cleat: × its height)
    roof           purlins, ridge purlins, eave struts, sag rods, ridge ties, roof braces, flange braces and cleats on
                   the rafters — per m² of SLOPING roof (both slopes × the building length between the end frame lines)
    walls          girts, wall braces, flange braces and cleats on the columns — per m² of side wall (2 × length × eave)
    not counted    the end walls (gable girts, wind columns, cap plates: their own load path, step 7) and opening framing
"""

from __future__ import annotations

import math
import re

from .frame_loads import STEEL_KN_M3
from ..peb.secondary import cf_dims

ROOF = {"purlin", "ridge_purlin", "eave_strut", "sag_rod", "ridge_tie", "roof_brace"}
WALL = {"girt", "wall_brace"}


def area_mm2(profile: str) -> float:
    p = profile.strip()
    if p[:1] in "CZ":
        d = cf_dims(p)
        return d["t"] * (d["H"] + 2 * d["B"] + 2 * d["D"] - 4 * d["t"])
    if m := re.fullmatch(r"RD(\d+(?:\.\d+)?)", p):
        return math.pi * float(m[1]) ** 2 / 4
    if m := re.fullmatch(r"L(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", p):
        b, t = float(m[1]), float(m[2])
        return (2 * b - t) * t
    if m := re.fullmatch(r"PL(\d+(?:\.\d+)?)x(\d+(?:\.\d+)?)", p):
        return float(m[1]) * float(m[2])
    raise ValueError(f"no area rule for profile {profile}")


def _length(m: dict) -> float:
    return m["length"] if "length" in m else math.dist(m["start"], m["end"])


def secondary_kpa(out: dict) -> dict:
    inp = out["input"]
    span, eave, slope = inp["span"], inp["eave_height"], inp["roof_slope"]
    L = inp["bay_spacing"] * inp["n_bays"]
    roof_area = 2 * (span / 2) * math.sqrt(1 + slope * slope) * L * 1e-6       # m², sloping
    wall_area = 2 * L * eave * 1e-6
    kn = {"roof": 0.0, "wall": 0.0}
    by_role: dict[str, float] = {}
    for m in out["members"]:
        r = m["role"]
        if r in ROOF:
            k = "roof"
        elif r in WALL:
            k = "wall"
        elif r == "flange_brace":
            k = "roof" if m.get("host", "").startswith("rafter") else "wall"
        else:
            continue
        w = area_mm2(m["profile"]) * _length(m) * 1e-9 * STEEL_KN_M3
        kn[k] += w
        by_role[r] = by_role.get(r, 0.0) + w
    for c in out.get("cleats", []):
        host = c.get("host", "")
        if not (host.startswith("rafter") or host.startswith("column")):
            continue
        w = area_mm2(c["profile"]) * c["height"] * 1e-9 * STEEL_KN_M3
        kn["roof" if host.startswith("rafter") else "wall"] += w
        by_role["cleat"] = by_role.get("cleat", 0.0) + w
    return {"roof_kpa": round(kn["roof"] / roof_area, 5), "wall_kpa": round(kn["wall"] / wall_area, 5),
            "roof_kN": round(kn["roof"], 3), "wall_kN": round(kn["wall"], 3), "roof_m2": round(roof_area, 3), "wall_m2": round(wall_area, 3),
            "by_role_kN": {k: round(v, 3) for k, v in sorted(by_role.items())}}
