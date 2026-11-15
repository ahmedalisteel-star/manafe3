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
    STIFFENERS  (review 2026-11-12) bs = floor5((200 − 6)/2 − 5) = 90; the load path at building 1's interior knee
                (Puf 701.25, Rst 601.41, φVpanel 562.67): F = max(Rst, ΔV 138.58) = 601.41; the flange puts 701.25 − 601.41
                = 99.84 straight into the web; the stiffener web welds 562.67 − 99.84 = 462.83; the corner 138.58;
                contact 300.705 kN across 70 mm: ts ≥ 13.45 → 15; to the flange 300 705 / 2 / 70 = 2147.89 per line →
                10 mm (2300.22; base 0.45 × 355 × 15 = 2396.25), U 0.9338; FULL DEPTH (user 2026-11-15): web weld
                489.2 − 2 × 10 − 2 × 20 = 429.2: 462 830 / 4 / 429.2 = 269.59 → 5 mm, U 0.3516; the 6 mm column web, both
                faces: 462 830 / 429.2 = 1078.36 ≤ min(0.6 × 355 × 6 = 1278, 0.45 × 490 × 6 = 1323), U 0.8438
                end knee (F 319.98, all to the web): flange 1142.79 → 5 mm, U 0.9936; web 745.53, U 0.5834
                negative control, the half-depth option (214.6): 539.18 per line (U 0.7032); the web 2156.71 → U 1.6876
                FAILS "doubler or thicker web" (a 16 mm web: 3408, U 0.6328); end knee 1491.05 → U 1.1667 FAILS
                CJP control: F 1200 on ts 30: 4285.71 per line, a fillet would need 18.63 → CJP (base 4792.5)
    DIAGONAL    612.3 × 355 = 217.37 kN, bs 90: per end line 603.81 → 5 mm, U 0.525; the corner 138.58 / 0.7084 = 195.62
                < 217.37; a corner of 400 kN governs: 1111.11 per line → 5 mm, U 0.9661; As 2000 on t 30, bs 60:
                2958.33 per line → a fillet would need 12.86 → CJP
    WIND COLUMN BU 300 × 6, 150 × 8 (d 316, Q 184 800, I 70 431 200), L 6000, w 4.6564 kN/m: end V = 13.9692 → q 36.65;
                gable girts at 1250 mm: P = 5.8205 kN over lb = 8 + 5 (8 + 5) = 73 → 79.73; √(36.65² + 79.73²) = 87.75 at
                the ends (M 0); mid-height: M 20.9538, flange brace 2 % × 20.9538 / 0.308 = 1.3606 kN → 18.64, with the
                girt 81.88 < 87.75
    END RAFTER  y → x along the member: x = |y − y_start| √1.01 (6000 → 6029.93); V 50 kN on 200 × 10 / 475 × 6 → 83.96
    DOUBLER     138.56 / 489.2 = 283.24 → 5 mm; 1100 kN → 2248.57, needs 14.66 → CJP (base 0.45 × 490 × 12 = 2646)
    EP STIFF.   ts 12: into the plate 0.45 × 355 × 12 = 1917 per line → 10 mm (2300.22), U 0.8334 — the base metal
                "develops plate (by definition)"; along the flange
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
    # Building 1 interior knee, bs 90, ts 15, FULL DEPTH (469.2 − 2 × 20 = 429.2): F 601.41 across the flange, 462.83
    # into the web: 462 830 / 4 / 429.2 = 269.59 per line → 5 mm (U 0.3516); the web 1078.36 / 1278 = 0.8438 → designed
    f = column_stiffener_welds(601.41, 462.83, 90, 15, 469.2, 10, 6, "S355JR", ST)
    assert f["length_web"] == 429.2 and f["to_web"]["flow"] == pytest.approx(269.59, abs=0.01) and f["to_web"]["leg"] == 5.0
    assert f["to_web"]["U"] == pytest.approx(0.3516, abs=1e-4) and f["web_base_metal"]["flow_total"] == pytest.approx(1078.36, abs=0.01)
    assert f["web_base_metal"]["U"] == pytest.approx(0.8438, abs=1e-4) and f["status"] == "DESIGNED"
    fe = column_stiffener_welds(319.98, 319.98, 90, 12, 469.2, 10, 6, "S355JR", ST)              # end knee: 745.53, U 0.5834
    assert fe["web_base_metal"]["flow_total"] == pytest.approx(745.53, abs=0.01) and fe["web_base_metal"]["U"] == pytest.approx(0.5834, abs=1e-4)
    assert fe["to_web"]["flow"] == pytest.approx(186.38, abs=0.01) and fe["status"] == "DESIGNED"
    # negative control, the HALF-DEPTH option (234.6 − 20 = 214.6, one clip): the same forces FAIL the 6 mm web
    r = column_stiffener_welds(601.41, 462.83, 90, 15, 489.2 / 2 - 10, 10, 6, "S355JR", ST, clips=1)
    fl, wb, wbm = r["to_flange"], r["to_web"], r["web_base_metal"]
    assert r["length_flange"] == 70 and r["length_web"] == 214.6
    assert fl["flow"] == pytest.approx(2147.89, abs=0.01) and fl["leg"] == 10.0 and fl["U"] == pytest.approx(0.9338, abs=1e-4)
    assert fl["base_metal"] == pytest.approx(2396.25)
    assert wb["flow"] == pytest.approx(539.18, abs=0.01) and wb["leg"] == 5.0 and wb["U"] == pytest.approx(0.7032, abs=1e-4)
    # the 6 mm column web under the welds on both faces: FAILS, fix "doubler or thicker web"
    assert wbm["flow_total"] == pytest.approx(2156.71, abs=0.01) and wbm["capacity"] == pytest.approx(1278.0)
    assert (wbm["yield"], wbm["rupture"]) == pytest.approx((1278.0, 1323.0)) and wbm["U"] == pytest.approx(1.6876, abs=1e-4)
    assert r["status"] == "FAILS" and r["fixes"] == ["doubler or thicker web"] and "both faces" in r["why"]
    # negative control: a 16 mm web takes it (3408 N/mm, U 0.6328)
    r16 = column_stiffener_welds(601.41, 462.83, 90, 15, 489.2 / 2 - 10, 10, 16, "S355JR", ST, clips=1)
    assert r16["status"] == "DESIGNED" and r16["web_base_metal"]["U"] == pytest.approx(0.6328, abs=1e-4)
    # the end knee: 5 mm to the flange, the web still FAILS (1491.05 > 1278)
    e = column_stiffener_welds(319.98, 319.98, 90, 12, 489.2 / 2 - 10, 10, 6, "S355JR", ST, clips=1)
    assert e["to_flange"]["flow"] == pytest.approx(1142.79, abs=0.01) and e["to_flange"]["leg"] == 5.0
    assert e["to_flange"]["U"] == pytest.approx(0.9936, abs=1e-4)
    assert e["web_base_metal"]["U"] == pytest.approx(1.1667, abs=1e-4) and e["status"] == "FAILS"
    # negative control to CJP: 1200 kN on a 30 mm stiffener — a fillet would need 18.63 mm
    c = column_stiffener_welds(1200.0, 0.0, 90, 30, 469.2, 10, 16, "S355JR", ST)
    assert c["to_flange"]["flow"] == pytest.approx(4285.71, abs=0.01) and c["to_flange"]["type"] == CJP and c["status"] == "DESIGNED"
    # no force: the minimum legs (J2.4 / shop_min_leg), never zero
    z = column_stiffener_welds(0.0, 0.0, 90, 12, 469.2, 10, 6, "S355JR", ST)
    assert z["to_flange"]["leg"] == 5.0 == z["to_web"]["leg"] and z["to_flange"]["sized_by"] == "minimum"


def test_wind_column_and_end_rafter_flange_web_by_hand():
    L, w = 6000.0, 4.6564
    rows = [(x, w * (L / 2 - x) / 1000.0, w * x * (L - x) / 2e6) for x in [L * k / 20 for k in range(21)]]
    m = {"id": "WF1", "role": "wind_column", "section": {"segments": [{"length": L, "hw_start": 300.0, "hw_end": 300.0,
         "tw": 6.0, "bf_top": 150.0, "tf_top": 8.0, "bf_bot": 150.0, "tf_bot": 8.0}]}}
    local = {"t_cleat": 8.0, "spacing": 1250.0, "flange_braces": True}
    r = flange_web_member(m, [("LRFD C&C inward", rows)], "S355JR", ST, local, [])
    g = r["segments"][0]["governing"]
    assert g["q"] == pytest.approx(36.65, abs=0.01) and g["lb"] == 73.0 and g["P_local"] == pytest.approx(5.8205, abs=1e-3)
    assert g["p_local"] == pytest.approx(79.73, abs=0.01) and g["flow"] == pytest.approx(87.75, abs=0.01) and g["x"] in (0.0, L)
    assert r["segments"][0]["weld"]["leg"] == 5.0 and r["status"] == "DESIGNED" and r["end_zones"] == []
    assert W._spacing([0.0, 1250.0, 2500.0, 3750.0, 5000.0]) == 1250.0
    # end-wall rafter A (y 0 → 12000): the side-B stations are left out, x = y √1.01
    ef = {"results": {"LRFD: c": {"set": "LRFD", "rafter_stations": [[0.0, 0, 50.0, 0.0], [6000.0, 0, 20.0, 30.0],
                                                                     [12000.0, 0, -10.0, 0.0], [18000.0, 0, 99.0, 0.0]]},
                      "ASD: c": {"set": "ASD", "rafter_stations": [[0.0, 0, 999.0, 0.0]]}}}
    er = {"id": "EFRA", "role": "end_rafter", "start": [0.0, 0.0, 6000.0], "end": [0.0, 12000.0, 7200.0],
          "section": {"segments": [{"length": 12000.0 * math.sqrt(1.01), "hw_start": 475.0, "hw_end": 475.0, "tw": 6.0,
                                    "bf_top": 200.0, "tf_top": 10.0, "bf_bot": 200.0, "tf_bot": 10.0}]}}
    st_ = W.end_rafter_stations(ef, er, math.sqrt(1.01))
    assert [c for c, _ in st_] == ["LRFD: c"] and [round(x, 2) for x, _, _ in st_[0][1]] == [0.0, 6029.93, 12059.85]
    rr = flange_web_member(er, st_, "S355JR", ST, {"t_cleat": 8.0, "spacing": None, "flange_braces": False}, [])
    assert rr["segments"][0]["governing"]["flow"] == pytest.approx(83.96, abs=0.01)      # V 50, not the side-B 99


def test_diagonal_doubler_endplate_stiffener_welds_by_hand():
    d = diagonal_welds(612.3, 355.0, 90, 12, 10, "S355JR", ST, corner_axial=195.62)
    assert d["force_pair"] == pytest.approx(217.37, abs=0.01) and d["ends"]["flow"] == pytest.approx(603.81, abs=0.01)
    assert d["ends"]["leg"] == 5.0 and d["ends"]["U"] == pytest.approx(0.525, abs=1e-4) and d["status"] == "DESIGNED"
    k = diagonal_welds(612.3, 355.0, 90, 12, 10, "S355JR", ST, corner_axial=400.0)              # the corner governs
    assert k["force_pair"] == 400.0 and k["ends"]["flow"] == pytest.approx(1111.11, abs=0.01)
    assert k["ends"]["U"] == pytest.approx(0.9661, abs=1e-4)
    dc = diagonal_welds(2000.0, 355.0, 60, 30, 20, "S355JR", ST)
    assert dc["ends"]["flow"] == pytest.approx(2958.33, abs=0.01) and dc["ends"]["type"] == CJP
    db = doubler_welds(138.56, 489.2, 12, 10, "S355JR", ST)
    assert db["flow"] == pytest.approx(283.24, abs=0.01) and db["flange_edges"]["leg"] == 5.0 and db["status"] == "DESIGNED"
    dbc = doubler_welds(1100.0, 489.2, 12, 20, "S355JR", ST)
    assert dbc["flow"] == pytest.approx(2248.57, abs=0.01) and dbc["flange_edges"]["type"] == CJP
    assert dbc["flange_edges"]["base_metal"] == pytest.approx(2646.0)
    e = endplate_stiffener_welds(70, 121.2, 12, 18, 10, "S355JR", ST)
    tp, tf = e["to_end_plate"], e["to_beam_flange"]
    # into the end plate the demand IS the stiffener's design strength: the base metal "develops plate (by definition)"
    # and U is the weld metal's: 1917 / 2300.22 = 0.8334 (not a bare U 1.0)
    assert tp["flow"] == pytest.approx(1917.0) and tp["leg"] == 10.0 and tp["U"] == pytest.approx(0.8334, abs=1e-4)
    assert tp["base_metal"].startswith("develops plate (by definition)")
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
        dV = p["Vu"] - p["phiVpanel"] if dg else 0.0
        F = max(t["Rst"], dV)
        Fw = min(F, p["phiVpanel"] - (p["Vu"] - F))
        assert t["bs"] == 90.0 and t["load_path"]["F_pair"] == pytest.approx(F, abs=0.02)
        assert t["load_path"]["F_web"] == pytest.approx(Fw, abs=0.03) and t["load_path"]["F_corner"] == pytest.approx(F - Fw, abs=0.03)
        need = F / 2 * 1000 / (0.9 * 355 * 70)
        assert t["t"] == min(s for s in (12.0, 15.0, 16.0, 18.0, 20.0) if s >= max(need, 90 / 16, 5.0))
        wbm = t["weld"]["web_base_metal"]
        assert t["length"] == 469.2 and wbm["flow_total"] == pytest.approx(Fw * 1000 / 429.2, abs=0.1) and wbm["ok"]
        assert x["status"] == "DESIGNED" and wbm["U"] == pytest.approx(Fw * 1000 / 429.2 / 1278.0, abs=1e-3)
        if dg:
            assert (t["t"], t["weld"]["to_flange"]["leg"], t["weld"]["to_web"]["leg"]) == (15.0, 10.0, 5.0)
            assert dg["weld"]["ends"]["leg"] == 5.0 and dg["weld"]["corner_axial"] == pytest.approx(dV / dg["cos_theta"], abs=0.1)
        else:
            assert (t["t"], t["weld"]["to_flange"]["leg"], t["weld"]["to_web"]["leg"]) == (12.0, 5.0, 5.0)
    bs = building_bases(jr, out, BaseSettings(concrete="C25/30"))
    r = W.building_welds(jr, out, an, bs, base_settings=BaseSettings(concrete="C25/30"), li=li)
    json.dumps(r, allow_nan=True)
    assert r["banner"].startswith("NOT FOR ISSUE") and r["concrete_fc"] == 25.0 and W.BUTT_SPLICE_NOTE in r["notes"]
    assert r["settings"] == {k: getattr(ST, k) for k in WeldSettings.__dataclass_fields__}
    assert r["counts"]["flange_web"] == {"DESIGNED": 26}                                       # 20 frame + 6 wind columns
    wcs = [m for m in r["flange_web"] if m["role"] == "wind_column"]
    assert len(wcs) == 6 and all(m["local_loads"]["carried_by"] == "gable girts" and not m["end_zones"] for m in wcs)
    for m in wcs:
        g = m["segments"][0]["governing"]
        assert g["q"] == pytest.approx(flange_web_q({"hw": 300.0, "tw": 6.0, "bf_top": 150.0, "tf_top": 8.0, "bf_bot": 150.0,
                                                     "tf_bot": 8.0}, g["V"])["q"], abs=0.01) and g["lb"] == 73.0
    for m in (m for m in r["flange_web"] if m["role"] != "wind_column"):
        for s in m["segments"]:
            g = s["governing"]
            q = flange_web_q(_sec_from(g), g["V"])["q"]
            assert g["q"] == pytest.approx(q, abs=0.01) and g["flow"] >= g["q"] - 1e-6
            assert g["lb"] == 83.0 and s["weld"]["sides"].startswith("one side") and s["weld"]["leg"] == 5.0
        assert m["end_zones"] and all(z["weld"]["sides"] == "both sides" for z in m["end_zones"])
    braced = [b for b in r["bases"] if b.get("brace_case")]
    assert len(braced) == 8 and all(b["status"] == "PARTIAL - brace case NOT EVALUATED" for b in braced)
    for b in braced:
        bc = b["brace_case"]
        assert bc["status"] == "NOT EVALUATED" and bc["cases"] == []
        assert bc["V_weak"] == pytest.approx(bc["T"] * bc["cos_a"], abs=1e-3) and bc["T_sin_a"] == pytest.approx(bc["T"] * bc["sin_a"], abs=1e-3)
    assert all(b["status"] == "DESIGNED" and b["leg"] == 5.0 for b in r["bases"] if not b.get("brace_case"))
    assert not any("shear_lug" in b for b in r["bases"])                       # anchors not failing (no pedestal given)


def _sec_from(g):
    """The governing station's section back from its depth (one-segment tapers: 200 × 10 flanges, tw 6 in building 1)."""
    return {"hw": g["d"] - 20.0, "tw": 6.0, "bf_top": 200.0, "tf_top": 10.0, "bf_bot": 200.0, "tf_bot": 10.0}
