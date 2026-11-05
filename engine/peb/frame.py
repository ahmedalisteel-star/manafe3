# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 0 portal frame: geometry only, NOT a design.

A symmetric gable portal frame repeated on every frame line: two columns and two rafters per frame.

Axes (the Manafe3 / DetailCraft model axes, mm, Z up):
    X  along the building — frame lines 1, 2, … n+1 at x = i · bay_spacing (DetailCraft's numbered grids)
    Y  across the span    — column lines A at y = 0 and B at y = span (DetailCraft's lettered grids)
    Z  up                 — columns from z = 0 to the eave; the apex at z = eave + roof_slope · span / 2

BIMSteelAuto's engine uses X across the frame and Y along the building. When later phases hand this frame to it,
the swap happens in exactly one place (a function next to this one), never scattered through the code.

The profiles are hot-rolled placeholders picked from the span so the 3D view looks plausible. They are NOT designed
and carry `designed: False`; real member sizes come from Phase 3-4 (analysis and design).
"""

from __future__ import annotations

import math
import string
from dataclasses import dataclass

#: Placeholder sizes by span (mm): (max span, column profile, rafter profile). Names as DetailCraft's table has them.
PLACEHOLDER_SIZES = [
    (15000.0, "HEA300", "IPE400"),
    (24000.0, "HEA400", "IPE500"),
    (math.inf, "HEA500", "IPE600"),
]
MATERIAL = "S355"
MAX_FRAME_LINES = 60   # DetailCraft keeps at most 60 grid lines per direction


@dataclass(frozen=True)
class FrameInput:
    span: float            # mm, column line A to column line B (centre lines)
    eave_height: float     # mm, ground to the top of the column work line
    roof_slope: float      # rise / run, e.g. 0.1 for 1:10
    bay_spacing: float     # mm, frame line to frame line
    n_bays: int            # number of bays; frames = n_bays + 1

    def check(self) -> None:
        if not (3000 <= self.span <= 120000):
            raise ValueError("span must be 3000 to 120000 mm")
        if not (2000 <= self.eave_height <= 40000):
            raise ValueError("eave height must be 2000 to 40000 mm")
        if not (0 <= self.roof_slope <= 1):
            raise ValueError("roof slope is rise/run and must be 0 to 1 (0.1 = 1:10)")
        if not (1000 <= self.bay_spacing <= 20000):
            raise ValueError("bay spacing must be 1000 to 20000 mm")
        if not (1 <= self.n_bays <= MAX_FRAME_LINES - 1):
            raise ValueError(f"number of bays must be 1 to {MAX_FRAME_LINES - 1}")


def _r(v: float) -> float:
    """Round to 0.001 mm so the JSON is stable."""
    return round(v + 0.0, 3)


def placeholder_profiles(span: float) -> tuple[str, str]:
    for limit, col, raf in PLACEHOLDER_SIZES:
        if span <= limit:
            return col, raf
    raise AssertionError("unreachable")


def column_line_labels(n: int) -> list[str]:
    return list(string.ascii_uppercase[:n])


def portal_frame(inp: FrameInput) -> dict:
    """The frame as plain data: grids, levels and members (start/end points, profile, role)."""
    inp.check()
    span, eave, slope, bay, nb = inp.span, inp.eave_height, inp.roof_slope, inp.bay_spacing, inp.n_bays
    apex_z = eave + slope * span / 2.0
    col_prof, raf_prof = placeholder_profiles(span)
    a, b = column_line_labels(2)

    members: list[dict] = []
    for i in range(nb + 1):
        x = i * bay
        line = str(i + 1)
        base_a, base_b = (x, 0.0, 0.0), (x, span, 0.0)
        eave_a, eave_b = (x, 0.0, eave), (x, span, eave)
        apex = (x, span / 2.0, apex_z)
        for role, side, start, end, prof in (
            ("column", a, base_a, eave_a, col_prof),
            ("column", b, base_b, eave_b, col_prof),
            ("rafter", a, eave_a, apex, raf_prof),
            ("rafter", b, eave_b, apex, raf_prof),
        ):
            members.append({
                "id": f"F{line}-{'C' if role == 'column' else 'R'}{side}",
                "role": role,
                "frame_line": line,
                "side": side,
                "profile": prof,
                "material": MATERIAL,
                "start": [_r(c) for c in start],
                "end": [_r(c) for c in end],
                "designed": False,
            })

    return {
        "units": {"length": "mm"},
        "axes": "X along the building (frame lines), Y across the span (column lines), Z up",
        "input": {"span": span, "eave_height": eave, "roof_slope": slope, "bay_spacing": bay, "n_bays": nb},
        "apex_height": _r(apex_z),
        "rafter_length": _r(math.hypot(span / 2.0, apex_z - eave)),
        "grids": {
            "x": [{"label": str(i + 1), "at": _r(i * bay)} for i in range(nb + 1)],
            "y": [{"label": a, "at": 0.0}, {"label": b, "at": _r(span)}],
        },
        "levels": [{"name": "Ground", "z": 0.0}, {"name": "Eave", "z": _r(eave)}],
        "members": members,
        "notes": ["Placeholder hot-rolled profiles: NOT designed. Geometry only (Phase 0)."],
    }
