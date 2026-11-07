# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 3: loads on the frames — building 1 (span 24 000, eave 6 000, slope 0.1, 4 bays of 6 000), V 45 m/s,
exposure C, enclosed, roof secondary 0.05 kN/m² (given), single-skin sheeting 0.07.

Hand values:
    tributary width: interior frame (index 2) 6.0 m; end frame (index 0) 3.0 m
    dead on a rafter: (0.07 + 0.05) × 6 = 0.72 kN/m (sloping); collateral 0.10 × 6 = 0.60 kN/m (plan)
    Lr: At = 24 × 6 = 144 m² ≥ 55.74 → R1 = 0.6; F = 12 × 0.1 = 1.2 ≤ 4 → R2 = 1; 0.96 × 0.6 = 0.576 → the §4.8.2 minimum
        0.58 → 0.58 × 6 = 3.48 kN/m (end frame: At 72 → same Lr → 1.74 kN/m)
    self-weight of the 400 rafter segment: A = 400·6 + 2·250·12 = 8 400 mm² → 8 400e-6 × 76.982 = 0.64665 kN/m
    qh: θ = 5.71° ≤ 10° → h = eave = 6.0 m; Kz = 2.01 (6 / 274.32)^(2/9.5) = 0.898878 (Table 26.10-1, exposure C);
        qh = 0.613 × 0.898878 × Kzt 1 × Kd 0.85 × Ke 1 × 45² = 0.94843 kN/m²
    combinations, 6 wind cases: LRFD 1.4D, 1.2D+1.6Lr, 6 × (1.2D+1.6Lr+0.5W), 6 × (1.2D+1.0W+0.5Lr), 6 × (0.9D+1.0W) = 20;
        ASD 1.0D, 1.0D+1.0Lr, 6 × (1.0D+0.6W), 6 × (1.0D+0.45W+0.75Lr), 6 × (0.6D+0.6W) = 20;
        collateral C at D's factor in all but the 12 uplift combinations (user decision)
"""

import math

import pytest

from bimsteelauto.analysis.frame import FrameSections, MemberSectionSpec, build_layout
from bimsteelauto.loads.wind import envelope_pressures, wind_loads_for_frame
from engine.analysis.frame_loads import STEEL_KN_M3, frame_loads
from engine.analysis.frame_model import frame_line_model
from engine.peb.builtup_frame import builtup_frame_members, default_sizes
from engine.peb.loads_input import LoadsInput

LI = LoadsInput(V=45, exposure="C")


def fl(i):
    ms = builtup_frame_members(24000, 6000, 0.1, 6000.0 * i, str(i + 1), default_sizes(24000))
    info = frame_line_model(ms, 24000, 6000, 0.1, (6000,) * 4)
    return info, frame_loads(info, i, LI, roof_secondary_kpa=0.05)


def one(res, case, mark):
    xs = [x for x in res.loads if x.case == case and x.member_mark == mark]
    assert len(xs) == 1, (case, mark, xs)
    return xs[0]


def test_gravity_by_hand():
    info, r = fl(2)
    assert r.tributary_m == 6.0
    d = [x for x in r.loads if x.case == "D" and x.member_mark == "RA2" and not x.origin.startswith("self")][0]
    assert d.w == pytest.approx(0.72) and d.direction.name == "GLOBAL_Y"
    assert one(r, "C", "RA2").w == pytest.approx(0.60) and one(r, "C", "RA2").direction.name == "GLOBAL_Y_PROJECTED"
    assert r.Lr.R1 == 0.6 and r.Lr.R2 == 1.0 and r.Lr.Lr == 0.58 and one(r, "Lr", "RA1").w == pytest.approx(3.48)
    sw = [x for x in r.loads if x.case == "D" and x.member_mark == "RA2" and x.origin.startswith("self")][0]
    assert sw.w == pytest.approx(8400e-6 * STEEL_KN_M3) and sw.w == pytest.approx(0.64665, abs=1e-5) and sw.w_end == sw.w
    swc = [x for x in r.loads if x.case == "D" and x.member_mark == "CA" and x.origin.startswith("self")][0]
    assert swc.w_end > swc.w                                    # a tapered column: heavier at the top
    assert not [x for x in r.loads if x.member_mark in ("KAL", "KBL")]   # rigid links carry nothing
    _, e = fl(0)
    assert e.tributary_m == 3.0 and one(e, "Lr", "RA1").w == pytest.approx(1.74)


def test_qh_by_hand():
    _, r = fl(2)
    kz = 2.01 * (6.0 / 274.32) ** (2 / 9.5)
    assert r.wind.qh == pytest.approx(0.613 * kz * 0.85 * 45 ** 2 / 1000, rel=1e-6)
    assert r.wind.qh == pytest.approx(0.94843, abs=1e-5)


def test_wind_copied_from_bimsteelauto_onto_every_sub_member():
    info, r = fl(2)
    assert r.cases == ("D", "C", "Lr", "WA+L", "WA-L", "WA+R", "WA-R", "WB+", "WB-")
    std = build_layout(info.layout.geometry, FrameSections(MemberSectionSpec.prismatic(info.layout.members[0].taper.start), MemberSectionSpec.prismatic(info.layout.members[0].taper.start)))
    ref = {(x.case, x.member_mark): x for x in wind_loads_for_frame(std, 2, envelope_pressures(info.layout.geometry, LI.site()), from_left=True)}
    for nm, case in (("WA+L", "W_A_pi_pos"), ("WB-", "W_B_pi_neg")):
        assert one(r, nm, "RA1").w == ref[(case, "R1")].w and one(r, nm, "RA2").w == ref[(case, "R1")].w   # both segments
        assert one(r, nm, "RB1").w == ref[(case, "R2")].w and one(r, nm, "CA").w == ref[(case, "C1")].w and one(r, nm, "CB").w == ref[(case, "C2")].w
    right = {(x.case, x.member_mark): x for x in wind_loads_for_frame(std, 2, envelope_pressures(info.layout.geometry, LI.site()), from_left=False)}
    assert one(r, "WA+R", "CA").w == right[("W_A_pi_pos", "C1")].w
    assert one(r, "WA+L", "CA").w != one(r, "WA+R", "CA").w        # windward and leeward differ
    _, e = fl(0)
    assert abs(one(e, "WA+L", "RA1").w) / e.tributary_m > abs(one(r, "WA+L", "RA1").w) / r.tributary_m   # end zone: bigger per m²


def test_combinations_and_collateral():
    _, r = fl(2)
    lr = [c for c in r.combinations if c[2] == "LRFD"]
    asd = [c for c in r.combinations if c[2] == "ASD"]
    assert len(lr) == 20 and len(asd) == 20
    up = [c for c in r.combinations if "C" not in c[1]]
    assert len(up) == 12 and all(c[1]["D"] in (0.9, 0.6) and "Lr" not in c[1] for c in up)
    g = [c for c in lr if c[0].startswith("LRFD: 1.2D+1.6Lr") and c[1].get("C") == 1.2]
    assert g and all(c[0].endswith("(+C)") for c in g)
    assert all(c[0].startswith(c[2] + ": ") for c in r.combinations)
    only = frame_loads(fl(2)[0], 2, LoadsInput(V=45, exposure="C", asd=False))
    assert {c[2] for c in only.combinations} == {"LRFD"}
