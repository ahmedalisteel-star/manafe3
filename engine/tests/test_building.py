# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 2 step 7: the whole building — building 1 (span 24 000, eave 6 000, slope 0.1, 4 bays of 6 000), composed from
the component cases checked by hand in test_secondary_*, test_bracing, test_endwall, test_openings.

Main frames at both ends (default), braced bays 1 and 4 (default):
    main frame members 5 lines × 4 = 20
    roof: 10 Z lines a side × 4 pieces = 80; eave struts 2 lines × 4 = 8; side girts 8 lines × 4 = 32
    sag rods 84; X-bracing 16 roof + 8 wall = 24; flange braces 36 rafter + 32 column = 68
    wind columns 3 per end = 6; gable girts 18 per end = 36            → 358 members; cleats 30 lines × 5 frames = 150
End rafter at the first end instead: −4 main frame members, +5 wind columns + 2 end rafters − 3 = +4, and the 4 column
flange braces at x = 0 go (2 girts × 2 walls, the end columns' inward braces) → 354.
COUNT IS NOT CORRECTNESS: the positions behind these numbers are checked in the component tests; here a few are spot-checked
again through the whole-building call.
"""

from collections import Counter

import pytest
from fastapi.testclient import TestClient

from engine.api import app
from engine.peb.building import BuildingInput, peb_building
from engine.sections.builtup import BuiltUpMember

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)


def roles(out):
    return Counter(m["role"] for m in out["members"])


def test_building_1_composition():
    out = peb_building(BuildingInput(**B1))
    r = roles(out)
    assert r["column"] + r["rafter"] == 20
    assert r["purlin"] + r["ridge_purlin"] == 80 and r["eave_strut"] == 8 and r["girt"] == 32
    assert r["sag_rod"] == 84 and r["roof_brace"] == 16 and r["wall_brace"] == 8 and r["flange_brace"] == 68
    assert r["wind_column"] == 6 and r["gable_girt"] == 36
    assert len(out["members"]) == 358 and len(out["cleats"]) == 150
    assert out["braced_bays"] == [1, 4] and out["designed"] is False
    assert len({m["id"] for m in out["members"]}) == 358 and all(m["gen"] == "peb" for m in out["members"])
    for m in out["members"]:
        if "section" in m:
            BuiltUpMember.from_dicts(m["section"]["segments"])
    assert out["fasteners"] == [{"item": "nut M12", "count": 336}, {"item": "washer M12", "count": 336}]


def test_spot_positions_through_the_whole_call():
    out = peb_building(BuildingInput(**B1))
    by = {m["id"]: m for m in out["members"]}
    assert by["F2-RA"]["start"] == [6000, 824, 6082.4]                                   # Phase 1 case A
    p = by["RA1-2"]                                                                      # piece 5 400 → 12 600
    assert p["start"][0] == 5400 and p["length"] == 7200
    assert sorted({h["x"] for h in p["holes"] if abs(h["y"] - 33.333) < 1e-3}) == [3560, 3640]   # sag rods at 8 960 / 9 040
    assert by["WF1"]["start"] == [-125, 6000, 0] and by["WF1"]["end"][2] == pytest.approx(6173.885, abs=1e-3)
    assert {m["profile"] for m in out["members"] if m["role"] in ("sag_rod",)} == {"RD12"}


def test_end_rafter_variant_openings_and_options():
    out = peb_building(BuildingInput(**B1, end_first="rafter", bolt="M16", braced_bays=(2,),
                                     openings=({"wall": "A", "at": 7000, "width": 4000, "sill": 0, "height": 4000},)))
    r = roles(out)
    assert "F1-CA" not in {m["id"] for m in out["members"]} and r["end_rafter"] == 2 and r["wind_column"] == 8
    assert r["jamb"] == 2 and r["header"] == 1
    assert all(h["d"] in (18, 14) for m in out["members"] for h in m.get("holes", []))      # M16 frame/lap holes, Ø14 sag-rod holes
    assert any(h["d"] == 18 for m in out["members"] for h in m.get("holes", []))
    assert out["braced_bays"] == [2]
    base = peb_building(BuildingInput(**B1, end_first="rafter"))
    assert len(base["members"]) == 354


def test_api():
    c = TestClient(app)
    r = c.post("/peb/building", json={**B1, "openings": [{"wall": "B", "at": 3000, "width": 3000, "height": 3500}]})
    assert r.status_code == 200 and len(r.json()["members"]) > 350
    bad = c.post("/peb/building", json={**B1, "braced_bays": [9]})
    assert bad.status_code == 422 and "bay 9" in bad.json()["detail"]
