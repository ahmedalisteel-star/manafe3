# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 3 step 2: the frame model adapter, and bimsteelauto's solver on Manafe3-style layouts, against hand values.

1. Closed-form portal (prismatic, pinned bases, rigid joints, UDL w on the beam), force method with H redundant:
       H = w L² / (4 h (2k + 3)),  k = (I_beam / I_col)(h / L)
   L 12 000, h 6 000, same section → k = 0.5 → H = 10 × 12² / (4 × 6 × 4) = 15.000 kN; knee M = H h = 90 kN·m;
   mid-span M = wL²/8 − H h = 180 − 90 = 90 kN·m. (PyNite also has axial strain: allow 0.5 %.)
2. One tapered member: a cantilever column, fixed base, hw 300 → 800 (tw 8, flanges 250×12), L 6 000, UDL w = 5 kN/m
   sideways; tip deflection by an INDEPENDENT integration (Simpson, 2 000 slices, its own I(x) formula — not bimsteelauto's):
       δ = ∫ M(x) m(x) / (E I(x)) dx,  M = w (L − x)² / 2,  m = (L − x)
   the FE answer within 1 % at max_taper_step 0.05, and refining further changes it < 1 % (convergence).
3. Building 1 frame line 2 (span 24 000, eave 6 000, slope 0.1, span-rule sizes) geometry by hand:
       rafter start centroid: (824, 6 082.4 − 412·√1.01 = 5 668.345)    (plumb end: straight down by e/cos θ, e = 424/2)
       splice: roof point at 2 400 along (824 + 2 388.089, 6 082.4 + 238.809) − 212 × n(−0.0995037, 0.9950372)
               = (3 233.184, 6 110.261)
       ridge: (12 000, 7 200 − 212·√1.01 = 6 986.943), one node for both rafters
       column A: base centroid (162, 0) (hw 300: (324)/2); top at the rafter start height 5 668.345, hw there
               300 + 500 × 5 668.345 / 6 000 = 772.362 → centroid (398.181, 5 668.345); rigid arm to (824, 5 668.345)
"""

import math

import pytest

from bimsteelauto.analysis import FrameAnalysis, FrameLayout, LoadDirection
from bimsteelauto.analysis.frame import BaseFixity, FrameMember, ModelSettings
from bimsteelauto.sections import TaperedMember, WeldedI
from bimsteelauto.spec import MemberType, PEBGeometry
from engine.analysis.frame_model import frame_line_model
from engine.peb.builtup_frame import builtup_frame_members, default_sizes

E = 200000.0
GEO = PEBGeometry(span_widths=(12000.0,), bay_spacings=(6000.0,), eave_height=6000.0, roof_slope=0.0, purlin_spacing=1250, girt_spacing=1250)


def test_closed_form_portal():
    S = WeldedI(d=400, tw=8, bf_top=200, tf_top=12, bf_bot=200, tf_bot=12)
    nodes = {"B1": (0.0, 0.0), "K1": (0.0, 6000.0), "K2": (12000.0, 6000.0), "B2": (12000.0, 0.0)}
    mem = (FrameMember("C1", MemberType.COLUMN, TaperedMember(S, S, 6000), nodes["B1"], nodes["K1"]),
           FrameMember("R1", MemberType.RAFTER, TaperedMember(S, S, 12000), nodes["K1"], nodes["K2"]),
           FrameMember("C2", MemberType.COLUMN, TaperedMember(S, S, 6000), nodes["B2"], nodes["K2"]))
    fa = FrameAnalysis(FrameLayout(members=mem, nodes=nodes, base_nodes=("B1", "B2"), eave_nodes=("K1", "K2"), ridge_nodes=("K1",), geometry=GEO, settings=ModelSettings()))
    fa.add_line_load("D", "R1", 10.0)
    fa.add_combination("D", {"D": 1.0})
    env = fa.solve(p_delta=False)
    h, v, _ = env.base_reaction("B1", "D")
    assert abs(h) == pytest.approx(15.0, rel=5e-3) and v == pytest.approx(60.0, rel=1e-9)
    assert env.max_abs("C1", "M") == pytest.approx(90.0, rel=5e-3)
    assert env.max_abs("R1", "M") == pytest.approx(90.0, rel=5e-3)


def _I(hw, tw=8.0, bf=250.0, tf=12.0):
    return tw * hw ** 3 / 12 + 2 * (bf * tf ** 3 / 12 + bf * tf * (hw / 2 + tf / 2) ** 2)


def _tip_by_integration(L=6000.0, w=5.0, n=2000):
    f = lambda x: (w * (L - x) ** 2 / 2) * (L - x) / (E * _I(300 + 500 * x / L))
    h = L / n
    return h / 3 * sum((1 if k in (0, n) else 4 if k % 2 else 2) * f(k * h) for k in range(n + 1))


def _tip_fe(step):
    a, b = WeldedI(d=324, tw=8, bf_top=250, tf_top=12, bf_bot=250, tf_bot=12), WeldedI(d=824, tw=8, bf_top=250, tf_top=12, bf_bot=250, tf_bot=12)
    nodes = {"B": (0.0, 0.0), "T": (0.0, 6000.0)}
    lay = FrameLayout(members=(FrameMember("C", MemberType.COLUMN, TaperedMember(a, b, 6000), nodes["B"], nodes["T"]),), nodes=nodes,
                      base_nodes=("B",), eave_nodes=("T",), ridge_nodes=("T",), geometry=GEO, settings=ModelSettings(base_fixity=BaseFixity.FIXED, max_taper_step=step))
    fa = FrameAnalysis(lay)
    fa.add_line_load("W", "C", 5.0, LoadDirection.GLOBAL_X)
    fa.add_combination("W", {"W": 1.0})
    fa.solve(p_delta=False)
    return abs(fa.model.nodes["T"].DX["W"])


def test_tapered_member_against_integration_and_convergence():
    exact = _tip_by_integration()
    coarse, fine, finer = _tip_fe(0.10), _tip_fe(0.05), _tip_fe(0.01)
    assert fine == pytest.approx(exact, rel=0.01)
    assert abs(fine / finer - 1) < 0.01 and abs(finer / exact - 1) < 0.01
    assert abs(coarse / exact - 1) < 0.03                           # 10 % depth steps: within a few %


def test_building_frame_geometry_by_hand():
    ms = builtup_frame_members(24000, 6000, 0.1, 6000, "2", default_sizes(24000))
    info = frame_line_model(ms, 24000, 6000, 0.1, (6000,) * 4)
    n = info.layout.nodes
    c = math.sqrt(1.01)
    assert n["RA0"] == pytest.approx((824, 6082.4 - 412 * c), abs=1e-3)
    assert n["RAS1"] == pytest.approx((3233.184, 6110.261), abs=1e-3)
    assert n["RIDGE"] == pytest.approx((12000, 7200 - 212 * c), abs=1e-3) and "RIDGEB" not in n
    assert n["BA"] == pytest.approx((162, 0), abs=1e-3) and n["BB"] == pytest.approx((24000 - 162, 0), abs=1e-3)
    assert n["KA"] == pytest.approx((398.181, 6082.4 - 412 * c), abs=1e-3)
    assert {f.mark for f in info.layout.members} == {"CA", "CB", "RA1", "RA2", "RB1", "RB2", "KAL", "KBL"}
    assert info.roles["KAL"] == "link" and info.marks["RA1"] == "F2-RA"


def test_building_frame_statics():
    ms = builtup_frame_members(24000, 6000, 0.1, 6000, "2", default_sizes(24000))
    info = frame_line_model(ms, 24000, 6000, 0.1, (6000,) * 4)
    fa = FrameAnalysis(info.layout)
    for f in info.layout.members:
        if f.mark.startswith("R"):
            fa.add_line_load("L", f.mark, 3.0, LoadDirection.GLOBAL_Y_PROJECTED)     # 3 kN/m on plan
    fa.add_combination("L", {"L": 1.0})
    env = fa.solve(p_delta=False)
    hA, vA, _ = env.base_reaction("BA", "L")
    hB, vB, _ = env.base_reaction("BB", "L")
    plan = 2 * (12000 - 824)                                                        # the rafters' plan length, column face to apex
    assert vA + vB == pytest.approx(3.0 * plan / 1000, rel=1e-6)                     # Σ V = w × plan length
    assert hA + hB == pytest.approx(0.0, abs=1e-6) and vA == pytest.approx(vB, rel=1e-9)   # symmetric
    assert hA > 0                                                                    # the thrust pushes the bases outwards
