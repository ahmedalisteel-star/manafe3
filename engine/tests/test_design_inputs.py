# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 1: design inputs from the model — plate strengths, design members, restraint points, the moment sign
into bimsteelauto. Building 1: 24 m span, eave 6 m, slope 0.1, 4 × 6 m bays (frame line 3 interior, line 1 an end frame)."""

import dataclasses
import math

import pytest
from Pynite import FEModel3D

from engine.analysis.frame_loads import frame_loads
from engine.analysis.frame_model import frame_line_model
from engine.analysis.solve import analyse_frame_line
from engine.design.inputs import VERIFIED, bsa_moment, design_members, plate_strength, restraints, section_strength
from engine.peb.building import BuildingInput, peb_building
from engine.peb.builtup_frame import builtup_frame_members, default_sizes
from engine.peb.loads_input import LoadsInput

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)


def line(i, sizes=None):
    return frame_line_model(builtup_frame_members(24000, 6000, 0.1, 6000.0 * i, str(i + 1), sizes or default_sizes(24000)),
                            24000, 6000, 0.1, (6000,) * 4)


def test_plate_strengths():
    assert plate_strength("S355", 12)["Fy"] == 355 and plate_strength("S355", 20)["Fy"] == 345      # EN 10025-2 bands
    assert plate_strength("S355", 16)["Fy"] == 355 and plate_strength("S275", 25)["Fy"] == 265
    assert plate_strength("S355", 25)["Fu"] == 470 and plate_strength("A572 Gr 50", 25)["Fy"] == 345
    assert plate_strength("St 52", 20)["Fy"] == pytest.approx(3.6 * 98.0665, abs=0.01)             # 353.04 MPa
    with pytest.raises(ValueError, match="unknown"):
        plate_strength("S460", 10)                                                                 # not in the table: refused
    with pytest.raises(ValueError, match="give Fy"):
        plate_strength("S355", 50)                                                                 # beyond the bands listed
    seg = {"grade": "S355", "tw": 8, "tf_top": 20, "tf_bot": 12}
    s = section_strength(seg)
    assert s["Fy"] == 345 and s["governed_by"] == "top flange t = 20"                              # the thick flange governs
    assert not any(VERIFIED.values())


def test_pynite_sign_and_the_boundary():
    """PyNite: sagging is NEGATIVE (simply supported, −wL²/8), hogging positive. bimsteelauto wants + = top in compression."""
    m = FEModel3D()
    m.add_node("A", 0, 0, 0); m.add_node("B", 10000, 0, 0)
    m.add_material("S", 200000, 77000, 0.3, 7.85e-8); m.add_section("s", 5000, 1e7, 1e8, 1e6)
    m.add_member("M", "A", "B", "S", "s")
    m.def_support("A", True, True, True, True, False, False); m.def_support("B", False, True, True, False, False, False)
    m.add_member_dist_load("M", "FY", -10, -10, case="D"); m.add_load_combo("D", {"D": 1.0}); m.analyze_linear()
    M = m.members["M"].moment("Mz", 5000, "D") / 1e6
    assert M == pytest.approx(-125.0)                                       # 10 N/mm × 10² m² / 8
    assert bsa_moment((0, 0), (10000, 0), (0.0, 1.0), M) == pytest.approx(125.0)        # sagging → top in compression
    assert bsa_moment((10000, 0), (0, 0), (0.0, 1.0), M) == pytest.approx(125.0)        # the same beam drawn backwards
    assert bsa_moment((0, 0), (10000, 0), (0.0, -1.0), M) == pytest.approx(-125.0)      # section upside down


@pytest.mark.parametrize("constant_columns", [False, True])
def test_knee_compresses_the_inner_flange_on_both_columns(constant_columns):
    """Gravity on a pinned portal: the knee puts the column's OUTER flange (its section 'top') in tension, so bimsteelauto
    must see Mz < 0 (inner flange in compression) on BOTH columns — also when the columns are constant depth and exactly
    vertical, where PyNite's local y of column B points INTO the building (the trap)."""
    z = default_sizes(24000)
    if constant_columns:
        z = dataclasses.replace(z, hw_base=z.hw_knee)
    info = line(2, z)
    fl = frame_loads(info, 2, LoadsInput(V=45, exposure="C"))
    fl = type(fl)(loads=tuple(l for l in fl.loads if l.case == "D"), cases=("D",), combinations=(), tributary_m=fl.tributary_m, Lr=fl.Lr, wind=fl.wind)
    r = analyse_frame_line(info, fl, p_delta=False)
    cols = {m.mark: m for m in info.layout.members if m.mark in ("CA", "CB")}
    if constant_columns:
        assert all(abs(c.i_point[0] - c.j_point[0]) < 1e-6 for c in cols.values())     # exactly vertical
    for mk, normal in (("CA", (-1.0, 0.0)), ("CB", (1.0, 0.0))):
        c = cols[mk]
        knee = r["results"]["D"]["members"][mk][-1][3]
        assert bsa_moment(c.i_point, c.j_point, normal, knee) < 0, (mk, constant_columns)
    ra = next(m for m in info.layout.members if m.mark == "RA1")
    assert bsa_moment(ra.i_point, ra.j_point, (0.0, 1.0), r["results"]["D"]["members"]["RA1"][0][3]) < 0   # haunch: hogging


def test_design_members_chain_the_rafter_halves():
    dms = {d["name"]: d for d in design_members(line(2))}
    assert set(dms) == {"rafter A", "rafter B", "column A", "column B"}
    ra = dms["rafter A"]
    assert [c["mark"] for c in ra["chain"]] == ["RA1", "RA2"] and ra["chain"][1]["s0"] == pytest.approx(ra["chain"][0]["length"])
    assert ra["length"] == pytest.approx(sum(c["length"] for c in ra["chain"]))          # the splice is NOT an end


def test_restraints_from_the_model():
    out = peb_building(BuildingInput(**B1))
    info = line(2)
    r = restraints(out, info, 12000.0)
    # column A outer flange at the girts (z 1250, 2500, 3750, 5000). Longhand for the first: the centroid line runs from
    # BA (162, 0) to KA; u = (KA − BA) / |KA − BA|; the girt (y 0, z 1250) projects to t = (0 − 162)·ux + 1250·uy
    ca = next(m for m in info.layout.members if m.mark == "CA")
    (x0, y0), (x1, y1) = ca.i_point, ca.j_point
    L = math.hypot(x1 - x0, y1 - y0)
    t1 = (0 - x0) * (x1 - x0) / L + (1250 - y0) * (y1 - y0) / L
    assert t1 == pytest.approx(1242.17, abs=0.05)
    assert r["column A"]["top"][0] == pytest.approx(t1, abs=0.1) and len(r["column A"]["top"]) == 4
    assert len(r["column A"]["bottom"]) == 2                                       # flange braces at the top two girts
    # rafter: every purlin line and the ridge purlin of side A crossing x = 12 000 (the eave strut is over the column: not
    # on the rafter chain); bottom flange: the three flange braces over the haunch (+ the next purlin)
    lines_a = {m["line"] for m in out["members"] if m["role"] in ("purlin", "ridge_purlin") and m["side"] == "A"}
    assert len(r["rafter A"]["top"]) == len(lines_a) == 10
    assert len(r["rafter A"]["bottom"]) == 3 and r["rafter A"]["bottom"] == r["rafter B"]["bottom"]
    assert all(0 < s < r["rafter A"]["length"] for s in r["rafter A"]["top"])
    # negative control: an END frame line has no rafter flange braces in the model (Phase 2: interior frames only)
    r1 = restraints(out, line(0), 0.0)
    assert r1["rafter A"]["bottom"] == [] and len(r1["rafter A"]["top"]) == 10
