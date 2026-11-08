# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 7: end walls of building 1 (24 × 24 m, eave 6 m, slope 0.1, bays 4 × 6 m; first end wall = end rafter
on wind columns, last = main frame; V 45 m/s, exposure C).

Checked: the wind-column strips and the longitudinal feed (areas longhand, total = bimsteelauto's p × area);
the end-rafter frame by statics computed LONGHAND from the geometry (not from the module's own tally) and by an
independent anastruct model of the same frame under Lr (hinged column tops, pinned bases, one lateral restraint —
under Lr the end-wall diagonals carry nothing, so it is the same structure); the end-wall bracing load path.
"""

import math

import pytest
from anastruct import SystemElements

from bimsteelauto.sections import WeldedI

from engine.analysis.endwall_analysis import end_rafter_frame, longitudinal_feed, wind_columns
from engine.analysis.frame_loads import STEEL_KN_M3
from engine.peb.building import BuildingInput, peb_building
from engine.peb.endwall import WIND_COLUMN
from engine.peb.loads_input import LoadsInput

LI = LoadsInput(V=45, exposure="C")


@pytest.fixture(scope="module")
def out():
    return peb_building(BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4, end_first="rafter"))


@pytest.fixture(scope="module")
def frame(out):
    return end_rafter_frame(out, "first", LI)


def test_wind_column_strips(out):
    """The strips (C&C values themselves: test_cc_wind.py)."""
    cols = {c["id"]: c for c in wind_columns(out, LI)["columns"]}
    assert set(cols) == {"WF1", "WF2", "WF3", "WF4", "WF5", "WL1", "WL2", "WL3"}            # the frame end: interior only
    # strips: supports 125 / 6000 / 12000 / 18000 / 23875 at both ends; corner strips to the building edge
    assert cols["WF1"]["strip_m"] == pytest.approx(3.0625) and cols["WF2"]["strip_m"] == pytest.approx(5.9375)
    assert cols["WL2"]["strip_m"] == pytest.approx(6.0)
    assert sum(cols[k]["strip_m"] for k in ("WF1", "WF2", "WF3", "WF4", "WF5")) == pytest.approx(24.0)


def test_longitudinal_feed_actual_top_reactions(out):
    """Longhand: one end wall is 24 × 6 + 24 × 1.2 / 2 = 158.4 m². Each support's strip, a simple beam of its own height,
    gives half its strip × height to the top, half to the base, and the wall above its top straight to the roof. So per
    wall top + base = 158.4 m², and the total force = bimsteelauto's net longitudinal pressure × 158.4 (its §28.3.4
    minimum included). The eave share is no longer a blanket 0.5 (negative control: it must differ)."""
    f = longitudinal_feed(out, LI)
    for end in ("first", "last"):
        w = f["walls"][end]
        assert w["top_m2"] + w["base_m2"] == pytest.approx(158.4, abs=1e-6)
    # the last wall (main frame): corner columns held at the eave (6.0 m), wind columns to under the rafter
    assert [r["height_m"] for r in f["walls"]["last"]["supports"]] == [6.0, 6.1638, 6.7638, 6.1638, 6.0]
    # WL2 by hand: strip 9 → 15 m, height 6.7638; wall area under the roof = 2 × 3 × (6.9 + 7.2) / 2 = 42.3 m²
    s = f["walls"]["last"]["supports"][2]
    area = 3.0 * (6.0 + 0.1 * 9.0 + 6.0 + 0.1 * 12.0) / 2 * 2                         # 9→12 and 12→15, symmetric
    assert s["area_m2"] == pytest.approx(area, abs=1e-6) and s["base_m2"] == pytest.approx(6.0 * 6.7638 / 2, abs=5e-4)   # height typed to 0.1 mm
    assert s["top_m2"] == pytest.approx(area - 6.0 * 6.7638 / 2, abs=5e-4)
    gc_net = 0.40 - (-0.29)                                                              # Load Case B, zones 5 − 6
    assert f["p_net_kpa"] == pytest.approx(f["minimum_scale"] * 0.94843 * gc_net, abs=1e-4)
    assert f["minimum_scale"] > 1.0                                                      # §28.3.4 governs on this building
    tot = f["F_eave"] + f["F_base"]
    assert tot == pytest.approx(f["p_net_kpa"] * 158.4, rel=1e-4)                        # same total as bimsteelauto's p × area
    share = f["F_eave"] / tot
    assert 0.51 < share < 0.56 and abs(share - 0.5) > 0.01                               # the real split, not 0.5


@pytest.mark.slow
def test_end_frame_statics_longhand(out, frame):
    raf = next(m for m in out["members"] if m["id"] == "EFRA")["section"]["segments"][0]
    A_r = (raf["hw_start"] * raf["tw"] + raf["bf_top"] * raf["tf_top"] + raf["bf_bot"] * raf["tf_bot"]) * 1e-6
    A_c = (WIND_COLUMN["hw"] * WIND_COLUMN["tw"] + 2 * WIND_COLUMN["bf"] * WIND_COLUMN["tf"]) * 1e-6
    sloped = 24.0 * math.sqrt(1.01)                                                # m, both slopes
    trib = 3.0                                                                     # half the 6 m end bay
    assert frame["tributary_m"] == pytest.approx(trib)
    # the wind columns, modelled from the base to the rafter's centroid line: heights from the model's own nodes are
    # not used — longhand: roof line minus the centroid's plumb depth (symmetric section: d/2 × √1.01)
    d = raf["hw_start"] + raf["tf_top"] + raf["tf_bot"]
    e = d / 2 * math.sqrt(1.01) / 1000
    h = sum(6.0 + 0.1 * min(y, 24 - y) - e for y in (0.125, 6.0, 12.0, 18.0, 23.875))
    D = A_r * STEEL_KN_M3 * sloped + 0.07 * trib * sloped + A_c * STEEL_KN_M3 * h  # single skin 0.07 kN/m²
    Lr = 0.58 * trib * 24.0                     # At 72 m² = 775 ft² → R1 = 1.2 − 0.775 < 0.6 → 0.6; 0.96 × 0.6 < 0.58 floor
    C = 0.10 * trib * 24.0
    for case, total in (("D", D), ("Lr", Lr), ("C", C)):
        res = frame["results"][case]
        assert sum(v[1] for v in res["reactions"].values()) == pytest.approx(total, rel=1e-4, abs=3e-3), case   # 5 × 0.0005 rounding
        assert all(v == 0.0 for v in res["braces"].values()) and all(abs(v[0]) < 1e-6 for v in res["reactions"].values())
    # wind: horizontal balance — no external restraint any more, the bracing lands on the column bases
    for case in ("WA+L", "WB+"):
        res = frame["results"][case]
        fx, fy = frame["applied"][case]
        assert sum(v[0] for v in res["reactions"].values()) + fx == pytest.approx(0.0, abs=4e-3)   # values rounded to 0.001
        assert sum(v[1] for v in res["reactions"].values()) + fy == pytest.approx(0.0, abs=4e-3)   # 6 values rounded to 0.001
    s = frame["summary"]
    assert s["rafter_M_LRFD"][0].startswith("LRFD: ") and s["apex_ASD"][0].startswith("ASD: ")


@pytest.mark.slow
def test_end_frame_vs_anastruct_under_Lr(out, frame):
    raf = next(m for m in out["members"] if m["id"] == "EFRA")["section"]["segments"][0]
    d = raf["hw_start"] + raf["tf_top"] + raf["tf_bot"]
    e = d / 2 * math.sqrt(1.01) / 1000
    zc = lambda y: 6.0 + 0.1 * min(y, 24 - y) - e
    ys = [0.0, 0.125, 6.0, 12.0, 18.0, 23.875, 24.0]
    ss = SystemElements()
    # the real sections (the reactions of a continuous beam on axially flexible props depend on EI / EA)
    rw = WeldedI(d=d, tw=raf["tw"], bf_top=raf["bf_top"], tf_top=raf["tf_top"], bf_bot=raf["bf_bot"], tf_bot=raf["tf_bot"])
    cw = WeldedI(d=WIND_COLUMN["hw"] + 2 * WIND_COLUMN["tf"], tw=WIND_COLUMN["tw"], bf_top=WIND_COLUMN["bf"], tf_top=WIND_COLUMN["tf"],
                 bf_bot=WIND_COLUMN["bf"], tf_bot=WIND_COLUMN["tf"])
    E = 2e8                                               # kN/m²
    for a, b in zip(ys, ys[1:]):
        el = ss.add_element([[a, zc(a)], [b, zc(b)]], EA=E * rw.A * 1e-6, EI=E * rw.Ix * 1e-12)
        L = math.hypot(b - a, zc(b) - zc(a))
        ss.q_load(q=-0.58 * 3.0 * (b - a) / L, element_id=el, direction="y")
    bases = {}
    for k, y in enumerate((0.125, 6.0, 12.0, 18.0, 23.875)):
        ss.add_element([[y, 0.0], [y, zc(y)]], EA=E * cw.A * 1e-6, EI=E * cw.Ix * 1e-12, spring={2: 0})
        bases[f"WF{k + 1}"] = ss.find_node_id([y, 0.0])
        ss.add_support_hinged(bases[f"WF{k + 1}"])
    ss.add_support_roll(ss.find_node_id([0.0, zc(0.0)]), direction="y")   # "y" = holds x (pinned in the probe)
    ss.solve()
    rf = ss.reaction_forces
    res = frame["results"]["Lr"]["reactions"]
    for cid, n in bases.items():
        assert -rf[n].Fy == pytest.approx(res[cid][1], rel=0.01), cid


@pytest.mark.slow
def test_end_wall_bracing_geometry_and_load_path(out, frame):
    """Default: one braced bay (bay 1, between the corner column at y 125 and WF2 at 6 000) on the end-rafter wall, none on
    the main-frame wall. Geometry by hand: the wind columns' centre plane x = −125 + (300 + 2·8)/2 = 33; XF1a from WF1's base
    to 100 below WF2's top (6 163.835 → 6 063.835): length √(5 875² + 6 063.835²) = 8 443.087.
    Load path: everything horizontal that reaches rafter level (roof wind + half of each corner column's side-wall wind,
    a pinned-pinned column) goes into ONE diagonal: T·cos θ = H_roof; the other diagonal is slack (negative control), and
    the wind from the other side loads the other diagonal."""
    xb = {m["id"]: m for m in out["members"] if m["role"] == "endwall_brace"}
    assert set(xb) == {"XF1a", "XF1b"} and xb["XF1a"]["profile"] == "RD20"
    assert xb["XF1a"]["start"] == [33.0, 125.0, 0.0] and xb["XF1a"]["end"][2] == pytest.approx(6063.835, abs=1e-3)
    assert xb["XF1a"]["length"] == pytest.approx(8443.087, abs=1e-3)
    for case, works, slack in (("WA+L", "XF1a", "XF1b"), ("WA+R", "XF1b", "XF1a"), ("WB+", "XF1b", "XF1a")):
        b = frame["results"][case]["braces"]
        H = frame["roof_H"][case]
        assert b[works] * frame["brace_cos"][works] == pytest.approx(abs(H), abs=2e-3), case
        assert b[slack] == 0.0, case
    assert frame["summary"]["brace_T_LRFD"][0].startswith("LRFD: ")


def test_end_rafter_wall_without_bracing_is_refused():
    o = peb_building(BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4, end_first="rafter", end_braced_bays=()))
    assert not any(m["role"] == "endwall_brace" for m in o["members"])
    with pytest.raises(ValueError, match="no in-plane stability"):
        end_rafter_frame(o, "first", LI)
    with pytest.raises(ValueError, match="does not exist"):
        peb_building(BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4, end_first="rafter", end_braced_bays=(5,)))


@pytest.mark.slow
def test_end_frame_strength_by_the_direct_analysis_method(frame):
    """LRFD on the end frame: 0.8 stiffness, 4 elements per member, notional 0.002·Yi. Statics: under 1.4D [±N] the
    horizontal base reactions (the braced column bases included) balance 0.002 × the factored gravity, in the right
    direction, and one diagonal carries it while the other is slack; the vertical reactions are the gravity."""
    d = frame["dam"]
    assert d["stiffness"] == 0.8 and d["min_segments"] == 4 and d["notional"] == 0.002 and d["tau"]["ok"]
    G = 1.4 * (-(frame["applied"]["D"][1] + frame["applied"]["C"][1]))                   # kN down, from the load tally
    for name, sg in (("LRFD: 1.4D (+C) [+N]", 1.0), ("LRFD: 1.4D (+C) [-N]", -1.0)):
        r = frame["results"][name]
        assert r["set"] == "LRFD"
        assert sum(v[1] for v in r["reactions"].values()) == pytest.approx(G, abs=5e-3)
        assert sum(v[0] for v in r["reactions"].values()) == pytest.approx(-sg * 0.002 * G, abs=5e-3)
        assert sum(1 for v in r["braces"].values() if v > 0) == 1                       # one diagonal works
    assert "LRFD: 1.4D (+C)" not in frame["results"] and frame["results"]["D"]["set"] == "case"


@pytest.mark.slow
def test_rod_tension_never_below_statics(frame):
    """Every LRFD combination: the working diagonal carries at least H / cos θ (statics: the pinned columns take no
    shear), and the other diagonal nothing."""
    for c, r in frame["results"].items():
        if r["set"] != "LRFD":
            continue
        work = "XF1a" if r["roof_H"] >= 0 else "XF1b"
        idle = "XF1b" if work == "XF1a" else "XF1a"
        assert r["braces"][work] >= abs(r["roof_H"]) / frame["brace_cos"][work] - 2e-3, c
        assert r["braces"][idle] == 0.0, c


def test_pynite_never_reactivates_a_tension_only_member():
    """Why the strength set does not use PyNite's tension-only switch: a braced bay (pinned posts, X of rods) under a
    heavy gravity load on the beam and a small lateral load. The posts shorten, both rods see compression in the first
    pass, PyNite switches both off — and never back on (Analysis._check_TC_convergence only checks ACTIVE members), so
    the bay is left a mechanism. If a PyNite release ever fixes this, this test fails: re-think the workaround."""
    from Pynite import FEModel3D
    m = FEModel3D()
    m.add_material("S", 200000.0, 77000.0, 0.3, 7.85e-8)
    m.add_section("post", 4000.0, 1e7, 5e7, 1e5)
    m.add_section("rod", 314.0, 1.0, 1.0, 1.0)
    for n, (x, y) in {"A": (0, 0), "B": (6000, 0), "C": (0, 6000), "D": (6000, 6000)}.items():
        m.add_node(n, x, y, 0.0)
        m.def_support(n, support_DZ=True, support_RX=True, support_RY=True)
    for n in ("A", "B"):
        m.def_support(n, True, True, True, True, True, False)
    m.add_member("P1", "A", "C", "S", "post"); m.add_member("P2", "B", "D", "S", "post"); m.add_member("BM", "C", "D", "S", "post")
    m.def_releases("P1", Rzj=True); m.def_releases("P2", Rzj=True)
    m.add_member("X1", "A", "D", "S", "rod", tension_only=True); m.add_member("X2", "B", "C", "S", "rod", tension_only=True)
    for x in ("X1", "X2"):
        m.def_releases(x, Ryi=True, Rzi=True, Ryj=True, Rzj=True)
    m.add_member_dist_load("BM", "FY", -50.0, -50.0, case="G")            # 50 kN/m: 150 kN per post
    m.add_node_load("C", "FX", 100.0, case="W")                           # 0.1 kN sideways
    m.add_load_combo("c", {"G": 1.0, "W": 1.0})
    try:
        m.analyze(check_statics=False)
    except Exception:
        return                                                            # it may also refuse to solve: the same trap
    assert m.members["X1"].active["c"] is False and m.members["X2"].active["c"] is False
