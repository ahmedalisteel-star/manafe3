# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 3: knee / ridge / splice end plates (engine/connections/endplates.py). The 4E / 4ES / 8ES yield lines,
bolt strengths, prying and J10 checks are bimsteelauto_connections' (VERIFIED there); here the Manafe3 parts by hand.

Independent values (longhand, written out below; NOT recomputed by the code under test):
    DG 16 flush (from memory — the arithmetic is checked here, NOT the formula): bp 300, g 100, pf 40, h1 350 (two-bolt),
        h2 = 350 − 72 = 278, pb 72 (four-bolt): s = ½ √30 000 = 86.6025
        two-bolt  = 150 (350 (1/40 + 1/86.6025) − ½) + 0.02 (350 (40 + 86.6025)) = 1843.72 + 886.22 = 2729.94
        four-bolt = 150 (350 (1/40 + 1/86.6025) + 278/86.6025 − ½) + 0.02 (350 (40 + 54) + 278 (86.6025 + 18)) + 50
                  = 2325.23 + 1239.59 + 50 = 3614.82
    Extended rows, d 400, tf 10 / 10, M20 (pf = max(40, 32) = 40, de 30, pb 60): 4E h = 400 + 40 − 5 = 435, 400 − 10 − 40 − 5
        = 345; 8ES h = 495, 435, 345, 285
    Flange weld full strength 200 × 10 S355: 355 × 200 × 10 = 710 kN; per mm of leg 0.75 × 0.6 × 482 × 0.707 × 200 × 2 × 1.5
        = 92.01 kN → 7.72 → 8 mm (≤ 10 and ≤ 12); a 300 × 25 flange: 2662.5 kN / 138.0 = 19.3 mm > 12 → CJP
    Shear fallback, M20 8.8, threads included: φRn = 0.75 × 0.45 × 800 × 314.16 = 84.82 kN per bolt; J3-3a with Vu 500 kN on
        8 bolts: frv = 62.5 kN / 314.16 = 198.94 MPa; F'nt = 1.3 × 600 − 600 / (0.75 × 360) × 198.94 = 337.9 MPa
Negative controls: the concurrent pair is used, never the largest M with the largest T of another combination; 8.8 that
fails up to the largest size switches to 10.9 only when allowed, else FAILS with fixes; a joint without forces, an
unknown grade → NOT EVALUATED.

Step 3 follow-ups (2026-11-12) — one hand value per decision, longhand (S355JR in the library: Fy 355, Fu 490 up to 40 mm):
    KNEE (rafter d 495, 200 × 10 flanges, tw 6, slope 1:10 → the plate sees d 497.469, tf 10.050; lever 487.419):
        4E M24: pf 40: h = 497.469 + 40 − 5.025 = 532.444 and 497.469 − 10.050 − 40 − 5.025 = 442.394, Σh 974.838
        Pt M24 8.8 = 600 × 452.389 = 271.434 kN; φMnp = 0.75 × 2 × 271.434 × 974.838 = 396.91 kN·m, the same for both signs
        Yp (DG 4, 4E; bp 250, g 100, s = ½ √25 000 = 79.057) = 125 [442.394 (1/40 + 1/79.057) + 532.444/40 − ½]
            + 0.02 × 442.394 × 119.057 = 3683.36 + 1053.40 = 4736.76; t_req = √(1.11 × 396.906e6 / (0.9 × 355 × 4736.76))
            = 17.06 → stock 18
        +M demand: 217.7 + 61.8 × 487.419 / 2000 = 232.761 (the largest tension WITH its own moment)
        shear M24 8.8 N: 0.75 × 0.45 × 800 × 452.389 = 122.15 kN; bearing on the 10 mm column flange, lc = 36 − 13.5 = 22.5:
            0.75 × 1.2 × 22.5 × 10 × 490 = 99.225 kN governs; 4 compression-side bolts 396.9 kN; U = 217 / 396.9 = 0.5467
    ORDER 4E → 4ES → 8ES, the smallest bolt first (Mu 700): 4E / 4ES M30: 1.5 × 424.115 × 974.838 = 620.16 < 700;
        8ES Σh = 1949.676: M20 1.5 × 188.496 × 1949.676 = 551.26 < 700; M24 793.81 ≥ 700 → 8ES M24
    RIDGE (d 424, 250 × 12, slope 1:10 → d 426.115, tf 12.060; bp 300, g 100, s 86.6025), M20, flush top:
        h1 = 426.115 − 12.060 − 40 − 6.030 = 368.025; two-bolt φMnp = 1.5 × 188.496 × 368.025 = 104.06 kN·m
        two-bolt Yp = 150 (368.025 (1/40 + 1/86.6025) − ½) + 0.02 × 368.025 × 126.6025 = 1942.53 + 931.86 = 2874.39
            t_req = √(1.11 × 104.057e6 / (0.9 × 355 × 2874.39)) = 11.21 → 12
        four-bolt (pb 60, h2 308.025) Yp = 150 (13.4502 + 3.5568 − ½) + 0.02 (368.025 × 85 + 308.025 × 101.6025) + 50
            = 2476.05 + 1251.56 + 50 = 3777.61; φMnp = 1.5 × 188.496 × 676.05 = 191.15; t_req 13.26 → 15
        Mu 100 ≤ 104.06 but the two-bolt Tu = 100 000 / (2 × 368.025) = 135.86 kN fails the prying cross-check → four-bolt
        bottom 4E: h = 460.085, 368.025; φMnp 234.14; Yp = 150 (13.4502 + 11.5021 − ½) + 931.86 = 4599.71; t_req 13.30 → 15
        splice (cos 1): h1 = 424 − 12 − 40 − 6 = 366; φMnp = 1.5 × 188.496 × 366 = 103.48
    J3.7: φT' = 0.75 × 337.9 × 314.16 = 79.62 kN; U = max(62.5 / 84.82, 50 / 79.62) = 0.7368; the switch at 4 × 84.82 =
        339.3 kN; bearing lc = 30 − 11 = 19, t 20, Fu 470: 0.75 × 1.2 × 19 × 20 × 470 = 160.74 kN
    WELDS (E70: 0.75 × 0.6 × 482 × 0.707 = 153.348 MPa per mm of leg, per line): 300 × 12 flange 1278 kN / 138.013 = 9.26
        → 10 mm (1380.13 kN); 300 × 16 flange 1704 / 138.013 = 12.35 → 14 > 12 → CJP; with the limit at 16: 14 mm,
        1932.19 kN; a 10 mm leg imposed on the 200 × 10 flange: base metal 0.75 × 0.6 × 490 × 10 × 200 × 2 = 882.0 kN governs;
        web: zone 80 mm: 355 × 6 × 80 = 170.4 kN / (153.348 × 80 × 2 × 1.5 = 36.80) = 4.63 → 5 mm (184.02 kN); shear 150 kN
        on 380 − 160 = 220 mm: 153.348 × 220 × 2 = 67.47 kN / mm → 3 mm (the minimum; 202.42 kN)
    COLUMN (d 489.2, tw 6, tf 10, bf 200, k 16, lb 46, near the end; Puf = Mu / 0.49):
        J10.1 0.9 × 6.25 × 355 × 10² × ½ = 99.84 kN; J10.2 355 × 6 (2.5 × 16 + 46) = 183.18 kN;
        J10.3 0.75 × 0.4 × 36 [1 + 3 (46/489.2)(0.6)^1.5] √(200 000 × 355 × 10/6) = 132.89 kN;
        J10.5 0.9 × 24 × 216 √(200 000 × 355) / 469.2 × ½ = 41.89 kN — listed, NOT applied
        Puf 90: all of J10.1–3 pass → stiffeners by dimensions: bs = 60 (200/3 − 3 → 5 mm steps), ts ≥ max(10/2, 60/16) → 12
        Puf 120: Rst = 120 − 99.84 = 20.16 kN (with J10.5 applied it would be 78.11), As = 20 160 / (0.9 × 355) = 63.1 mm²
        Puf 700: Rst 600.16, As 1878.4, ts ≥ 1878.4 / 120 = 15.65 → 16; panel J10.6 = G2.1 (kv = 5 + 5/(490/469.2)² = 9.585,
            Cv1 1) = 0.9 × 0.6 × 355 × 489.2 × 6 = 562.68 kN; cos θ = 489.2 / √(489.2² + 490²) = 0.7065;
            As = 137 320 / (0.9 × 355 × 0.7065) = 608.3 mm² → 12 mm pair; doubler td = 137 320 / (0.9 × 0.6 × 355 × 489.2) = 1.46
    CLEARANCES: nut corner = AF / cos 30° / 2 + 5: M20 (30) 22.32, M24 (36) 25.78, M27 (41) 28.67, M30 (46) 31.56 mm
    STIFFENER 4ES M20: hst = 40 + 30 = 70, Lst = 70 / tan 30° = 121.2, ts ≥ 70 / (0.56 √(200 000/355) = 13.29) = 5.27 → 12;
        8ES M24, tw 14: hst = 40 + 36 + 72 = 148 → ts ≥ 14 → 15
"""

import json
import math

import pytest
from bimsteelauto_connections.welds import min_weld_size

from engine.connections import endplates as ep
from engine.connections.endplates import (DG16_MARK, EndPlateSettings, _side, clearances, column_side, corner_radius,
                                          design_joint, endplate_stiffener, extended_rows, fillet_or_cjp, flange_weld,
                                          flush_Yp, shear_for_sign, sign_demands, web_weld)

ST = EndPlateSettings()
RS = {"d": 424.0, "tw": 6.0, "bf_top": 250.0, "tf_top": 12.0, "bf_bot": 250.0, "tf_bot": 12.0}
COS = 1 / math.sqrt(1.01)
KNEE_RS = {"d": 495.0, "tw": 6.0, "bf_top": 200.0, "tf_top": 10.0, "bf_bot": 200.0, "tf_bot": 10.0}
KNEE_COL = {"d": 489.2, "tw": 6.0, "tf": 10.0, "bf": 200.0, "Pr": 90.0, "Py": 2000.0}
NEG, POS, FLUSH = "-M (top flange in tension)", "+M (bottom flange in tension)", "-M (top flange in tension, flush)"
SEC = {"d": 400.0, "tf_t": 10.0, "tf_c": 10.0, "bf": 200.0, "tw": 6.0}


def _knee(Mneg=341.8, Mpos=217.7, Ptens=(61.8, 217.7)):
    return _joint(Mneg=Mneg, Mpos=Mpos, cap=197.5, Ptens=Ptens, Vu=217.0, kind="knee")


def _joint(Mneg=100.0, Mpos=60.0, cap=223.8, T_with_neg=0.0, Ptens=(40.0, -30.0), Vu=150.0, kind="ridge", status="EVALUATED"):
    pt_val, pt_M = Ptens
    return {"id": "F3-R", "type": kind, "status": status,
            "forces": {"M_neg": {"value": Mneg, "M": -Mneg, "V": 5.0, "P": -T_with_neg, "combo": "LRFD: A"},
                       "M_pos": {"value": Mpos, "M": Mpos, "V": 5.0, "P": 20.0, "combo": "LRFD: B"},
                       "P_tens": {"value": pt_val, "M": pt_M, "V": 3.0, "P": -pt_val, "combo": "LRFD: C"}},
            "design": {"Mu_neg": {"value": max(Mneg, cap), "capacity_based": cap}, "Mu_pos": {"value": max(Mpos, cap), "capacity_based": cap},
                       "Vu": {"value": Vu}, "Pu": {"value": 20.0}, "Tu": {"value": pt_val}}}


def test_flush_yield_lines_arithmetic():
    s = 0.5 * math.sqrt(300 * 100)
    two = 150 * (350 * (1 / 40 + 1 / s) - 0.5) + 0.02 * (350 * (40 + s))
    four = 150 * (350 * (1 / 40 + 1 / s) + 278 / s - 0.5) + 0.02 * (350 * (40 + 54) + 278 * (s + 18)) + 50
    assert two == pytest.approx(2729.94, abs=0.01) and four == pytest.approx(3614.82, abs=0.01)
    assert flush_Yp("two-bolt", 300, 100, 40, (350,))["Yp"] == pytest.approx(two, rel=1e-12)
    r = flush_Yp("four-bolt", 300, 100, 40, (350, 278), 72)
    assert r["Yp"] == pytest.approx(four, rel=1e-12) and r["verified"] is False and "TO CONFIRM" in r["clause"]
    assert flush_Yp("two-bolt", 300, 100, 120, (350,))["pf_used"] == pytest.approx(s)          # pf capped at s


def test_extended_rows_by_hand():
    sec = {"d": 400.0, "tf_t": 10.0, "tf_c": 10.0, "bf": 200.0, "tw": 6.0}
    assert extended_rows(sec, 20, "4E", ST)["h_rows"] == (435.0, 345.0)
    r = extended_rows(sec, 20, "8ES", ST)
    assert r["h_rows"] == (495.0, 435.0, 345.0, 285.0) and r["n_bolts"] == 8 and r["extension"] == 40 + 30 + 60


def test_welds_by_hand():
    w = flange_weld(200, 10, 20, "S355JR", ST)
    assert w["type"] == "double fillet" and w["leg"] == 8.0 and w["demand"] == pytest.approx(710.0)
    assert w["capacity"] == pytest.approx(0.75 * 0.6 * 482 * 0.707 * 8 * 200 * 2 * 1.5 / 1000, abs=0.01)   # 736.07
    assert w["min_leg_J2_4"] == 5.0 and w["governs"] == "weld metal" and w["U"] == pytest.approx(0.9646, abs=1e-4)
    cjp = flange_weld(300, 25, 30, "S355JR", ST)
    assert cjp["type"].startswith("CJP") and "12" in cjp["why"]


def test_cjp_switch_above_12mm_by_hand():
    w12 = flange_weld(300, 12, 20, "S355JR", ST)                                  # 9.26 mm needed → 10
    assert (w12["type"], w12["leg"]) == ("double fillet", 10.0) and w12["capacity"] == pytest.approx(1380.13, abs=0.01)
    w16 = flange_weld(300, 16, 20, "S355JR", ST)                                  # 12.35 mm needed → 14 > 12
    assert w16["type"].startswith("CJP") and w16["leg"] == 0.0 and w16["U"] == 1.0 and "12 mm" in w16["why"]
    assert w16["demand"] == pytest.approx(1704.0) and w16["capacity"] == pytest.approx(1704.0)   # full strength
    big = flange_weld(300, 16, 20, "S355JR", EndPlateSettings(weld_max_fillet=16.0))             # negative control
    assert (big["type"], big["leg"]) == ("double fillet", 14.0) and big["capacity"] == pytest.approx(1932.19, abs=0.01)
    # one size per joint type: a 10 mm leg imposed where 8 mm is enough — the base metal then governs
    w10 = flange_weld(200, 10, 20, "S355JR", ST, 10.0)
    assert w10["leg"] == 10.0 and w10["capacity"] == pytest.approx(882.0, abs=0.01) and w10["governs"] == "base metal"


def test_web_weld_and_tee_joint_by_hand():
    ww = web_weld(SEC, 80.0, 150.0, 18.0, "S355JR", ST)
    tz, sh = ww["tension_zone"], ww["shear"]
    assert ww["zone_length"] == 80.0 and tz["demand"] == pytest.approx(170.4) and tz["theta"] == 90.0
    assert tz["leg"] == 5.0 and tz["capacity"] == pytest.approx(184.02, abs=0.01)
    assert sh["length"] == 220.0 and sh["theta"] == 0.0 and sh["leg"] == 3.0 == sh["min_leg_J2_4"]
    assert sh["capacity"] == pytest.approx(202.42, abs=0.01) and ww["leg"] == 5.0
    assert web_weld(SEC, 500.0, 150.0, 18.0, "S355JR", ST)["zone_length"] == 190.0     # never more than half the web
    # the library's tee mode: a 6 mm web on a 25 mm plate is weldable with the Table J2.4 minimum of the THINNER part
    t = fillet_or_cjp(50.0, 200.0, 0.0, 6.0, 25.0, "S355JR", ST)
    assert (t["type"], t["leg"]) == ("double fillet", 3.0) and t["capacity"] == pytest.approx(184.02, abs=0.01)
    assert "size_fillet_weld" in t["sized_by"] and not hasattr(ep, "tjoint_fillet")    # no separate Manafe3 routine
    assert [min_weld_size(x) for x in (6, 7, 13, 14, 19, 20)] == [3, 5, 5, 6, 6, 8]
    with pytest.raises(ValueError):
        fillet_or_cjp(0.0, 200.0, 0.0, 6.0, 25.0, "S355JR", ST)


def test_concurrent_pair_not_max_with_max():
    # largest -M 100 kN·m comes with NO tension (combo A); the largest tension 40 kN comes with -30 kN·m (combo C)
    j = _joint(Mneg=100.0, cap=0.0001, T_with_neg=0.0, Ptens=(40.0, -30.0))
    lever = 400.0
    d = sign_demands(j, lever)["-M"]
    assert d["Mu_eq"] == pytest.approx(100.0)                                       # combo A: 100 + 0
    assert {c["combo"] for c in d["candidates"]} == {"LRFD: A", "LRFD: C"}
    assert max(c["Mu_eq"] for c in d["candidates"]) < 100.0 + 40.0 * lever / 2000.0   # never 100 with 40 kN (= 108)
    # tension concurrent with the largest moment is added: 100 + 25 × 400 / 2000 = 105
    assert sign_demands(_joint(Mneg=100.0, cap=0.0001, T_with_neg=25.0), lever)["-M"]["Mu_eq"] == pytest.approx(105.0)
    # with the 50 % rule governing: max(30, 223.8) + 40 × 0.2 = 231.8 beats max(100, 223.8) + 0 = 223.8
    assert sign_demands(_joint(), lever)["-M"]["Mu_eq"] == pytest.approx(231.8)
    # +M: the largest tension (40 kN) comes with a −M moment → not a +M candidate; the +M moment comes with 20 kN of
    # COMPRESSION → not credited: 60 + 0
    pos = sign_demands(j, lever)["+M"]
    assert [c["combo"] for c in pos["candidates"]] == ["LRFD: B"] and pos["T"] == 0.0 and pos["Mu_eq"] == pytest.approx(60.0)
    # the largest tension with ITS OWN +M moment: 217.7 + 61.8 × 487.419 / 2000 = 232.761 beats 217.7 with compression
    kp = sign_demands(_knee(), 487.419)["+M"]
    assert kp["pair"] == "largest tension with its moment" and kp["combo"] == "LRFD: C"
    assert kp["Mu_eq"] == pytest.approx(232.761, abs=1e-3) and [c["Mu_eq"] for c in kp["candidates"]] == [217.7, kp["Mu_eq"]]
    # no moment of a sign in any combination: the 50 % rule alone, no combination named
    none = _joint()
    none["forces"]["M_pos"]["combo"] = None
    alone = sign_demands(none, lever)["+M"]
    assert alone["combo"] is None and alone["Mu_eq"] == pytest.approx(223.8) and alone["T"] == 0.0


def test_shear_fallback_to_all_bolts_with_J3_7():
    plies = [(20.0, 470.0), (20.0, 470.0)]
    ok = shear_for_sign(200.0, 4, 4, 50.0, 20, "8.8", plies, 30.0, ST)
    assert ok["method"].startswith("compression-side bolts only") and ok["bolt_shear"] == pytest.approx(84.82, abs=0.01)
    r = shear_for_sign(500.0, 4, 4, 50.0, 20, "8.8", plies, 30.0, ST)
    assert r["method"].startswith("ALL bolts (8)") and r["shear_per_bolt"] == pytest.approx(62.5)
    frv = 62500 / (math.pi * 400 / 4 * 1.0)                                          # 198.94 MPa
    assert r["Fnt_modified"] == pytest.approx(1.3 * 600 - 600 / (0.75 * 360) * frv, abs=0.2)
    assert r["Fnt_modified"] == pytest.approx(337.9, abs=0.1) and r["phiT_reduced"] == pytest.approx(79.62, abs=0.01)
    assert r["U"] == pytest.approx(0.7368, abs=1e-4) and r["phiVn"] == pytest.approx(8 * 84.823, abs=0.01)
    assert ok["phiVn"] == pytest.approx(339.29, abs=0.01) and ok["U"] == pytest.approx(0.5895, abs=1e-4)
    assert ok["bearing_tearout"] == pytest.approx(160.74, abs=0.01) and "Fnt_modified" not in ok
    # the switch is exactly at the compression-side capacity 4 × 84.82 = 339.3 kN
    assert shear_for_sign(339.0, 4, 4, 50.0, 20, "8.8", plies, 30.0, ST)["method"].startswith("compression-side bolts only")
    assert shear_for_sign(340.0, 4, 4, 50.0, 20, "8.8", plies, 30.0, ST)["method"].startswith("ALL bolts (8)")
    # negative controls: tension bolts at 100 kN fail the reduced tension (100 / 79.62); 700 kN fails in shear (87.5 / 84.82)
    assert shear_for_sign(500.0, 4, 4, 100.0, 20, "8.8", plies, 30.0, ST)["U"] == pytest.approx(1.256, abs=1e-3)
    assert shear_for_sign(700.0, 4, 4, 10.0, 20, "8.8", plies, 30.0, ST)["U"] == pytest.approx(1.0316, abs=1e-4)
    # the thinner ply governs the bearing: M24 on a 10 mm column flange (Fu 490), lc = 36 − 13.5 = 22.5 mm
    thin = shear_for_sign(217.0, 4, 4, 50.0, 24, "8.8", [(18.0, 490.0), (10.0, 490.0)], 36.0, ST)
    assert thin["bolt_shear"] == pytest.approx(122.15, abs=0.01) and thin["bearing_tearout"] == pytest.approx(99.225, abs=0.001)
    assert thin["phiVn"] == pytest.approx(396.9, abs=0.01)


def test_knee_both_signs_by_hand():
    st = EndPlateSettings(configs=("4E",), bolt_sizes=(24.0,))
    r = design_joint(_knee(), KNEE_RS, COS, "S355", st, KNEE_COL)
    assert r["status"] == "DESIGNED" and "not_for_issue" not in r                       # a knee has no flush side
    for k in (NEG, POS):
        s = r["sides"][k]
        assert s["kind"] == "4E" and s["rows"]["h_rows"] == pytest.approx((532.444, 442.394), abs=1e-3)
        assert s["phiMnp_bolts"] == pytest.approx(396.91, abs=0.01)
        assert s["Yp"] == pytest.approx(4736.76, abs=0.02) and s["Yp_verified"] is True
        assert s["t_req"] == pytest.approx(17.06, abs=0.01) and s["t"] == 18.0 == r["t"]
        v = r["shear"][k]
        assert v["bearing_tearout"] == pytest.approx(99.225, abs=0.001) and "(4)" in v["method"]
        assert v["phiVn"] == pytest.approx(396.9, abs=0.01) and v["U"] == pytest.approx(0.5467, abs=1e-4)
    assert r["sides"][NEG]["Mu"] == pytest.approx(341.8) and r["sides"][POS]["Mu"] == pytest.approx(232.761, abs=1e-3)
    assert r["sides"][NEG]["U_bolts"] == pytest.approx(0.8612, abs=1e-4) and r["governs"] == {"bolts": NEG, "plate": NEG}
    assert r["sides"][NEG]["prying_check"]["Tu_per_bolt"] == pytest.approx(175.31, abs=0.01)     # 341 800 / (2 × 974.838)
    # the other sign governing: −M 150 → max(150, 197.5) + 61.8 × 487.419 / 2000 = 212.561; +M 341.8
    rev = design_joint(_knee(Mneg=150.0, Mpos=341.8, Ptens=(61.8, -150.0)), KNEE_RS, COS, "S355", st, KNEE_COL)
    assert rev["governs"] == {"bolts": POS, "plate": POS} and rev["sides"][POS]["Mu"] == pytest.approx(341.8)
    assert rev["sides"][NEG]["Mu"] == pytest.approx(212.561, abs=1e-3)
    assert (rev["config"], rev["bolt"]["d"], rev["t"]) == (r["config"], r["bolt"]["d"], r["t"])   # the same layout


def test_config_and_bolt_order_by_hand():
    j7 = _knee(Mneg=700.0)
    r = design_joint(j7, KNEE_RS, COS, "S355", ST, KNEE_COL)
    assert (r["status"], r["config"], r["bolt"]["d"], r["bolt"]["grade"]) == ("DESIGNED", "8ES", 24.0, "8.8")
    assert r["sides"][NEG]["rows"]["h_rows"] == pytest.approx((604.444, 532.444, 442.394, 370.394), abs=1e-3)
    assert r["sides"][NEG]["phiMnp_bolts"] == pytest.approx(793.81, abs=0.01)
    assert r["endplate_stiffener"]["height"] == 148.0 and r["endplate_stiffener"]["t"] == 12.0
    # negative controls: every candidate tried before it fails on the bolts
    for cfg, db, phi in (("4E", 30.0, 620.16), ("4ES", 30.0, 620.16), ("8ES", 20.0, 551.26)):
        f = design_joint(j7, KNEE_RS, COS, "S355", EndPlateSettings(configs=(cfg,), bolt_sizes=(db,), escalate_to_10_9=False),
                         KNEE_COL)
        assert f["status"] == "FAILS" and "bolts (no-prying moment) too weak" in f["why"]
        assert f["sides"][NEG]["phiMnp_bolts"] == pytest.approx(phi, abs=0.01)


def test_ridge_flush_side_by_hand():
    st = EndPlateSettings(bolt_sizes=(20.0,))

    def ridge(M, kind="ridge", cos=COS):
        return design_joint(_joint(Mneg=M, Mpos=60.0, cap=0.0001, Ptens=(1.0, 1.0), Vu=100.0, kind=kind), RS, cos, "S355", st)
    r = ridge(90.0)
    fl, bot = r["sides"][FLUSH], r["sides"][POS]
    assert fl["kind"] == "flush two-bolt" and fl["rows"]["h_rows"] == pytest.approx((368.025,), abs=1e-3)
    assert fl["Yp"] == pytest.approx(2874.39, abs=0.02) and fl["Yp_verified"] is False and "TO CONFIRM" in fl["Yp_clause"]
    assert fl["phiMnp_bolts"] == pytest.approx(104.06, abs=0.01) and fl["U_bolts"] == pytest.approx(0.8649, abs=1e-4)
    assert fl["t_req"] == pytest.approx(11.21, abs=0.01) and fl["t_need"] == 12.0
    assert fl["prying_check"]["Tu_per_bolt"] == pytest.approx(122.27, abs=0.01)                # 90 000 / (2 × 368.025)
    assert bot["kind"] == "4E" and bot["rows"]["h_rows"] == pytest.approx((460.085, 368.025), abs=1e-3)
    assert bot["Yp"] == pytest.approx(4599.71, abs=0.02) and bot["Yp_verified"] is True
    assert bot["phiMnp_bolts"] == pytest.approx(234.14, abs=0.01) and bot["t_req"] == pytest.approx(13.30, abs=0.01)
    assert r["t"] == 15.0 and r["governs"] == {"bolts": FLUSH, "plate": FLUSH}                   # one plate: the thicker need
    # 100 kN·m is within the two-bolt moment (104.06) but its bolt force 135.86 kN fails the prying cross-check → four-bolt
    for M in (100.0, 150.0):
        f4 = ridge(M)["sides"][FLUSH]
        assert f4["kind"] == "flush four-bolt" and f4["rows"]["h_rows"] == pytest.approx((368.025, 308.025), abs=1e-3)
        assert f4["Yp"] == pytest.approx(3777.61, abs=0.02) and f4["phiMnp_bolts"] == pytest.approx(191.15, abs=0.01)
        assert f4["t_req"] == pytest.approx(13.26, abs=0.01) and f4["t_need"] == 15.0
    sp = ridge(90.0, "rafter_splice", 1.0)                                                      # square cut: h1 = 366
    assert sp["sides"][FLUSH]["rows"]["h_rows"] == (366.0,) and sp["sides"][FLUSH]["phiMnp_bolts"] == pytest.approx(103.48, abs=0.01)
    for x in (r, ridge(150.0), sp):
        assert x["status"] == "DESIGNED" and x["not_for_issue"] == DG16_MARK


def test_dg16_mark_only_while_unverified(monkeypatch):
    assert DG16_MARK == "NOT FOR ISSUE: DG 16 flush unverified" and ep.VERIFIED["flush_Yp_DG16"] is False
    assert "not_for_issue" not in design_joint(_knee(), KNEE_RS, COS, "S355", ST, KNEE_COL)       # negative control: a knee
    big = _joint(Mneg=200.0, Mpos=100.0, cap=0.0001, Ptens=(1.0, 1.0), Vu=100.0)
    no = design_joint(big, RS, COS, "S355", EndPlateSettings(configs=("4E",), bolt_sizes=(20.0,), escalate_to_10_9=False))
    assert no["status"] == "FAILS" and no["not_for_issue"] == DG16_MARK                           # a failing ridge keeps it
    assert design_joint(_joint(), RS, COS, "S355", ST)["not_for_issue"] == DG16_MARK
    monkeypatch.setitem(ep.VERIFIED, "flush_Yp_DG16", True)                                       # after the user confirms
    assert "not_for_issue" not in design_joint(_joint(), RS, COS, "S355", ST)


def test_column_side_J10_and_stiffeners_by_hand():
    def cs(Puf, col=KNEE_COL, st=ST):
        return column_side(Puf * 0.49, 500.0, 10.0, 490.0, 46.0, col, "S355JR", st)       # Puf = Mu / (500 − 10)
    a = cs(90.0)
    ch = {c["check"][:5]: c for c in a["checks"]}
    assert a["Puf"] == pytest.approx(90.0) and ch["J10.1"]["phiRn"] == pytest.approx(99.84, abs=0.01)
    assert ch["J10.2"]["phiRn"] == pytest.approx(183.18, abs=0.01) and ch["J10.3"]["phiRn"] == pytest.approx(132.89, abs=0.01)
    # J10.5 would fail (90 / 41.89 = 2.15) — listed, NOT applied; J10.4 not applied either
    assert ch["J10.5"]["phiRn"] == pytest.approx(41.89, abs=0.01) and ch["J10.5"]["U"] == pytest.approx(2.148, abs=1e-3)
    assert ch["J10.5"]["applicable"] is False and ch["J10.4"]["applicable"] is False and "phiRn" not in ch["J10.4"]
    t = a["transverse_stiffeners"]
    assert a["ok"] and t["Rst"] == 0.0 and t["As_req"] == 0.0 and t["sized_by"].startswith("J10.8")
    assert (t["bs"], t["t_req"], t["t"], t["length"]) == (60, 5.0, 12.0, 244.6) and "diagonal_stiffener" not in a["panel_zone"]
    # negative control: J10.1 fails at 120 kN → the stiffener force is from J10.1–3 only (20.16, not 120 − 41.89 = 78.11)
    b = cs(120.0)["transverse_stiffeners"]
    assert b["Rst"] == pytest.approx(20.16, abs=0.01) and b["As_req"] == pytest.approx(63.1, abs=0.1)
    assert b["sized_by"].startswith("J10.7") and b["t"] == 12.0
    c = cs(700.0)
    assert c["transverse_stiffeners"]["Rst"] == pytest.approx(600.16, abs=0.01)
    assert c["transverse_stiffeners"]["t_req"] == pytest.approx(15.65, abs=0.01) and c["transverse_stiffeners"]["t"] == 16.0
    p = c["panel_zone"]
    assert p["phi_J10_6"] == pytest.approx(562.68, abs=0.01) and p["phi_G2_1"] == pytest.approx(562.68, abs=0.01)
    assert p["G2_1"]["kv"] == pytest.approx(9.585, abs=1e-3) and p["G2_1"]["Cv1"] == 1.0 and p["U"] == pytest.approx(1.2441, abs=1e-4)
    dg = p["diagonal_stiffener"]
    assert dg["cos_theta"] == pytest.approx(0.7065, abs=1e-4) and dg["As_req"] == pytest.approx(608.3, abs=0.1)
    assert (dg["pair_bs"], dg["t"]) == (60, 12.0) and "doubler" not in p and "NOT EVALUATED" in dg["weld"]
    # the doubler option: td = 1.46 → 12 mm stock; negative control: a 16 mm web needs neither
    d = cs(700.0, st=EndPlateSettings(panel_zone="doubler"))["panel_zone"]
    assert d["doubler"]["td_req"] == pytest.approx(1.46, abs=0.01) and d["doubler"]["t"] == 12.0 and "diagonal_stiffener" not in d
    thick = cs(700.0, col={"d": 489.2, "tw": 16.0, "tf": 20.0, "bf": 250.0, "Pr": 90.0, "Py": 5000.0})["panel_zone"]
    assert thick["phiVpanel"] == pytest.approx(1500.47, abs=0.01) and "diagonal_stiffener" not in thick and "doubler" not in thick
    # no stock plate for the stiffener → not ok (never a silent pass)
    assert cs(700.0, st=EndPlateSettings(plate_stock=(12.0, 15.0)))["ok"] is False


def test_clearances_by_hand():
    sec = {"d": 500.0, "tf_t": 10.0, "tf_c": 10.0, "bf": 200.0, "tw": 6.0}
    thick = {**sec, "tw": 20.0}
    assert [corner_radius(d) + 5 for d in (20, 24, 27, 30)] == pytest.approx([22.32, 25.78, 28.67, 31.56], abs=0.01)
    ok = clearances(sec, 24, 250, 100, 40, 8, 5, ST, 200)                  # plate edge, web wrench, pitch, column flange edge
    assert [(c["value"], c["required"], c["ok"]) for c in ok] == [(75.0, 30.0, True), (42.0, 25.8, True), (32.0, 25.8, True),
                                                                  (50.0, 30.0, True)]
    bad = clearances(thick, 30, 200, 140, 42, 12, 10, ST, 150)
    assert [(c["value"], c["required"], c["ok"]) for c in bad] == [(30.0, 38.0, False), (50.0, 31.6, True), (30.0, 31.6, False),
                                                                   (5.0, 38.0, False)]
    assert [c["ok"] for c in clearances(thick, 30, 250, 100, 42, 8, 10, ST)] == [True, False, True]    # 50 − 10 − 10 = 30 < 31.56
    assert [c["ok"] for c in clearances(sec, 27, 250, 140, 40, 12, 5, ST)] == [True, True, False]      # 40 − 12 = 28 < 28.67
    assert clearances(sec, 27, 250, 140, 40, 12, 5, EndPlateSettings(wrench_allowance=4.0))[2]["ok"]   # 28 ≥ 27.67
    # at the joint: a 150 mm column flange, M24 on gauge 100: (150 − 100) / 2 = 25 < 30 → FAILS, the check named
    one = EndPlateSettings(configs=("4E",), bolt_sizes=(24.0,), escalate_to_10_9=False)
    f = design_joint(_knee(), KNEE_RS, COS, "S355", one, {**KNEE_COL, "bf": 150.0})
    assert f["status"] == "FAILS" and f["ok"] is False
    assert f["failed_checks"] == ["clearance: column flange edge (bf_col - g)/2 >= Table J3.4M (25 < 30 mm)"]
    assert f["why"] == f["failed_checks"][0]
    assert design_joint(_knee(), KNEE_RS, COS, "S355", one, {**KNEE_COL, "bf": 160.0})["status"] == "DESIGNED"   # 30 ≥ 30
    # no bolt size clears it (M20 25 < 26, M24 25 < 30, M27 / M30 on gauge 140: 5 mm): FAILS, not a bigger bolt
    every = design_joint(_knee(), KNEE_RS, COS, "S355", ST, {**KNEE_COL, "bf": 150.0})
    assert every["status"] == "FAILS" and "column flange edge" in every["why"]


def test_defaults_bolt_minimum_plate_width_gauge_stiffener():
    tiny = _joint(Mneg=10.0, Mpos=10.0, cap=0.0001, Ptens=(1.0, 1.0), Vu=20.0)
    assert design_joint(tiny, RS, COS, "S355", ST)["bolt"]["d"] == 20.0                           # M20 minimum, main frames
    assert design_joint(tiny, RS, COS, "S355", EndPlateSettings(bolt_min_main=16.0))["bolt"]["d"] == 16.0   # negative control
    s20 = _side("4ES", SEC, 20, "8.8", "S355JR", 100.0, ST)
    assert (s20["bp"], s20["g"]) == (250.0, 100.0) and s20["phiMnp_bolts"] == pytest.approx(220.54, abs=0.01)   # Σh 780
    s27 = _side("4E", {**SEC, "bf": 225.0}, 27, "8.8", "S355JR", 100.0, ST)
    assert (s27["bp"], s27["g"]) == (280.0, 140.0) and ST.gauge(24) == 100.0                      # bf + 50 → up to 10 mm
    assert (ST.pf(20), ST.pf(24), ST.pf(30)) == (40.0, 40.0, 42.0)                                # max(40, d + 12)
    assert endplate_stiffener("4ES", s20, 6.0, "S355JR", ST.plate_stock) == {"height": 70.0, "length": 121.2, "t": 12.0,
                                                                             "weld": "NOT EVALUATED (step 4)"}
    assert endplate_stiffener("4E", s20, 6.0, "S355JR", ST.plate_stock) is None
    s8 = _side("8ES", {**SEC, "tw": 14.0}, 24, "8.8", "S355JR", 100.0, ST)
    st8 = endplate_stiffener("8ES", s8, 14.0, "S355JR", ST.plate_stock)
    assert (st8["height"], st8["length"], st8["t"]) == (148.0, 256.3, 15.0)                       # ts ≥ the beam web
    assert endplate_stiffener("8ES", s8, 14.0, "S355JR", (12.0,))["t"] is None                    # negative control


def test_knee_one_layout_both_signs_and_column_side():
    col = {"d": 489.2, "tw": 6.0, "tf": 10.0, "bf": 200.0, "Pr": 90.0, "Py": 2000.0}
    rs = {"d": 495.0, "tw": 6.0, "bf_top": 200.0, "tf_top": 10.0, "bf_bot": 200.0, "tf_bot": 10.0}
    j = _joint(Mneg=341.8, Mpos=217.7, cap=197.5, Ptens=(61.8, 217.7), Vu=217.0, kind="knee")
    r = design_joint(j, rs, 1 / math.sqrt(1.01), "S355", ST, col)
    assert r["status"] == "DESIGNED", r.get("why")
    assert set(r["sides"]) == {"-M (top flange in tension)", "+M (bottom flange in tension)"}
    assert {s["kind"] for s in r["sides"].values()} == {r["config"]}                         # one layout, both signs
    assert r["governs"]["bolts"] in r["sides"] and r["bolt"]["d"] >= 20 and r["bolt"]["threads"] == "included"
    cs = r["column_side"]
    assert {c["check"][:5]: c.get("applicable", True) for c in cs["checks"]}["J10.5"] is False
    assert any(c["check"].startswith("J10.4") and c["applicable"] is False for c in cs["checks"])
    assert cs["transverse_stiffeners"]["t"] is not None and "NOT EVALUATED" in cs["transverse_stiffeners"]["weld"]
    p = cs["panel_zone"]
    a, h = p["G2_1"]["a"], p["G2_1"]["h"]
    kv = 5 + 5 / (a / h) ** 2
    cv1 = min(1.0, 1.10 * math.sqrt(kv * 200000 / 355) / (h / 6.0))
    assert p["G2_1"]["kv"] == pytest.approx(kv, abs=1e-3) and p["G2_1"]["Cv1"] == pytest.approx(cv1, abs=1e-4)
    assert p["phi_G2_1"] == pytest.approx(0.9 * 0.6 * 355 * 489.2 * 6.0 * cv1 / 1000, rel=1e-3)
    if "diagonal_stiffener" in p:
        dg = p["diagonal_stiffener"]
        assert dg["cos_theta"] == pytest.approx(489.2 / math.hypot(489.2, a), abs=1e-4)
        assert dg["As_req"] == pytest.approx((p["Vu"] - p["phiVpanel"]) * 1000 / (0.9 * 355 * dg["cos_theta"]), rel=1e-3)
    json.dumps(r, allow_nan=False)


def test_ridge_flush_top_and_grade_escalation():
    r = design_joint(_joint(), RS, 1 / math.sqrt(1.01), "S355", ST)
    assert r["status"] == "DESIGNED" and r["sides"]["-M (top flange in tension, flush)"]["kind"].startswith("flush")
    assert r["sides"]["-M (top flange in tension, flush)"]["Yp_verified"] is False
    # by hand: four-bolt flush, M20, plate sees d 426.11, tf 12.06: h1 = 426.11 - 12.06 - 40 - 6.03 = 368.02, h2 = 308.02;
    # phiMnp = 0.75 x 2 x Pt x 676.04: 8.8 Pt = 600 x 314.16 = 188.5 kN -> 191.1 kN.m; 10.9 Pt = 235.6 kN -> 238.9 kN.m
    big = _joint(Mneg=200.0, Mpos=100.0, cap=0.0001, Ptens=(1.0, 1.0), Vu=100.0)          # 200 between the two
    esc = design_joint(big, RS, 1 / math.sqrt(1.01), "S355", EndPlateSettings(configs=("4E",), bolt_sizes=(20.0,)))
    assert esc["status"] == "DESIGNED" and esc["bolt"]["grade"] == "10.9" and "8.8 failed up to M20" in esc["grade_note"]
    fl = esc["sides"]["-M (top flange in tension, flush)"]
    assert fl["phiMnp_bolts"] == pytest.approx(0.75 * 2 * 750 * math.pi * 100 * (368.02 + 308.02) / 1e6, rel=2e-3)
    no = design_joint(big, RS, 1 / math.sqrt(1.01), "S355", EndPlateSettings(configs=("4E",), bolt_sizes=(20.0,), escalate_to_10_9=False))
    assert no["status"] == "FAILS" and no["bolt"]["grade"] == "8.8" and no["fixes"]                 # negative control


def test_not_evaluated_and_settings():
    assert design_joint(_joint(status="NOT EVALUATED"), RS, 1.0, "S355", ST)["status"] == "NOT EVALUATED"
    assert design_joint(_joint(), RS, 1.0, "S690", ST)["status"] == "NOT EVALUATED"
    for bad in ({"configs": ["5E"]}, {"panel_zone": "x"}, {"bolt_sizes": [18]}, {"electrode": "E90"}, {"nope": 1}):
        with pytest.raises(ValueError):
            EndPlateSettings.from_dict(bad)


@pytest.mark.slow
def test_sized_building_1_end_plates_one_per_type():
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.endplates import building_endplates
    from engine.connections.joints import building_joints
    from engine.peb.building import peb_building, resolve
    from engine.tests.test_joints import _sized

    b0, li = _sized()
    b, _ = resolve(b0)
    out = peb_building(b)
    jr = building_joints(b0, li, analysis=analyse_building(b, li), out=out)
    r = building_endplates(jr, out)
    json.dumps(r, allow_nan=False)
    assert r["counts"] == {"DESIGNED": 25} and r["banner"].startswith("NOT FOR ISSUE")
    assert r["settings"] == {k: getattr(ST, k) for k in EndPlateSettings.__dataclass_fields__}    # every default listed
    flush = [x["joint"] for x in r["joints"] if x["type"] != "knee"]
    assert flush and r["not_for_issue"] == {DG16_MARK: flush} and any(n.startswith(DG16_MARK) for n in r["notes"])
    assert all(x.get("not_for_issue") == (DG16_MARK if x["type"] != "knee" else None) for x in r["joints"])
    assert all(x["welds"]["flanges"]["type"] == "double fillet" and "size_fillet_weld" in x["welds"]["flanges"]["sized_by"]
               for x in r["joints"])
    for ty in ("knee", "ridge", "rafter_splice"):
        rows = [x for x in r["joints"] if x["type"] == ty]
        assert len({(x["bolt"]["d"], x["bolt"]["grade"], x["t"]) for x in rows}) == 1             # one size per type
        assert len({(x["welds"]["flanges"]["leg"], x["welds"]["web"]["leg"]) for x in rows}) == 1
        p = r["per_type"][ty]
        assert rows[0]["bolt"]["d"] == p["db"] and rows[0]["t"] == p["t"] and p["db"] >= 20
    knees = [x for x in r["joints"] if x["type"] == "knee"]
    assert all("transverse_stiffeners" in x["column_side"] for x in knees)                        # at every knee
    js = {j["id"]: j for j in jr["joints"]}
    for x in r["joints"]:                                                                           # concurrent pairs from step 1
        for sg, d in x["demands"].items():
            if d["combo"]:
                F = js[x["joint"]]["forces"]
                assert d["combo"] in {F["M_neg"].get("combo"), F["M_pos"].get("combo"), F["P_tens"].get("combo")}
