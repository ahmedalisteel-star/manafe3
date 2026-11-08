# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 3: the loads on one frame line, and the combinations — bimsteelauto's verified load modules, unchanged.

Cases (all kN/m on the frame's members):
    D      frame self-weight (plates: A × 76.98 kN/m³, varying along a taper) + roof sheeting and the model's roof
           secondary steel (purlins, eave struts, rods, bracing, cleats) per m² of SLOPING roof on the rafters + wall
           sheeting and girts per m² of wall hung on the columns (bimsteelauto's surface discipline)
    C      collateral, per m² of PLAN (user decision) — its own case
    Lr     Lo · R1 · R2 from the frame's tributary area (bimsteelauto roof_live_load; never typed), per m² of plan
    wind   bimsteelauto Ch. 28 envelope: Load Case A from the left and from the right, Load Case B, each with + and − GCpi
           (6 cases), end-zone coefficients where the frame line is in the end zone, the §28.3.4 minimum — computed by
           wind_loads_for_frame on bimsteelauto's own 4-member layout (C1 R1 R2 C2) and copied onto every Manafe3
           sub-member of the same surface (column A ← C1, rafter A segments ← R1, rafter B ← R2, column B ← C2)
Combinations: pluggable sets (COMBINATION_SETS — the ECP 201 hook); by default bimsteelauto's ASCE 7-16 LRFD and ASD over the 6 wind cases, with C at D's factor in every one EXCEPT
the uplift combinations (LRFD 0.9D + 1.0W, ASD 0.6D + 0.6W) — user decision; names prefixed "LRFD: " / "ASD: ".
Rigid links carry no load.
"""

from __future__ import annotations

from dataclasses import dataclass

from bimsteelauto.analysis import LoadDirection
from bimsteelauto.analysis.frame import FrameSections, MemberSectionSpec, build_layout
from bimsteelauto.loads.combinations import asd_combinations, lrfd_combinations
from bimsteelauto.loads.frame import tributary_width
from bimsteelauto.loads.gravity import frame_tributary_area, roof_live_load
from bimsteelauto.loads.wind import envelope_pressures, wind_loads_for_frame

from ..peb.loads_input import LoadsInput

STEEL_KN_M3 = 7850.0 * 9.80665 / 1000.0          # 76.982 kN/m³
WIND_NAMES = {("W_A_pi_pos", True): "WA+L", ("W_A_pi_neg", True): "WA-L", ("W_A_pi_pos", False): "WA+R",
              ("W_A_pi_neg", False): "WA-R", ("W_B_pi_pos", True): "WB+", ("W_B_pi_neg", True): "WB-"}
SURFACE_OF = {"C1": "column A", "R1": "rafter A", "R2": "rafter B", "C2": "column B"}


@dataclass(frozen=True)
class Load:
    """One line load on one member (bimsteelauto's FrameLoad + an end value for a varying load, e.g. a taper's weight)."""
    case: str
    member_mark: str
    w: float                      # kN/m at the member's start
    direction: LoadDirection
    origin: str = ""
    w_end: float | None = None    # kN/m at its end; None = uniform


@dataclass(frozen=True)
class FrameLoads:
    loads: tuple["Load", ...]
    cases: tuple[str, ...]
    combinations: tuple[tuple[str, dict, str], ...]      # (name, factors, "LRFD" | "ASD")
    tributary_m: float
    Lr: object
    wind: object


@dataclass(frozen=True)
class CombinationSet:
    """One pluggable set of load combinations — the ECP 201 hook. ``build(wind_cases)`` gives (name, factors) pairs over
    the cases D, Lr and the wind cases; collateral C is added at D's factor except in the set's uplift combinations
    (D at ``uplift_d`` with wind and without Lr — user decision)."""
    key: str                      # the label every result carries ("LRFD", "ASD", "ECP201-…")
    reference: str
    build: object
    uplift_d: float
    role: str                     # "strength" | "serviceability"


def _from_bsa(fn):
    return lambda wind_cases: [(c.name, dict(c.factors)) for c in fn(wind_cases=wind_cases)]


def _ecp201_not_entered(wind_cases):
    raise NotImplementedError("ECP 201 load combinations: not entered yet. They will come from the user's ecp205-lrfd "
                              "library, with clause references (user decision 2026-11-08); Manafe3 never invents them.")


#: The registry. LRFD / ASD: bimsteelauto's ASCE 7-16 §2.3 / §2.4 sets (VERIFIED there). ECP201: the slot for the Egyptian
#: code (ECP 201) — registered, refusing until its factors are supplied.
COMBINATION_SETS: dict[str, CombinationSet] = {
    "LRFD": CombinationSet("LRFD", "ASCE 7-16 §2.3.1 (bimsteelauto lrfd_combinations)", _from_bsa(lrfd_combinations), 0.9, "strength"),
    "ASD": CombinationSet("ASD", "ASCE 7-16 §2.4.1 (bimsteelauto asd_combinations)", _from_bsa(asd_combinations), 0.6, "serviceability"),
    "ECP201": CombinationSet("ECP201", "ECP 201 (later: from the user's ecp205-lrfd library, with clauses)", _ecp201_not_entered, 0.0, "strength"),
}


def register_combination_set(cs: CombinationSet) -> None:
    COMBINATION_SETS[cs.key] = cs


def combinations(li: LoadsInput, wind_cases: tuple[str, ...], extra: tuple[str, ...] = ()) -> tuple[tuple[str, dict, str], ...]:
    keys = [k for k, on in (("LRFD", li.lrfd), ("ASD", li.asd)) if on] + [k for k in extra if k not in ("LRFD", "ASD")]
    out = []
    for key in keys:
        cs = COMBINATION_SETS[key]
        label, uplift_d = cs.key, cs.uplift_d
        for name, factors in cs.build(wind_cases):
            f = dict(factors)
            uplift = f.get("D") == uplift_d and any(k in wind_cases for k in f) and "Lr" not in f
            if "D" in f and not uplift:
                f["C"] = f["D"]
            out.append((f"{label}: {name}" + ("" if uplift or "D" not in f else " (+C)"), f, label))
    return tuple(out)


def frame_loads(info, frame_index: int, li: LoadsInput, roof_secondary_kpa: float = 0.0, wall_secondary_kpa: float = 0.0) -> FrameLoads:
    lay = info.layout
    geom = lay.geometry
    trib = tributary_width(geom, frame_index)                     # m
    loads: list[Load] = []
    by_role: dict[str, list[str]] = {}
    for f in lay.members:
        role = info.roles[f.mark]
        if role == "link":
            continue
        by_role.setdefault(role, []).append(f.mark)
        a0, a1 = f.taper.start.A, f.taper.end.A
        loads.append(Load("D", f.mark, a0 * 1e-6 * STEEL_KN_M3, LoadDirection.GLOBAL_Y, f"self-weight A {a0:.0f} -> {a1:.0f} mm2 x 76.98 kN/m3",
                          w_end=a1 * 1e-6 * STEEL_KN_M3))
    rafters = by_role.get("rafter A", []) + by_role.get("rafter B", [])
    columns = by_role.get("column A", []) + by_role.get("column B", [])
    roof_d = li.roof_sheeting + roof_secondary_kpa
    wall_d = li.wall_sheeting + wall_secondary_kpa
    lr = roof_live_load(frame_tributary_area(geom, frame_index), geom.roof_slope, Lo=li.Lo)
    for mk in rafters:
        loads.append(Load("D", mk, roof_d * trib, LoadDirection.GLOBAL_Y, f"roof sheeting {li.roof_sheeting} + secondary {roof_secondary_kpa:.4f} kN/m2 (sloping) x {trib:.3f} m"))
        loads.append(Load("C", mk, li.collateral * trib, LoadDirection.GLOBAL_Y_PROJECTED, f"collateral {li.collateral} kN/m2 (plan) x {trib:.3f} m"))
        loads.append(Load("Lr", mk, lr.Lr * trib, LoadDirection.GLOBAL_Y_PROJECTED, f"Lr = {li.Lo} x R1 {lr.R1:.3f} x R2 {lr.R2:.3f} = {lr.Lr:.3f} kN/m2 (plan) x {trib:.3f} m"))
    for mk in columns:
        loads.append(Load("D", mk, wall_d * trib, LoadDirection.GLOBAL_Y, f"wall sheeting {li.wall_sheeting} + girts {wall_secondary_kpa:.4f} kN/m2 x {trib:.3f} m"))
    # wind, through bimsteelauto's own layout (C1 R1 R2 C2)
    wind = envelope_pressures(geom, li.site())
    rep = lay.members[0].taper.start
    std = build_layout(geom, FrameSections(column=MemberSectionSpec.prismatic(rep), rafter=MemberSectionSpec.prismatic(rep)))
    names = []
    for from_left in (True, False):
        for fl in wind_loads_for_frame(std, frame_index, wind, from_left=from_left):
            nm = WIND_NAMES.get((fl.case, from_left))
            if nm is None:                                      # Load Case B: once (it does not depend on the side)
                continue
            if nm not in names:
                names.append(nm)
            for mk in by_role.get(SURFACE_OF[fl.member_mark], []):
                if fl.member_mark.startswith("C"):
                    # A wall pressure is horizontal. bimsteelauto applies it NORMAL to an exactly vertical column (local
                    # axes of a vertical PyNite member); a Manafe3 column on its tapered centroid line is slightly inclined
                    # and PyNite turns its local y the other way — the load flipped (found by the statics test). So: global
                    # X (positive w = toward +X, bimsteelauto's convention for columns), per metre of member, scaled by
                    # height / length so the total stays p × tributary × height.
                    m = next(f for f in lay.members if f.mark == mk)
                    k = abs(m.j_point[1] - m.i_point[1]) / m.length
                    loads.append(Load(nm, mk, fl.w * k, LoadDirection.GLOBAL_X, fl.origin + f" (global X, x {k:.5f} height/length)"))
                else:
                    loads.append(Load(nm, mk, fl.w, fl.direction, fl.origin))
    order = ["WA+L", "WA-L", "WA+R", "WA-R", "WB+", "WB-"]                # a fixed order for tables and the CSV
    names = sorted(names, key=order.index)
    cases = ("D", "C", "Lr", *names)
    return FrameLoads(loads=tuple(loads), cases=cases, combinations=combinations(li, tuple(names)), tributary_m=trib, Lr=lr, wind=wind)

