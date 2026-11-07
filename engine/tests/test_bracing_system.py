# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 6: the longitudinal bracing system of building 1 (24 × 24 m, eave 6 m, slope 0.1, bays 4 × 6 m, braced
bays 1 and 4, V 45 m/s, exposure C).

The chain is re-derived LONGHAND here from the pressure (bimsteelauto's, VERIFIED there): endwall areas, eave share, the
share per bay, V / cos θ on Manafe3's own panel depths. The wall diagonal is then checked a second, independent way: a
PyNite tension-only truss of the wall panel; the compression diagonal must carry ~nothing (the negative control).
"""

import math

import pytest
from Pynite import FEModel3D

from bimsteelauto.spec import PEBGeometry
from engine.analysis.bracing_system import longitudinal_bracing
from engine.peb.building import BuildingInput, peb_building
from engine.peb.loads_input import LoadsInput

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)
GEOM = PEBGeometry(span_widths=(24000.0,), bay_spacings=(6000.0,) * 4, eave_height=6000.0, roof_slope=0.1,
                   purlin_spacing=1250.0, girt_spacing=1250.0)


@pytest.fixture(scope="module")
def result():
    braces = [m for m in peb_building(BuildingInput(**B1))["members"] if m["role"] in ("roof_brace", "wall_brace")]
    return braces, longitudinal_bracing(GEOM, LoadsInput(V=45, exposure="C"), braces, [0, 3])


def test_chain_longhand(result):
    braces, r = result
    p = r["pressure_kpa"]
    assert p > 0
    B, H, rise = 24.0, 6.0, 1.2                                    # m; rise = 0.1 × 12
    F_eave = p * (B * H / 2 + B * rise / 2)                        # half the rectangle + the whole gable
    F_base = p * B * H / 2
    u = r["sets"]["case"]
    assert u["F_eave"] == pytest.approx(F_eave, abs=2e-3) and u["F_base"] == pytest.approx(F_base, abs=2e-3)
    per_bay = F_eave / 2                                           # 2 braced bays
    assert u["per_braced_bay"] == pytest.approx(per_bay, abs=2e-3)
    # wall: one X (eave 6000 ≤ 1.5 × 6000), base to 100 below the eave → depth 5 900; 2 sidewalls
    assert r["wall_panel"]["depth"] == pytest.approx(5900.0, abs=0.1)
    assert u["wall_diagonal"] == pytest.approx(per_bay / 2 * math.hypot(6.0, 5.9) / 6.0, abs=2e-3)
    # roof: Manafe3's deepest panel along the slope (taken from the generated braces), half the bay share per slope
    d = r["roof_panel"]["depth"] / 1000
    assert 4.0 < d < 8.0                                           # panels near 45° on a 12.06 m slope (2 panels)
    assert u["roof_diagonal"] == pytest.approx(per_bay / 2 * math.hypot(6.0, d) / 6.0, abs=2e-3)
    # sets: LRFD 1.0 W, ASD 0.6 W
    assert r["sets"]["LRFD"]["wall_diagonal"] == u["wall_diagonal"]
    assert r["sets"]["ASD"]["wall_diagonal"] == pytest.approx(0.6 * u["wall_diagonal"], abs=2e-3)
    assert r["designed"] is False and any("eave_share" in a for a in r["assumptions"])


def test_wall_panel_tension_only_truss(result):
    """PyNite, tension-only diagonals, all members pinned: the panel shear at the top goes into ONE diagonal."""
    _, r = result
    V = r["sets"]["case"]["wall_base_shear"]                       # kN, one sidewall
    b, h = 6000.0, r["wall_panel"]["depth"]                        # mm
    m = FEModel3D()
    m.add_material("S", 200.0, 77.0, 0.3, 7.85e-8)                 # kN/mm²
    m.add_section("col", 5000.0, 1e8, 1e8, 1e6)
    m.add_section("rod", 314.0, 1e3, 1e3, 1e3)
    for n, (x, z) in {"A0": (0, 0), "B0": (b, 0), "A1": (0, h), "B1": (b, h)}.items():
        m.add_node(n, x, 0.0, z)
        m.def_support(n, support_DY=True, support_RX=True, support_RY=True, support_RZ=True)
    for n in ("A0", "B0"):
        m.def_support(n, True, True, True, True, True, True)
    for name, i, j, sec, t in (("CA", "A0", "A1", "col", False), ("CB", "B0", "B1", "col", False), ("S", "A1", "B1", "col", False),
                               ("D1", "A0", "B1", "rod", True), ("D2", "B0", "A1", "rod", True)):
        m.add_member(name, i, j, "S", sec, tension_only=t)
        m.def_releases(name, Ryi=True, Rzi=True, Ryj=True, Rzj=True)
    m.add_node_load("A1", "FX", V, case="W")
    m.add_load_combo("W", {"W": 1.0})
    m.analyze(check_statics=False)
    # pushed toward +X at the top left: A0 → B1 (D1) lengthens = the tension diagonal; B0 → A1 (D2) would shorten
    ax = lambda k: max(abs(m.members[k].max_axial("W")), abs(m.members[k].min_axial("W")))
    tension = ax("D1")
    assert tension == pytest.approx(r["sets"]["case"]["wall_diagonal"], rel=1e-3)
    assert ax("D2") < 1e-3 * tension                               # the compression diagonal drops out
