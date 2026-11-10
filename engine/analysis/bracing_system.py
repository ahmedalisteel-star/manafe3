# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 3 step 6: the longitudinal (tension-only X-bracing) system — bimsteelauto's verified chain, on Manafe3's panels,
driven by the ACTUAL end-wall top reactions (user decision 2026-11-08).

    F_eave     endwall_analysis.longitudinal_feed: each end-wall support a simple beam under MWFRS end-wall pressure
               (bimsteelauto Load Case B 5 / 6 with the §28.3.4 minimum); top reactions + the wall above the tops,
               summed per end wall, windward + leeward, the worse wind direction. (Was: bimsteelauto endwall_force with a
               blanket eave_share 0.5 — replaced.)
    chain      bimsteelauto's rules, unchanged: each braced bay an equal share F_eave / n_braced; roof X half per slope;
               wall X split between the 2 sidewalls; one tension diagonal per panel, T = V / cos θ (BracedBay); eave-strut
               drag forces (bimsteelauto _strut_forces — its own private helper, called, not copied)
    panels     Manafe3's OWN panels (engine/peb/bracing.py): the deepest generated panel governs
    sets       unfactored (W = 1.0), LRFD (1.0 W), ASD (0.6 W); strength from LRFD
Independent check (tests): a PyNite tension-only truss of the wall panel gives the same diagonal force. Not designed.
"""

from __future__ import annotations

import math

from bimsteelauto.analysis.bracing import BracedBay, BracingPlane, LongitudinalSystem, _strut_forces

FACTORS = {"case": 1.0, "LRFD": 1.0, "ASD": 0.6}


def _depth(brace: dict, bay: float) -> float:
    return math.sqrt(max(brace["length"] ** 2 - bay ** 2, 0.0))


def longitudinal_bracing(geom, braces: list[dict], braced_bays: list[int], feed: dict) -> dict:
    """geom: PEBGeometry; braces: the building's roof_brace / wall_brace members; braced_bays 0-based;
    feed: endwall_analysis.longitudinal_feed(out, li)."""
    j0 = braced_bays[0]
    bay = geom.bay_spacings[j0]
    roof_d = max(_depth(b, bay) for b in braces if b["role"] == "roof_brace" and b["bay"] == j0)
    wall_d = max(_depth(b, bay) for b in braces if b["role"] == "wall_brace" and b["bay"] == j0)
    system = LongitudinalSystem(geometry=geom, braced_bays=tuple(braced_bays), roof_panel_depth=roof_d)
    F_eave, F_base = feed["F_eave"], feed["F_base"]
    per_bay = F_eave / system.n_braced
    roof_bay = system.roof_bay(j0)
    wall_bay = BracedBay(index=j0, plane=BracingPlane.SIDEWALL, width=bay, depth=wall_d)
    roof_T = roof_bay.diagonal_force(per_bay / 2.0)
    wall_shear = per_bay / system.n_braced_walls
    wall_T = wall_bay.diagonal_force(wall_shear)
    # bimsteelauto's strut drag takes F_eave / 2 per end (a symmetric split); with the real per-side top forces the
    # windward end delivers more, so it is given 2 × the larger side's top force (each end then carries the larger)
    d = feed["directions"][feed["governing"]]
    struts = _strut_forces(system, 2.0 * max(d["windward_top"], d["leeward_top"]))
    sets = {}
    for s, k in FACTORS.items():
        sets[s] = {"factor": k, "F_eave": round(k * F_eave, 3), "F_base": round(k * F_base, 3),
                   "per_braced_bay": round(k * per_bay, 3), "roof_diagonal": round(k * roof_T, 3),
                   "wall_diagonal": round(k * wall_T, 3), "wall_base_shear": round(k * wall_shear, 3),
                   "strut": [[j + 1, round(k * v, 3)] for j, v in struts], "max_strut": round(k * max((abs(v) for _, v in struts), default=0.0), 3)}
    return {
        "pressure_kpa": feed["p_net_kpa"], "p_side_kpa": feed["p_side_kpa"], "governing": feed["governing"],
        "eave_share": round(F_eave / (F_eave + F_base), 4),
        "braced_bays": [j + 1 for j in braced_bays],
        "roof_panel": {"width": bay, "depth": round(roof_d, 1), "cos": round(roof_bay.cos_theta, 5)},
        "wall_panel": {"width": bay, "depth": round(wall_d, 1), "cos": round(wall_bay.cos_theta, 5)},
        "sets": sets,
        "assumptions": ["F_eave from the actual end-wall top reactions (simple-beam supports, MWFRS), not a blanket half",
                        "tension-only diagonals: the compression diagonal of each X carries nothing",
                        "each braced bay carries an equal share (bimsteelauto)"],
        "notes": "Strength from LRFD (1.0W). Not designed (Phase 4).",
        "designed": False,
    }
