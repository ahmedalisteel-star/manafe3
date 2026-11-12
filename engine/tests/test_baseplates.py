# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 2 / 2b: base plates and anchor rods (engine/connections/baseplates.py). The bearing / thickness / anchor
relations are bimsteelauto_connections' (VERIFIED there against DG 1 and Hilti PROFIS); here: the plumbing, the layout,
the inside-rod plate model, the anchor reinforcement, the statuses.

Independent values (by hand):
    DG 1 Table 2.3 row (the next inch rod up): M16 → 3/4 in.: hole 1 5/16 in. = 33.3 mm, washer 2 in. = 50.8 mm;
        M20 → 7/8 in.: washer 63.5; M24 → 1 in.: washer 76.2. Clearance c = washer/2 + 8 + 5 rounded up to 5:
        M16 25.4 + 13 = 38.4 → 40; M20 44.75 → 45; M24 51.1 → 55
    Building 1 column base: d = 300 + 2 × 12 = 324, bf 250, tf 12, tw 8 (column web 8: its deepest web 800 > 600).
    Inside, M20 (the main-frame minimum): s ≥ max(4 × 20 = 80, 63.5 + 10 = 73.5) = 80 along the web; across the web
        max(8 + 2 × 45 = 98, 80) → 100; fits: 40 + 45 = 85 ≤ 324/2 − 12 = 150; plate N = 374 → 375, B = 300;
        lever to the web face = 100/2 − 8/2 = 46
    Inside, M16: along 65, across 90, lever 41.  Outside, M16: along 405, across 250, N 485, B 330
    Inside-rod plate, M20 (pure uplift 48.971 kN, Mu = 0 → 4 rods, T = 12.243 kN each): b_side = min(2 × 46 + 80 = 172,
        300) = 172, b_eff = 86; t = √(4 × 12 242.75 × 46 / (0.9 × 355 × 86)) = √81.985 = 9.055 mm
    Anchors, M20 ISO 4.6 (fya 240, futa 400 MPa — ISO 898-1 Table 3; NOT ductile → φ 0.65 / 0.60), Ase 245 mm²:
        tension steel φNsa = 0.65 × 4 × 245 × 400 = 254.80 kN → 48.971 / 254.80 = 0.19219
        shear steel (cast-in, grout pad × 0.8) φVsa = 0.60 × 4 × 0.8 × 0.6 × 245 × 400 = 112.896 kN → 64.769 → 0.57371
    Anchor reinforcement (ACI 318-19 17.5.2.1(b), φ 0.75, B500 fy 500): Vua 64.769 → As,req = 64 769 / (0.75 × 500) =
        172.72 mm²; one hairpin T12 = 2 × 113.10 = 226.19 mm² (T10: 157.08 < 172.72) → φVn = 0.75 × 226.19 × 500 = 84.823 kN;
        ld (Table 25.4.2.3, db ≤ 20, ψg 1.15) = 500 × 1.15 × 12 / (2.1 × √30) = 599.9 → 600 mm
    17.8 with the reinforcement, uplift case: ut 0.542, uv = 44.12 / 84.823 = 0.5201 → (0.542 + 0.5201) / 1.2 = 0.885
Negative controls: rods that do not fit between the flanges; no pedestal → the anchors' concrete modes NOT EVALUATED;
anchor reinforcement switched off → FAILS naming shear breakout; a pryout failure is not "fixed" by hairpins; a pedestal
too shallow for the 300 mm minimum → NOT EVALUATED; hooked anchors refused; a joint without forces → NOT EVALUATED.
"""

import json
import math
from types import SimpleNamespace

import pytest

from engine.connections.baseplates import (WASHER_NOTE, BaseSettings, _with_reinforcement, anchor_reinforcement, clearance,
                                           design_base, development_length, dg1_row, inside_rod_plate, interaction_17_8,
                                           layout_geometry, rod_label)

SEC = {"d": 324.0, "bf": 250.0, "tf": 12.0, "tw": 8.0}
SMALL = {"along_d": 600, "across": 500, "depth": 700}


def _joint(comp=101.601, H_c=64.769, upl=48.971, H_u=-44.12, status="EVALUATED", kind="base"):
    return {"id": "F3-BA", "type": kind, "status": status, "members": [{"id": "F3-CA"}],
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


def test_rod_lists_grades_and_minimums():
    st = BaseSettings()
    assert st.anchor_grade == "4.6" and st.rods("frame")[0] == 20 and st.rods("wind")[0] == 16
    f = BaseSettings(anchor_grade="F1554-36")
    assert all(d in (19.05, 22.225, 25.4, 28.575, 31.75, 38.1) for d in f.rods("frame"))         # inch only
    assert rod_label(f.rods("frame")[0]) == '7/8"' and rod_label(20.0) == "M20"
    p = BaseSettings(pedestal={"along_d": 900, "across": 600, "depth": 600})
    assert p.hefs("frame") == [300, 350, 400, 450, 500] and p.hefs("wind")[0] == 150


def test_layouts_by_hand():
    g = layout_geometry(SEC, 20, "inside")
    assert g["fits"] and (g["s_along_d"], g["s_across"], g["N"], g["B"], g["lever_to_web"]) == (80, 100, 375, 300, 46)
    g16 = layout_geometry(SEC, 16, "inside")
    assert (g16["s_along_d"], g16["s_across"], g16["lever_to_web"]) == (65, 90, 41)
    o = layout_geometry(SEC, 16, "outside")
    assert (o["s_along_d"], o["s_across"], o["N"], o["B"]) == (405, 250, 485, 330)
    bad = layout_geometry({"d": 200.0, "bf": 150.0, "tf": 12.0, "tw": 6.0}, 36, "inside")      # 75 + 60 > 88
    assert not bad["fits"] and "do not fit" in bad["why"]


def test_inside_rod_plate_longhand():
    ip = inside_rod_plate(48.971 / 4, 46.0, 80.0, 300.0, 355.0)
    assert ip["b_eff"] == pytest.approx(86.0) and ip["t_req"] == pytest.approx(9.055, abs=1e-3)
    ip2 = inside_rod_plate(48.971 / 4, 41.0, 65.0, 120.0, 355.0)                                # the flanges cap it
    assert ip2["b_side"] == 120.0 and ip2["t_req"] == pytest.approx(math.sqrt(4 * 12242.75 * 41 / (0.9 * 355 * 60)), rel=1e-9)
    assert inside_rod_plate(0.0, 41.0, 65.0, 300.0, 355.0)["t_req"] == 0.0


def test_anchor_reinforcement_and_interaction_longhand():
    ar = anchor_reinforcement(64.769, 500.0, 30.0)
    assert (ar["hairpins"], ar["bar"]) == (1, 12.0) and ar["As_req"] == pytest.approx(172.7, abs=0.05)
    assert ar["As"] == pytest.approx(226.2, abs=0.05) and ar["phiVn"] == pytest.approx(84.823, abs=1e-3)
    assert ar["ld"] == 600 and development_length(12, 500, 30) == pytest.approx(599.9, abs=0.1)
    assert anchor_reinforcement(1000.0, 500.0, 30.0) is None                  # beyond 4 hairpins of T20
    assert interaction_17_8(0.542, 44.12 / 84.823)[0] == pytest.approx(0.885, abs=1e-3)
    assert interaction_17_8(0.9, 0.15) == (0.9, "17.8.1: Vua <= 0.2 phiVn, full tension")
    assert interaction_17_8(0.1, 0.7)[0] == 0.7


def test_hairpins_do_not_fix_a_pryout_failure():
    def chk(rows_v):
        return SimpleNamespace(tension=[("17.6.1 steel strength", 100.0, 0.1)], shear=rows_v, Nua=10.0, Vua=60.0, phiNn=100.0)
    only_breakout = [("17.7.1 steel strength", 120.0, 0.5), ("17.7.2 concrete breakout", 40.0, 1.5), ("17.7.3 concrete pryout", 90.0, 0.67)]
    with_pryout = [("17.7.1 steel strength", 120.0, 0.5), ("17.7.2 concrete breakout", 40.0, 1.5), ("17.7.3 concrete pryout", 50.0, 1.2)]
    st = BaseSettings()
    assert _with_reinforcement([({"name": "c"}, chk(only_breakout))], st) is not None
    assert _with_reinforcement([({"name": "c"}, chk(with_pryout))], st) is None


def test_no_pedestal_plate_designed_anchors_not_evaluated():
    r = design_base(_joint(), SEC, "S355", BaseSettings())
    assert r["status"] == "PLATE DESIGNED - ANCHORS NOT EVALUATED" and any("pedestal" in m for m in r["missing"])
    assert WASHER_NOTE in r["notes"] and r["rod"]["label"] == "M20" and r["plate_grade"] == "S355JR"
    assert r["anchor_type"].startswith("headed") and r["anchor_grade_source"]["checked_against_source"] is False
    upl = next(c for c in r["cases"] if c["name"] == "max uplift")
    assert upl["T_anchor"] == pytest.approx(48.971) and upl["inside_plate"]["t_req"] == pytest.approx(9.055, abs=1e-3)
    a = next(x for x in r["anchors"] if x["case"] == "max uplift")
    modes = {m["mode"]: m for m in a["modes"]}
    assert set(modes) == {"17.6.1 steel strength", "17.7.1 steel strength"}
    assert modes["17.6.1 steel strength"]["U"] == pytest.approx(48.971 / 254.80, abs=1e-4)
    sh = next(x for x in r["anchors"] if x["case"] == "max shear")
    assert {m["mode"]: m for m in sh["modes"]}["17.7.1 steel strength"]["U"] == pytest.approx(64.769 / 112.896, abs=1e-4)
    assert "NOT EVALUATED" in a["status"] and a["interaction"] is None
    json.dumps(r, allow_nan=False)


def test_small_pedestal_anchor_reinforcement_first():
    r = design_base(_joint(), SEC, "S355", BaseSettings(pedestal=SMALL))
    assert r["status"] == "DESIGNED WITH ANCHOR REINFORCEMENT - DEVELOPMENT NOT EVALUATED"
    assert r["rod"]["label"] == "M20" and r["hef"] == 300
    ar = r["anchor_reinforcement"]
    assert (ar["hairpins"], ar["bar"]) == (1, 12.0) and ar["phiVn"] == pytest.approx(84.823, abs=1e-3)
    u = next(c for c in ar["cases"] if c["case"] == "max uplift")
    assert u["interaction"] == pytest.approx(0.885, abs=1e-3)
    assert any("developed" in m for m in r["missing"])                       # the development is stated, never a pass
    # negative control: reinforcement switched off → FAILS, naming shear breakout and the reinforcement first
    off = design_base(_joint(), SEC, "S355", BaseSettings(pedestal=SMALL, anchor_reinforcement=False))
    assert off["status"] == "FAILS" and any("shear breakout" in f and f.split(": ", 1)[1].startswith("anchor reinforcement") for f in off["fixes"])
    json.dumps(r, allow_nan=False)


def test_not_evaluated_cases():
    shallow = design_base(_joint(), SEC, "S355", BaseSettings(pedestal={"along_d": 900, "across": 600, "depth": 350}))
    assert shallow["status"] == "NOT EVALUATED" and "300" in shallow["missing"][0]
    r = design_base(_joint(status="NOT EVALUATED"), SEC, "S355", BaseSettings())
    assert r["status"] == "NOT EVALUATED" and r.get("rod") is None
    assert design_base(_joint(), SEC, "S690", BaseSettings())["status"] == "NOT EVALUATED"
    for bad in ({"layout": "middle"}, {"anchor_grade": "5.6"}, {"pedestal": {"along_d": 600}}, {"concrete": "C20"},
                {"anchor_type": "hooked"}, {"hef_step": 0}):
        with pytest.raises(ValueError):
            BaseSettings.from_dict(bad)


def test_st37_plate_from_the_ecp_values():
    r = design_base(_joint(), SEC, "St 37", BaseSettings())
    assert r["plate_grade"] == "St 37" and r["status"] == "PLATE DESIGNED - ANCHORS NOT EVALUATED"
    upl = next(c for c in r["cases"] if c["name"] == "max uplift")
    # Fy 2.40 t/cm² × 98.0665 = 235.36 MPa: t = √(4 × 12 242.75 × 46 / (0.9 × 235.36 × 86)) = 11.120 mm
    assert upl["inside_plate"]["t_req"] == pytest.approx(math.sqrt(4 * 12242.75 * 46 / (0.9 * 235.36 * 86)), rel=1e-6)


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
    sm = building_bases(jr, out, BaseSettings(pedestal=SMALL))
    # interior frames (thrust 64.8 kN): hairpins; end frames (35.5 kN) and wind columns pass without
    assert sm["counts"] == {"DESIGNED": 10, "DESIGNED WITH ANCHOR REINFORCEMENT - DEVELOPMENT NOT EVALUATED": 6}
    js = {j["id"]: j for j in jr["joints"]}
    for x in sm["bases"]:
        if x["type"] == "base":
            u = next(c for c in x["cases"] if c["name"] == "max uplift")
            assert u["T_anchor"] == pytest.approx(js[x["joint"]]["forces"]["uplift"]["value"], abs=1e-3)
            assert x["rod"]["d"] >= 20 and x["hef"] >= 300                              # the main-frame minimums
        else:
            assert x["rod"]["d"] >= 16 and x["hef"] >= 150
    json.dumps(sm, allow_nan=False)
