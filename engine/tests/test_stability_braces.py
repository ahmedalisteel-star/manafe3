# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 5c: flange braces, sag rods, ridge ties (engine/connections/stability_braces.py). Independent values
written out longhand below (the angle by two rectangles and parallel axes, NOT the code's closed form).

    ANGLE L50×5   (no root fillets) A = 250 + 225 = 475; centroid 14.342105 from the heel; Ix = 50 × 5³/12 + 250 ×
                  (2.5 − 14.342105)² + 5 × 45³/12 + 225 × (27.5 − 14.342105)² = 112 502.74; Ixy = 250 (25 − 14.342105)
                  (2.5 − 14.342105) + 225 (2.5 − 14.342105)(27.5 − 14.342105) = −66 611.84; Iz = Ix − |Ixy| = 45 890.90;
                  ra = 15.38986, rz = 9.82916
    E5(a)         L 700: L/ra = 45.4845 ≤ 80 → Lc/r = 72 + 0.75 × 45.4845 = 106.1134; Fe = π² 200 000 / 106.1134² =
                  175.3031; Fy/Fe = 2.0251 ≤ 2.25 → Fcr = 0.658^2.0251 × 355 = 152.0982; φPn = 0.9 × 152.0982 × 475 = 65.022 kN
                  leg b/t = 10 ≤ 0.45 √(200 000 / 355) = 10.681 → nonslender
    TENSION       min(0.9 × 355 × 475 = 151.76, 0.75 × 470 × (50 − 14) × 5 = 63.45) = 63.45 kN
    STIFFNESS     a pair, L 700, cos α = 1/√2: 2 × 200 000 × 475 × 0.5 / 700 = 135.714 kN/mm; the PL8 × 100 cleat at y_c 100:
                  3 × 200 000 × (8 × 100³ / 12) / 100³ = 400 kN/mm; in series 1 / (1/135.714 + 1/400) = 101.333 kN/mm
    APP. 6        Mr 100 kN·m, Cd 2, ho 400, Lbr 1500: Prb = 0.02 × 100 000 × 2 / 400 = 10 kN; βbr = 10 × 100e6 × 2 /
                  (0.75 × 1500 × 400) = 4444.4 N/mm = 4.4444 kN/mm
    Cd            M (0, 0) (1000, 10) (2000, −10) (3000, 0): one inflection at 1500 (the zero end moments are not); brace
                  points 1000 / 1400 / 2500 → 1400 gets Cd 2
    Lbr           points 1000, 3000 on a 6000 member: 1000 → max(1000, 2000) = 2000; 3000 → max(2000, 3000) = 3000;
                  the shorter (slip Δo): 1000 → 1000, 3000 → 2000
    H2 (1 bolt)   L50×5, L 700, Fy 355, P 10 kN on the gauge line g 28 at the contact face: (dx, dy) = (13.657895,
                  −14.342105); e_w = 28 / √2 = 19.798990, e_z = 0.684211 / √2 = 0.483810; Iw = 112 502.74 + 66 611.84 =
                  179 114.58; the farthest corners c_w = 50 / √2 = 35.35534 (a toe), c_z = 14.342105 √2 = 20.28280 (the heel): Sz = 1297.991,
                  Sw = 8830.861. Compression: L / rz = 71.21665, Fe 389.194, Fcr = 0.658^(355/389.194) × 355 = 242.3398,
                  Fa = 218.106; Mnz = 1.5 × 355 × 1297.991 = 691 180 N·mm; Myw = 3 134 956, Mcr = 9 × 200 000 × 475 × 9.82916
                  × 5 / (8 × 700) = 7 503 512 → My/Mcr 0.4178 → Mnw = (1.92 − 1.17 √0.4178) Myw = 3 648 283; B1z = 1 / (1 −
                  10 000 / 184 868) = 1.057186, B1w = 1.014054; U = 21.053/218.106 + 1.057186 × 197 990 / 622 062 + 1.014054 ×
                  4838.1 / 3 283 460 = 0.434500; tension (no B1, Fta 319.5): 0.385646
    SPRINGS       braces 135.714, cleat 400, purlin axial 23.782 (the bolt slip is NOT a spring, review 2026-11-15):
                  1 / (1/135.714 + 1/400 + 1/23.782) = 19.2615 kN/mm
    SLIP          a one-time slip 2 mm as an added imperfection, Lbr 1250: Δo = 1250 / 500 = 2.5, × (1 + 2 / 2.5) = 1.8;
                  slip 0 → × 1.0 (the old force). H2 at 10 × 1.8 = 18 kN (L 700): B1z = 1 / (1 − 18 000 / 184 868) =
                  1.107870 → U = 0.811168
    L60×6 H2      (the end-frame fix option) two rectangles: A 684, x̄ 17.210526, Ix 233 285.68, Ixy −138 126.32; Sz = Iz /
                  (60/√2) = 2242.928, Sw = Iw / (17.210526 √2) = 15 259.73; gauge 35: e_w = 35/√2 = 24.748737, e_z =
                  0.578947/√2 = 0.409378; L 700, P 18 kN → U 0.543461
    MERGE         points 100 / 3000 on a 6000 member, tol 150: 100 merges with the end 0 → its only segment 2900 (shorter
                  and longer); 3000 → 2900 / 3000; a wind column 6268.4 with points 1250 / 3750 / 6250: 6250 merges with the
                  top → 2500
    RD12 S355     Ab 113.097: threads 0.75 × 0.75 × 470 × 113.097 = 29.900 kN; body 0.9 × 355 × 113.097 = 36.134 kN;
                  40 × 40 × 4 washer through a 2 mm S350GD web: 0.75 × 0.6 × 420 × 160 × 2 = 60.48 kN
"""

from __future__ import annotations

import math

import pytest

from engine.connections import stability_braces as S
from engine.connections.cleats import cleat_cases


def test_angle_properties_and_strength():
    a = S.angle_props(50.0, 5.0)
    assert a["A"] == 475.0 and a["xbar"] == pytest.approx(14.342105, abs=1e-6)
    assert a["Ix"] == pytest.approx(112502.74, abs=0.01) and a["Ixy"] == pytest.approx(-66611.84, abs=0.01)
    assert a["ra"] == pytest.approx(15.38986, abs=1e-5) and a["rz"] == pytest.approx(9.82916, abs=1e-5)
    c = S.angle_compression(50.0, 5.0, 700.0, 355.0)
    assert c["Lc_r"] == pytest.approx(106.1134, abs=1e-3) and c["phiPn"] == pytest.approx(65.022, rel=5e-4)
    assert not c["slender_leg"] and S.angle_compression(50.0, 4.0, 700.0, 355.0)["slender_leg"]     # b/t 12.5 > 10.68
    assert S.angle_tension(50.0, 5.0, 14.0, 355.0, 470.0) == pytest.approx(63.45)


def test_angle_eccentric_h2():
    c = S.angle_eccentric(50.0, 5.0, 700.0, 355.0, 10.0, 28.0)
    assert c["e_w"] == pytest.approx(19.798990, abs=1e-6) and c["e_z"] == pytest.approx(0.483810, abs=1e-6)
    assert c["Sz"] == pytest.approx(1297.991, abs=1e-3) and c["Sw"] == pytest.approx(8830.861, abs=1e-2)
    assert c["Mnw"] == pytest.approx(3648283.0, rel=1e-5) and c["B1z"] == pytest.approx(1.057186, abs=1e-6)
    assert c["U"] == pytest.approx(0.434500, abs=1e-5)
    assert S.angle_eccentric(50.0, 5.0, 700.0, 355.0, -10.0, 28.0)["U"] == pytest.approx(0.385646, abs=1e-5)
    # NEGATIVE CONTROL: the eccentric angle is far weaker than E5 would say (E5 phiPn 65.0 kN -> U 0.154 at 10 kN)
    assert c["U"] > 2.5 * 10.0 / S.angle_compression(50.0, 5.0, 700.0, 355.0)["phiPn"]
    assert S.angle_eccentric(50.0, 5.0, 700.0, 355.0, 30.0, 28.0)["U"] > 1.0


def test_stiffness_and_demand():
    k = S.stiffness_provided(2, 475.0, 700.0, 1 / math.sqrt(2), 8.0, 100.0, 100.0)
    assert k["braces"] == pytest.approx(135.714, abs=1e-3) and k["cleat"] == pytest.approx(400.0) and k["system"] == pytest.approx(101.333, abs=1e-3)
    ks = S.stiffness_provided(2, 475.0, 700.0, 1 / math.sqrt(2), 8.0, 100.0, 100.0, k_secondary=23.782)
    assert ks["system"] == pytest.approx(19.2615, abs=1e-4) and ks["web local bending"] == math.inf
    assert "bolt slip" not in ks                                                   # a one-time slip is not a spring


def test_l60_fix_option_h2():
    assert S.angle_eccentric(60.0, 6.0, 700.0, 355.0, 18.0, 35.0)["U"] == pytest.approx(0.543461, abs=1e-5)


def test_slip_as_imperfection():
    assert S.slip_factor(2.0, 1250.0) == pytest.approx(1.8)
    assert S.slip_factor(0.0, 1250.0) == 1.0                                       # NEGATIVE CONTROL: no slip, the old force
    P = 10.0 * S.slip_factor(2.0, 1250.0)
    c = S.angle_eccentric(50.0, 5.0, 700.0, 355.0, P, 28.0)
    assert c["B1z"] == pytest.approx(1.107870, abs=1e-6) and c["U"] == pytest.approx(0.811168, abs=1e-5)
    one = S.stiffness_provided(1, 475.0, 700.0, 1 / math.sqrt(2), 8.0, 100.0, 100.0)
    assert one["braces"] == pytest.approx(135.714 / 2, abs=1e-3)                           # an end frame: one brace
    d = S.point_demand(100.0, 2.0, 400.0, 1500.0)
    assert d["Prb"] == pytest.approx(10.0) and d["beta"] == pytest.approx(4.4444, abs=1e-4)


def test_brace_groups_ridge():
    """The ridge group (user 2026-11-17): building 1's rafter flange knee A → ridge → knee B, each half 11 562.3 mm (the 5c
    model), flange-brace points at 688.6 / 1874.6 / 3060.4 / 11 362.3 on each half; side B maps to u = 23 124.6 − s.
    The ridge-purlin points 11 362.3 and 11 762.3 are 400 mm apart (< 500) → ONE group; outside it: 11 362.3 − 3060.4 =
    8301.9 on the left, (23 124.6 − 3060.4) − 11 762.3 = 8301.9 on the right → Lbr = Lsh = 8301.9; slip factor 1 + 2 /
    (8301.9 / 500) = 1.120454. NEGATIVE CONTROLS: group distance 0 → the two points stand alone, the shorter segment is
    the 400 mm between them → factor 3.5; and the OLD half-rafter rule (the ridge end a brace point) → 11 562.3 − 11 362.3
    = 200 mm → factor 6.0."""
    half, sA = 11562.3, [688.6, 1874.6, 3060.4, 11362.3]
    us = sA + [2 * half - x for x in sA]
    g = S.brace_groups(us, (0.0, 2 * half), 500.0, 150.0)
    ridge = next(x for x in g if len(x["members"]) == 2)
    assert sorted(us[i] for i in ridge["members"]) == [pytest.approx(11362.3), pytest.approx(11762.3)]
    assert ridge["Lbr"] == pytest.approx(8301.9) and ridge["Lsh"] == pytest.approx(8301.9)
    assert S.slip_factor(2.0, ridge["Lsh"]) == pytest.approx(1.120454, abs=1e-6)
    assert len(g) == 7 and all(len(x["members"]) == 1 for x in g if x is not ridge)
    alone = S.brace_groups(us, (0.0, 2 * half), 0.0, 150.0)
    p = next(x for x in alone if abs(us[x["members"][0]] - 11362.3) < 0.01)
    assert p["Lsh"] == pytest.approx(400.0) and S.slip_factor(2.0, p["Lsh"]) == pytest.approx(3.5)
    old = S.lbr_short_of(sA, (0.0, half))[11362.3]
    assert old == pytest.approx(200.0) and S.slip_factor(2.0, old) == pytest.approx(6.0)
    # a flange end within 150 mm merges (the wind-column top 18.4 mm): only the segment below counts
    wc = S.brace_groups([1250.0, 3750.0, 6250.0], (0.0, 6268.4), 500.0, 150.0)
    assert wc[-1]["Lsh"] == wc[-1]["Lbr"] == pytest.approx(2500.0) and wc[-1]["near_end"] == [6268.4]


def test_inflections_cd_lbr():
    rows = [(0.0, 0.0), (1000.0, 10.0), (2000.0, -10.0), (3000.0, 0.0)]
    assert S.inflections(rows) == [1500.0]
    assert S.inflections([(0.0, 0.0), (1000.0, -5.0), (2000.0, -9.0)]) == []         # a pinned end is not an inflection
    # NEGATIVE CONTROL for the Cd fix (review 2026-11-15): a pinned base (M 0) with single curvature -> Cd 1 everywhere
    pinned = [(0.0, 0.0), (1250.0, -40.0), (2500.0, -80.0), (5000.0, -160.0), (6000.0, -190.0)]
    assert S.cd_factors([3750.0, 5000.0], pinned) == {3750.0: 1.0, 5000.0: 1.0}
    assert S.cd_factors([1000.0, 1400.0, 2500.0], rows) == {1000.0: 1.0, 1400.0: 2.0, 2500.0: 1.0}
    assert S.lbr_of([1000.0, 3000.0], (0.0, 6000.0)) == {1000.0: 2000.0, 3000.0: 3000.0}
    # the slip imperfection's Δo uses the SHORTER adjacent segment (user 2026-11-16): 1000 → 1000, 3000 → 2000
    assert S.lbr_short_of([1000.0, 3000.0], (0.0, 6000.0)) == {1000.0: 1000.0, 3000.0: 2000.0}
    # a point within 150 mm of an end / another point merges with it: the segment beyond is used (user 2026-11-16)
    assert S.lbr_short_of([100.0, 3000.0], (0.0, 6000.0), 150.0) == {100.0: 2900.0, 3000.0: 2900.0}
    assert S.lbr_of([100.0, 3000.0], (0.0, 6000.0), 150.0) == {100.0: 2900.0, 3000.0: 3000.0}
    assert S.lbr_short_of([1250.0, 3750.0, 6250.0], (0.0, 6268.4), 150.0)[6250.0] == 2500.0
    assert S.lbr_short_of([1250.0, 3750.0, 6250.0], (0.0, 6268.4))[6250.0] == pytest.approx(18.4)   # NEGATIVE CONTROL: no merge
    assert S.merged_points([100.0, 3000.0], (0.0, 6000.0), 150.0) == [{"s": 100.0, "near": 0.0, "distance": 100.0,
                                                                       "with": "member end"}]


def test_rod_rows():
    r = {x[1]: x for x in S.rod_rows(10.0, 12.0, 355.0, 470.0, 2.0, 420.0, 40.0)}
    assert r["rod threads"][4] == pytest.approx(29.900, abs=1e-3) and r["rod body yield"][4] == pytest.approx(36.134, abs=1e-3)
    assert r["plate washer pulled through the web"][4] == pytest.approx(60.48)


def test_cleat_cases_with_flange_brace_force():
    cs = {c["combo"]: c for c in cleat_cases({"kind": "purlin"}, {"D": 1.0, "C": 0.0, "Lr": 0.0, "Win": 1.0, "Wout": -1.0},
                                             None, 0.1, 0.0, 5.0)}
    assert cs["1.4D + flange brace"]["N"] == 5.0 and cs["1.4D - flange brace"]["N"] == -5.0 and "1.4D" not in cs
    assert cs["0.9D+1.0W - flange brace"]["R"] == pytest.approx(0.9 - 1.0)


def _building1():
    from engine.connections.joints import joint_list
    from engine.peb.building import peb_building, resolve
    from engine.tests.test_joints import _sized
    b0, li = _sized()
    b, _ = resolve(b0)
    out = peb_building(b)
    return {"joints": joint_list(b, out)}, out, li


def test_sag_rods_and_ties_without_analysis():
    jr, out, li = _building1()
    r = S.building_stability_braces(jr, out, {"frames": []}, li)
    # no frame moments → every rafter / column brace point NOT EVALUATED, never a U (negative control)
    fr = [x for x in r["flange_braces"] if x.get("host_role") in ("rafter", "column")]
    assert fr and all(x["status"] == S.NOT_EVALUATED and "checks" not in x for x in fr)
    assert r["counts"]["sag_rods"] == {"DESIGNED": 8} and r["counts"]["ridge_ties"] == {"DESIGNED": 4}
    sf = r["sag_forces"]
    c = 1 / math.sqrt(1 + 0.1 ** 2)
    for side, rows in sf["sides"].items():
        for row, rec in rows.items():
            for combo, v in rec["combos"].items():
                Ts = [p["T"] for p in v["pieces"]]
                assert Ts == sorted(Ts)                                         # accumulating up the slope
                assert v["tie"] == pytest.approx(v["slope_total"] * c)
                assert len(v["pieces"]) == len(rec["lines"]) - 1
    # the tie takes the larger slope's total
    tie = r["ridge_ties"][0]
    tot = max(rec["combos"][tie["combo"]]["tie"] for rows in sf["sides"].values() for rr, rec in rows.items() if abs(rr - tie["row"]) < 0.1)
    assert tie["T"] == pytest.approx(tot, abs=1e-3)


def test_sag_equilibrium():
    """NEGATIVE CONTROL against a lost load: a roof line's weak-axis reactions (frames + rows) add up to tan θ × its load."""
    from engine.connections.cleats import line_reactions
    from engine.design.cfs_checks import building_lines, tied_rows
    jr, out, li = _building1()
    ok, bad = tied_rows(out)
    ln = next(x for x in building_lines(out, li) if x["kind"] == "purlin")
    rows = [r for r in ok + bad if ln["nodes"][0] < r < ln["nodes"][-1]]
    nodes = sorted(set(ln["nodes"] + rows))
    q = [0.1 * ln["cases"]["D"][0]] * (len(nodes) - 1)
    R = line_reactions({**ln, "nodes": nodes, "supports": sorted(set(ln["supports"] + rows)), "cases": {"D": q}}, 4.27e6)
    assert sum(v["D"] for v in R.values()) == pytest.approx(q[0] * (nodes[-1] - nodes[0]) / 1000, abs=1e-6)


@pytest.mark.slow
def test_building_1_step_5c():
    from engine.analysis.building_analysis import analyse_building
    jr, out, li = _building1()
    from engine.peb.building import resolve
    from engine.tests.test_joints import _sized
    b, _ = resolve(_sized()[0])
    an = analyse_building(b, li)
    r = S.building_stability_braces(jr, out, an, li)
    # + the 10 ridge-purlin points (open item 11), each ridge pair one group (2026-11-17): PARTIAL, web U 0.129 / 0.139
    assert r["counts"]["flange_braces"] == {S.FAILS_AISI: 34, "FAILS": 4, "PARTIAL": 40}
    rp = [x for x in r["flange_braces"] if x["s"] > 11000 and x["host_role"] == "rafter"]
    assert len(rp) == 10 and all(x["status"] == "PARTIAL" and x["demand"]["L_short"] == pytest.approx(8301.9, abs=0.2)
                                 and x["demand"]["slip_factor"] == pytest.approx(1.1205, abs=1e-3) for x in rp)
    assert sorted({x["split"]["group_braces"] for x in rp}) == [2, 4]                 # end frames 2, interior 4
    for x in (x for x in r["flange_braces"] if x["status"] == S.FAILS_AISI):
        Uw = next(c["U"] for c in x["checks"] if c["key"] == "web")
        assert x["fix_options"][0] == f"2 bolts per end: web bearing U {Uw / 2:.3f} (E5 then applies instead of H2)"
        assert "gauge in that bay: t ≥" in x["fix_options"][1]
        assert x["demand"]["slip_factor"] == pytest.approx(1 + 2.0 / (x["demand"]["L_short"] / 500), rel=5e-3)
    plain = [x for x in r["flange_braces"] if x["status"] == "FAILS"]               # the end-frame first purlin: H2 > 1 too
    assert len(plain) == 4 and all(any(c["U"] > 1 and "H2" in c["name"] for c in x["checks"]) for x in plain)
    for x in plain:                                                                  # the H2 fix options with their U
        P, L = x["demand"]["P_brace"], 692.676
        assert f"2 bolts per end: E5 compression U {P / S.angle_compression(50.0, 5.0, L, 355.0)['phiPn']:.3f}" in x["fix_options"]
        assert f"L60x6 (gauge 35 mm, 1 bolt): H2 compression U {S.angle_eccentric(60.0, 6.0, L, 355.0, P, 35.0)['U']:.3f}" in x["fix_options"]
    # the pair split (user 2026-11-16): equal braces half each, an end-frame single brace the full force
    # the ridge groups share by stiffness over all their braces: interior 4 → 0.25 each, end frames 2 → 0.5 each
    assert sorted({tuple(x["split"]["shares"]) for x in r["flange_braces"]}) == [(0.25, 0.25), (0.5,), (0.5, 0.5), (1.0,)]
    assert sum(1 for x in r["flange_braces"] if x["split"]["n"] == 1) == 20 + 4
    # brace points within 150 mm of a member end merge — the wind-column tops (geometry warnings for step 7)
    assert sorted(w["host"] for w in r["geometry_warnings"]) == ["WF1", "WF3", "WL1", "WL3"]
    top = max(r["flange_braces"], key=lambda x: x["demand"]["slip_factor"])        # WF2 / WL2: 618 mm below the top, no merge
    assert top["demand"]["slip_factor"] == pytest.approx(1 + 2 / (618.4 / 500), abs=1e-3) and top["host"] in ("WF2", "WL2")
    assert sum(x["n"] for x in r["flange_braces"]) == 116 + 16
    assert all(S.FRAME_END_NOTE in x["notes"] and any("E5 does not apply" in n for n in x["notes"]) for x in r["flange_braces"])
    assert not any(c["name"].startswith("flange brace compression (E5") for x in r["flange_braces"] for c in x["checks"])
    worst = lambda name: max(next(c["U"] for c in x["checks"] if c["name"] == name) for x in r["flange_braces"])
    assert worst("bearing on the purlin / girt web") == pytest.approx(1.6247, abs=2e-3)
    assert worst("flange brace compression on the gauge line (1 bolt: H2, eccentric both axes)") == pytest.approx(1.0121, abs=2e-3)
    assert worst("brace stiffness βbr (App. 6.3.2a) vs every spring in series") == pytest.approx(0.3609, abs=2e-3)
    assert all(x["stiffness"]["web_normal_cos"] < 1e-6 and x["demand"]["slip_mm"] == 2.0 for x in r["flange_braces"])
    for x in r["flange_braces"]:
        dm = x["demand"]
        assert dm["slip_factor"] == pytest.approx(1 + 2.0 / (dm["L_short"] / 500), rel=5e-3)   # L_short printed to 0.1 mm
        assert dm["L_short"] <= dm["Lbr"] + 1e-6
        assert dm["Prb_amplified"] == pytest.approx(dm["Prb"] * dm["slip_factor"], abs=2e-3 + 5e-4 * dm["slip_factor"])
    # the weld capped at J2.2b (6 mm on PL8): every cleat needing more fails its weld, with the PL10 option and its U
    assert r["cleats"]["counts"] == {"DESIGNED": 174, "FAILS": 22} and r["cleats"]["detail"]["weld_leg"] == 6.0
    for x in (x for x in r["cleats"]["cleats"] if x["status"] == "FAILS"):
        w = next(c for c in x["checks"] if c["name"].startswith("weld metal"))
        assert w["U"] > 1 and f"→ U {w['U'] * 6 / 8:.3f} at 8 mm" in " ".join(x["fix_options"])
    for x in r["cleats"]["cleats"]:
        bad = [c for c in x["checks"] if c["U"] > 1] if "checks" in x else []
        if x["status"] == "FAILS":
            assert any(not c["ref"].startswith("AISI") for c in bad)
        elif x["status"] == S.FAILS_AISI:
            assert bad and all(c["ref"].startswith("AISI") for c in bad)
    j = r["cleats"]["weld_j2_2b"]
    assert (j["t_cleat"], j["max_leg"], j["leg"], j["sized_leg"], j["capped"]) == (8.0, 6.0, 6.0, 10.0, True)
    assert len(j["cleats_needing_more_than_max"]) == 22
    assert max(x["U_after"] for x in r["cleats_changed"]) == pytest.approx(1.3998, abs=2e-3)
    # NEGATIVE CONTROL: slip 0 gives the old forces (all PARTIAL, the cleats 196 DESIGNED with a 6 mm weld)
    r0 = S.building_stability_braces(jr, out, an, li, S.StabilitySettings(slip=0.0))
    assert r0["counts"]["flange_braces"] == {"PARTIAL": 78} and r0["cleats"]["counts"] == {"DESIGNED": 196}
    assert r0["cleats"]["detail"]["weld_leg"] == 6.0 and not r0["cleats"]["weld_j2_2b"]["capped"]
    assert all(x["fixes"] for x in r["flange_braces"] if x["status"] == S.FAILS)
    # 2 bolts per end: E5 instead of H2 (and the H2 rows gone)
    two = S.building_stability_braces(jr, out, an, li, S.StabilitySettings(bolts_per_end=2))
    names = {c["name"] for x in two["flange_braces"] for c in x["checks"]}
    assert "flange brace compression (E5(a), E3)" in names and not any("H2" in n for n in names)
