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
"""

import json
import math

import pytest

from engine.connections.endplates import (EndPlateSettings, design_joint, extended_rows, flange_weld, flush_Yp, j24_min_leg,
                                          shear_for_sign, sign_demands, tjoint_fillet)

ST = EndPlateSettings()
RS = {"d": 424.0, "tw": 6.0, "bf_top": 250.0, "tf_top": 12.0, "bf_bot": 250.0, "tf_bot": 12.0}


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
    cjp = flange_weld(300, 25, 30, "S355JR", ST)
    assert cjp["type"].startswith("CJP") and "12" in cjp["why"]
    assert [j24_min_leg(t) for t in (6, 10, 16, 25)] == [3.0, 5.0, 6.0, 8.0]                 # by the THINNER part
    # a 6 mm web on a 25 mm plate is weldable (the library's edge rule t - 2 would refuse it): minimum 3 by the web
    assert tjoint_fillet(50.0, 200.0, 0.0, 6.0, ST)["type"] == "double fillet"


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


def test_shear_fallback_to_all_bolts_with_J3_7():
    plies = [(20.0, 470.0), (20.0, 470.0)]
    ok = shear_for_sign(200.0, 4, 4, 50.0, 20, "8.8", plies, 30.0, ST)
    assert ok["method"].startswith("compression-side bolts only") and ok["bolt_shear"] == pytest.approx(84.82, abs=0.01)
    r = shear_for_sign(500.0, 4, 4, 50.0, 20, "8.8", plies, 30.0, ST)
    assert r["method"].startswith("ALL bolts (8)") and r["shear_per_bolt"] == pytest.approx(62.5)
    frv = 62500 / (math.pi * 400 / 4 * 1.0)                                          # 198.94 MPa
    assert r["Fnt_modified"] == pytest.approx(1.3 * 600 - 600 / (0.75 * 360) * frv, abs=0.2)


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
