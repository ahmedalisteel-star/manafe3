# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 5a: the cleats (engine/connections/cleats.py). Independent values written out longhand below; NOT
recomputed by the code under test.

Geometry = building 1's purlin cleat: PL8 × 100 × 180, holes 14 mm at 45 / 155 mm up (pitch 110), Z200 × 65 × 20 × 2.0 web
(H 200, t 2), cleat S355JR (library: Fy 355, Fu 490), web S350GD (Fy 350, Fu 420), M12 8.8 threads included.

    BOLT        Ab = π 12² / 4 = 113.097 mm²; library 8.8 Fnv (threads included) = 0.45 × 800 = 360 MPa:
                φRv = 0.75 × 360 × 113.097 = 30.536 kN; Fnt = 0.75 × 800 = 600: φRt = 0.75 × 600 × 113.097 = 50.894 kN
                J3-3a: T 10, V 15 per bolt → min(50.894, 1.3 × 50.894 − 50.894 × 15 / 30.536) = min(50.894, 41.162)
                → U = 10 / 41.162 = 0.24294
    UPLIFT      R −10 kN (N 0, F_out 0) on one column of 2 bolts:
                bolt shear 5 / 30.536 = 0.16374
                cleat bearing (toward the top edge): upper lc = 180 − 155 − 7 = 18 → min(1.2 × 18 × 8 × 490 = 84 672,
                  2.4 × 12 × 8 × 490 = 112 896) = 84 672 N; lower lc = 110 − 14 = 96 → 112 896; φ Σ = 0.75 × 197 568
                  = 148.176 kN → U 0.067488
                web bearing (toward the bottom flange) — AISI S100-16 J3 (step 5c retrofit, VERIFIED False): d/t = 6 → C 3.0,
                  mf 0.75: φ 0.60 × 3 × 0.75 × 12 × 2 × 420 = 13.608 kN; edge shear φ 0.70 (Fu/Fy 1.2) × 2 × e × 420 with
                  e = lc + 7: lower e 43 → 25.284, upper e 103 → 60.564; Σ min = 27.216 kN → U 0.367431
                cleat block shear: Lv = 180 − 45 = 135, Agv 1080, Anv = (135 − 1.5 × 15.6) 8 = 892.8,
                  Ant = (50 − 7.8) 8 = 337.6: min(0.6 × 490 × 892.8 + 490 × 337.6 = 427 907.2,
                  0.6 × 355 × 1080 + 490 × 337.6 = 395 464) × 0.75 = 296.598 kN → U 0.033716
    GRAVITY     R +10: cleat lower lc = 45 − 7 = 38 → min(1.2 × 38 × 8 × 490 = 178 752, 112 896) = 112 896; upper 112 896
                  → 169.344 kN, U 0.059051; no block shear (no free edge toward the flange)
    STRUT END   the + side piece of an interior eave-strut cleat (columns at ±25), its butt end 20 mm from its hole:
                N +20 (tension): web e = 20 (the hole centre to the butt end) → AISI min(13.608, 0.70 × 2 × 20 × 420 =
                  11.760) per bolt, both bolts edge bolts: 23.520 kN → U 0.85034; N +25 → U 1.06293 → FAILS ("strut end")
                cleat lc = 50 − 25 − 7 = 18 → 84 672 per bolt → 127.008 kN → U 0.15747
                web block shear: Agv = 2 × 20 × 2 = 80, Anv = 2 (20 − 7.8) 2 = 48.8, Ant = (110 − 15.6) 2 = 188.8:
                  min(0.6 × 420 × 48.8 + 420 × 188.8 = 91 593.6, 0.6 × 350 × 80 + 79 296 = 96 096) × 0.75 = 68.6952 kN
                  → U 0.29114
                N −20 (compression, NEGATIVE CONTROL: the same force the other way passes): the web bears into its
                  long side (e 5970 → AISI bearing 2 × 13.608 = 27.216); the cleat toward the other column lc = 50 − 14 = 36 →
                  min(1.2 × 36 × 8 × 490 = 169 344, 112 896) → 169.344 kN
    SECTION     R +10, F_out 1: Lc = 2.1 × 155 = 325.5, r = 8 / √12 = 2.30940, Lc/r = 140.946, Fe = π² 200 000 / 140.946²
                = 99.362 MPa, Fy / Fe = 3.5728 > 2.25 → Fcr = 0.877 × 99.362 = 87.140, φPn = 0.9 × 87.140 × 800 = 62.741 kN;
                M_out = 1 × 100 + 10 × (8 + 2) / 2 = 150 kN·mm; φMy = 0.9 × 355 × 100 × 8² / 4 = 511.2 kN·mm;
                P / Pc = 0.15939 < 0.2 → H1-1b: 0.079693 + 0.29343 = 0.37312
                in-plane F11 (Lb 155): Lb d / t² = 155 × 100 / 64 = 242.19 (45.07 < · ≤ 1070) → Mn = (1.52 − 0.274 ×
                242.19 × 355 / 200 000) × 355 × 13 333.3 = 6 637 000 N·mm (≤ Mp 7 100 000) → φMnx = 5.9733 kN·m
    WELD        R −10 uplift: M_out = 10 × 5 = 50 kN·mm; across = (10 / 200 + 50 / (8 × 100)) × 1000 = 112.5 N/mm;
                5 mm E70, no directional increase: 0.75 × 0.6 × 482 × 0.70711 × 5 = 766.86 → U 0.14670; the cleat base
                metal across (J4.1, 2 lines): min(0.9 × 355 × 8, 0.75 × 490 × 8) / 2 = 1278 → U 0.088028
                N_net 10 (in-plane moment): across 3 × 10 000 × 100 / 100² = 300 N/mm + along 10 000 / 200 = 50
    HOST        J10.1: 0.9 × 6.25 × 355 × 10² = 199.69 kN, within 10 tf of the end: 99.844; W 100 < 0.15 × 700 → not required
                J10.2 (k = 10 + 5, lb 8, interior): 355 × 6 × (75 + 8) = 176.79 kN; at the end: 355 × 6 × (37.5 + 8) = 96.915
                J10.3 (d 495, interior): 0.75 × 0.8 × 36 × (1 + 3 × 8/495 × 0.6^1.5) × √(200 000 × 355 × 10 / 6)
                = 0.75 × 28.8 × 1.022535 × 10 878.1 = 240.26 kN
    REACTIONS   simple span q L / 2; two equal spans 3 q L / 8, 10 q L / 8, 3 q L / 8; with a 300 mm overhang on a 6 m
                simple span: R = q (6300)² / (2 × 6000) and q × 6300 − that
"""

from __future__ import annotations

import copy
import math

import pytest

from engine.connections import cleats as C

GEOM = {"d": 12.0, "d0": 14.0, "t_cleat": 8.0, "W": 100.0, "h": 180.0, "up_low": 45.0, "up_high": 155.0,
        "rows": [45.0, 155.0], "columns": [0.0], "H": 200.0, "t_web": 2.0}
GEOM2 = {**GEOM, "columns": [-25.0, 25.0]}
MATS = {"cleat": (355.0, 490.0), "web": (350.0, 420.0)}
BOLTS = {"phiRv": 30.536, "phiRt": 50.894}
PURLIN = {"piece": "P", "along": 0.0, "side": 1.0, "e_minus": 6000.0, "e_plus": 6000.0, "butt": False}
STRUT = {"piece": "S", "along": 25.0, "side": 1.0, "e_minus": 20.0, "e_plus": 5970.0, "butt": True}
HOST = {"member": "H", "tf": 10.0, "tw": 6.0, "d": 495.0, "bf": 200.0, "Fy": 355.0, "end_distance": 2000.0}
ST = C.CleatSettings()


def _rows(rows):
    return {r[1]: r for r in rows}


def test_bolt_strengths_and_j3_7():
    from bimsteelauto_connections.bolts import bolt_shear_capacity, bolt_tension_capacity
    assert bolt_shear_capacity("8.8", 12.0, threads="N") == pytest.approx(30.536, abs=2e-3)
    assert bolt_tension_capacity("8.8", 12.0) == pytest.approx(50.894, abs=2e-3)
    assert C.bolt_tension_with_shear(10.0, 15.0, 50.894, 30.536) == pytest.approx(0.24294, abs=1e-4)
    assert C.bolt_tension_with_shear(10.0, 1.0, 50.894, 30.536) == pytest.approx(10 / 50.894, abs=1e-5)   # capped at φRt
    assert C.bolt_tension_with_shear(0.0, 15.0, 50.894, 30.536) == 0.0


def test_aisi_bearing_longhand():
    assert C.aisi_bearing_C(12, 2) == 3.0 and C.aisi_bearing_C(12, 0.8) == pytest.approx(2.5) and C.aisi_bearing_C(24, 1.0) == 1.8
    assert C.aisi_bolt_bearing(12, 2, 43, 350, 420) == pytest.approx(13.608)
    assert C.aisi_bolt_bearing(12, 2, 43, 350, 420, mf=1.0) == pytest.approx(18.144)
    assert C.aisi_bolt_bearing(12, 2, 20, 350, 420) == pytest.approx(11.76)
    assert C.aisi_bolt_bearing(12, 2, 20, 400, 420) == pytest.approx(0.60 * 2 * 20 * 420 / 1000)     # Fu/Fy 1.05 < 1.08
    assert C.web_hole(12, 14, 36, 6.0, 355, 490, 0.75) == pytest.approx(C.hole_strength(12, 36, 6.0, 490))   # ≥ 4.76: AISC


def test_primitives_longhand():
    assert C.hole_strength(12, 18, 8, 490) == pytest.approx(0.75 * 84.672, rel=5e-4)
    assert C.hole_strength(12, 96, 8, 490) == pytest.approx(0.75 * 112.896, rel=5e-4)
    assert C.hole_strength(12, 0.0, 8, 490) == 0.0                                    # a hole on the edge: nothing
    assert C.block_shear(1080, 892.8, 337.6, 355, 490) == pytest.approx(296.598, rel=5e-4)
    assert C.block_shear(1080, -1.0, 337.6, 355, 490) == 0.0
    assert C.plate_compression(100, 8, 2.1 * 155, 355) == pytest.approx(62.741, rel=1e-3)
    m = C.plate_moments(100, 8, 155, 355)
    assert m["rule_x"] == "F11-2" and m["phiMx"] == pytest.approx(5973.3, rel=1e-3) and m["phiMy"] == pytest.approx(511.2, rel=1e-6)
    assert C.plate_moments(100, 8, 10, 355)["rule_x"] == "F11-1"                     # Lb d / t² = 15.6 < 45.07: no LTB
    assert C.h1_1(10, 62.741, 0, 5973.3, 150, 511.2) == pytest.approx(0.37312, abs=1e-4)
    assert C.h1_1(20, 62.741, 0, 5973.3, 150, 511.2) == pytest.approx(20 / 62.741 + 8 / 9 * 150 / 511.2, abs=1e-4)


def test_uplift_piece_hand_values():
    r = _rows(C.check_piece(GEOM, PURLIN, {"R": -10.0, "N": 0.0, "F_out": 0.0}, MATS, BOLTS))
    assert r["bolt shear"][5] == pytest.approx(0.16374, abs=1e-4)
    assert r["bearing / tearout - cleat"][4] == pytest.approx(148.176, rel=5e-4)
    assert r["bearing / tearout - web"][4] == pytest.approx(27.216, rel=1e-6)
    assert r["bearing / tearout - web"][5] == pytest.approx(0.367431, rel=1e-5) and "AISI" in r["bearing / tearout - web"][2]
    assert r["block shear - cleat"][4] == pytest.approx(296.598, rel=5e-4)
    assert "block shear - web" not in r                                             # the web runs on: no free edge


def test_gravity_piece_hand_values():
    r = _rows(C.check_piece(GEOM, PURLIN, {"R": 10.0, "N": 0.0, "F_out": 0.0}, MATS, BOLTS))
    assert r["bearing / tearout - cleat"][4] == pytest.approx(169.344, rel=5e-4)
    assert "block shear - cleat" not in r                                           # toward the flange: no free edge


def test_strut_butt_end_tension_fails_compression_passes():
    rt = _rows(C.check_piece(GEOM2, STRUT, {"R": 0.0, "N": 20.0, "F_out": 0.0}, MATS, BOLTS))
    web = rt["bearing / tearout - web"]
    assert web[0] == "strut end" and web[4] == pytest.approx(23.52, rel=1e-6) and web[5] == pytest.approx(0.85034, rel=1e-5)
    assert rt["bearing / tearout - cleat"][4] == pytest.approx(127.008, rel=5e-4)
    assert rt["block shear - web"][4] == pytest.approx(68.6952, rel=5e-4)
    rc = _rows(C.check_piece(GEOM2, STRUT, {"R": 0.0, "N": -20.0, "F_out": 0.0}, MATS, BOLTS))
    assert rc["bearing / tearout - web"][4] == pytest.approx(27.216, rel=1e-6)
    assert rc["bearing / tearout - cleat"][4] == pytest.approx(169.344, rel=5e-4)
    assert "block shear - cleat" not in rc                                          # pushed toward the other column
    # the whole cleat: FAILS with the strut-end fix
    out = C.check_cleat(GEOM2, [STRUT], [[{"combo": "W", "R": 0.0, "N": 25.0, "F_out": 0.0}]], MATS, BOLTS, HOST, 5.0, "S355JR", ST)
    assert out["checks"][0]["U"] == pytest.approx(1.06293, abs=1e-4)
    assert out["status"] == C.FAILS and out["governing"]["name"] == "bearing / tearout - web"
    assert any("butt end" in f for f in out["fixes"])


def test_section_rows():
    rows = _rows(C.check_cleat_section(GEOM, [PURLIN], [{"R": 10.0, "N": 0.0, "F_out": 1.0}], MATS, ST))
    sec = rows["cleat axial (compression) + bending at the flange"]
    assert sec[4] == pytest.approx(62.741, rel=1e-3) and sec[5] == pytest.approx(0.37312, abs=2e-4)
    up = _rows(C.check_cleat_section(GEOM, [PURLIN], [{"R": -10.0, "N": 0.0, "F_out": 0.0}], MATS, ST))
    assert up["cleat axial (tension) + bending at the flange"][4] == pytest.approx(0.9 * 355 * 800 / 1000)
    assert up["cleat net tension at the bolt row"][4] == pytest.approx(0.75 * 490 * (100 - 15.6) * 8 / 1000)
    assert "cleat shear (N)" not in up


def test_weld_flows_and_rows():
    f = C.weld_flows(GEOM, [PURLIN], [{"R": -10.0, "N": 0.0, "F_out": 0.0}])
    assert f["across"] == pytest.approx(112.5) and f["along"] == 0.0 and f["resultant"] == pytest.approx(112.5)
    r = _rows(C.weld_rows(f, 5.0, GEOM, "S355JR", ST))
    wm = [v for k, v in r.items() if k.startswith("weld metal")][0]
    assert wm[4] == pytest.approx(766.86, rel=5e-4) and wm[5] == pytest.approx(0.14670, rel=5e-4)
    bm = [v for k, v in r.items() if k.startswith("base metal")][0]
    assert bm[5] == pytest.approx(112.5 / 1278.0, rel=1e-4)
    fn = C.weld_flows(GEOM, [PURLIN], [{"R": 0.0, "N": 10.0, "F_out": 0.0}])
    assert fn["across"] == pytest.approx(300.0) and fn["along"] == pytest.approx(50.0)
    assert C.weld_leg(700.0, 8.0, ST) == 5.0 and C.weld_leg(800.0, 8.0, ST) == 6.0 and C.weld_leg(99999.0, 8.0, ST) is None


def test_host_rows():
    t = _rows(C.host_rows(HOST, -10.0, GEOM, ST))
    assert t["flange local bending"][4] == pytest.approx(199.69, rel=1e-3)
    near = _rows(C.host_rows({**HOST, "end_distance": 50.0}, -10.0, GEOM, ST))
    assert list(near.values())[0][4] == pytest.approx(99.844, rel=1e-3)
    wide = C.host_rows({**HOST, "bf": 700.0}, -10.0, GEOM, ST)
    assert "not required" in wide[0][1] and wide[0][5] == 0.0
    c = _rows(C.host_rows(HOST, 10.0, GEOM, ST))
    assert c["web local yielding"][4] == pytest.approx(176.79, rel=1e-3)
    assert c["web local crippling"][4] == pytest.approx(240.26, rel=1e-3)
    ce = _rows(C.host_rows({**HOST, "end_distance": 100.0}, 10.0, GEOM, ST))
    assert ce["web local yielding"][4] == pytest.approx(96.915, rel=1e-3)


def test_line_reactions_hand_values():
    q = 2.0                                                                        # kN/m = N/mm
    one = C.line_reactions({"nodes": [0.0, 6000.0], "supports": [0.0, 6000.0], "cases": {"D": [q]}}, 1e6)
    assert one[0.0]["D"] == pytest.approx(6.0, abs=1e-6) and one[6000.0]["D"] == pytest.approx(6.0, abs=1e-6)
    two = C.line_reactions({"nodes": [0.0, 6000.0, 12000.0], "supports": [0.0, 6000.0, 12000.0], "cases": {"D": [q, q]}}, 1e6)
    assert two[0.0]["D"] == pytest.approx(3 * 12 / 8, abs=1e-6) and two[6000.0]["D"] == pytest.approx(10 * 12 / 8, abs=1e-6)
    ov = C.line_reactions({"nodes": [-300.0, 0.0, 6000.0], "supports": [0.0, 6000.0], "cases": {"D": [q, q]}}, 1e6)
    Rl = q * 6300.0 ** 2 / (2 * 6000.0) / 1000.0
    assert ov[0.0]["D"] == pytest.approx(Rl, abs=1e-6) and ov[6000.0]["D"] == pytest.approx(q * 6.3 - Rl, abs=1e-6)
    up = C.line_reactions({"nodes": [0.0, 6000.0], "supports": [0.0, 6000.0], "cases": {"Wout": [-q]}}, 1e6)
    assert up[0.0]["Wout"] == pytest.approx(-6.0, abs=1e-6)                       # uplift: away from the frame


def test_cleat_cases():
    ln = {"kind": "eave_strut"}
    R = {"D": 1.0, "C": 0.5, "Lr": 2.0, "Win": 1.0, "Wout": -3.0}
    cs = {c["combo"]: c for c in C.cleat_cases(ln, R, None, 0.1, 10.0)}
    assert cs["1.4D"]["R"] == pytest.approx(2.1) and cs["1.4D"]["F_out"] == pytest.approx(0.21) and cs["1.4D"]["N"] == 0.0
    assert cs["1.2D+1.6Lr+0.5W"]["R"] == pytest.approx(1.8 + 3.2 + 0.5) and cs["1.2D+1.6Lr+0.5W"]["N"] == pytest.approx(5.0)
    assert cs["1.2D+1.6Lr+0.5W (wind reversed)"]["N"] == pytest.approx(-5.0)
    assert cs["0.9D+1.0W"]["R"] == pytest.approx(0.9 - 3.0) and cs["0.9D+1.0W"]["F_out"] == pytest.approx(0.09)
    wall = {c["combo"]: c for c in C.cleat_cases({"kind": "girt"}, {"Win": 4.0, "Wout": -4.0}, {"D": 1.0}, 0.1, 0.0)}
    assert wall["1.4D"]["R"] == 0.0 and wall["1.4D"]["F_out"] == pytest.approx(1.4)
    assert wall["0.9D+1.0W outward"]["R"] == pytest.approx(-4.0) and wall["0.9D+1.0W outward"]["F_out"] == pytest.approx(0.9)


def test_settings():
    with pytest.raises(ValueError):
        C.CleatSettings(threads="Q").check()
    with pytest.raises(ValueError):
        C.CleatSettings.from_dict({"nope": 1})
    assert C.CleatSettings.from_dict({"K_cleat": 1.0}).K_cleat == 1.0


def _building1():
    from engine.connections.joints import joint_list
    from engine.peb.building import peb_building, resolve
    from engine.tests.test_joints import _sized
    b0, li = _sized()
    b, _ = resolve(b0)
    out = peb_building(b)
    return {"joints": joint_list(b, out)}, out, li


def test_building_1_cleats():
    from engine.design.cfs_checks import building_lines
    jr, out, li = _building1()
    r = C.building_cleats(jr, out, li)
    assert r["banner"].startswith("NOT FOR ISSUE") and r["counts"] == {"DESIGNED": 196}
    assert r["detail"]["weld_leg"] == 5.0 and r["detail"]["bolts"].startswith("2 x M12 8.8")
    assert all(x["governing"]["U"] <= 1.0 for x in r["cleats"])
    # an interior eave-strut cleat: two simple spans (one with the 300 mm overhang) — hand values from the line loads
    lines = {ln["id"]: ln for ln in building_lines(out, li)}
    x = next(x for x in r["cleats"] if x["joint"] == "CL2")
    a, b = lines["RA0-1"]["cases"], lines["RA0-2"]["cases"]
    q = lambda cs, i: 1.2 * (cs["D"][i] + cs["C"][i]) + 1.6 * cs["Lr"][i] + 0.5 * cs["Win"][i]
    qa, qb = q(a, 0), q(b, 0)
    Rl = qa * 6.3 ** 2 / (2 * 6.0)
    hand = (qa * 6.3 - Rl) + qb * 6.0 / 2
    case = next(c for c in x["cases"] if c["combo"] == "1.2D+1.6Lr+0.5W")
    assert case["R"] == pytest.approx(hand, abs=2e-3)
    assert case["F_out"] == pytest.approx(0.1 * hand - 0.1 * 0.5 * (a["Win"][0] * (6.3 - 6.3 ** 2 / 12) + b["Win"][0] * 3.0), abs=2e-3)
    assert [p["e_minus"] for p in x["pieces"]] == [6275.0, 20.0] and [p["along"] for p in x["pieces"]] == [-25.0, 25.0]
    # equilibrium (NEGATIVE CONTROL against a lost reaction): every line's reactions add up to its load
    for ln in lines.values():
        sd = __import__("engine.design.cfs_checks", fromlist=["section_data"]).section_data(ln["profile"], ln["grade"])
        Rs = C.line_reactions(ln, sd["Ix"])
        for case_, qs in ln["cases"].items():
            tot = sum(qq * (ln["nodes"][i + 1] - ln["nodes"][i]) / 1000 for i, qq in enumerate(qs))
            assert sum(R[case_] for R in Rs.values()) == pytest.approx(tot, abs=1e-6)


def test_building_1_not_evaluated():
    jr, out, li = _building1()
    out2 = copy.deepcopy(out)
    for m in out2["members"]:
        if m.get("line") == "RA1":
            m["material"] = "XYZ"
    jr2 = copy.deepcopy(jr)
    j = next(j for j in jr2["joints"] if j["type"] == "cleat" and out2["cleats"][int(j["id"][2:]) - 1]["line"] == "RA2")
    j["members"] = [m for m in j["members"] if "distance" not in m]
    r = C.building_cleats(jr2, out2, li)
    ne = [x for x in r["cleats"] if x["status"] == C.NOT_EVALUATED]
    assert {x["line"] for x in ne} == {"RA1", "RA2"} and len(ne) == 5 + 1
    assert all("checks" not in x for x in ne)                                       # never a U for a missing input
    assert any("web grade" in m for x in ne for m in x["missing"]) and any("host" in m for x in ne for m in x["missing"])
