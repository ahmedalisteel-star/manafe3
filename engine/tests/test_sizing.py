# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 8: the sizing loop (engine/design/sizing.py).

    ladders      plates 6 … 25 (web ≥ 6, flange ≥ 8), flange widths 150 … 300, depths in 25 mm steps; hw_base and
                 hw_rafter ≥ 300 and ≤ hw_knee (the generator's minimums kept); the end of a ladder → None
    webs         BuiltUpSizes.tw_column / tw_haunch / tw_rafter override the 6 / 8 mm rule; None keeps it
    weight       one frame of building 1 by hand: column web (300 + 800) / 2 × 8 and flanges 2 × 250 × 12 over 6000; haunch
                 web (800 + 400) / 2 × 8 over 2400; rafter web 400 × 6 over 11 176 √1.01 − 2400; × 2 sides × 7.85e-6
    remap        held forces follow each analysis member to its new length (x × L_new / L_old), P V M unchanged
    loop         building 1 converges (the sizes repeat), its FULL check ≤ 0.90 and serviceability ≤ 1.0, every plate on
                 its ladder and at or above its minimum (slow)
"""

import dataclasses
import math

import pytest

from engine.design import sizing as sz
from engine.peb.builtup_frame import builtup_frame_members, default_sizes
from engine.peb.building import BuildingInput
from engine.peb.loads_input import LoadsInput

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)


def test_ladders_and_minimums():
    z = sz.explicit(default_sizes(24000))
    assert (z.tw_column, z.tw_haunch, z.tw_rafter) == (8.0, 8.0, 6.0)          # the rule written out
    assert sz.step(z, "tf", +1).tf == 14.0 and sz.step(z, "tf", -1).tf == 10.0
    assert sz.step(dataclasses.replace(z, tf=8.0), "tf", -1) is None          # flange ≥ 8
    assert sz.step(z, "tw_rafter", -1) is None                                  # web ≥ 6
    assert sz.step(dataclasses.replace(z, tw_rafter=25.0), "tw_rafter", +1) is None
    assert sz.step(z, "bf", +1).bf == 300.0 and sz.step(z, "bf", -1).bf == 220.0
    assert sz.step(dataclasses.replace(z, bf=150.0), "bf", -1) is None
    assert sz.step(z, "hw_knee", +1).hw_knee == 825.0
    assert sz.step(z, "hw_base", -1) is None                                    # 300 is the minimum
    assert sz.step(z, "hw_rafter", -1).hw_rafter == 375.0 and sz.step(dataclasses.replace(z, hw_rafter=300.0), "hw_rafter", -1) is None
    z2 = dataclasses.replace(z, hw_rafter=800.0)
    assert sz.step(z2, "hw_rafter", +1) is None                                 # not deeper than the knee
    assert sz.step(dataclasses.replace(z, tf=11.0), "tf", +1).tf == 12.0        # off-ladder values snap to the ladder


def test_web_overrides():
    z = dataclasses.replace(default_sizes(24000), tw_column=10.0, tw_haunch=12.0, tw_rafter=6.0)
    ms = builtup_frame_members(24000, 6000, 0.1, 0.0, "1", z)
    col = next(m for m in ms if m["role"] == "column")["section"]["segments"]
    raf = next(m for m in ms if m["role"] == "rafter")["section"]["segments"]
    assert {s["tw"] for s in col} == {10.0} and raf[0]["tw"] == 12.0 and {s["tw"] for s in raf[1:]} == {6.0}
    ms0 = builtup_frame_members(24000, 6000, 0.1, 0.0, "1", default_sizes(24000))
    assert next(m for m in ms0 if m["role"] == "rafter")["section"]["segments"][0]["tw"] == 8.0   # the rule kept


def test_frame_weight_by_hand():
    b = BuildingInput(**B1)
    z = default_sizes(24000)
    L_raf = (12000 - (800 + 24)) * math.sqrt(1.01)
    col = ((300 + 800) / 2 * 8 + 2 * 250 * 12) * 6000
    hau = ((800 + 400) / 2 * 8 + 2 * 250 * 12) * 2400
    raf = (400 * 6 + 2 * 250 * 12) * (L_raf - 2400)
    assert sz.frame_weight(b, z) == pytest.approx(2 * (col + hau + raf) * 7.85e-6, rel=1e-6)


def test_remap():
    from engine.analysis.frame_model import frame_line_model
    z0 = default_sizes(24000)
    z1 = dataclasses.replace(z0, hw_knee=900.0)
    i0 = frame_line_model(builtup_frame_members(24000, 6000, 0.1, 0.0, "1", z0), 24000, 6000, 0.1, (6000,) * 4)
    i1 = frame_line_model(builtup_frame_members(24000, 6000, 0.1, 0.0, "1", z1), 24000, 6000, 0.1, (6000,) * 4)
    L0 = {m.mark: m.length for m in i0.layout.members}
    L1 = {m.mark: m.length for m in i1.layout.members}
    res = {"combos": [["X", "LRFD"]], "results": {"X": {"members": {k: [[0.0, 1.0, 2.0, 3.0], [L0[k], 4.0, 5.0, 6.0]] for k in L0}}}}
    r = sz.remap(res, i0, i1, ["X"])
    for k in L0:
        assert r["results"]["X"]["members"][k][1] == [pytest.approx(L1[k]), 4.0, 5.0, 6.0]


def test_cf_ladder():
    c = sz.cf_candidates("Z200x65x20x2.0")
    assert c[0] == "Z150x65x20x1.5" and c[-1] == "Z300x65x20x3"
    areas = [(float(n[1:].split("x")[0]) + 2 * 65 + 2 * 20) * float(n.split("x")[-1]) for n in c]
    assert areas == sorted(areas) and len(c) == 36


@pytest.mark.slow
def test_building_1_converges():
    r = sz.size_frames(BuildingInput(**B1), LoadsInput(V=45, exposure="C"), stability="prismatic")
    assert r["converged"] and r["passed"]
    assert r["max_ratio"] <= sz.TARGET + 1e-9 and r["service_ratio"] <= 1.0
    s = r["sizes"]
    assert s["tf"] in sz.PLATES and s["tf"] >= 8 and s["bf"] in sz.FLANGE_WIDTHS
    for k in ("tw_column", "tw_haunch", "tw_rafter"):
        assert s[k] in sz.PLATES and s[k] >= 6
    for k in ("hw_knee", "hw_rafter", "hw_base"):
        assert s[k] % 25 == 0 and s[k] >= 300
    assert s["hw_rafter"] <= s["hw_knee"] and s["hw_base"] <= s["hw_knee"]
    assert r["kg_per_frame"] < r["rounds"][0]["kg_per_frame"]                # building 1's defaults are light-loaded (0.39)


@pytest.mark.slow
def test_cold_formed_by_r_factor_with_strict_beside():
    r = sz.size_cold_formed(BuildingInput(**B1), LoadsInput(V=45, exposure="C"))
    assert r["uplift_method"] == "r_factor" and r["R_VERIFIED"] is False
    assert "NOT FOR ISSUE" in r["banner"] and "R-FACTOR" in r["banner"]
    assert r["passed"]
    for role in ("purlin", "eave_strut", "girt"):
        v = r["roles"][role]
        assert v["to"] and v["ratio"] <= sz.TARGET and v["strict_ratio"] >= v["ratio"] - 1e-9     # strict never lighter
        assert r["sections"][role] == v["to"]
    # building 1 under the strict rule: the purlins and eave struts fail on the R-factor's choice (free flange 6 m)
    assert r["roles"]["eave_strut"]["strict_ratio"] > 1.0
