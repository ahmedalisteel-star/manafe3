# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 5d + step 6 slots (engine/connections/eave_transfer.py). Independent values written out longhand below.

    F6 (minor axis)  200 × 10 flanges, hw 475, tw 6, Fy 355: Zy = 2 × 10 × 200² / 4 + 475 × 6² / 4 = 204 275; Iy = 2 × 10 ×
                     200³ / 12 + 475 × 6³ / 12 = 13 341 883.3, Sy = Iy / 100 = 133 418.8; Mp = min(72.5176e6, 1.6 × 355 ×
                     133 418.8 = 75.782e6) = 72.5176e6; λ = 200 / 20 = 10 > λp = 0.38 √(200 000 / 355) = 9.0193, ≤ λr = 23.7346
                     → F6-2: Mn = 72.5176e6 − (72.5176e6 − 0.7 × 355 × 133 418.8)(10 − 9.0193) / (23.7346 − 9.0193)
                     = 69.8936e6 → φMny = 62 904 kN·mm; G6 φVny = 0.9 × 0.6 × 355 × 2 × 2000 = 766.8 kN
    TOP FLANGE       d 495, Mx 100 kN·m, P 50, F_x 15, a 700: Ff = 100 000 / 485 + 25 = 231.186 kN → / (0.9 × 355 × 2000)
                     = 0.361793; 15 × 700 = 10 500 kN·mm / (0.9 × 355 × 100 000 / 1000 = 31 950) = 0.328638 → U 0.690431
    FLANGE SPAN      F 10 at 2000 of 8000: 10 × 2000 × 6000 / 8000 = 15 000 kN·mm
    SLOT             d0 18 + 41.22 + 17.2 + 6 = 82.42 → 83 mm; tolerance 0 → 77 mm (negative control)
    KNEE J3.7        M24 8.8: φRt = 0.75 × 600 × 452.39 = 203.58, φRv = 0.75 × 360 × 452.39 = 122.15; T 70, V 2: cap =
                     min(187.325, 203.58, 1.3 × 203.58 − 203.58 × 2 / 122.15 = 261.32) = 187.325 → U 0.373682
    CLIP             F 16.186, offset 100: M = 1618.6 kN·mm; Z = 150 × 10² / 4 = 3750 → 0.9 × 355 × 3750 = 1198.125 kN·mm
                     → U 1.350939; 2 × M16 8.8: φRv = 0.75 × 360 × 201.062 = 54.287 → U 16.186 / 2 / 54.287 = 0.149077;
                     the clip, long slot ⊥ force, lc = 40 − 9 = 31: min(1.0 × 31 × 10 × 490 = 151 900, 2.0 × 16 × 10 × 490
                     = 156 800) × 0.75 = 113.925 per bolt → 227.85 kN
"""

from __future__ import annotations

import math

import pytest

from engine.connections import eave_transfer as E

SEC = {"bf_top": 200.0, "tf_top": 10.0, "bf_bot": 200.0, "tf_bot": 10.0, "hw": 475.0, "tw": 6.0, "d": 495.0}


def test_minor_axis_f6_g6():
    m = E.minor_axis(SEC, 355.0)
    assert m["rule"] == "F6-2" and m["lambda"] == 10.0
    assert m["phiMny"] == pytest.approx(62904.0, rel=2e-4) and m["phiVny"] == pytest.approx(766.8)
    compact = E.minor_axis({**SEC, "tf_top": 12.0, "tf_bot": 12.0}, 355.0)     # λ 8.33 ≤ 9.02: F6-1, Mn = Mp
    assert compact["rule"] == "F6-1"


def test_top_flange_alone_and_flange_span():
    t = E.top_flange_alone(SEC, 355.0, 100.0, 50.0, 15.0, 700.0)
    assert t["Ff"] == pytest.approx(231.186, abs=1e-3) and t["U"] == pytest.approx(0.690431, abs=1e-5)
    assert E.top_flange_alone(SEC, 355.0, 100.0, 50.0, 0.0, 700.0)["bending"] == 0.0   # NEGATIVE CONTROL: no F_x, no bending
    assert E.flange_lateral(10.0, 2000.0, 6000.0) == pytest.approx(15000.0)


def test_slot_and_bolts():
    assert E.slot_length(18.0, 41.22, 17.2, 6.0) == 83 and E.slot_length(18.0, 41.22, 17.2, 0.0) == 77
    assert E.slot_length(18.0, -3.0, -1.0, 6.0) == 24                                # no movement: d0 + tolerance
    assert E.bolt_tension_shear_U(70.0, 2.0, 203.58, 122.15, 187.325) == pytest.approx(0.373682, abs=1e-5)


def test_settings():
    with pytest.raises(ValueError):
        E.EaveSettings(clip_t=0.0).check()
    with pytest.raises(ValueError):
        E.EaveSettings(wc_bolts=0).check()


@pytest.mark.slow
def test_building_1_eave_and_wind_column_tops():
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.endplates import building_endplates
    from engine.connections.joints import building_joints
    from engine.peb.building import peb_building, resolve
    from engine.tests.test_joints import _sized
    b0, li = _sized()
    b, _ = resolve(b0)
    out = peb_building(b)
    an = analyse_building(b, li)
    jr = building_joints(b0, li, analysis=an, out=out)
    ep = building_endplates(jr, out)
    r = E.building_eave_transfer(b, jr, out, an, ep)
    assert r["banner"].startswith("NOT FOR ISSUE") and r["counts"] == {"eave": {"DESIGNED": 4, "FAILS": 4}, "wind_column_tops": {"FAILS": 6}}
    bf = r["brace_forces_roof"]
    assert bf["T_minimum"] == pytest.approx(21.128, abs=1e-3)                        # the minimum governs the roof diagonal
    for x in r["eave"]:
        assert x["F_x_minimum"] == pytest.approx(bf["T_minimum"] * x["u_x"], abs=2e-3)
        names = {c["name"] for c in x["checks"]}
        assert any(n.startswith("column top (own line, not item 7)") for n in names)  # its own line (4a)
        if x["frame_x"] in (6000, 18000):                                           # interior braced-bay frames
            assert x["status"] == E.FAILS and x["governing"]["name"].startswith("top flange alone") and E.SUGGEST in x["suggestion"]
        else:
            assert x["status"] == E.DESIGNED and x["suggestion"] is None
    worst = max(r["eave"], key=lambda x: x["governing"]["U"])
    assert worst["governing"]["U"] == pytest.approx(1.0641, abs=2e-3)
    w = {x["wind_column"]: x for x in r["wind_column_tops"]}
    assert w["WF1"]["slot"]["length"] == 83 and w["WF2"]["slot"]["length"] == 148 and w["WF1"]["slot"]["exceeds_long_slot"]
    clip = next(c for c in w["WF1"]["checks"] if c["name"].startswith("clip bending"))
    assert clip["U"] == pytest.approx(1.350939, abs=1e-4) and w["WF1"]["offset"] == 100.0
    assert next(c for c in w["WF1"]["checks"] if c["name"].startswith("bearing / tear-out on the clip"))["capacity"] == pytest.approx(227.85, rel=5e-4)
    # 7a: a flange brace at the ridge wind column (the ridge group) → no lateral moment; WF1 flagged, M = F a b / L
    assert w["WF2"]["flange"]["at_brace"] and w["WF2"]["flange"]["M_lat"] == 0.0
    f1 = w["WF1"]["flange"]
    assert not f1["at_brace"] and any(n.startswith("FLAG: no flange brace") for n in w["WF1"]["notes"])
    a_, b_ = f1["u_wind_column"] - f1["left"], f1["right"] - f1["u_wind_column"]
    assert f1["M_lat"] == pytest.approx(16.186 * a_ * b_ / (a_ + b_) / 1000.0, abs=2e-3)
    # NEGATIVE CONTROL: no bracing split in the analysis → every eave node NOT EVALUATED, never a U
    an2 = {**an, "bracing": {**an["bracing"], "minimum_scale": None}}
    r2 = E.building_eave_transfer(b, jr, out, an2, ep)
    assert r2["counts"]["eave"] == {"NOT EVALUATED": 8} and all("checks" not in x for x in r2["eave"])
