# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Open item 11 (step 5c-fix, user 2026-11-16): the ridge and the knee as inner-flange brace points in the Phase 4 rafter
and column checks (engine/design/frame_checks.py).

    KNEE    braced only with a flange brace within 1500 mm of the corner on the rafter AND the column: building 1 — rafter
            705.9 ≤ 1500, column 5801.4 − 5003.9 = 797.5 ≤ 1500 → braced; a column brace at 3000 only → 2801.4 > 1500 → not
            braced (the inner-flange LTB at the knee NOT EVALUATED, never a pass)
    RIDGE   braced when a flange brace sits at the ridge purlin on both sides, or within 150 mm of the ridge end; with no
            ridge brace: the two halves as one member for the inner-flange FLEXURE only (P = 0), combined by H1 with the
            half's own axial term: a < 0.2 → a/2 + f, else a + 8/9 f
    BUILDING 1  ridge braces ON (the generator default): the half-rafter check stands — interior 0.8292 (Phase 4 before:
            0.8288; +0.0004 from the 16 added braces' dead load); OFF (negative control): across the ridge 1.4387 interior
            (f 1.4272 by DG 25, segment 3086.8 → 20 058.6), 0.6832 end
"""

from __future__ import annotations

import dataclasses
from types import SimpleNamespace

import pytest

from engine.design import frame_checks as F


def _mem(L, bottom):
    return (SimpleNamespace(taper=SimpleNamespace(length=L)), {"restraints": {"bottom": list(bottom)}})


def test_knee_rule():
    k = F.knee_braced(_mem(11572.7, [705.9, 1894.2, 3086.8]), _mem(5801.4, [3753.5, 5003.9]))
    assert k["braced"] and k["rafter_brace"] == 705.9 and k["column_brace_below_top"] == pytest.approx(797.5)
    no = F.knee_braced(_mem(11572.7, [705.9]), _mem(5801.4, [3000.0]))               # NEGATIVE CONTROL: 2801.4 > 1500
    assert not no["braced"] and no["column_brace_below_top"] is None
    assert not F.knee_braced(_mem(11572.7, [1600.0]), _mem(5801.4, [5003.9]))["braced"]   # rafter brace 1600 > 1500
    assert F.knee_braced(_mem(11572.7, [1600.0]), _mem(5801.4, [5003.9]), tol=2000.0)["braced"]


def test_ridge_rule():
    out = {"members": [{"role": "ridge_purlin", "side": "A", "line": "RA10"},
                       {"role": "flange_brace", "host": "rafter A", "start": [6000.0, 0, 0], "line": "RA10"}]}
    assert F.ridge_braced(out, 6000.0, "A", _mem(11572.7, [705.9, 11388.7]))["by"] == "flange brace at the ridge purlin"
    assert not F.ridge_braced(out, 12000.0, "A", _mem(11572.7, [705.9]))["braced"]     # another frame: no brace there
    near = F.ridge_braced({"members": []}, 6000.0, "A", _mem(11572.7, [705.9, 11472.7]))
    assert near["braced"] and near["by"] == "flange brace 100.0 mm from the ridge"
    assert not F.ridge_braced({"members": []}, 6000.0, "A", _mem(11572.7, [705.9, 11388.7]))["braced"]   # 184 > 150


@pytest.mark.slow
def test_building_1_ridge_on_off():
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.joints import _frame_info
    from engine.peb.building import peb_building, resolve
    from engine.tests.test_joints import _sized
    b0, li = _sized()
    res = {}
    for on in (True, False):
        b, _ = resolve(dataclasses.replace(b0, ridge_flange_braces=on))
        out = peb_building(b)
        an = analyse_building(b, li)
        f = {x["line"]: x for x in an["frames"]}
        for i, line in ((1, "2"), (0, "1")):
            ms, info = _frame_info(b, i, base=an["input"].get("base", "pinned"))
            r = F.check_frame_line(info, f[line]["result"], out, b.frame_xs()[i], F.strengths_by_mark(ms), compare=False)
            res[(on, line)] = {m["name"]: m for m in r["members"]}
    on2, off2, on1, off1 = res[(True, "2")], res[(False, "2")], res[(True, "1")], res[(False, "1")]
    assert on2["rafter A"]["across_ridge"]["ridge_braced"] and on2["rafter A"]["ratio"] == pytest.approx(0.8292, abs=5e-4)
    assert on1["rafter A"]["ratio"] == pytest.approx(0.4364, abs=5e-4)
    assert all(m["knee"]["braced"] for m in on2.values() if "knee" in m)
    a = off2["rafter A"]["across_ridge"]
    assert not a["ridge_braced"] and a["ratio"] == pytest.approx(1.4387, abs=2e-3) and off2["rafter A"]["ratio"] == a["ratio"]
    assert a["inner_flange_segment_across_ridge"] == [pytest.approx(3086.8, abs=0.2), pytest.approx(20058.6, abs=0.2)]
    u = a["axial_half"] / 2 + a["flexure_across"] if a["axial_half"] < 0.2 else a["axial_half"] + 8 / 9 * a["flexure_across"]
    assert a["ratio"] == pytest.approx(u, abs=1e-4)                                   # H1 with the half's axial term
    assert off1["rafter A"]["ratio"] == pytest.approx(0.6832, abs=2e-3)
    assert off2["rafter A"]["governing"].startswith("across the ridge")
    # a knee that does NOT qualify (tolerance 100 mm on building 1): NOT EVALUATED, never a number; JSON / UI: None
    from engine.design.design_run import _ratio, clean
    b, _ = resolve(b0)
    out = peb_building(b)
    an = analyse_building(b, li)
    ms, info = _frame_info(b, 1, base=an["input"].get("base", "pinned"))
    r = F.check_frame_line(info, {x["line"]: x for x in an["frames"]}["2"]["result"], out, b.frame_xs()[1],
                           F.strengths_by_mark(ms), compare=False, knee_tol=100.0)
    for m in r["members"]:
        assert m["status"] == "NOT EVALUATED" and not m["passed"] and "NOT EVALUATED" in m["governing"]
        assert clean(m)["ratio"] is None and _ratio(m["ratio"]) is None
