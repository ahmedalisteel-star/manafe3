# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Built-up members: hand-checked section properties, sectionproperties cross-check, splice and minimum checks.

Longhand (y from the bottom fibre; parts = bottom flange, web, top flange; d = hw + tf_top + tf_bot):
    A = Σ a_i,   ȳ = Σ a_i·y_i / A,   Ix = Σ (I0_i + a_i (y_i − ȳ)²),   Sx_top = Ix / (d − ȳ),   Sx_bot = Ix / ȳ
    Iy = tf_bot·bf_bot³/12 + tf_top·bf_top³/12 + hw·tw³/12
    Zx = Σ |a_i · (y_i − y_pna)|  with the plastic neutral axis splitting A in half

S1  constant, hw 600, tw 6, flanges 200×10 both:
    A  = 600·6 + 2·200·10 = 3 600 + 4 000 = 7 600 mm²
    Ix = 6·600³/12 + 2·(200·10³/12 + 2 000·305²) = 108 000 000 + 2·(16 666.67 + 186 050 000) = 480 133 333.3 mm⁴
    Sx = Ix / 310 = 1 548 817.2 mm³          Zx = 2·2 000·305 + 6·600²/4 = 1 220 000 + 540 000 = 1 760 000 mm³
    Iy = 2·10·200³/12 + 600·6³/12 = 13 333 333.3 + 10 800 = 13 344 133.3 mm⁴

T1  tapered column, L 6 000, hw 300 → 800, tw 8, flanges 250×12 both:
    x = 0     hw 300: A = 2 400 + 6 000 = 8 400;  Ix = 8·300³/12 + 2·(36 000 + 3 000·156²) = 18 000 000 + 146 088 000 = 164 088 000
    x = 3 000 hw 550: A = 4 400 + 6 000 = 10 400; Ix = 8·550³/12 + 2·(36 000 + 3 000·281²) = 110 916 666.7 + 473 838 000
                      = 584 754 666.7;  Sx = Ix/287 = 2 037 472.7;  Zx = 2·3 000·281 + 8·550²/4 = 1 686 000 + 605 000 = 2 291 000
                      Iy = 2·12·250³/12 + 550·8³/12 = 31 250 000 + 23 466.7 = 31 273 466.7
    x = 6 000 hw 800: A = 6 400 + 6 000 = 12 400; Ix = 8·800³/12 + 2·(36 000 + 3 000·406²) = 341 333 333.3 + 989 088 000 = 1 330 421 333.3
    mass = mean A × L × 7850 = 10 400e-6 · 6 · 7 850 = 489.84 kg   (A is linear in hw, so the mean is exact)

T2  tapered haunch, singly symmetric, L 4 000, hw 800 → 400, tw 8, top 250×12, bottom 250×16; at x = 0 (hw 800):
    A  = 6 400 + 3 000 + 4 000 = 13 400 mm²
    ȳ  = (4 000·8 + 6 400·416 + 3 000·822) / 13 400 = 5 160 400 / 13 400 = 385.104 mm
    Ix = 85 333.3 + 4 000·377.104² + 341 333 333.3 + 6 400·30.896² + 36 000 + 3 000·436.896² = 1 489 027 920 mm⁴
    Sx_top = Ix / (828 − 385.104) = 3 362 030;   Sx_bot = Ix / 385.104 = 3 866 556 mm³
    PNA: half area 6 700 = 4 000 (bottom flange) + 8·337.5 → y_pna = 16 + 337.5 = 353.5
    Zx = 4 000·345.5 + 8·337.5²/2 + 8·462.5²/2 + 3 000·468.5 = 1 382 000 + 455 625 + 855 625 + 1 405 500 = 4 098 750 mm³
    Iy = 16·250³/12 + 12·250³/12 + 800·8³/12 = 36 458 333.3 + 34 133.3 = 36 492 466.7 mm⁴
"""

import pytest
from fastapi.testclient import TestClient

from engine.api import app
from engine.sections.builtup import BuiltUpError, BuiltUpMember, Segment

REL = 1e-6


def seg(**kw):
    base = dict(length=6000, hw_start=600, hw_end=600, tw=6, bf_top=200, tf_top=10, bf_bot=200, tf_bot=10)
    base.update(kw)
    return Segment(**base)


S1 = BuiltUpMember((seg(),))
T1 = BuiltUpMember((seg(length=6000, hw_start=300, hw_end=800, tw=8, bf_top=250, tf_top=12, bf_bot=250, tf_bot=12),))
T2 = BuiltUpMember((seg(length=4000, hw_start=800, hw_end=400, tw=8, bf_top=250, tf_top=12, bf_bot=250, tf_bot=16),))


# ---- hand-checked values ----------------------------------------------------------------------------------------

def test_s1_constant_section_by_hand():
    p = S1.properties_at(2000)
    assert p["d"] == 620
    assert p["A"] == pytest.approx(7600, rel=REL)
    assert p["Ix"] == pytest.approx(480_133_333.3, rel=REL)
    assert p["Sx_top"] == pytest.approx(1_548_817.2, rel=REL) and p["Sx_bot"] == pytest.approx(1_548_817.2, rel=REL)
    assert p["Zx"] == pytest.approx(1_760_000, rel=REL)
    assert p["Iy"] == pytest.approx(13_344_133.3, rel=REL)


def test_t1_tapered_column_by_hand():
    a, m, b = T1.properties_at(0), T1.properties_at(3000), T1.properties_at(6000)
    assert (a["hw"], m["hw"], b["hw"]) == (300, 550, 800)
    assert a["A"] == pytest.approx(8400, rel=REL) and a["Ix"] == pytest.approx(164_088_000, rel=REL)
    assert m["A"] == pytest.approx(10_400, rel=REL)
    assert m["Ix"] == pytest.approx(584_754_666.7, rel=REL)
    assert m["Sx"] == pytest.approx(2_037_472.7, rel=REL)
    assert m["Zx"] == pytest.approx(2_291_000, rel=REL)
    assert m["Iy"] == pytest.approx(31_273_466.7, rel=REL)
    assert b["A"] == pytest.approx(12_400, rel=REL) and b["Ix"] == pytest.approx(1_330_421_333.3, rel=REL)
    assert T1.mass_axis() == pytest.approx(489.84, rel=REL)


def test_t2_singly_symmetric_haunch_by_hand():
    p = T2.properties_at(0)
    assert p["d"] == 828
    assert p["A"] == pytest.approx(13_400, rel=REL)
    assert p["y_bar"] == pytest.approx(385.104, abs=0.001)
    assert p["Ix"] == pytest.approx(1_489_027_920, rel=REL)
    assert p["Sx_top"] == pytest.approx(3_362_030, rel=REL)
    assert p["Sx_bot"] == pytest.approx(3_866_556, rel=REL)
    assert p["Sx"] == p["Sx_top"]                       # the smaller one governs
    assert p["Zx"] == pytest.approx(4_098_750, rel=REL)
    assert p["Iy"] == pytest.approx(36_492_466.7, rel=REL)


# ---- independent cross-check: sectionproperties (FE mesh integration), within 1 % at 5 stations ------------------

def fe_props(hw, tw, bf_top, tf_top, bf_bot, tf_bot):
    from sectionproperties.analysis import Section
    from sectionproperties.pre.geometry import Geometry
    from shapely.geometry import box

    d = hw + tf_top + tf_bot
    g = (Geometry(box(-bf_bot / 2, 0, bf_bot / 2, tf_bot))
         + Geometry(box(-tw / 2, tf_bot, tw / 2, tf_bot + hw))
         + Geometry(box(-bf_top / 2, tf_bot + hw, bf_top / 2, d)))
    g.create_mesh(mesh_sizes=[max(tw, 6) ** 2 * 4])
    s = Section(g)
    s.calculate_geometric_properties()
    s.calculate_plastic_properties()
    ixx, iyy, _ = s.get_ic()
    zxx_top, zxx_bot, _, _ = s.get_z()
    sxx, _ = s.get_s()
    return {"A": s.get_area(), "Ix": ixx, "Iy": iyy, "Sx_top": zxx_top, "Sx_bot": zxx_bot, "Zx": sxx}


@pytest.mark.parametrize("member", [T1, T2], ids=["T1", "T2"])
@pytest.mark.parametrize("frac", [0.0, 0.25, 0.5, 0.75, 1.0])
def test_against_sectionproperties_within_1pct(member, frac):
    seg0 = member.segments[0]
    x = member.length * frac
    ours = member.properties_at(x)
    fe = fe_props(ours["hw"], seg0.tw, seg0.bf_top, seg0.tf_top, seg0.bf_bot, seg0.tf_bot)
    for k in ("A", "Ix", "Iy", "Sx_top", "Sx_bot", "Zx"):
        assert ours[k] == pytest.approx(fe[k], rel=0.01), k


def test_negative_control_the_cross_check_catches_a_depth_mixup():
    """If hw were taken as the OVERALL depth (the conversion forgotten), the 1 % check must fail."""
    from bimsteelauto.sections import WeldedI
    wrong = WeldedI(d=800, tw=8, bf_top=250, tf_top=12, bf_bot=250, tf_bot=16)    # d = hw: the classic mistake
    fe = fe_props(800, 8, 250, 12, 250, 16)
    assert abs(wrong.Ix / fe["Ix"] - 1) > 0.01


# ---- segments, splices, minimums ----------------------------------------------------------------------------------

def test_splice_joins_equal_webs_and_flange_widths():
    haunch = seg(length=2400, hw_start=800, hw_end=400, tw=8, bf_top=250, tf_top=12, bf_bot=250, tf_bot=12)
    rafter = seg(length=9600, hw_start=400, hw_end=400, tw=6, bf_top=250, tf_top=10, bf_bot=250, tf_bot=10)
    m = BuiltUpMember((haunch, rafter))                 # thicknesses may change at a splice
    assert m.length == 12000 and m.splices == [2400]
    assert m.properties_at(2400)["segment"] == 2       # the splice belongs to the segment that starts there
    assert m.properties_at(2399.9)["segment"] == 1
    assert m.properties_at(12000)["segment"] == 2
    with pytest.raises(BuiltUpError, match=r"splice 1 .*web depths differ \(400 \| 450"):
        BuiltUpMember((haunch, seg(length=9600, hw_start=450, hw_end=450, bf_top=250, bf_bot=250)))
    with pytest.raises(BuiltUpError, match=r"splice 1 .*top flange widths differ"):
        BuiltUpMember((haunch, seg(length=9600, hw_start=400, hw_end=400, bf_top=200, bf_bot=250)))
    with pytest.raises(BuiltUpError, match=r"splice 1 .*bottom flange widths differ"):
        BuiltUpMember((haunch, seg(length=9600, hw_start=400, hw_end=400, bf_top=250, bf_bot=300)))


@pytest.mark.parametrize("kw, msg", [
    (dict(tw=5), r"web 5 mm is under the shop minimum 6"),
    (dict(tf_top=6), r"top flange 6 mm is under the shop minimum 8"),
    (dict(tf_bot=7.9), r"bottom flange 7.9 mm is under the shop minimum 8"),
    (dict(grade="Q235"), r"grade 'Q235' is not one of"),
    (dict(hw_end=0), r"hw_end must be positive"),
    (dict(bf_top=6), r"bf_top 6 must be wider than the web"),
])
def test_minimums_and_bad_input_refused(kw, msg):
    with pytest.raises(BuiltUpError, match=msg):
        BuiltUpMember((seg(**kw),))
    assert BuiltUpMember((seg(tw=6, tf_top=8, tf_bot=8),)).length == 6000     # exactly the minimums is allowed


def test_x_outside_refused():
    with pytest.raises(BuiltUpError, match="outside the member"):
        T1.properties_at(6001)


# ---- HTTP --------------------------------------------------------------------------------------------------------

def test_endpoint():
    c = TestClient(app)
    body = {"segments": [dict(length=6000, hw_start=300, hw_end=800, tw=8, bf_top=250, tf_top=12, bf_bot=250, tf_bot=12)], "x": [3000]}
    r = c.post("/section/builtup", json=body)
    assert r.status_code == 200
    j = r.json()
    assert j["stations"][0]["Ix"] == pytest.approx(584_754_666.7, rel=REL)
    assert j["mass_axis"] == pytest.approx(489.84, rel=REL)
    bad = c.post("/section/builtup", json={"segments": [dict(body["segments"][0], tw=5)]})
    assert bad.status_code == 422 and "shop minimum" in bad.json()["detail"]
