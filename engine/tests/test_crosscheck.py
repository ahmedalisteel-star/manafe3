# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 3 step 5: the interior frame of building 1 cross-checked with anastruct (independent FE code, its own taper
slicing), first order, for a gravity case (D) and a wind case (WA+L); and the STAAD.Pro .std text by hand.

anastruct's conventions are pinned down here first, on cantilevers, so the comparison cannot pass by a sign accident.
"""

import pytest
from anastruct import SystemElements

from engine.analysis.crosscheck import anastruct_frame
from engine.analysis.frame_loads import frame_loads
from engine.analysis.frame_model import frame_line_model
from engine.analysis.solve import analyse_frame_line
from engine.analysis.staad import staad_frame
from engine.peb.builtup_frame import builtup_frame_members, default_sizes
from engine.peb.loads_input import LoadsInput

pytestmark = pytest.mark.slow          # whole frame solves (see pyproject [tool.pytest.ini_options])


def test_anastruct_conventions():
    ss = SystemElements()                                   # cantilever along x, q = −1 in "y": a DOWNWARD load
    e = ss.add_element(location=[[0, 0], [10, 0]], EA=1e6, EI=1e4)
    ss.add_support_fixed(1)
    ss.q_load(q=-1.0, element_id=e, direction="y")
    ss.solve()
    assert ss.get_node_results_system(1)["Fy"] == pytest.approx(-10.0)         # reported = −(real reaction +10 up)
    assert ss.get_node_results_system(2)["uy"] == pytest.approx(10 ** 4 / (8 * 1e4))   # reported = −(real −qL⁴/8EI)
    ss = SystemElements()                                   # cantilever along y, q = +1 in "x": a load toward +x
    e = ss.add_element(location=[[0, 0], [0, 10]], EA=1e6, EI=1e4)
    ss.add_support_fixed(1)
    ss.q_load(q=1.0, element_id=e, direction="x")
    ss.solve()
    assert ss.get_node_results_system(1)["Fx"] == pytest.approx(10.0)          # reported = −(real −10)
    assert ss.get_node_results_system(2)["ux"] == pytest.approx(-0.125)        # reported = −(real +0.125)
    ss = SystemElements()                                   # q_perp with direction "y" = a load toward +x
    e = ss.add_element(location=[[0, 0], [0, 10]], EA=1e6, EI=1e4)
    ss.add_support_fixed(1)
    ss.q_load(q=0.0, element_id=e, direction="y", q_perp=1.0)
    ss.solve()
    assert ss.get_node_results_system(2)["ux"] == pytest.approx(-0.125)
    ss = SystemElements()                                   # THE TRAP: a second q_load on an element REPLACES the first
    e = ss.add_element(location=[[0, 0], [10, 0]], EA=1e6, EI=1e4)
    ss.add_support_fixed(1)
    ss.q_load(q=-1.0, element_id=e, direction="y")
    ss.q_load(q=-1.0, element_id=e, direction="y")
    ss.solve()
    assert ss.get_node_results_system(1)["Fy"] == pytest.approx(-10.0)         # not −20


@pytest.fixture(scope="module")
def frame():
    ms = builtup_frame_members(24000, 6000, 0.1, 12000.0, "3", default_sizes(24000))
    info = frame_line_model(ms, 24000, 6000, 0.1, (6000,) * 4)
    fl = frame_loads(info, 2, LoadsInput(V=45, exposure="C"), roof_secondary_kpa=0.05, wall_secondary_kpa=0.03)
    return info, fl, analyse_frame_line(info, fl, p_delta=False)


@pytest.mark.parametrize("case", ["D", "WA+L"])
def test_pynite_and_anastruct_agree(frame, case):
    info, fl, r = frame
    a = anastruct_frame(info, fl, case)
    res = r["results"][case]
    for b in ("BA", "BB"):
        assert a["reactions"][b][1] == pytest.approx(res["reactions"][b][1], rel=0.01, abs=0.05), (case, b, "V")
        assert a["reactions"][b][0] == pytest.approx(res["reactions"][b][0], rel=0.02, abs=0.05), (case, b, "H")
    for mk in ("CA", "RA1", "RB2"):
        pm = max(abs(st[3]) for st in res["members"][mk])
        assert a["max_M"][mk] == pytest.approx(pm, rel=0.02), (case, mk)
    assert a["apex_dy"] == pytest.approx(res["apex"], rel=0.02, abs=0.05), case


def test_staad_text(frame):
    info, fl, _ = frame
    txt = staad_frame(info, fl, title="B1 frame 3")
    lines = txt.splitlines()
    assert lines[0] == "STAAD PLANE" and "UNIT METER KN" in lines and lines[-1] == "FINISH"
    assert "1 0.824 5.66835 0;" in lines                    # RA0 (the first node): (824, 5 668.345) mm → m, 6 significant digits
    ra1 = [l for l in lines if l.endswith("* RA1 F3-RA")][0]
    k = ra1.split()[0]
    assert f"{k} TAPERED 0.824 0.008 0.424 0.25 0.012 0.25 0.012" in lines       # 800 + 24 → 400 + 24, tw 8, 250×12
    assert sum(1 for l in lines if l.endswith("PRIS AX 1 IZ 1   * rigid arm")) == 2
    assert "1 2 PINNED" in lines or any(l.endswith("PINNED") for l in lines)
    assert sum(1 for l in lines if l.startswith("LOAD ") and "TITLE" in l) == 9
    assert sum(1 for l in lines if l.startswith("LOAD COMBINATION")) == 40
    assert any(" UNI PY -3.48" in l for l in lines)                              # Lr on a rafter: 0.58 × 6, plan
    assert any(" UNI GX " in l for l in lines) and any(" UNI Y " in l for l in lines) and any(" TRAP GY " in l for l in lines)
