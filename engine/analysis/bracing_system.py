# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 6: the longitudinal (tension-only X-bracing) system — bimsteelauto's verified chain, on Manafe3's panels.

    pressure   bimsteelauto longitudinal_endwall_pressure: Load Case B zones 5 − 6 (windward − leeward endwall; GCpi
               cancels), with the ASCE 7-16 §28.3.4 minimum over the endwall silhouette
    forces     bimsteelauto solve_longitudinal: endwall force → eave level (eave_share 0.5 — ACCEPTED ASSUMPTION: the
               wind columns span base to rafter, pinned top and bottom, so each end takes half the wall) → eave strut →
               the braced bays equally → roof X (half per slope) and wall X (split between the 2 sidewalls) →
               one tension diagonal per panel, T = V / cos θ
    panels     Manafe3's OWN panels (engine/peb/bracing.py): the roof X runs between purlin nodes near 45°, the wall X
               has one or two panels — the panel depth is taken from the generated brace members (the deepest panel
               governs), not bimsteelauto's default of one X over the whole slope / eave height
    sets       unfactored (W = 1.0), LRFD (1.0 W — ASCE 7-16 2.3.1), ASD (0.6 W — 2.4.1); strength from LRFD
Independent check (tests): a PyNite tension-only truss of the wall panel (pinned members, the compression diagonal drops
out) must give the same diagonal force. Not designed (Phase 4).
"""

from __future__ import annotations

import math

from bimsteelauto.analysis.bracing import BracedBay, BracingPlane, LongitudinalSystem, solve_longitudinal
from bimsteelauto.loads.wind import envelope_pressures, longitudinal_endwall_pressure

EAVE_SHARE = 0.5
FACTORS = {"case": 1.0, "LRFD": 1.0, "ASD": 0.6}


def _depth(brace: dict, bay: float) -> float:
    return math.sqrt(max(brace["length"] ** 2 - bay ** 2, 0.0))


def longitudinal_bracing(geom, li, braces: list[dict], braced_bays: list[int]) -> dict:
    """geom: PEBGeometry; li: LoadsInput; braces: the building's roof_brace / wall_brace members; braced_bays 0-based."""
    wind = envelope_pressures(geom, li.site())
    p, minimum = longitudinal_endwall_pressure(geom, wind)
    j0 = braced_bays[0]
    bay = geom.bay_spacings[j0]
    roof_d = max(_depth(b, bay) for b in braces if b["role"] == "roof_brace" and b["bay"] == j0)
    wall_d = max(_depth(b, bay) for b in braces if b["role"] == "wall_brace" and b["bay"] == j0)
    system = LongitudinalSystem(geometry=geom, braced_bays=tuple(braced_bays), roof_panel_depth=roof_d)
    f = solve_longitudinal(system, p, eave_share=EAVE_SHARE)
    wall_bay = BracedBay(index=j0, plane=BracingPlane.SIDEWALL, width=bay, depth=wall_d)
    wall_shear = f.per_braced_bay / system.n_braced_walls
    wall_T = wall_bay.diagonal_force(wall_shear)
    sets = {}
    for s, k in FACTORS.items():
        sets[s] = {"factor": k, "F_eave": round(k * f.F_eave, 3), "F_base": round(k * f.F_base, 3),
                   "per_braced_bay": round(k * f.per_braced_bay, 3), "roof_diagonal": round(k * f.roof_diagonal, 3),
                   "wall_diagonal": round(k * wall_T, 3), "wall_base_shear": round(k * wall_shear, 3),
                   "strut": [[j + 1, round(k * v, 3)] for j, v in f.strut_forces], "max_strut": round(k * f.max_strut_force, 3)}
    return {
        "pressure_kpa": round(p, 5),
        "minimum": None if minimum is None else {"governs": bool(minimum.governs), "F_computed": round(minimum.F_computed, 2),
                                                  "F_minimum": round(minimum.F_minimum, 2)},
        "braced_bays": [j + 1 for j in braced_bays],
        "roof_panel": {"width": bay, "depth": round(roof_d, 1), "cos": round(f.roof_bay.cos_theta, 5)},
        "wall_panel": {"width": bay, "depth": round(wall_d, 1), "cos": round(wall_bay.cos_theta, 5)},
        "sets": sets,
        "assumptions": [f"eave_share {EAVE_SHARE}: wind columns span base to rafter, pinned top and bottom",
                        "tension-only diagonals: the compression diagonal of each X carries nothing",
                        "both endwalls loaded; each braced bay carries an equal share (bimsteelauto)"],
        "notes": "Strength from LRFD (1.0W). Not designed (Phase 4).",
        "designed": False,
    }
