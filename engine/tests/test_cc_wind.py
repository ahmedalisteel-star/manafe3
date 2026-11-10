# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""C&C wall pressures (ASCE 7-16 Ch. 30, engine/analysis/cc_wind.py) — VERIFIED False; this is the hand-check of ONE
case, written out longhand (user, 2026-11-08): wind column WF3 of building 1 (24 m span, eave 6 m, slope 0.1 → θ 5.71°,
V 45 m/s, exposure C; qh 0.94843 kN/m² from bimsteelauto).

    L = 6.7638 m (base to under the rafter), strip 6.000 m
    A = L × max(6.000, L/3 = 2.2546) = 40.583 m² = 40.583 / 0.09290304 = 436.83 ft²
    t = (log10 436.83 − 1) / (log10 500 − 1) = (2.64033 − 1) / (2.69897 − 1) = 0.96549
    zone 4 (its strip 3.0–9.0 m is beyond a = 2.4 m from the corners):
        GCp+ = 1.0 + (0.7 − 1.0)·0.96549 = 0.71035  × 0.9 (θ ≤ 10°) = 0.63932
        GCp− = −1.1 + (−0.8 + 1.1)·0.96549 = −0.81035 × 0.9 = −0.72932
    p in  = 0.94843 × (0.63932 + 0.18) = 0.77706 kN/m²;  p out = 0.94843 × (−0.72932 − 0.18) = −0.86241 kN/m²
    both beyond the 16 psf = 0.76608 kN/m² minimum (just)
    w in = 0.77706 × 6.0 = 4.6624 kN/m;  M = 4.6624 × 6.7638² / 8 = 26.662 kN·m
"""

import pytest

from engine.analysis.cc_wind import MIN_CC_KPA, VERIFIED, cc_wall_pressure, effective_area, gcp_wall
from engine.analysis.endwall_analysis import wind_columns
from engine.peb.building import BuildingInput, peb_building
from engine.peb.loads_input import LoadsInput


def test_hand_check_wf3():
    A = effective_area(6.7638, 6.0)
    assert A == pytest.approx(40.583, abs=1e-3)
    gp, gn = gcp_wall("4", A, 5.711)
    assert gp == pytest.approx(0.63932, abs=2e-5) and gn == pytest.approx(-0.72932, abs=2e-5)
    p = cc_wall_pressure(0.94843, "4", A, 5.711, (0.18, -0.18))
    assert p["inward"] == pytest.approx(0.77706, abs=2e-5) and p["outward"] == pytest.approx(-0.86241, abs=2e-5)
    assert MIN_CC_KPA == pytest.approx(0.76608, abs=1e-5) and not p["minimum_governs"] and p["VERIFIED"] is False
    assert not any(VERIFIED.values())                                           # new code: every flag starts False


def test_bounds_zone5_theta_and_minimum():
    assert gcp_wall("5", 0.5, 20.0) == pytest.approx((1.0, -1.4))               # ≤ 10 ft², θ > 10°: the figure's top values
    assert gcp_wall("5", 100.0, 20.0) == pytest.approx((0.7, -0.8))             # ≥ 500 ft²
    assert gcp_wall("4", 0.5, 5.0) == pytest.approx((0.9, -0.99))               # θ ≤ 10°: × 0.9
    assert effective_area(9.0, 2.0) == pytest.approx(27.0)                      # span/3 = 3 governs the width
    small = cc_wall_pressure(0.3, "4", 100.0, 20.0, (0.18, -0.18))              # a weak site: the minimum governs
    assert small["inward"] == pytest.approx(MIN_CC_KPA) and small["outward"] == pytest.approx(-MIN_CC_KPA) and small["minimum_governs"]


def test_wind_columns_use_cc():
    out = peb_building(BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4, end_first="rafter"))
    r = wind_columns(out, LoadsInput(V=45, exposure="C"))
    c = {x["id"]: x for x in r["columns"]}
    assert r["VERIFIED"] is False and r["a_mm"] == pytest.approx(2400.0)
    assert c["WF1"]["cc"]["zone"] == "5" and c["WF2"]["cc"]["zone"] == "4" and c["WL2"]["cc"]["zone"] == "4"
    assert c["WF3"]["L_m"] == pytest.approx(6.7638) and c["WF3"]["sets"]["case"]["inward"]["M"] == pytest.approx(26.662, abs=2e-3)
    assert c["WF3"]["sets"]["ASD"]["outward"]["M"] == pytest.approx(0.6 * -0.86241 * 6.0 * 6.7638 ** 2 / 8, abs=2e-3)
    # negative control: the corner column, zone 5, smaller area → larger suction than an interior one
    assert c["WF1"]["cc"]["outward"] < c["WF3"]["cc"]["outward"]
