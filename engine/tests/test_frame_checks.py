# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 3: main-frame member checks (engine/design/frame_checks.py) — the Manafe3 plumbing into bimsteelauto's
check_member. The limit states themselves are verified longhand in bimsteelauto (test_e7_slender, test_slender_web_
flexure_shear, test_design_verification; DG 25 in test_nonprismatic / test_dg25_application, NOT VERIFIED).

Independent checks here:
    chain      the section at a distance along a rafter half is its own piece's (splices: each station keeps its piece)
    forces     every station of every chain piece arrives at s0 + x with P, V, M unchanged (synthetic result, by hand)
    strength   Fy = the lowest plate over the whole design member (section_strength by hand)
    longhand   the shear check at a station: 0.90 × 0.6 Fy d tw Cv1 (G2.1, kv 5.34) of the section AT that station
    must fail  the same frame with a moment five times its capacity: ratio > 1, passed False
    building   frame line 3 of building 1 (slow): every member checked, the governing forces are the analysis' own,
               the Ritz cross-check within 1 %, the banner and the open DG 25 flags carried
"""

import math

import pytest

from engine.analysis.frame_model import frame_line_model
from engine.design.frame_checks import BANNER, EPS, ChainTaper, check_frame_line, design_inputs, strengths_by_mark
from engine.design.inputs import design_members, section_strength
from engine.peb.building import BuildingInput, peb_building
from engine.peb.builtup_frame import builtup_frame_members, default_sizes

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)


@pytest.fixture(scope="module")
def setup():
    ms = builtup_frame_members(24000, 6000, 0.1, 12000.0, "3", default_sizes(24000))
    info = frame_line_model(ms, 24000, 6000, 0.1, (6000,) * 4)
    return ms, info, peb_building(BuildingInput(**B1))


def synthetic(info, P=50.0, V=20.0, M=100.0):
    """One LRFD combination; every member: stations at 0, L/2, L with P, V and a moment varying along it."""
    lay = info.layout
    members = {m.mark: [[0.0, P, V, M], [m.length / 2, P, V, 0.5 * M], [m.length, P, V, -M]]
               for m in lay.members if info.roles[m.mark] != "link"}
    return {"combos": [["D", "case"], ["LRFD: test", "LRFD"], ["ASD: test", "ASD"]],
            "results": {"LRFD: test": {"members": members}}}


def test_chain_taper_takes_each_pieces_own_section(setup):
    ms, info, out = setup
    lay = {m.mark: m for m in info.layout.members}
    ra = next(d for d in design_members(info) if d["name"] == "rafter A")
    taper = ChainTaper("rafter A", [(c["s0"], lay[c["mark"]].taper) for c in ra["chain"]])
    assert taper.length == pytest.approx(sum(c["length"] for c in ra["chain"]))
    for c in ra["chain"]:
        t = lay[c["mark"]].taper
        assert taper.at(c["s0"] + EPS) == t.at(EPS)                                     # start of the piece: its own
        assert taper.at(c["s0"] + c["length"] - EPS) == t.at(c["length"] - EPS)          # its end: still its own
    assert len(ra["chain"]) >= 2                                                         # there IS a splice to test


def test_forces_bracing_strength_plumbing(setup):
    ms, info, out = setup
    res = synthetic(info)
    st = strengths_by_mark(ms)
    rows = design_inputs(info, res, out, 12000.0, st)
    assert {dm["name"] for dm, _, _ in rows} == {"column A", "column B", "rafter A", "rafter B"}
    for dm, inp, notes in rows:
        assert list(inp.forces) == ["LRFD: test"]                                        # LRFD only: ASD and cases left out
        sts = inp.forces["LRFD: test"]
        assert len(sts) == 3 * len(dm["chain"])
        for k, c in enumerate(dm["chain"]):
            a, mid, b = sts[3 * k: 3 * k + 3]
            assert (a.station, mid.station, b.station) == pytest.approx((c["s0"] + EPS, c["s0"] + c["length"] / 2, c["s0"] + c["length"] - EPS))
            assert (a.P, a.Vy, a.Mz, b.Mz) == (50.0, 20.0, 100.0, -100.0)
        # Fy: the lowest plate of the whole design member, by hand from the segments
        side = dm["side"]
        m = next(x for x in ms if x["role"] == dm["kind"] and x["side"] == side)
        assert inp.materials.Fy_builtup == min(section_strength(s)["Fy"] for s in m["section"]["segments"])
        assert inp.K_in_plane == 1.0 and inp.stability == "dg25"
        assert inp.bracing.top_flange == tuple(notes["restraints"]["top"]) and inp.bracing.bottom_flange == tuple(notes["restraints"]["bottom"])
    with pytest.raises(ValueError, match="no LRFD"):
        design_inputs(info, {"combos": [["D", "case"]], "results": {}}, out, 12000.0, st)


def test_shear_check_longhand_through_the_chain(setup):
    """Constant V on every station: the shear capacity at the governing station = 0.90 x 0.6 Fy d tw Cv1 of the section
    there (welded: phi 0.90; kv = 5.34, no stiffeners; G2-3 / G2-4) — longhand, SI."""
    ms, info, out = setup
    res = synthetic(info, P=0.0, V=200.0, M=1.0)
    r = check_frame_line(info, res, out, 12000.0, strengths_by_mark(ms), stability="prismatic", compare=False)
    for mem in r["members"]:
        sh = next(c for c in mem["checks"] if c["name"].startswith("Shear"))
        dm, inp, _ = next(x for x in design_inputs(info, res, out, 12000.0, strengths_by_mark(ms)) if x[0]["name"] == mem["name"])
        s = inp.taper.at(mem["x"])
        Fy, E = inp.materials.Fy_builtup, 29000.0 * 6.894757293168361
        lim = 1.10 * math.sqrt(5.34 * E / Fy)
        cv1 = 1.0 if s.h / s.tw <= lim else lim / (s.h / s.tw)
        assert sh["capacity"] == pytest.approx(0.90 * 0.6 * Fy * s.d * s.tw * cv1 / 1000, rel=2e-3), mem["name"]
        assert sh["demand"] == pytest.approx(200.0)


def test_a_section_that_must_fail(setup):
    ms, info, out = setup
    ok = check_frame_line(info, synthetic(info, P=10.0, V=10.0, M=50.0), out, 12000.0, strengths_by_mark(ms), stability="prismatic", compare=False)
    assert all(m["passed"] for m in ok["members"])
    cap = min(next(c for c in m["checks"] if c["name"].startswith("Flexure"))["capacity"] for m in ok["members"])
    bad = check_frame_line(info, synthetic(info, P=10.0, V=10.0, M=5 * cap), out, 12000.0, strengths_by_mark(ms), stability="prismatic", compare=False)
    assert all(not m["passed"] and m["ratio"] > 1.0 for m in bad["members"])
    assert bad["max_ratio"] > 4.0 and bad["banner"] == BANNER


@pytest.mark.slow
def test_frame_line_3_of_building_1(setup):
    from engine.analysis.building_analysis import _line_setup
    from engine.analysis.secondary_weight import secondary_kpa
    from engine.analysis.solve import analyse_frame_line
    from engine.peb.loads_input import LoadsInput

    ms, info0, out = setup
    b = BuildingInput(**B1)
    info, fl, fy = _line_setup(b, LoadsInput(V=45, exposure="C"), 2, secondary_kpa(out), 0.10, with_fy=True)
    res = analyse_frame_line(info, fl, fy=fy)
    r = check_frame_line(info, res, out, 12000.0, strengths_by_mark(ms))
    assert r["banner"] == BANNER and r["stability"] == "dg25" and not r["designed"]
    assert {"design.nonprismatic.dg25_ltb", "design.nonprismatic.dg25_compression"} <= set(r["open_flags"])
    assert 0.1 < r["max_ratio"] < 1.0                                                  # default sizes carry building 1
    by = {m["name"]: m for m in r["members"]}
    assert by["rafter A"]["ratio"] == pytest.approx(by["rafter B"]["ratio"], rel=1e-3)   # symmetric frame and loading
    for m in r["members"]:
        assert m["combo"].startswith("LRFD") and "prismatic_ratio" in m
        for c in m["checks"]:
            if "Ritz cross-check" in c["note"]:
                assert abs(float(c["note"].split("Ritz cross-check")[1].split("(")[1].split("%")[0])) < 1.0
        # the governing forces are the analysis' own at that distance along the chain
        dm = next(d for d in design_members(info) if d["name"] == m["name"])
        # x is reported to 0.1 mm; at a splice both pieces have a station there (their P, V differ slightly: the
        # pieces' centroid lines meet at a small angle), so the governing one must be among the candidates
        cands = [(s[1], s[2], s[3]) for c in dm["chain"] for s in res["results"][m["combo"]]["members"][c["mark"]]
                 if abs(c["s0"] + min(max(s[0], EPS), c["length"] - EPS) - m["x"]) <= 0.1]
        got = (m["forces"]["P"], m["forces"]["V"], m["forces"]["M"])
        assert cands and any(all(math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-9) for a, b in zip(cd, got)) for cd in cands), (cands, got)
