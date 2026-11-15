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
    Lbr           points 1000, 3000 on a 6000 member: 1000 → max(1000, 2000) = 2000; 3000 → max(2000, 3000) = 3000
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


def test_stiffness_and_demand():
    k = S.stiffness_provided(2, 475.0, 700.0, 1 / math.sqrt(2), 8.0, 100.0, 100.0)
    assert k["braces"] == pytest.approx(135.714, abs=1e-3) and k["cleat"] == pytest.approx(400.0) and k["system"] == pytest.approx(101.333, abs=1e-3)
    one = S.stiffness_provided(1, 475.0, 700.0, 1 / math.sqrt(2), 8.0, 100.0, 100.0)
    assert one["braces"] == pytest.approx(135.714 / 2, abs=1e-3)                           # an end frame: one brace
    d = S.point_demand(100.0, 2.0, 400.0, 1500.0)
    assert d["Prb"] == pytest.approx(10.0) and d["beta"] == pytest.approx(4.4444, abs=1e-4)


def test_inflections_cd_lbr():
    rows = [(0.0, 0.0), (1000.0, 10.0), (2000.0, -10.0), (3000.0, 0.0)]
    assert S.inflections(rows) == [1500.0]
    assert S.inflections([(0.0, 0.0), (1000.0, -5.0), (2000.0, -9.0)]) == []         # a pinned end is not an inflection
    assert S.cd_factors([1000.0, 1400.0, 2500.0], rows) == {1000.0: 1.0, 1400.0: 2.0, 2500.0: 1.0}
    assert S.lbr_of([1000.0, 3000.0], (0.0, 6000.0)) == {1000.0: 2000.0, 3000.0: 3000.0}


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
    assert r["counts"]["flange_braces"] == {"PARTIAL": 68}                               # the frame-side end: not in the model
    assert sum(x["n"] for x in r["flange_braces"]) == 116
    assert all(S.FRAME_END_NOTE in x["notes"] and any("E5 condition" in n for n in x["notes"]) for x in r["flange_braces"])
    worst = lambda name: max(next(c["U"] for c in x["checks"] if c["name"] == name) for x in r["flange_braces"])
    assert worst("bearing on the purlin / girt web") == pytest.approx(0.7088, abs=2e-3)
    assert worst("flange brace compression (E5(a), E3)") < 0.2 and worst("brace stiffness βbr (App. 6.3.2a) vs braces + cleat in series") < 0.1
    assert r["cleats"]["counts"] == {"DESIGNED": 196} and r["cleats"]["detail"]["weld_leg"] == 6.0
    assert len(r["cleats_changed"]) == 68 and max(x["U_after"] for x in r["cleats_changed"]) == pytest.approx(0.8889, abs=2e-3)
    # a NEGATIVE CONTROL: 5 × the brace force fails the thin-web bearing, with a fix
    big = S.building_stability_braces(jr, out, an, li, S.StabilitySettings(brace_fraction=0.10))
    assert big["counts"]["flange_braces"].get("FAILS", 0) > 0
    assert all(x["fixes"] for x in big["flange_braces"] if x["status"] == S.FAILS)
