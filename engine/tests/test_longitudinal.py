# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Open item 6: longitudinal wind at the braced-bay bases (engine/connections/longitudinal.py). Values longhand, NOT
recomputed by the code under test — building 1, frame line 1, base A (the Phase 3 analysis):
    wall brace 6000 × 5900 mm: L = 8414.868, cos α = 0.71302, sin α = 0.70114
    bracing LRFD (1.0 W) wall diagonal 21.075 kN with the §28.3.4 minimum governing: scale k = 1.11743 →
        Case B alone T_B = 21.075 / 1.11743 = 18.861 kN; the minimum alone = T_B × 1.11743 = 21.075 kN
    0.9D + 1.0WB+ : frame Ry = −22.302 (uplift), Rx = −7.72; brace 18.861: up 18.861 × 0.70114 = 13.224, across 13.448
        → Pu = −22.302 − 13.224 = −35.526 kN (≈ 22.3 + 13.2 = 35.5 uplift), V_strong 7.72, V_weak 13.448
    1.2D + 1.6Lr + 0.5WB+ : brace × 0.5 = 9.430 → Pu = 36.44 − 6.612 = 29.828
    minimum family, dead load only (D: Rx 6.521, Ry 15.088): 0.9D: Ry 13.579, T 21.075: up 14.777, across 15.027 →
        Pu = 13.579 − 14.777 = −1.197 (1.2 kN uplift), V_strong 5.869; 1.2D: 18.106 − 14.777 = 3.329
    limits: h = 6000 + (7200 − 6000)/2 = 6600 ≤ 18 000 and ≤ min(24 000, 24 000) → met; torsion: one-story, 6600 ≤ 9144 →
        exempt
Negative controls: the minimum family never takes a WB reaction (its Ry is the dead load's only); an eave of 18 000 mm
(h 18 600 > 18 000) → the pairing NOT EVALUATED; h above the least plan dimension → NOT EVALUATED; h 9 600 with no
flexible diaphragm → torsion NOT EVALUATED, a braced-bay base never EVALUATED.
"""

import math

import pytest

from engine.connections.longitudinal import (H_LOW_RISE, braced_base, brace_forces, low_rise_limits, members_not_evaluated,
                                             paired_cases, torsion_exception, wind_factor)

COS, SIN = 6000 / math.hypot(6000, 5900), 5900 / math.hypot(6000, 5900)
FRES = {"results": {"D": {"set": "case", "reactions": {"BA": [6.521, 15.088, 0.0]}},
                    "LRFD: 0.9D+1.0WB+": {"set": "LRFD", "reactions": {"BA": [-7.72, -22.302, 0.0]}},
                    "LRFD: 1.2D+1.6Lr+0.5WB+ (+C)": {"set": "LRFD", "reactions": {"BA": [24.537, 36.44, 0.0]}},
                    "LRFD: 0.9D+1.0WA+L": {"set": "LRFD", "reactions": {"BA": [-21.742, -24.479, 0.0]}}},
        "factors": {"LRFD: 0.9D+1.0WB+": {"D": 0.9, "WB+": 1.0}, "LRFD: 1.2D+1.6Lr+0.5WB+ (+C)": {"D": 1.2, "WB+": 0.5},
                    "LRFD: 0.9D+1.0WA+L": {"D": 0.9, "WA+L": 1.0}}}
BRACING = {"sets": {"LRFD": {"wall_diagonal": 21.075}}, "minimum_scale": 1.11743, "minimum_ratio": 1.11743}


def _out(eave=6000.0, apex=7200.0, span=24000.0, bays=(6000.0,) * 4):
    return {"input": {"eave_height": eave, "span": span, "bays": list(bays), "bay_spacing": bays[0], "n_bays": len(bays)},
            "apex_height": apex,
            "members": [{"id": "F1-CA", "role": "column", "side": "A", "start": [0.0, 0.0, 0.0], "end": [0.0, 0.0, eave]},
                        {"id": "F3-CA", "role": "column", "side": "A", "start": [12000.0, 0.0, 0.0], "end": [12000.0, 0.0, eave]},
                        {"id": "P313", "role": "wall_brace", "side": "A", "bay": 0, "start": [0.0, 203.75, 0.0],
                         "end": [6000.0, 203.75, 5900.0], "length": 8414.868},
                        {"id": "RA0-1", "role": "eave_strut", "side": "A", "start": [0.0, 0.0, eave], "end": [6000.0, 0.0, eave]}]}


AN = {"bracing": BRACING, "frames": [{"line": "1", "x": 0.0, "same_as": "1", "result": FRES}]}
JOINT = {"id": "F1-BA", "type": "base", "point": [0.0, 160.0, 0.0]}
COL = {"id": "F1-CA", "role": "column", "side": "A"}


def test_brace_force_split_by_hand():
    f = brace_forces(BRACING)
    assert f["T_caseB"] == pytest.approx(18.861, abs=1e-3) and f["T_minimum"] == pytest.approx(21.075, abs=1e-3)
    assert f["minimum_governs"] is True
    g = brace_forces({"sets": {"LRFD": {"wall_diagonal": 21.075}}, "minimum_scale": 1.0, "minimum_ratio": 0.9})
    assert g["T_caseB"] == pytest.approx(21.075) and g["T_minimum"] == pytest.approx(18.9675) and g["minimum_governs"] is False
    assert brace_forces({"sets": {"LRFD": {"wall_diagonal": 21.075}}}) is None          # an old result: no split → None
    assert wind_factor({"D": 0.9, "WB-": 1.0}) == 1.0 and wind_factor({"D": 0.9, "WA+L": 1.0}) is None


def test_frame_line_1_pairs_by_hand():
    cases = paired_cases(FRES, "BA", brace_forces(BRACING), COS, SIN)
    by = {c["combo"]: c for c in cases}
    assert set(by) == {"LRFD: 0.9D+1.0WB+", "LRFD: 1.2D+1.6Lr+0.5WB+ (+C)", "0.9D + 1.0W minimum (ASCE 7-16 §28.3.4), dead load only",
                       "1.2D + 1.0W minimum (ASCE 7-16 §28.3.4), dead load only"}          # WA+L is not a longitudinal case
    u = by["LRFD: 0.9D+1.0WB+"]
    assert (u["T_brace"], u["Ry_frame"], u["Pu"], u["V_strong"], u["V_weak"]) == pytest.approx((18.861, -22.302, -35.526, 7.72, 13.448), abs=2e-3)
    h = by["LRFD: 1.2D+1.6Lr+0.5WB+ (+C)"]
    assert h["wind_factor"] == 0.5 and h["T_brace"] == pytest.approx(9.430, abs=2e-3) and h["Pu"] == pytest.approx(29.828, abs=2e-3)
    m9 = by["0.9D + 1.0W minimum (ASCE 7-16 §28.3.4), dead load only"]
    assert (m9["T_brace"], m9["Ry_frame"], m9["Pu"], m9["V_strong"], m9["V_weak"]) == pytest.approx((21.075, 13.579, -1.197, 5.869, 15.027), abs=2e-3)
    assert by["1.2D + 1.0W minimum (ASCE 7-16 §28.3.4), dead load only"]["Pu"] == pytest.approx(3.329, abs=2e-3)
    # negative control: the minimum family takes the DEAD-LOAD reaction only, never a WB uplift; the Case B pairs take the
    # Case B brace force, never the minimum one
    mins = [c for c in cases if c["family"] == "minimum"]
    assert sorted(c["Ry_frame"] for c in mins) == pytest.approx([0.9 * 15.088, 1.2 * 15.088], abs=1e-3)
    assert all(c["T_brace"] == pytest.approx(18.861 * c["wind_factor"], abs=2e-3) for c in cases if c["family"] == "Case B")
    assert min(c["Pu"] for c in mins) > -22.302                                       # never −22.302 − 14.777 = −37.1


def test_braced_base_and_the_limits():
    r = braced_base(JOINT, COL, _out(), AN)
    assert r["status"] == "EVALUATED" and r["brace"] == "P313" and r["cos_a"] == pytest.approx(0.71302, abs=1e-5)
    assert r["limits"]["h"] == 6600.0 and r["limits"]["ok"] and r["torsion"]["status"] == "EXEMPT"
    assert min(c["Pu"] for c in r["cases"]) == pytest.approx(-35.526, abs=2e-3)
    assert braced_base({**JOINT, "point": [12000.0, 160.0, 0.0]}, COL, _out(), AN) is None     # no brace lands there
    # negative control: h = 18 000 + 600 = 18 600 > 18 000 → the pairing NOT EVALUATED (printed)
    hi = braced_base(JOINT, COL, _out(eave=18000.0, apex=19200.0), AN)
    assert hi["status"] == "NOT EVALUATED" and hi["cases"] == [] and "18 m" in hi["why"]
    assert hi["limits"]["h"] == 18600.0 and hi["limits"]["h_max"] == H_LOW_RISE and hi["limits"]["h_ok"] is False
    # h above the least plan dimension (span 12 000, length 2 × 5000 = 10 000, h 10 500)
    lim = low_rise_limits(_out(eave=10000.0, apex=11000.0, span=12000.0, bays=(5000.0, 5000.0)))
    assert lim["least_plan"] == 10000.0 and lim["h_ok"] and lim["h_le_least_ok"] is False and lim["ok"] is False
    # an analysis without the Case B / minimum split → NOT EVALUATED, never a guess
    old = braced_base(JOINT, COL, _out(), {**AN, "bracing": {"sets": BRACING["sets"]}})
    assert old["status"] == "NOT EVALUATED" and "split" in old["why"]


def test_torsion_exception():
    assert torsion_exception(_out())["status"] == "EXEMPT"                                     # 6600 ≤ 9144
    t = torsion_exception(_out(eave=9000.0, apex=10200.0))                                     # h 9600
    assert t["status"] == "NOT EVALUATED" and t["one_story_h_ok"] is False and "NOT EVALUATED" in t["why"]
    assert torsion_exception(_out(eave=9000.0, apex=10200.0), flexible_diaphragm=True)["status"] == "EXEMPT"
    r = braced_base(JOINT, COL, _out(eave=9000.0, apex=10200.0), AN)
    assert r["status"] == "NOT EVALUATED" and r["cases"] and "torsional" in r["why"]           # pairs shown, never DESIGNED


def test_members_not_evaluated():
    # open item 7 built (2026-11-17): with the setting on (default) the braced-bay columns and the eave struts are checked
    assert members_not_evaluated(_out()) == []
    # NEGATIVE CONTROL: the setting off → the old rows, NOT EVALUATED
    o = _out()
    o["input"]["brace_axial"] = False
    rows = members_not_evaluated(o)
    assert [(r["member"], r["role"]) for r in rows] == [("F1-CA", "braced-bay column"), ("RA0-1", "eave strut")]
    assert all("NOT EVALUATED" in r["status"] and "open item 7" in r["status"] for r in rows)
    # an end-rafter wall's column under a wall brace stays NOT EVALUATED (no main frame on that line to load)
    o = _out()
    o["end_walls"] = [{"end": "first", "kind": "rafter", "x_frame": 0.0}]
    assert [(r["member"], r["role"]) for r in members_not_evaluated(o)] == [("F1-CA", "braced-bay column")]
