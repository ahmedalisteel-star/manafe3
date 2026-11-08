# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 8 (engine): the whole building — taper-step convergence, the secondary steel weighed by hand, frame-line
de-duplication (a de-duplicated line re-solved on its own must match), labels, the API."""

import math

import pytest
from fastapi.testclient import TestClient

from engine.analysis.building_analysis import TAPER_STEP, _line_setup, analyse_building
from engine.analysis.frame_loads import STEEL_KN_M3
from engine.analysis.secondary_weight import area_mm2, secondary_kpa
from engine.analysis.solve import analyse_frame_line
from engine.api import app
from engine.peb.building import BuildingInput, peb_building
from engine.peb.loads_input import LoadsInput

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)
LI = LoadsInput(V=45, exposure="C")


def _two_cases(fl):
    return type(fl)(loads=tuple(l for l in fl.loads if l.case in ("D", "WA+L")), cases=("D", "WA+L"), combinations=(),
                    tributary_m=fl.tributary_m, Lr=fl.Lr, wind=fl.wind)


@pytest.mark.slow
def test_taper_step_converged():
    """The analysis step (0.10) against a fine one (0.025): apex, sway, base thrust, max moments within 1 %."""
    b = BuildingInput(**B1)
    sec = {"roof_kpa": 0.07, "wall_kpa": 0.055}
    r = {}
    for step in (TAPER_STEP, 0.025):
        info, fl = _line_setup(b, LI, 2, sec, step)
        r[step] = analyse_frame_line(info, _two_cases(fl), p_delta=False)
    a, f = r[TAPER_STEP]["results"], r[0.025]["results"]
    mmax = lambda res, mk: max(abs(s[3]) for s in res["members"][mk])
    assert a["D"]["apex"] == pytest.approx(f["D"]["apex"], rel=0.01)
    assert a["WA+L"]["sway"] == pytest.approx(f["WA+L"]["sway"], rel=0.01)
    assert a["D"]["reactions"]["BA"][0] == pytest.approx(f["D"]["reactions"]["BA"][0], rel=0.01)
    for mk in ("CA", "RA1", "RB1"):
        assert mmax(a["D"], mk) == pytest.approx(mmax(f["D"], mk), rel=0.01) and mmax(a["WA+L"], mk) == pytest.approx(mmax(f["WA+L"], mk), rel=0.01)


def test_secondary_weight_by_hand():
    assert area_mm2("Z200x65x20x2.0") == pytest.approx(2.0 * (200 + 2 * 65 + 2 * 20 - 4 * 2.0))     # 724 mm²
    assert area_mm2("RD12") == pytest.approx(113.097, abs=1e-3) and area_mm2("L50x5") == pytest.approx(475.0)
    assert area_mm2("PL8x100") == 800.0
    with pytest.raises(ValueError):
        area_mm2("HEA200")                                       # no rule → refused, never guessed
    s = secondary_kpa(peb_building(BuildingInput(**B1)))
    assert s["roof_m2"] == pytest.approx(2 * 12.0 * math.sqrt(1.01) * 24.0, abs=1e-3)
    assert s["wall_m2"] == pytest.approx(2 * 24.0 * 6.0)
    assert s["roof_kpa"] == pytest.approx(s["roof_kN"] / s["roof_m2"], abs=1e-5)
    # the roof bracing alone, longhand: 16 rods RD20, each panel 6 m wide by its slope depth — the lengths come from the
    # model, the weight per metre by hand: π·20²/4 = 314.16 mm² → 0.024185 kN/m
    out = peb_building(BuildingInput(**B1))
    rods = [m for m in out["members"] if m["role"] == "roof_brace"]
    assert len(rods) == 16 and all(m["profile"] == "RD20" for m in rods)
    assert s["by_role_kN"]["roof_brace"] == pytest.approx(sum(m["length"] for m in rods) / 1000 * 314.159e-6 * STEEL_KN_M3, abs=2e-3)
    assert 0.03 < s["roof_kpa"] < 0.12 and 0.02 < s["wall_kpa"] < 0.10         # sanity band for Z200 at ~1.25 m


@pytest.fixture(scope="module")
def whole():
    return analyse_building(BuildingInput(**B1, end_first="rafter"), LI, p_delta=False, workers=2)


@pytest.mark.slow
def test_building_dedup_and_labels(whole):
    r = whole
    assert r["banner"].startswith("NOT FOR ISSUE") and r["designed"] is False
    same = {f["line"]: f["same_as"] for f in r["frames"]}
    assert same == {"2": "2", "3": "2", "4": "2", "5": "5"}              # line 1 is an end-rafter wall; 5 has half the tributary
    assert [f for f in r["frames"] if f["line"] == "3"][0].get("result") is None
    std = [f for f in r["frames"] if f["line"] == "2"][0]["result"]["staad"]
    assert std.startswith("STAAD PLANE") and "NOT FOR ISSUE" in std and std.rstrip().endswith("FINISH")
    assert len(r["end_frames"]) == 1 and r["end_frames"][0]["end"] == "first"
    assert r["sets"] == {"strength": "LRFD", "serviceability": "ASD", "foundation": "case (unfactored)"}
    # the de-duplicated line 4, solved on its own, must give line 2's numbers
    info, fl = _line_setup(BuildingInput(**B1, end_first="rafter"), LI, 3, r["secondary"], TAPER_STEP)
    own = analyse_frame_line(info, _two_cases(fl), p_delta=False)
    two = [f for f in r["frames"] if f["line"] == "2"][0]["result"]
    for case in ("D", "WA+L"):
        assert own["results"][case]["reactions"] == two["results"][case]["reactions"]
    # line 5 is different: its D base reaction is about half of line 2's (half the tributary, plus its own self-weight)
    five = [f for f in r["frames"] if f["line"] == "5"][0]["result"]
    v2, v5 = two["results"]["D"]["reactions"]["BA"][1], five["results"]["D"]["reactions"]["BA"][1]
    assert 0.45 < v5 / v2 < 0.75


@pytest.mark.slow
def test_api_analysis():
    c = TestClient(app)
    r = c.post("/peb/analysis", json={"building": {**B1, "n_bays": 2}, "loads": {"V": 45, "exposure": "C"}, "p_delta": False})
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["banner"].startswith("NOT FOR ISSUE") and [f["line"] for f in j["frames"]] == ["1", "2", "3"]
    bad = c.post("/peb/analysis", json={"building": B1, "loads": {"exposure": "C"}})
    assert bad.status_code == 422 and "V" in bad.text                       # no wind speed: refused, never assumed
