# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 2: base plates and anchor rods (engine/connections/baseplates.py). The bearing / thickness / anchor
relations are bimsteelauto_connections' (VERIFIED there against DG 1 and Hilti PROFIS); here: the plumbing, the layout,
the new inside-rod plate model, the statuses.

Independent values (by hand):
    DG 1 Table 2.3 row (the next inch rod up): M16 → 3/4 in.: hole 1 5/16 in. = 33.3 mm, washer 2 in. = 50.8 mm;
        M20 → 7/8 in.: washer 63.5; M24 → 1 in.: washer 76.2. Clearance c = washer/2 + 8 + 5 rounded up to 5:
        M16 25.4 + 13 = 38.4 → 40; M20 44.75 → 45; M24 51.1 → 55
    Building 1 column base: d = 300 + 2 × 12 = 324, bf 250, tf 12, tw 8 (column web 8: its deepest web 800 > 600).
    Inside, M16: s ≥ max(4 × 16 = 64, 50.8 + 10 = 60.8) = 64 → along the web 65; across the web max(8 + 2 × 40 = 88, 64)
        → 90; fits: 65/2 + 40 = 72.5 ≤ 324/2 − 12 = 150; plate N = 324 + 50 = 374 → 375, B = 250 + 50 = 300;
        lever to the web face = 90/2 − 8/2 = 41
    Outside, M16: along the depth 324 + 80 = 404 → 405, across max(250, 64) = 250; N = 405 + 80 = 485, B = 330
    Inside-rod plate (pure uplift 48.971 kN, Mu = 0 → 4 rods, T = 12.243 kN each): b_side = min(2 × 41 + 65 = 147,
        324 − 24 = 300) = 147, b_eff = 73.5; t = √(4 × 12 243 × 41 / (0.9 × 355 × 73.5)) = √85.502 = 9.247 mm
    Anchors, M16 F1554 Gr 36 (futa = min(400, 1.9 × 248 = 471.2, 862) = 400 MPa, Ase 157 mm², ductile):
        tension steel φNsa = 0.75 × 4 × 157 × 400 = 188.40 kN → 48.971 / 188.40 = 0.2599
        shear steel (cast-in, grout pad × 0.8) φVsa = 0.65 × 4 × 0.8 × 0.6 × 157 × 400 = 78.374 kN → 64.769 → 0.8264
Negative controls: rods that do not fit between the flanges; no pedestal → the anchors' concrete modes NOT EVALUATED (never
a pass); a grade the library does not list (St 37) → NOT EVALUATED; a small pedestal → FAILS naming shear breakout and
suggesting the fixes; a joint without forces → NOT EVALUATED.
"""

import json
import math

import pytest

from engine.connections.baseplates import (WASHER_NOTE, BaseSettings, clearance, design_base, dg1_row, inside_rod_plate,
                                           layout_geometry)

SEC = {"d": 324.0, "bf": 250.0, "tf": 12.0, "tw": 8.0}


def _joint(comp=101.601, H_c=64.769, upl=48.971, H_u=-44.12, status="EVALUATED"):
    return {"id": "F3-BA", "type": "base", "status": status, "members": [{"id": "F3-CA"}],
            "forces": None if status != "EVALUATED" else {
                "compression": {"value": comp, "H": H_c, "V": comp, "M": 0.0, "combo": "LRFD: 1.2D+1.6Lr"},
                "uplift": {"value": upl, "H": H_u, "V": -upl, "M": 0.0, "combo": "LRFD: 0.9D+1.0W"},
                "shear": {"value": abs(H_c), "H": H_c, "V": comp, "M": 0.0, "combo": "LRFD: 1.2D+1.6Lr"},
                "moment": {"value": 0.0, "combo": None}}}


def test_dg1_rows_and_clearance():
    r = dg1_row(16)
    assert r["hole"] == pytest.approx(33.3, abs=0.05) and r["washer"] == pytest.approx(50.8)
    assert dg1_row(20)["washer"] == pytest.approx(63.5) and dg1_row(24)["washer"] == pytest.approx(76.2)
    assert [clearance(d) for d in (16, 20, 24)] == [40, 45, 55]


def test_layouts_by_hand():
    g = layout_geometry(SEC, 16, "inside")
    assert g["fits"] and (g["s_along_d"], g["s_across"], g["N"], g["B"], g["lever_to_web"]) == (65, 90, 375, 300, 41)
    o = layout_geometry(SEC, 16, "outside")
    assert (o["s_along_d"], o["s_across"], o["N"], o["B"]) == (405, 250, 485, 330)
    # negative control: M36 inside a 200 deep section: s = 150 → 75 + c 60 = 135 > 200/2 − 12 = 88
    bad = layout_geometry({"d": 200.0, "bf": 150.0, "tf": 12.0, "tw": 6.0}, 36, "inside")
    assert not bad["fits"] and "do not fit" in bad["why"]


def test_inside_rod_plate_longhand():
    ip = inside_rod_plate(48.971 / 4, 41.0, 65.0, 300.0, 355.0)
    assert ip["b_eff"] == pytest.approx(73.5) and ip["t_req"] == pytest.approx(9.247, abs=1e-3)
    # the flanges cap the shared width: clear depth 120 < 2 × 41 + 65 → b_side 120, b_eff 60 → t = √(4·12 243·41/(0.9·355·60))
    ip2 = inside_rod_plate(48.971 / 4, 41.0, 65.0, 120.0, 355.0)
    assert ip2["b_side"] == 120.0 and ip2["t_req"] == pytest.approx(math.sqrt(4 * 12242.75 * 41 / (0.9 * 355 * 60)), rel=1e-9)
    assert inside_rod_plate(0.0, 41.0, 65.0, 300.0, 355.0)["t_req"] == 0.0


def test_no_pedestal_plate_designed_anchors_not_evaluated():
    r = design_base(_joint(), SEC, "S355", BaseSettings())
    assert r["status"] == "PLATE DESIGNED - ANCHORS NOT EVALUATED" and any("pedestal" in m for m in r["missing"])
    assert WASHER_NOTE in r["notes"] and r["rod"]["d"] == 16 and r["plate_grade"] == "S355JR"
    upl = next(c for c in r["cases"] if c["name"] == "max uplift")
    assert upl["T_anchor"] == pytest.approx(48.971) and upl["T_rod"] == pytest.approx(12.243, abs=1e-3)
    assert upl["inside_plate"]["t_req"] == pytest.approx(9.247, abs=1e-3) and r["t"] >= 12.0
    a = next(x for x in r["anchors"] if x["case"] == "max uplift")
    modes = {m["mode"]: m for m in a["modes"]}
    assert set(modes) == {"17.6.1 steel strength", "17.7.1 steel strength"}            # concrete modes not shown as checked
    assert modes["17.6.1 steel strength"]["U"] == pytest.approx(48.971 / 188.40, abs=1e-4)
    assert "NOT EVALUATED" in a["status"] and a["interaction"] is None
    sh = next(x for x in r["anchors"] if x["case"] == "max shear")
    assert {m["mode"]: m for m in sh["modes"]}["17.7.1 steel strength"]["U"] == pytest.approx(64.769 / 78.374, abs=1e-4)
    json.dumps(r, allow_nan=False)


def test_pedestal_small_fails_with_fixes_large_passes():
    small = design_base(_joint(), SEC, "S355", BaseSettings(pedestal={"along_d": 600, "across": 500, "depth": 700}))
    assert small["status"] == "FAILS" and small["rod"]["d"] == 16                       # the smallest rod whose steel passes
    assert any("shear breakout" in f and "hairpins" in f and "shear lug" in f for f in small["fixes"])
    big = design_base(_joint(), SEC, "S355", BaseSettings(pedestal={"along_d": 1300, "across": 700, "depth": 900}))
    assert big["status"] == "DESIGNED" and all(a["passed"] for a in big["anchors"])
    assert big["app_params"]["washers"] == 1 and big["app_params"]["layout"] == "inside" and big["hef"] >= 150
    assert all(a["status"] == "EVALUATED" and a["interaction"] <= 1.0 for a in big["anchors"])


def test_not_evaluated_cases():
    assert design_base(_joint(), SEC, "St 37", BaseSettings())["status"] == "NOT EVALUATED"
    r = design_base(_joint(status="NOT EVALUATED"), SEC, "S355", BaseSettings())
    assert r["status"] == "NOT EVALUATED" and r.get("rod") is None
    for bad in ({"layout": "middle"}, {"anchor_grade": "4.6"}, {"pedestal": {"along_d": 600}}, {"concrete": "C20"}):
        with pytest.raises(ValueError):
            BaseSettings.from_dict(bad)


def test_outside_layout_uses_the_library_tension_interface():
    r = design_base(_joint(), SEC, "S355", BaseSettings(layout="outside"))
    upl = next(c for c in r["cases"] if c["name"] == "max uplift")
    assert "inside_plate" not in upl and r["geometry"]["layout"] == "outside"


@pytest.mark.slow
def test_building_1_bases():
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.baseplates import building_bases
    from engine.connections.joints import building_joints
    from engine.peb.building import BuildingInput, peb_building, resolve
    from engine.peb.loads_input import LoadsInput

    b0 = BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)
    b, _ = resolve(b0)
    out = peb_building(b)
    li = LoadsInput(V=45, exposure="C")
    jr = building_joints(b0, li, analysis=analyse_building(b, li), out=out)
    r = building_bases(jr, out)
    assert len(r["bases"]) == 16 and r["counts"] == {"PLATE DESIGNED - ANCHORS NOT EVALUATED": 16}   # 10 frame + 6 wind columns
    assert r["banner"].startswith("NOT FOR ISSUE") and r["warnings"] and WASHER_NOTE in r["notes"]
    big = building_bases(jr, out, BaseSettings(pedestal={"along_d": 1300, "across": 700, "depth": 900}))
    assert big["counts"] == {"DESIGNED": 16}
    # the uplift case of every frame base carries the step-1 uplift as the group tension (pinned: T = |Pu|)
    js = {j["id"]: j for j in jr["joints"]}
    for x in big["bases"]:
        if x["type"] == "base":
            u = next(c for c in x["cases"] if c["name"] == "max uplift")
            assert u["T_anchor"] == pytest.approx(js[x["joint"]]["forces"]["uplift"]["value"], abs=1e-3)
    json.dumps(big, allow_nan=False)
