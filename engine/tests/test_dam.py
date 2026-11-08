# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 2: the Direct Analysis Method (AISC 360-16 Chapter C) in the strength analysis — building 1, frame line 3
(24 m span, eave 6 m, slope 0.1, bays 6 m; V 45 m/s, exposure C).

Independent checks:
    stiffness   a uniformly scaled frame carries the SAME forces and moves 1/0.8 = 1.25 × as far (linear) — so the
                reduction reached every member, and nothing else changed
    notional    statics: Σ horizontal reactions = −0.002 × Σ factored gravity (the gravity summed here from the load list,
                longhand), and the vertical reactions are untouched
    direction   the notional cases follow the combination's net lateral load; gravity-only runs both ways
    τb          αPr/Pns re-computed at the reported station from the result and the section
    C2.3(c)     forced (a tiny Fy): the solver must switch to 0.003·Yi and statics must show it
    service     the unfactored cases and ASD keep the nominal stiffness: identical to a run without the DAM
"""

import pytest

from bimsteelauto.analysis import FrameAnalysis

from engine.analysis.building_analysis import _line_setup
from engine.analysis.solve import (DAM_STIFFNESS, ReducedStiffnessAnalysis, _solve, analyse_frame_line,
                                   strength_combinations)
from engine.peb.building import BuildingInput
from engine.peb.loads_input import LoadsInput

B1 = BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)
SEC = {"roof_kpa": 0.07, "wall_kpa": 0.055}


@pytest.fixture(scope="module")
def line3():
    info, fl, fy = _line_setup(B1, LoadsInput(V=45, exposure="C"), 2, SEC, 0.10, with_fy=True)
    return info, fl, fy, analyse_frame_line(info, fl, fy=fy)


def gravity_total(info, fl, factors):
    """Σ factored vertical load, kN, longhand from the load list (GLOBAL_Y per metre of member, PROJECTED per metre of plan)."""
    g = {m.mark: m for m in info.layout.members}
    tot = 0.0
    for ld in fl.loads:
        f = factors.get(ld.case, 0.0)
        if not f or ld.direction.name not in ("GLOBAL_Y", "GLOBAL_Y_PROJECTED"):
            continue
        m = g[ld.member_mark]
        w = (ld.w + (ld.w if ld.w_end is None else ld.w_end)) / 2
        L = m.length if ld.direction.name == "GLOBAL_Y" else abs(m.j_point[0] - m.i_point[0])
        tot += f * w * L / 1000
    return tot


def test_reduced_stiffness_scales_movement_not_forces():
    info, fl = _line_setup(B1, LoadsInput(V=45, exposure="C"), 2, SEC, 0.10)
    combos = [("WA+L", {"WA+L": 1.0})]
    nom = _solve(FrameAnalysis, info, fl.loads, combos, False)
    red = _solve(ReducedStiffnessAnalysis, info, fl.loads, combos, False, factor=DAM_STIFFNESS)
    for n in ("KA", "KB", "RIDGE"):
        for k in (0, 1):
            assert red.displacements[n]["WA+L"][k] == pytest.approx(nom.displacements[n]["WA+L"][k] / 0.8, rel=1e-6)
    for b in ("BA", "BB"):
        for k in (0, 1):
            assert red.reactions[b]["WA+L"][k] == pytest.approx(nom.reactions[b]["WA+L"][k], rel=1e-6, abs=1e-9)
    # second order: the softer frame is amplified MORE (the reason the DAM reduces stiffness)
    nom2 = _solve(FrameAnalysis, info, fl.loads, [("c", {"D": 1.2, "Lr": 1.6, "WA+L": 0.5})], True)
    red2 = _solve(ReducedStiffnessAnalysis, info, fl.loads, [("c", {"D": 1.2, "Lr": 1.6, "WA+L": 0.5})], True, factor=DAM_STIFFNESS)
    sway = lambda e: (e.displacements["KA"]["c"][0] + e.displacements["KB"]["c"][0]) / 2
    assert sway(red2) / sway(nom2) > 1.25


def test_notional_statics(line3):
    info, fl, fy, r = line3
    for name, factors, ratio in (("LRFD: 1.4D (+C) [+N]", {"D": 1.4, "C": 1.4}, 0.002),
                                 ("LRFD: 1.4D (+C) [-N]", {"D": 1.4, "C": 1.4}, -0.002),
                                 ("LRFD: 1.2D+1.6Lr (+C) [+N]", {"D": 1.2, "C": 1.2, "Lr": 1.6}, 0.002)):
        G = gravity_total(info, fl, factors)
        res = r["results"][name]["reactions"]
        assert sum(v[1] for v in res.values()) == pytest.approx(G, abs=2e-3), name
        assert sum(v[0] for v in res.values()) == pytest.approx(-ratio * G, abs=2e-3), name
    assert r["dam"]["stiffness"] == 0.8 and r["dam"]["notional"] == 0.002


def test_notional_direction_follows_the_lateral_load(line3):
    info, fl, fy, r = line3
    sc = {n: f for n, f, s in strength_combinations(info, fl)}
    assert sc["LRFD: 1.2D+1.0WA+L+0.5Lr (+C)"]["ND"] == pytest.approx(1.2)          # wind from the left pushes +X
    assert sc["LRFD: 1.2D+1.0WA+R+0.5Lr (+C)"]["ND"] == pytest.approx(-1.2)         # from the right: −X
    assert sc["LRFD: 0.9D+1.0WA+L"]["ND"] == pytest.approx(0.9) and "NC" not in sc["LRFD: 0.9D+1.0WA+L"]   # no collateral, no NC
    assert "LRFD: 1.4D (+C)" not in sc and {"LRFD: 1.4D (+C) [+N]", "LRFD: 1.4D (+C) [-N]"} <= set(sc)
    assert sum(1 for c, s in r["combos"] if s == "LRFD") == 22                       # 20 + the 2 gravity-only ones twice
    assert sum(1 for c, s in r["combos"] if s == "ASD") == 20 and sum(1 for c, s in r["combos"] if s == "case") == 9


def test_tau_b_check_by_hand(line3):
    info, fl, fy, r = line3
    t = r["dam"]["tau"]
    assert t["checked"] and t["ok"] and t["tau_b"] == 1.0 and 0 < t["alpha_Pr_Pns"] < 0.5
    m = next(x for x in info.layout.members if x.mark == t["member"])
    st = min(r["results"][t["combo"]]["members"][t["member"]], key=lambda s: abs(s[0] - t["x"]))
    A = m.taper.at(t["x"]).A                                                         # mm²
    assert t["alpha_Pr_Pns"] == pytest.approx(1.0 * st[1] * 1000 / (355 * A), rel=1e-3)   # S355, plates ≤ 16 mm


def test_tau_route_c23c_when_forced():
    info, fl, fy = _line_setup(B1, LoadsInput(V=45, exposure="C"), 2, SEC, 0.10, with_fy=True)
    weak = {k: 1.0 for k in fy}                                                      # 1 MPa: αPr/Pns ≫ 0.5
    r = analyse_frame_line(info, fl, fy=weak, p_delta=False)
    assert r["dam"]["tau"]["ok"] is False and r["dam"]["notional"] == pytest.approx(0.003) and "C2.3(c)" in r["dam"]["tau"]["route"]
    G = gravity_total(info, fl, {"D": 1.4, "C": 1.4})
    res = r["results"]["LRFD: 1.4D (+C) [+N]"]["reactions"]
    assert sum(v[0] for v in res.values()) == pytest.approx(-0.003 * G, abs=2e-3)


def test_service_set_keeps_nominal_stiffness(line3):
    info, fl, fy, r = line3
    plain = analyse_frame_line(info, fl, dam=False)
    for c in ("D", "WA+L", "ASD: 1.0D+0.6WA+L (+C)"):
        assert r["results"][c]["reactions"] == plain["results"][c]["reactions"], c
        assert r["results"][c]["sway"] == plain["results"][c]["sway"], c
    assert plain["dam"] == {"used": False} and sum(1 for c, s in plain["combos"] if s == "LRFD") == 20
