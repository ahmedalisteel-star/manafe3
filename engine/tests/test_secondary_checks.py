# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 5: wind columns, end rafters, bracing (engine/design/secondary_checks.py) — longhand per type.

    wind column   the demand is the simple beam's: M(L/2) = w L² / 8 (inward +, outward −), V(0) = w L / 2; the inner
                  flange braced only at the ends, the outer at every gable girt; shear capacity 0.90 × 0.6 Fy d tw Cv1
                  (G2.1, kv 5.34) longhand
    end rafter    the frame's station moments have the design sign (gravity: sagging + mid-span, hogging − over a wind
                  column) and their largest |M| is the solver's own rafter_M; bottom flange braced at the wind-column tops
    rod           RD20 S355 (d 20 → EN 10025-2 band ≤ 40: Fy 345, Fu 470): φRn = 0.75 × 0.75 × 470 × π 20² / 4 = 83.05 kN
    angle         L75x6 S355 (t 6 → Fy 355, Fu 470): A 864; yield 0.90 × 355 × 864 = 276.05 kN; rupture An 864 − 18 × 6 = 756,
                  Ae 0.6 × 756 = 453.6, 0.75 × 470 × 453.6 = 159.89 kN; r_min against an independent numerical integration
    must fail     a rod at 1.5 × its capacity: ratio 1.5, not passed
"""

import math

import pytest

from engine.design.secondary_checks import angle_props, end_rafter_inputs, tension_check, wind_column_inputs
from engine.analysis.endwall_analysis import WIND_COLUMN, end_rafter_frame
from engine.analysis.secondary_weight import secondary_kpa
from engine.peb.building import BuildingInput, peb_building
from engine.peb.loads_input import LoadsInput

LI = LoadsInput(V=45, exposure="C")


@pytest.fixture(scope="module")
def bld():
    out = peb_building(BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4, end_first="rafter"))
    sec = secondary_kpa(out)
    ef = end_rafter_frame(out, "first", LI, roof_secondary_kpa=sec["roof_kpa"], wall_secondary_kpa=sec["wall_kpa"])
    return out, ef


def test_rod_by_hand():
    r = tension_check("RD20", "S355", 21.596, 8000)
    cap = 0.75 * 0.75 * 470 * math.pi * 20 ** 2 / 4 / 1000
    assert cap == pytest.approx(83.05, abs=0.01)
    thread = next(c for c in r["checks"] if c["name"].startswith("Threaded"))
    assert thread["capacity"] == pytest.approx(cap, abs=1e-3) and r["ratio"] == pytest.approx(21.596 / cap, abs=1e-4)
    bad = tension_check("RD20", "S355", 1.5 * cap, 8000)
    assert bad["ratio"] == pytest.approx(1.5, abs=1e-3) and not bad["passed"]                        # negative control


def test_angle_by_hand():
    r = tension_check("L75x6", "S355", 100.0, 8000, "M16")
    y = next(c for c in r["checks"] if "yielding" in c["name"])
    u = next(c for c in r["checks"] if "rupture" in c["name"])
    assert y["capacity"] == pytest.approx(0.90 * 355 * 864 / 1000, abs=1e-3)                         # 276.048
    assert u["capacity"] == pytest.approx(0.75 * 470 * 0.6 * (864 - 18 * 6) / 1000, abs=1e-3)         # 159.894
    assert r["governing"].startswith("Tension rupture")
    # r_min independently: integrate the L on a 0.25 mm grid, principal minimum second moment
    b, t, h = 75.0, 6.0, 0.25
    pts = [((i + 0.5) * h, (j + 0.5) * h) for i in range(int(b / h)) for j in range(int(b / h)) if (i + 0.5) * h <= t or (j + 0.5) * h <= t]
    A = len(pts) * h * h
    cx = sum(p[0] for p in pts) * h * h / A
    cy = sum(p[1] for p in pts) * h * h / A
    Ix = sum((p[1] - cy) ** 2 for p in pts) * h * h + len(pts) * h ** 4 / 12
    Iy = sum((p[0] - cx) ** 2 for p in pts) * h * h + len(pts) * h ** 4 / 12
    Ixy = sum((p[0] - cx) * (p[1] - cy) for p in pts) * h * h
    Imin = (Ix + Iy) / 2 - math.sqrt(((Ix - Iy) / 2) ** 2 + Ixy ** 2)
    p = angle_props(b, t)
    assert p["A"] == pytest.approx(864) and A == pytest.approx(864, rel=1e-3)
    assert p["r_min"] == pytest.approx(math.sqrt(Imin / A), rel=2e-3)                                 # ≈ 14.7 mm


@pytest.mark.slow
def test_wind_column_demand_and_bracing(bld):
    out, ef = bld
    rows = wind_column_inputs(out, LI, {"first": ef})
    meta, inp = next(x for x in rows if x[0]["id"] == "WF3")
    L, wo, wi_ = meta["L_m"], abs(meta["sets"]["LRFD"]["outward"]["w"]), abs(meta["sets"]["LRFD"]["inward"]["w"])
    outw = inp.forces["LRFD C&C outward (+ frame P)"]
    inw = inp.forces["LRFD C&C inward (+ frame P)"]
    assert outw[10].Mz == pytest.approx(-wo * L * L / 8, rel=1e-9) and inw[10].Mz == pytest.approx(wi_ * L * L / 8, rel=1e-9)
    assert outw[0].Vy == pytest.approx(wo * L / 2, rel=1e-9)
    # inner flange: its flange braces from the gable girts (default every second girt from the top: WF3, top 6 764 → 6250, 3750,
    # 1250); outer flange: every girt
    assert inp.bracing.bottom_flange == tuple(meta["flange_braces"]) == (1250.0, 3750.0, 6250.0) and len(inp.bracing.top_flange) >= 3
    assert meta["P_frame"] > 0                                                                        # on an end-rafter wall: the frame's column load
    wl = next(x for x in wind_column_inputs(out, LI, {"first": ef}) if x[0]["id"].startswith("WL"))[0]
    assert wl["P_frame"] == 0.0                                                                       # a main-frame end wall: own weight only
    from engine.design.secondary_checks import _design_row
    d = _design_row(meta, inp)
    sh = next(c for c in d["checks"] if c["name"].startswith("Shear"))
    Fy, E = meta["Fy"], 200000.0 * 1.0
    h, tw, dd = WIND_COLUMN["hw"], WIND_COLUMN["tw"], WIND_COLUMN["hw"] + 2 * WIND_COLUMN["tf"]
    lim = 1.10 * math.sqrt(5.34 * 29000 * 6.894757293168361 / Fy)
    cv1 = 1.0 if h / tw <= lim else lim / (h / tw)
    assert sh["capacity"] == pytest.approx(0.90 * 0.6 * Fy * dd * tw * cv1 / 1000, rel=2e-3)
    assert 0 < d["ratio"] < 2
    # switched off on that wall: the inner flange is braced at the ends only, and the check is worse (negative control)
    out0 = peb_building(BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4, end_first="rafter", wc_braces_first=0))
    meta0, inp0 = next(x for x in wind_column_inputs(out0, LI, {"first": ef}) if x[0]["id"] == "WF3")
    d0 = _design_row(meta0, inp0)
    assert inp0.bracing.bottom_flange == () and d0["ratio"] > d["ratio"], (d0["ratio"], d["ratio"])


@pytest.mark.slow
def test_end_rafter_signs_and_bracing(bld):
    out, ef = bld
    rows = end_rafter_inputs(out, ef)
    meta, inp = rows[0]
    assert meta["id"] == "EFRA" and meta["Lb_bottom"] == pytest.approx([125.6, 6029.9], abs=0.1)     # wind columns at y 125, 6000
    grav = next(c for c, r in ef["results"].items() if r["set"] == "LRFD" and "Lr" in c and "W" not in c)
    st = ef["results"][grav]["rafter_stations"]
    # span y 6000 → 12000 (half A, between WF2 and WF3): sagging mid-span +, hogging over WF2 −
    mid = [M for y, P, V, M in st if 8900 < y < 9100]
    sup = [M for y, P, V, M in st if abs(y - 6000) < 1]
    assert mid and max(mid) > 0 and sup and min(sup) < 0, (mid, sup)
    assert max(abs(M) for _, _, _, M in st) == pytest.approx(ef["results"][grav]["rafter_M"], abs=2e-3)


@pytest.mark.slow
def test_whole_building_step5():
    import json
    from engine.design.secondary_checks import BANNER, secondary_checks
    r = secondary_checks(BuildingInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4, end_first="rafter"), LI)
    assert r["banner"] == BANNER and not r["designed"] and len(r["eave_struts"]) == 8 and r["cold_formed"]["max_ratio"] > 0
    assert len(r["wind_columns"]) == 5 + 3 and len(r["end_rafters"]) == 2                            # WF1–5 (corners too), WL at 6/12/18 m
    assert {x["what"] for x in r["bracing"]} == {"roof brace", "wall brace", "end-wall brace (first end)"}
    step5 = [x["ratio"] for x in r["wind_columns"] + r["end_rafters"] + r["bracing"]]
    assert 0 < max(step5) < 1.0                                                                       # default sizes carry building 1
    assert r["max_ratio"] == max(max(step5), r["cold_formed"]["max_ratio"])                          # cold-formed: strict uplift fails (step 6)
    json.dumps(r)                                                                                     # plain JSON for the API
