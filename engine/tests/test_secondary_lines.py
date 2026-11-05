# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 2 step 2: purlin and girt lines against hand values.

Building 1: span 24 000, eave 6 000, slope 0.1, length 24 000, defaults (spacing 1 250, eave strut s = 0, ridge 200 from apex,
girts from 1 250 every 1 250 up to eave − 300)
    roof slope length = 12 000·√1.01 = 12 059.851;  s_ridge = 11 859.851
    n = ceil(11 859.851 / 1 250) = ceil(9.488) = 10 → pitch 1 185.985 (≤ 1 250); 11 lines a side (strut + 9 + ridge)
    ridge purlin: y = s/√1.01 = 11 859.851 / 1.0049876 = 11 800.993, z = 6 000 + 0.1·y = 7 180.099;  side B: y = 24 000 − 11 800.993 = 12 199.007
    rotation atan(0.1) = 5.711°
    girts: 1 250, 2 500, 3 750, 5 000 (6 250 > 5 700)
Building 2: span 30 000, eave 7 500, slope 1:12, roof A spacing 1 500, roof B 1 250, apex gap 250, wall A first 1 000 spacing 1 500
    slope length = 15 000·√(1 + 1/144) = 15 051.993; s_ridge = 14 801.993
    side A: n = ceil(9.868) = 10 → pitch 1 480.199;  side B: n = ceil(11.842) = 12 → pitch 1 233.499
    wall A girts: 1 000, 2 500, 4 000, 5 500, 7 000 (≤ 7 200)
"""

import math

import pytest

from engine.peb.secondary import RoofSide, SecondaryInput, Wall, purlin_positions, secondary_lines


def test_building_1_defaults():
    out = secondary_lines(SecondaryInput(span=24000, eave_height=6000, roof_slope=0.1, length=24000))
    a = [m for m in out["roof"] if m["side"] == "A"]
    b = [m for m in out["roof"] if m["side"] == "B"]
    assert len(a) == 11 and len(b) == 11
    assert out["slope_length"] == pytest.approx(12059.851, abs=1e-3)
    assert [m["role"] for m in a][:2] == ["eave_strut", "purlin"] and a[-1]["role"] == "ridge_purlin"
    assert a[0]["profile"] == "C200x65x20x2.0" and a[1]["profile"] == "Z200x65x20x2.0"
    assert a[1]["s"] == pytest.approx(1185.985, abs=1e-3)
    assert max(y["s"] - x["s"] for x, y in zip(a, a[1:])) <= 1250
    r = a[-1]
    assert r["s"] == pytest.approx(11859.851, abs=1e-3)
    assert r["start"] == [0, pytest.approx(11800.993, abs=1e-3), pytest.approx(7180.099, abs=1e-3)] and r["end"][0] == 24000
    rb = b[-1]
    assert rb["start"][0] == 24000 and rb["end"][0] == 0 and rb["start"][1] == pytest.approx(12199.007, abs=1e-3)
    assert a[0]["start"] == [0, 0, 6000] and b[0]["start"] == [24000, 24000, 6000]
    assert all(m["rotation"] == pytest.approx(math.degrees(math.atan(0.1)), abs=1e-3) for m in out["roof"])
    ga = [g["z"] for g in out["walls"] if g["side"] == "A"]
    assert ga == [1250, 2500, 3750, 5000]
    gb = [g for g in out["walls"] if g["side"] == "B"]
    assert gb[0]["start"] == [24000, 24000, 1250] and gb[0]["end"] == [0, 24000, 1250] and gb[0]["rotation"] == 90
    assert out["designed"] is False


def test_building_2_per_side_settings():
    out = secondary_lines(SecondaryInput(span=30000, eave_height=7500, roof_slope=1 / 12, length=36000,
                                         roof_a=RoofSide(spacing=1500, apex_gap=250), roof_b=RoofSide(apex_gap=250),
                                         wall_a=Wall(first=1000, spacing=1500)))
    a = [m["s"] for m in out["roof"] if m["side"] == "A"]
    b = [m["s"] for m in out["roof"] if m["side"] == "B"]
    assert len(a) == 11 and a[1] == pytest.approx(1480.199, abs=1e-3) and a[-1] == pytest.approx(14801.993, abs=1e-3)
    assert len(b) == 13 and b[1] == pytest.approx(1233.499, abs=1e-3)
    assert [g["z"] for g in out["walls"] if g["side"] == "A"] == [1000, 2500, 4000, 5500, 7000]
    assert [g["z"] for g in out["walls"] if g["side"] == "B"] == [1250, 2500, 3750, 5000, 6250]


def test_an_exact_fit_does_not_add_a_line():
    # s_ridge − s0 exactly 10 × 1 250: 10 intervals, not 11
    span = 2 * (12500 + 200)
    assert len(purlin_positions(span, 0.0, RoofSide())) == 11


@pytest.mark.parametrize("bad, msg", [
    (dict(roof_a=RoofSide(apex_gap=100)), "150 to 300"),
    (dict(roof_b=RoofSide(spacing=200)), "purlin spacing"),
    (dict(wall_a=Wall(spacing=5000)), "girt spacing"),
])
def test_refusals(bad, msg):
    with pytest.raises(ValueError, match=msg):
        secondary_lines(SecondaryInput(span=24000, eave_height=6000, roof_slope=0.1, length=24000, **bad))
