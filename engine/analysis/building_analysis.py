# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 8 (engine side): the whole building's analysis, on demand (results are not stored in the model).

    frame lines   every main frame line (step 4) with the model's secondary steel weighed into case D
                  (secondary_weight.py); identical lines (same members, same loads — e.g. frames 2 and 4 of a symmetric
                  building) are solved ONCE and the others point to it ("same_as"); the distinct lines are solved in
                  parallel processes
    end walls     an end-rafter end wall: its frame (step 7); every end wall: the wind columns out of plane (step 7)
    longitudinal  the tension-only bracing system (step 6)
Taper slicing: max_taper_step 0.10 — CONVERGED: within 0.2 % of 0.025 on building 1 (apex, sway, moments, thrust;
engine/tests/test_building_analysis.py keeps that check), at ~2.5 × less time than 0.05.
Every output carries NOT FOR ISSUE: nothing here is a verified design (Phase 4 designs; this is analysis only).
"""

from __future__ import annotations

import os
from concurrent.futures import ProcessPoolExecutor

from ..peb.building import BuildingInput, peb_building
from ..peb.builtup_frame import builtup_frame_members, default_sizes
from ..peb.loads_input import LoadsInput
from ..design.inputs import section_strength
from .bracing_system import longitudinal_bracing
from .endwall_analysis import _geom, end_rafter_frame, longitudinal_feed, wind_columns
from .frame_loads import frame_loads
from .frame_model import frame_line_model
from .secondary_weight import secondary_kpa
from .solve import analyse_frame_line
from .staad import staad_frame

TAPER_STEP = 0.10
BANNER = "NOT FOR ISSUE — analysis only, members not designed (Phase 4)"


def _line_setup(b: BuildingInput, li: LoadsInput, i: int, sec: dict, step: float, with_fy: bool = False):
    sizes = b.sizes or default_sizes(b.span)
    ms = builtup_frame_members(b.span, b.eave_height, b.roof_slope, i * b.bay_spacing, str(i + 1), sizes)
    info = frame_line_model(ms, b.span, b.eave_height, b.roof_slope, (b.bay_spacing,) * b.n_bays, base=li.base, max_taper_step=step)
    fl = frame_loads(info, i, li, roof_secondary_kpa=sec["roof_kpa"], wall_secondary_kpa=sec["wall_kpa"])
    return (info, fl, fy_by_mark(ms)) if with_fy else (info, fl)


def fy_by_mark(ms: list[dict]) -> dict:
    """{analysis member mark: Fy MPa, the lowest of its plates} — column CA / CB, rafter segments RA1, RA2, … """
    out = {}
    for m in ms:
        segs = m["section"]["segments"]
        if m["role"] == "column":
            out["C" + m["side"]] = section_strength(segs[0])["Fy"]
        else:
            for k, s in enumerate(segs):
                out[f"R{m['side']}{k + 1}"] = section_strength(s)["Fy"]
    return out


def _solve_line(args):
    b, li, i, sec, step, p_delta = args
    info, fl, fy = _line_setup(b, li, i, sec, step, with_fy=True)
    r = analyse_frame_line(info, fl, p_delta=p_delta, label=f"Frame line {i + 1}", fy=fy)
    r["staad"] = staad_frame(info, fl, title=f"Manafe3 frame line {i + 1} (NOT FOR ISSUE)", base=li.base)   # for STAAD.Pro
    return r


def _signature(fl) -> tuple:
    return tuple((ld.case, ld.member_mark, round(ld.w, 9), ld.direction.name, None if ld.w_end is None else round(ld.w_end, 9)) for ld in fl.loads)


def analyse_building(b: BuildingInput, li: LoadsInput, *, p_delta: bool = True, step: float = TAPER_STEP, workers: int | None = None) -> dict:
    li.check()
    out = peb_building(b)
    sec = secondary_kpa(out)
    kinds = {0: b.end_first, b.n_bays: b.end_last}
    lines = [i for i in range(b.n_bays + 1) if kinds.get(i, "frame") == "frame"]
    first_of: dict[tuple, int] = {}
    same_as: dict[int, int] = {}
    for i in lines:
        _, fl = _line_setup(b, li, i, sec, step)
        same_as[i] = first_of.setdefault(_signature(fl), i)
    unique = sorted(set(same_as.values()))
    jobs = [(b, li, i, sec, step, p_delta) for i in unique]
    n = workers if workers is not None else min(len(jobs), max(1, (os.cpu_count() or 2) - 1))
    if n > 1:
        with ProcessPoolExecutor(max_workers=n) as ex:
            solved = dict(zip(unique, ex.map(_solve_line, jobs)))
    else:
        solved = {i: _solve_line(j) for i, j in zip(unique, jobs)}
    frames = []
    for i in lines:
        f = {"line": str(i + 1), "x": i * b.bay_spacing, "kind": "frame", "same_as": str(same_as[i] + 1)}
        if same_as[i] == i:
            f["result"] = solved[i]
        frames.append(f)
    end_frames = [end_rafter_frame(out, end, li, roof_secondary_kpa=sec["roof_kpa"], wall_secondary_kpa=sec["wall_kpa"])
                  for end, kind in (("first", b.end_first), ("last", b.end_last)) if kind == "rafter"]
    braces = [m for m in out["members"] if m["role"] in ("roof_brace", "wall_brace")]
    return {
        "banner": BANNER, "designed": False, "p_delta": p_delta, "taper_step": step,
        "loads": li.summary(), "secondary": sec,
        "frames": frames, "end_frames": end_frames,
        "wind_columns": wind_columns(out, li),
        "bracing": longitudinal_bracing(_geom(out["input"]), braces, [j - 1 for j in out["braced_bays"]], longitudinal_feed(out, li)),
        "sets": {"strength": "LRFD", "serviceability": "ASD", "foundation": "case (unfactored)"},
        "input": {**out["input"], "end_first": b.end_first, "end_last": b.end_last, "base": li.base},
    }
