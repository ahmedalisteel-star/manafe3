# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 4: the welds (engine/connections/welds.py). Independent values written out longhand below; NOT recomputed
by the code under test. E70: φ 0.75 × 0.60 × 482 × 0.707 = 153.348 N/mm per mm of leg per line (× 1.5 at θ 90° when the
directional increase is allowed). S355JR in the library: Fy 355, Fu 490 MPa up to 40 mm.

    STRENGTHS   5 mm: 766.74 N/mm (θ 0), 1150.11 (θ 90); base metal 6 mm web: 0.45 × 490 × 6 = 1323.0, a double fillet on
                it: 661.5 per line; a 16 mm stiffener pulled across (J4.1): 0.9 × 355 × 16 / 2 = 2556.0 per line
    q = VQ/I    d 495, tw 6, 200 × 10: I = 288 844 270.8, Q = 485 000 → V 217 kN: q = 364.37 N/mm
                unequal (250 × 12 top, 200 × 10 bottom, hw 475): d 497, ȳ = 278.774, I = 341 450 115.3,
                Q_top = 636 678.3, Q_bot = 547 547.8 → V 200 kN: q_top 372.93, q_bot 320.72
    LOCAL       lb = 8 + 5 (10 + 5) = 83 mm; purlin 9 kN → 108.43 N/mm; flange brace 2 % × 200 / 0.485 = 8.247 kN → 99.37;
                √(364.37² + 108.43² + 99.37²) = 392.93 → one side 5 mm, U 0.5125
                concurrency (two combinations): A V 217 constant (w 0) → 364.37; B V 50 → 0 over 1000 mm (w 0.05 kN/mm,
                purlins at 1185.99 → P 59.30 kN → 714.43 N/mm; q 83.95) → 719.37; max-with-max would be 802.0
    ONE / TWO   900 → one side 6 mm (920.09), U 0.9782; 1000 → 8 mm (1226.79), U 0.8151; 1240 → both sides, 620 per line
                (5 mm, the web base metal 661.5 governs), U 0.9373; 1300 → both, 650 per line, U 0.9826; 1400 > 1323 → FAILS
                "thicker web"; with one_side_max_leg 5: 900 → both sides 450 per line, U 0.6803
    END ZONE    0.9 × 0.6 × 355 × 6 = 1150.2 → 575.1 per line → 5 mm, U 575.1 / 661.5 = 0.8694
    BASE        column 489.2 × 200 × 10, web 6: flange lines 2 (2 × 200 − 6) = 788, web lines 2 × 469.2 = 938.4, Σ 1726.4;
                uplift 100: 57.92; strong 65 on the web: 69.27 → 90.29; weak 20 on the flanges: 25.38 → 63.24;
                web 5 mm: base metal 661.5 governs, U 0.1365; flanges: 63.24 / 766.74 = 0.0825; uplift 1200 → 695.09 > 661.5
                → FAILS; tp 55 > 50 → NOT EVALUATED
    BRACE       T 21.075 kN, 6000 × 5900 bay: T cos α = 15.027, T sin α = 14.777; frame Ry 30 (compression) in the SAME
                combination → Pu = 30 − 14.777 = 15.223
    LUG         f'c 25, B 200, h 100: φVbrg = 0.65 × 1.7 × 25 × 200 × 100 = 552.5 kN; Vu 65: Mu = 65 (50 + 50) = 6.5 kN·m,
                t ≥ √(4 × 6.5e6 / (0.9 × 355 × 200)) = 20.17 → 22; weld: 65 000 / 400 = 162.5, 6.5e6 / (22 × 200) = 1477.27
                → 1486.18 → 10 mm (1533.48), U 0.9692; Ψ tension Pu −40, 4 × M20 4.6 (Nsa 400 × 245 = 98 kN): 0.8980;
                compression Pu 100 on 400 × 300: 1.1333; Vu 2000 > 0.65 × 1.7 × 25 × 200 × 300 = 1657.5 → FAILS
    STIFFENERS  interior knee: Rst 601.4 + diagonal 153.9 = 755.3, each 377.65 kN; contact ts ≥ 377 650 / (0.9 × 355 × 40)
                = 29.55; to the flange 377 650 / 2 / 40 = 4720.62 per line: a fillet would need 20.52 mm → CJP (base metal
                0.45 × 355 × 30 = 4792.5, U 0.985); to the web (244.6 − 10 − 20 = 214.6) 879.89 → 6 mm, U 0.9563
                end knee: Rst 319.98, each 159.99: contact 12.52 → 15; flange 1999.88 → 10 mm (2300.22), U 0.8694; web
                372.76 → 5 mm (minimum)
    DIAGONAL    612.3 × 355 = 217.37 kN, each 108.68, per end line 905.69 → 5 mm (1150.11), U 0.7875; As 2000 on t 30:
                2958.33 per line → a fillet would need 12.86 → CJP
    DOUBLER     138.56 / 489.2 = 283.24 → 5 mm; 1100 kN → 2248.57, needs 14.66 → CJP (base 0.45 × 490 × 12 = 2646)
    EP STIFF.   ts 12: into the plate 0.45 × 355 × 12 = 1917 per line → 10 mm (base metal governs, U 1.0); along the flange
                0.3 × 355 × 12 = 1278 → 10 mm (base 1323, U 0.966); ts 20: 3195 per line, needs 13.89 → CJP
"""

import json
import math

import pytest

from engine.connections import welds as W
from engine.connections.welds import (CJP, WeldSettings, base_metal, base_weld, body_weld, column_stiffener_welds,
                                      diagonal_welds, doubler_welds, end_zone_weld, endplate_stiffener_welds,
                                      flange_web_member, flange_web_q, lug_bearing_factor, lug_needed, pair_brace_with_frame,
                                      shear_lug, spread_length, weld_metal)

ST = WeldSettings()
SEC = {"hw": 475.0, "tw": 6.0, "bf_top": 200.0, "tf_top": 10.0, "bf_bot": 200.0, "tf_bot": 10.0}
COL = {"d": 489.2, "tw": 6.0, "tf": 10.0, "bf": 200.0}


def test_strengths_by_hand():
    assert weld_metal(5) == pytest.approx(766.74, abs=0.01) and weld_metal(5, 90) == pytest.approx(1150.11, abs=0.01)
    assert weld_metal(5, 90, directional=False) == pytest.approx(766.74, abs=0.01)           # base weld: no increase
    assert base_metal(6, "S355JR") == pytest.approx(1323.0, abs=0.01)
    assert base_metal(6, "S355JR", 2) == pytest.approx(661.5, abs=0.01)                      # shared by a double fillet
    assert W.base_metal_tension(16, "S355JR", 2) == pytest.approx(2556.0, abs=0.01)
    for bad in ({"shear_fix": "x"}, {"shop_min_leg": 0}, {"one_side_max_leg": 14}, {"nope": 1}, {"electrode": "E90"}):
        with pytest.raises(ValueError):
            WeldSettings.from_dict(bad)


def test_shear_flow_by_hand():
    q = flange_web_q(SEC, 217.0)
    assert q["I"] == pytest.approx(288844270.8, abs=1) and q["Q_top"] == pytest.approx(485000.0)
    assert q["q"] == pytest.approx(364.37, abs=0.01) and q["q_top"] == pytest.approx(q["q_bot"])
    u = flange_web_q({**SEC, "bf_top": 250.0, "tf_top": 12.0}, -200.0)                          # the sign does not matter
    assert u["I"] == pytest.approx(341450115.3, abs=1) and u["Q_top"] == pytest.approx(636678.3, abs=0.1)
    assert u["q_top"] == pytest.approx(372.93, abs=0.01) and u["q_bot"] == pytest.approx(320.72, abs=0.01)
    assert u["q"] == pytest.approx(372.93, abs=0.01)


def test_local_loads_and_body_weld_by_hand():
    lb = spread_length(8.0, 10.0, ST)
    assert lb == 83.0 and W.local_flow(9.0, lb) == pytest.approx(108.43, abs=0.01)
    Ffb = 0.02 * 200.0 / 0.485
    flow = math.sqrt(364.37 ** 2 + W.local_flow(9.0, lb) ** 2 + W.local_flow(Ffb, lb) ** 2)
    assert W.local_flow(Ffb, lb) == pytest.approx(99.37, abs=0.01) and flow == pytest.approx(392.93, abs=0.01)
    w = body_weld(flow, SEC, "S355JR", ST)
    assert w["sides"].startswith("one side") and w["leg"] == 5.0 and w["U"] == pytest.approx(0.5125, abs=1e-4)
    six = body_weld(900.0, SEC, "S355JR", ST)
    assert (six["sides"][:8], six["leg"]) == ("one side", 6.0) and six["U"] == pytest.approx(0.9782, abs=1e-4)
    eight = body_weld(1000.0, SEC, "S355JR", ST)
    assert (eight["sides"][:8], eight["leg"]) == ("one side", 8.0) and eight["U"] == pytest.approx(0.8151, abs=1e-4)
    two = body_weld(1240.0, SEC, "S355JR", ST)                                              # 8 mm one side: 1226.79 < 1240
    assert two["sides"].startswith("both") and two["leg"] == 5.0 and two["governs"] == "base metal"
    assert two["U"] == pytest.approx(0.9373, abs=1e-4)
    assert body_weld(1300.0, SEC, "S355JR", ST)["U"] == pytest.approx(0.9826, abs=1e-4)
    # negative control: above the web base metal 0.45 Fu tw = 1323 two sides cannot help → FAILS, thicker web
    f = body_weld(1400.0, SEC, "S355JR", ST)
    assert f["type"] == "FAILS" and f["ok"] is False and f["fixes"] == ["thicker web"] and f["U"] == pytest.approx(1.0582, abs=1e-4)
    s5 = body_weld(900.0, SEC, "S355JR", WeldSettings(one_side_max_leg=5.0))                 # the setting
    assert s5["sides"].startswith("both") and s5["U"] == pytest.approx(0.6803, abs=1e-4)
    z = end_zone_weld(SEC, "S355JR", ST)
    assert z["flow_total"] == pytest.approx(1150.2) and z["leg"] == 5.0 and z["sides"] == "both sides"
    assert z["U"] == pytest.approx(0.8694, abs=1e-4)


def test_flange_web_concurrent_combination():
    m = {"id": "T-RA", "role": "rafter", "section": {"segments": [{"length": 1000.0, "hw_start": 475.0, "hw_end": 475.0,
         "tw": 6.0, "bf_top": 200.0, "tf_top": 10.0, "bf_bot": 200.0, "tf_bot": 10.0}]}}
    stations = [("A", [(0.0, 217.0, 0.0), (1000.0, 217.0, 0.0)]), ("B", [(0.0, 50.0, 0.0), (1000.0, 0.0, 0.0)])]
    local = {"t_cleat": 8.0, "spacing": 1185.99, "flange_braces": False}
    r = flange_web_member(m, stations, "S355JR", ST, local, [{"joint": "K", "at": 0.0}])
    g = r["segments"][0]["governing"]
    assert g["combo"] == "B" and g["flow"] == pytest.approx(719.37, abs=0.02)
    assert g["flow"] < 802.0 - 1.0                          # never the largest V (A) with the largest local load (B)
    assert r["segments"][0]["weld"]["leg"] == 5.0 and r["status"] == "DESIGNED"
    assert r["end_zones"][0]["from"] == 0.0 and r["end_zones"][0]["to"] == 495.0 and W.BUTT_SPLICE_NOTE in r["notes"]
    # without the local loads only q counts: combination A, 364.37
    r0 = flange_web_member(m, stations, "S355JR", ST, {"t_cleat": 8.0, "spacing": None, "flange_braces": False}, [])
    assert r0["segments"][0]["governing"]["combo"] == "A" and r0["segments"][0]["governing"]["flow"] == pytest.approx(364.37, abs=0.01)


def test_base_weld_by_hand():
    cases = [{"name": "uplift", "Pu": -100.0, "V_strong": 65.0, "V_weak": 20.0}]
    r = base_weld(COL, 20.0, cases, "S355JR", ST)
    assert r["lengths"] == {"flanges": 788.0, "web": 938.4, "total": 1726.4}
    c = r["cases"][0]
    assert (c["uplift_flow"], c["web_shear_flow"], c["flange_shear_flow"], c["web"], c["flange"]) == \
        pytest.approx((57.92, 69.27, 25.38, 90.29, 63.24), abs=0.01)
    assert r["status"] == "DESIGNED" and r["leg"] == 5.0 and r["web"]["governs"] == "base metal"
    assert r["web"]["U"] == pytest.approx(0.1365, abs=1e-4) and r["flanges"]["U"] == pytest.approx(0.0825, abs=1e-4)
    assert any("50 mm, unmilled" in n for n in r["notes"])
    # compression is by bearing: a compression case puts nothing on the weld but its shear
    comp = base_weld(COL, 20.0, [{"name": "c", "Pu": 500.0, "V_strong": 0.0, "V_weak": 0.0}], "S355JR", ST)
    assert comp["cases"][0]["web"] == 0.0 and comp["leg"] == 5.0
    assert base_weld(COL, 50.0, cases, "S355JR", ST)["status"] == "DESIGNED"                    # 50 mm still covered
    big = base_weld(COL, 55.0, cases, "S355JR", ST)
    assert big["status"] == "NOT EVALUATED" and "M2.6" in big["missing"][0] and "leg" not in big
    f = base_weld(COL, 20.0, [{"name": "u", "Pu": -1200.0, "V_strong": 0.0, "V_weak": 0.0}], "S355JR", ST)
    assert f["status"] == "FAILS" and f["cases"][0]["web"] == pytest.approx(695.09, abs=0.01) and "thicker plate" in f["why"]


def test_brace_pairing_same_combination_only():
    cos_a, sin_a = 6000 / math.hypot(6000, 5900), 5900 / math.hypot(6000, 5900)
    r = pair_brace_with_frame({"C1": 21.075, "C2": 10.0}, {"C1": 30.0, "C3": -50.0}, cos_a, sin_a)
    assert len(r["cases"]) == 1 and r["unmatched"] == ["C2"] and "status" not in r
    c = r["cases"][0]
    assert c["combo"] == "C1" and c["V_weak"] == pytest.approx(15.027, abs=1e-3) and c["Pu"] == pytest.approx(15.223, abs=1e-3)
    # negative control: the largest frame uplift (C3, −50) is never paired with a brace force from another combination
    assert all(x["Pu"] > -50.0 for x in r["cases"])
    none = pair_brace_with_frame({"LRFD: bracing": 21.075}, {"LRFD: 0.9D+1.0WA+L": -24.5}, cos_a, sin_a)
    assert none["cases"] == [] and none["status"] == "NOT EVALUATED" and "same combination" in none["why"]


def test_shear_lug_by_hand():
    r = shear_lug(65.0, 0.0, 200.0, 20.0, 25.0, "S355JR", ST)
    assert r["height"] == 100.0 and r["bearing"]["phiVbrg"] == pytest.approx(552.5, abs=0.01)
    assert r["Mu"] == pytest.approx(6.5) and r["t_req"] == pytest.approx(20.17, abs=0.01) and r["t"] == 22.0
    w = r["weld"]
    assert (w["shear_flow"], w["moment_flow"], w["flow"]) == pytest.approx((162.5, 1477.27, 1486.18), abs=0.01)
    assert w["leg"] == 10.0 and w["U"] == pytest.approx(0.9692, abs=1e-4)
    # the breakout is NOT EVALUATED until the user sends ACI 17.11.3 — never a pass
    assert r["breakout"]["status"] == "NOT EVALUATED" and r["breakout"]["U"] == math.inf
    assert r["status"] == "DESIGNED - BREAKOUT NOT EVALUATED" and r["verified"] is False
    assert lug_bearing_factor(-40.0, 4, 98.0, 1.0, 25.0) == pytest.approx(0.8980, abs=1e-4)
    assert lug_bearing_factor(100.0, 4, 98.0, 120000.0, 25.0) == pytest.approx(1.1333, abs=1e-4)
    assert lug_bearing_factor(1e6, 4, 98.0, 120000.0, 25.0) == 2.0
    assert shear_lug(2000.0, 0.0, 200.0, 20.0, 25.0, "S355JR", ST)["status"] == "FAILS"          # > 1657.5 at h 300
    assert shear_lug(65.0, -40.0, 200.0, 20.0, 25.0, "S355JR", ST)["status"] == "NOT EVALUATED"  # no Nsa for tension
    # f'c is the base-plate step's concrete, not a constant: C30/37 → 30 MPa → bearing 663.0 kN
    assert shear_lug(65.0, 0.0, 200.0, 20.0, 30.0, "S355JR", ST)["bearing"]["phiVbrg"] == pytest.approx(663.0, abs=0.01)
    assert lug_needed({"status": "FAILS", "fixes": ["anchor reinforcement (hairpins or ties) first ... breakout"]})
    assert not lug_needed({"status": "DESIGNED"}) and not lug_needed({"status": "FAILS", "fixes": ["thicker plate"]})


def test_column_stiffener_welds_by_hand():
    # Building 1 interior knee: Rst 601.4 + the diagonal's horizontal part 153.9; ts 30 (the contact needs 29.55)
    r = column_stiffener_welds(601.4, 153.9, 60, 30, 489.2 / 2 - 10, 10, 6, "S355JR", ST)
    assert r["force_pair"] == pytest.approx(755.3) and r["force_each"] == pytest.approx(377.65)
    fl, wb = r["to_flange"], r["to_web"]
    assert fl["flow"] == pytest.approx(4720.62, abs=0.01) and fl["type"] == CJP and "12 mm" in fl["why"]
    assert fl["base_metal"] == pytest.approx(4792.5) and fl["U"] == pytest.approx(0.985, abs=1e-3)
    assert r["length_web"] == 214.6 and wb["flow"] == pytest.approx(879.89, abs=0.01) and wb["leg"] == 6.0
    assert wb["U"] == pytest.approx(0.9563, abs=1e-4) and r["status"] == "DESIGNED"
    # negative control: the end knee (Rst 319.98, no diagonal) stays a fillet — 10 mm to the flange, 5 mm to the web
    e = column_stiffener_welds(319.98, 0.0, 60, 15, 489.2 / 2 - 10, 10, 6, "S355JR", ST)
    assert e["to_flange"]["flow"] == pytest.approx(1999.88, abs=0.01) and e["to_flange"]["leg"] == 10.0
    assert e["to_flange"]["U"] == pytest.approx(0.8694, abs=1e-4)
    assert e["to_web"]["flow"] == pytest.approx(372.76, abs=0.01) and e["to_web"]["leg"] == 5.0
    # no force: the minimum legs (J2.4 / shop_min_leg), never zero
    z = column_stiffener_welds(0.0, 0.0, 60, 12, 234.6, 10, 6, "S355JR", ST)
    assert z["to_flange"]["leg"] == 5.0 == z["to_web"]["leg"] and z["to_flange"]["sized_by"] == "minimum"
    # a 16 mm stiffener cannot take the interior-knee force across 40 mm: FAILS, never a pass
    assert column_stiffener_welds(601.4, 153.9, 60, 16, 234.6, 10, 6, "S355JR", ST)["status"] == "FAILS"


def test_diagonal_doubler_endplate_stiffener_welds_by_hand():
    d = diagonal_welds(612.3, 355.0, 60, 12, 10, "S355JR", ST)
    assert d["force_pair"] == pytest.approx(217.37, abs=0.01) and d["ends"]["flow"] == pytest.approx(905.69, abs=0.01)
    assert d["ends"]["leg"] == 5.0 and d["ends"]["U"] == pytest.approx(0.7875, abs=1e-4) and d["status"] == "DESIGNED"
    dc = diagonal_welds(2000.0, 355.0, 60, 30, 20, "S355JR", ST)
    assert dc["ends"]["flow"] == pytest.approx(2958.33, abs=0.01) and dc["ends"]["type"] == CJP
    db = doubler_welds(138.56, 489.2, 12, 10, "S355JR", ST)
    assert db["flow"] == pytest.approx(283.24, abs=0.01) and db["flange_edges"]["leg"] == 5.0 and db["status"] == "DESIGNED"
    dbc = doubler_welds(1100.0, 489.2, 12, 20, "S355JR", ST)
    assert dbc["flow"] == pytest.approx(2248.57, abs=0.01) and dbc["flange_edges"]["type"] == CJP
    assert dbc["flange_edges"]["base_metal"] == pytest.approx(2646.0)
    e = endplate_stiffener_welds(70, 121.2, 12, 18, 10, "S355JR", ST)
    tp, tf = e["to_end_plate"], e["to_beam_flange"]
    assert tp["flow"] == pytest.approx(1917.0) and tp["leg"] == 10.0 and tp["U"] == pytest.approx(1.0, abs=1e-4)
    assert tf["flow"] == pytest.approx(1278.0) and tf["leg"] == 10.0 and tf["U"] == pytest.approx(0.966, abs=1e-3)
    assert e["status"] == "DESIGNED" and "reference only" in e["reference"]
    e20 = endplate_stiffener_welds(70, 121.2, 20, 25, 20, "S355JR", ST)
    assert e20["to_end_plate"]["flow"] == pytest.approx(3195.0) and e20["to_end_plate"]["type"] == CJP


@pytest.mark.slow
def test_sized_building_1_welds():
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.baseplates import BaseSettings, building_bases
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
    assert ep["counts"] == {"DESIGNED": 25}
    for x in (x for x in ep["joints"] if x["type"] == "knee"):
        cs = x["column_side"]
        t, p = cs["transverse_stiffeners"], cs["panel_zone"]
        dg = p.get("diagonal_stiffener")
        F = t["Rst"] + ((p["Vu"] - p["phiVpanel"]) / 0.9 if dg else 0.0)                       # As_req Fy cos θ = ΔV / φ
        assert t["weld"]["force_pair"] == pytest.approx(F, abs=0.05) and t["weld"]["status"] == "DESIGNED"
        need = F / 2 * 1000 / (0.9 * 355 * (t["bs"] - 20))
        assert t["t"] == min(s for s in (12.0, 15.0, 16.0, 18.0, 20.0, 22.0, 25.0, 30.0) if s >= max(need, t["bs"] / 16, 5.0))
        if dg:
            assert t["t"] == 30.0 and t["weld"]["to_flange"]["type"] == CJP and t["weld"]["to_web"]["leg"] == 6.0
            assert dg["weld"]["ends"]["leg"] == 5.0
    bs = building_bases(jr, out, BaseSettings(concrete="C25/30"))
    r = W.building_welds(jr, out, an, bs, base_settings=BaseSettings(concrete="C25/30"))
    json.dumps(r, allow_nan=True)
    assert r["banner"].startswith("NOT FOR ISSUE") and r["concrete_fc"] == 25.0 and W.BUTT_SPLICE_NOTE in r["notes"]
    assert r["settings"] == {k: getattr(ST, k) for k in WeldSettings.__dataclass_fields__}
    assert r["counts"]["flange_web"] == {"DESIGNED": 20}
    for m in r["flange_web"]:
        for s in m["segments"]:
            g = s["governing"]
            q = flange_web_q(_sec_from(g), g["V"])["q"]
            assert g["q"] == pytest.approx(q, abs=0.01) and g["flow"] >= g["q"] - 1e-6
            assert g["lb"] == 83.0 and s["weld"]["sides"].startswith("one side") and s["weld"]["leg"] == 5.0
        assert m["end_zones"] and all(z["weld"]["sides"] == "both sides" for z in m["end_zones"])
    braced = [b for b in r["bases"] if b.get("brace_case")]
    assert len(braced) == 8 and all(b["status"] == "DESIGNED - BRACE CASE NOT EVALUATED" for b in braced)
    for b in braced:
        bc = b["brace_case"]
        assert bc["status"] == "NOT EVALUATED" and bc["cases"] == []
        assert bc["V_weak"] == pytest.approx(bc["T"] * bc["cos_a"], abs=1e-3) and bc["T_sin_a"] == pytest.approx(bc["T"] * bc["sin_a"], abs=1e-3)
    assert all(b["status"] == "DESIGNED" and b["leg"] == 5.0 for b in r["bases"] if not b.get("brace_case"))
    assert not any("shear_lug" in b for b in r["bases"])                       # anchors not failing (no pedestal given)


def _sec_from(g):
    """The governing station's section back from its depth (one-segment tapers: 200 × 10 flanges, tw 6 in building 1)."""
    return {"hw": g["d"] - 20.0, "tw": 6.0, "bf_top": 200.0, "tf_top": 10.0, "bf_bot": 200.0, "tf_bot": 10.0}
