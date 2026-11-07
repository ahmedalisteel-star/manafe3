# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 7: end walls of building 1 (24 × 24 m, eave 6 m, slope 0.1, bays 4 × 6 m; first end wall = end rafter
on wind columns, last = main frame; V 45 m/s, exposure C).

Checked: wind columns against the closed-form simple beam (pressure from qh and the Fig. 28.3-1 coefficients by hand);
the end-rafter frame by statics computed LONGHAND from the geometry (not from the module's own tally) and by an
independent anastruct model of the same frame under Lr (hinged column tops, pinned bases, one lateral restraint).
"""

import math

import pytest
from anastruct import SystemElements

from bimsteelauto.sections import WeldedI

from engine.analysis.endwall_analysis import end_rafter_frame, wind_columns
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


def test_wind_columns_simple_beam(out):
    r = wind_columns(out, LI)
    qh = r["qh"]
    assert r["pressure_kpa"]["inward"] == pytest.approx(qh * (0.61 + 0.18), abs=1e-4)    # zone 5E, GCpi −0.18
    assert r["pressure_kpa"]["outward"] == pytest.approx(qh * (-0.43 - 0.18), abs=1e-4)  # zone 6E, GCpi +0.18
    cols = {c["id"]: c for c in r["columns"]}
    assert set(cols) == {"WF1", "WF2", "WF3", "WF4", "WF5", "WL1", "WL2", "WL3"}            # the frame end: interior only
    # strips: supports 125 / 6000 / 12000 / 18000 / 23875 at both ends; corner strips to the building edge
    assert cols["WF1"]["strip_m"] == pytest.approx(3.0625) and cols["WF2"]["strip_m"] == pytest.approx(5.9375)
    assert cols["WL2"]["strip_m"] == pytest.approx(6.0)
    assert sum(cols[k]["strip_m"] for k in ("WF1", "WF2", "WF3", "WF4", "WF5")) == pytest.approx(24.0)
    c = cols["WF3"]
    L = c["L_m"]
    w = r["pressure_kpa"]["inward"] * 6.0
    u = c["sets"]["case"]["inward"]
    assert u["M"] == pytest.approx(w * L * L / 8, abs=2e-3) and u["R_top"] == pytest.approx(w * L / 2, abs=2e-3)
    assert c["sets"]["ASD"]["inward"]["M"] == pytest.approx(0.6 * u["M"], abs=2e-3)
    assert any("OPEN" in n for n in r["notes"])


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
        assert abs(res["restraint_H"]) < 1e-6 and all(abs(v[0]) < 1e-6 for v in res["reactions"].values())
    # wind: horizontal balance including the end-wall restraint; reactions equal and opposite to the applied loads
    for case in ("WA+L", "WB+"):
        res = frame["results"][case]
        fx, fy = frame["applied"][case]
        assert sum(v[0] for v in res["reactions"].values()) + res["restraint_H"] + fx == pytest.approx(0.0, abs=4e-3)   # 6 values rounded to 0.001
        assert sum(v[1] for v in res["reactions"].values()) + fy == pytest.approx(0.0, abs=4e-3)   # 6 values rounded to 0.001
    s = frame["summary"]
    assert s["rafter_M_LRFD"][0].startswith("LRFD: ") and s["apex_ASD"][0].startswith("ASD: ")


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
