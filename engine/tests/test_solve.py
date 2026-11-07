# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 4: solving a frame line — statics for every load case, P-Delta, labels.

Statics (an independent check of what the solver received): for each case the base reactions must balance the applied
loads, integrated here from the load list with bimsteelauto's documented conventions —
    GLOBAL_Y: w kN/m along the member, downward;  GLOBAL_Y_PROJECTED: w per metre of plan, downward;
    NORMAL: a column's positive w pushes toward +X; a rafter's positive w presses onto its top face (down onto the roof).
A varying load (a taper's self-weight) by its mean value. Building 1, interior frame (index 2), V 45 m/s, exposure C.
"""

import math

import pytest

from engine.analysis.frame_loads import frame_loads
from engine.analysis.frame_model import frame_line_model
from engine.analysis.solve import analyse_frame_line
from engine.peb.builtup_frame import builtup_frame_members, default_sizes
from engine.peb.loads_input import LoadsInput


def setup(i=2, p_delta=True):
    ms = builtup_frame_members(24000, 6000, 0.1, 6000.0 * i, str(i + 1), default_sizes(24000))
    info = frame_line_model(ms, 24000, 6000, 0.1, (6000,) * 4)
    fl = frame_loads(info, i, LoadsInput(V=45, exposure="C"), roof_secondary_kpa=0.05, wall_secondary_kpa=0.03)
    return info, fl, analyse_frame_line(info, fl, p_delta=p_delta)


def applied(info, fl, case):
    fx = fy = 0.0
    pts = {m.mark: (m.i_point, m.j_point) for m in info.layout.members}
    for ld in fl.loads:
        if ld.case != case:
            continue
        (xi, yi), (xj, yj) = pts[ld.member_mark]
        L = math.hypot(xj - xi, yj - yi) / 1000
        w = (ld.w + (ld.w if ld.w_end is None else ld.w_end)) / 2
        if ld.direction.name == "GLOBAL_Y":
            fy -= w * L
        elif ld.direction.name == "GLOBAL_X":
            fx += w * L
        elif ld.direction.name == "GLOBAL_Y_PROJECTED":
            fy -= w * abs(xj - xi) / 1000
        elif ld.direction.name == "NORMAL":
            if info.roles[ld.member_mark].startswith("column"):
                fx += w * L
            else:
                nx, ny = -(yj - yi), (xj - xi)
                if ny < 0:
                    nx, ny = -nx, -ny
                n = math.hypot(nx, ny)
                fx -= w * L * nx / n
                fy -= w * L * ny / n
        else:
            raise AssertionError(f"unexpected direction {ld.direction}")
    return fx, fy


def test_statics_for_every_case():
    info, fl, r = setup()
    for case in fl.cases:
        res = r["results"][case]
        assert res["set"] == "case"
        rx = sum(res["reactions"][b][0] for b in r["base_nodes"])
        ry = sum(res["reactions"][b][1] for b in r["base_nodes"])
        fx, fy = applied(info, fl, case)
        assert rx + fx == pytest.approx(0.0, abs=0.02), case          # kN (P-Delta on: still in equilibrium)
        assert ry + fy == pytest.approx(0.0, abs=0.02), case
    d = r["results"]["D"]
    assert d["reactions"]["BA"][1] > 0 and d["reactions"]["BA"][1] == pytest.approx(d["reactions"]["BB"][1], rel=1e-6)   # symmetric gravity


def test_labels_drift_and_p_delta():
    info, fl, r = setup()
    sets = {c: s for c, s in r["combos"]}
    assert sum(1 for s in sets.values() if s == "LRFD") == 20 and sum(1 for s in sets.values() if s == "ASD") == 20 and sum(1 for s in sets.values() if s == "case") == 9
    assert all(v["set"] == "LRFD" for v in r["summary"]["max_M_LRFD"].values())
    assert r["summary"]["drift_ASD"][0].startswith("ASD: ") and r["summary"]["drift_ASD"][1] > 0
    assert r["summary"]["apex_ASD"][0].startswith("ASD: ") and r["summary"]["apex_ASD"][1] < 0          # the apex goes down
    assert r["results"]["WA+L"]["drift"] > 0                                                            # eave nodes KA / KB, not "E…"
    _, _, r1 = setup(p_delta=False)
    # P-Delta acts on the SWAY (the eaves' mean sideways movement; "drift", the largest single-eave movement, also holds the
    # knees spreading under gravity). Columns in COMPRESSION amplify it; columns in TENSION (net uplift: this light roof
    # under 0.6W suction) stiffen the frame and reduce it — the negative control.
    comp = r["results"]["ASD: 1.0D+0.45WA+L+0.75Lr (+C)"]
    tens = r["results"]["ASD: 1.0D+0.6WA+L (+C)"]
    p_col = lambda res: min(st[1] for st in res["members"]["CA"])               # P > 0 = compression
    assert p_col(comp) > 0 and max(st[1] for st in tens["members"]["CA"]) < 0      # the premise: compression / tension
    c1 = r1["results"]["ASD: 1.0D+0.45WA+L+0.75Lr (+C)"]
    t1 = r1["results"]["ASD: 1.0D+0.6WA+L (+C)"]
    assert comp["sway"] > c1["sway"] > 0 and comp["sway"] / c1["sway"] < 1.2     # amplified, modestly for this frame
    assert 0 < tens["sway"] < t1["sway"]                                         # reduced under tension
    assert set(r["results"]["D"]["members"]) == {"CA", "CB", "RA1", "RA2", "RB1", "RB2"}                # no rigid links in the output
