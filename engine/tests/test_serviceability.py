# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 4 step 4: serviceability (engine/design/serviceability.py) — ratios by hand.

    synthetic   a hand-made result: sway = |dx| / (H/100) of the worst eave over the ASD wind combinations only (a gravity
                combination with a bigger spread is NOT counted), rafter = the ridge's drop below the knee chord / (L/180)
    limits      editable: H/200 doubles the sway ratio; bad limits refused
    hook        crane members → a crane line with ratio inf, never a pass; no wind / no Lr → inf, not a pass
    building    frame line 3 of building 1 (slow): the ratios recomputed by hand from the solve's own displacements
"""

import math

import pytest

from engine.design.serviceability import ServiceLimits, frame_serviceability, rafter_deflection

NODES = {"BA": [0.0, 0.0], "KA": [300.0, 6000.0], "RA0": [500.0, 6100.0], "RAS1": [6000.0, 6650.0],
         "RIDGE": [12000.0, 7250.0], "RBS1": [18000.0, 6650.0], "RB0": [23500.0, 6100.0], "KB": [23700.0, 6000.0],
         "BB": [24000.0, 0.0]}


def res(disp_by_combo, combos, factors):
    return {"nodes": NODES, "combos": combos, "factors": factors,
            "results": {c: {"displacements": {n: d.get(n, [0.0, 0.0, 0.0]) for n in NODES}} for c, d in disp_by_combo.items()}}


def sample():
    return res({"Lr": {"RA0": [0, -2.0, 0], "RB0": [0, -4.0, 0], "RAS1": [0, -40.0, 0], "RIDGE": [0, -83.0, 0], "RBS1": [0, -41.0, 0]},
                "ASD: D + 0.6W": {"KA": [31.0, 0, 0], "KB": [-45.0, 0, 0]},
                "ASD: D + Lr": {"KA": [-90.0, 0, 0], "KB": [90.0, 0, 0]}},              # gravity spread: not "sway"
               [["Lr", "case"], ["ASD: D + 0.6W", "ASD"], ["ASD: D + Lr", "ASD"]],
               {"Lr": {"Lr": 1.0}, "ASD: D + 0.6W": {"D": 1.0, "WA+L": 0.6}, "ASD: D + Lr": {"D": 1.0, "Lr": 1.0}})


def test_ratios_by_hand():
    r = frame_serviceability(sample(), 24000.0)
    sway, raf = r["checks"]
    # sway: KB moves 45 mm; H = 6000 → allowed 60 → 0.75 (the 90 mm gravity spread is ignored)
    assert sway["node"] == "KB" and sway["combo"] == "ASD: D + 0.6W"
    assert sway["allowed"] == pytest.approx(60.0) and sway["ratio"] == pytest.approx(45.0 / 60.0)
    # rafter: chord from RA0 (-2) to RB0 (-4); at the ridge x = 12000 → t = 11500/23000 = 0.5 → chord -3; drop 80
    assert raf["node"] == "RIDGE" and raf["demand"] == pytest.approx(80.0)
    assert raf["allowed"] == pytest.approx(24000 / 180, abs=0.01) and raf["ratio"] == pytest.approx(80.0 / (24000 / 180), abs=1e-4)
    assert r["passed"] and r["max_ratio"] == pytest.approx(0.75)


def test_limits_editable_and_refused():
    r = frame_serviceability(sample(), 24000.0, ServiceLimits(sway=200, rafter_Lr=360))
    sway, raf = r["checks"]
    assert sway["ratio"] == pytest.approx(1.5) and not sway["passed"]                  # negative control: H/200 fails
    assert raf["ratio"] == pytest.approx(80.0 / (24000 / 360), abs=1e-4) and not r["passed"]
    assert ServiceLimits.from_dict({"sway": 150}).sway == 150
    for bad in ({"sway": 0}, {"rafter_Lr": -180}, {"purlin": float("nan")}, {"drift": 100}):
        with pytest.raises(ValueError):
            ServiceLimits.from_dict(bad)


def test_unevaluated_never_passes():
    r = frame_serviceability(sample(), 24000.0, has_crane=True)
    crane = r["checks"][-1]
    assert crane["ratio"] == math.inf and not crane["passed"] and not r["passed"]
    s = sample()
    s["combos"] = [c for c in s["combos"] if c[0] != "ASD: D + 0.6W"]
    del s["results"]["Lr"]
    r = frame_serviceability(s, 24000.0)
    assert all(c["ratio"] == math.inf and not c["passed"] for c in r["checks"])
    with pytest.raises(ValueError):
        rafter_deflection(s, "Lr")


@pytest.mark.slow
def test_frame_line_3_of_building_1_by_hand():
    from engine.analysis.building_analysis import _line_setup
    from engine.analysis.secondary_weight import secondary_kpa
    from engine.analysis.solve import analyse_frame_line
    from engine.peb.building import BuildingInput, peb_building
    from engine.peb.loads_input import LoadsInput

    b = BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)
    info, fl, fy = _line_setup(b, LoadsInput(V=45, exposure="C"), 2, secondary_kpa(peb_building(b)), 0.10, with_fy=True)
    res_ = analyse_frame_line(info, fl, fy=fy)
    r = frame_serviceability(res_, b.span)
    sway, raf = r["checks"]
    n = res_["nodes"]
    # sway by hand: over the ASD combinations that contain a wind case, max |dx| / ((y_K - y_B) / 100)
    best = max(abs(res_["results"][c]["displacements"][k][0]) / ((n[k][1] - n["B" + k[1]][1]) / 100)
               for c, s in res_["combos"] if s == "ASD" and any(f.startswith("W") for f in res_["factors"][c])
               for k in ("KA", "KB"))
    assert sway["ratio"] == pytest.approx(best, abs=1e-4)
    # rafter by hand: the ridge under Lr alone, below the RA0–RB0 chord (symmetric: the mean of the two knee ends)
    d = res_["results"]["Lr"]["displacements"]
    drop = (d["RA0"][1] + d["RB0"][1]) / 2 - d["RIDGE"][1]
    assert raf["node"] == "RIDGE" and raf["demand"] == pytest.approx(drop, abs=0.02)
    assert raf["ratio"] == pytest.approx(drop / (24000 / 180), abs=1e-3)
    assert 0 < raf["ratio"] < 2 and 0 < sway["ratio"] < 2                               # sane magnitudes
