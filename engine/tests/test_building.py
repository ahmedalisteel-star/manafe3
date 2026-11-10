# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 2 step 7: the whole building — building 1 (span 24 000, eave 6 000, slope 0.1, 4 bays of 6 000), composed from
the component cases checked by hand in test_secondary_*, test_bracing, test_endwall, test_openings.

Main frames at both ends (default), braced bays 1 and 4 (default):
    main frame members 5 lines × 4 = 20
    roof: 10 Z lines a side × 4 pieces = 80; eave struts 2 lines × 4 = 8; side girts 8 lines × 4 = 32
    sag rods 80 + ridge ties 4 (one per sag row, across the apex); X-bracing 16 roof + 8 wall = 24; flange braces: rafters 3 interior frames × 2 sides × 3 × 2 = 36 + the end frames'
    INWARD braces 2 × 2 × 3 = 12 (user, 2026-11-08), columns 32 → 80
    wind columns 3 per end = 6 + their cap plates 6; gable girts 18 per end = 36      → 376 members
    cleats: 30 lines × 5 frames = 150 + gable girts on the wind/corner columns per end: 4 full rows × 5 supports + the
    6 250 row × 3 = 23 → 46 → 196
End rafter at the first end instead: −4 main frame members, +5 wind columns + 2 end rafters − 3 = +4, and the 4 column
flange braces at x = 0 go (2 girts × 2 walls, the end columns' inward braces) → 354; + 5 + 3 cap plates → 362.
Since 2026-11-08: + the default end-wall X in that end-rafter wall (2 diagonals) + the LAST end frame's 6 inward rafter
flange braces (the first end has no main frame, so none there) → 370.
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
    assert r["sag_rod"] == 80 and r["ridge_tie"] == 4 and r["cap_plate"] == 6 and r["roof_brace"] == 16 and r["wall_brace"] == 8 and r["flange_brace"] == 80 + 28   # + wind-column braces (2026-11-09)
    assert r["wind_column"] == 6 and r["gable_girt"] == 36
    assert len(out["members"]) == 376 + 28 and len(out["cleats"]) == 196
    assert out["braced_bays"] == [1, 4] and out["designed"] is False
    assert len({m["id"] for m in out["members"]}) == 376 + 28 and all(m["gen"] == "peb" for m in out["members"])
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
    assert by["WF1"]["start"] == [-125, 6000, 0] and by["WF1"]["end"][2] == pytest.approx(6163.835, abs=1e-3)
    gc = [c for c in out["cleats"] if c["host"] == "wind column first" and c["base"][1] == 6000 and c["base"][2] == 1250][0]
    # first end: gable girt rotation 270 → its u = (0, 0, −1), v = (−1, 0, 0): the cleat starts 5 below and runs 180 out (−X)
    assert gc["start"] == [-125, 6000, 1245] and gc["end"] == [-305, 6000, 1245] and gc["width_dir"] == [0, 1, 0]
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
    assert len(base["members"]) == 370 + 32   # 362 + the end-wall X (2) + the last end frame's 6 inward rafter flange braces;
    # + wind-column flange braces: the end-rafter wall 18 (corners 2 + 2, inward only — the girt stops at −200; WF2, WF4 4 each,
    # WF3 6), the main-frame wall 14
    strap = peb_building(BuildingInput(**B1, ridge_tie="strap"))
    ties = [m for m in strap["members"] if m["role"] == "ridge_tie"]
    assert len(ties) == 4 and {m["profile"] for m in ties} == {"PL3x50"}
    assert {"item": "bolt M12 with nut and washer", "count": 8} in strap["fasteners"]
    assert strap["fasteners"][0] == {"item": "nut M12", "count": 320}                    # 80 sag rods × 4


def test_api():
    c = TestClient(app)
    r = c.post("/peb/building", json={**B1, "openings": [{"wall": "B", "at": 3000, "width": 3000, "height": 3500}]})
    assert r.status_code == 200 and len(r.json()["members"]) > 350
    bad = c.post("/peb/building", json={**B1, "braced_bays": [9]})
    assert bad.status_code == 422 and "bay 9" in bad.json()["detail"]


def test_wind_column_flange_braces():
    """User 2026-11-09: flange braces from the gable girts to the wind columns' inner flange, every second girt from the
    top by default, per wall, 0 = none. Hand values on building 1 (both end walls main frames, columns at y 6 / 12 / 18 m)."""
    out = peb_building(BuildingInput(**B1))
    fb = [m for m in out["members"] if m["role"] == "flange_brace" and m["host"].startswith("wind column")]
    at = lambda cid: sorted({m["start"][2] for m in fb if m["host"] == "wind column " + cid})
    # WF1 (top 6 163.8) carries rows 1250 … 5000 → from the top every second: 5000, 2500; WF2 (top 6 764) also 6250 → 6250, 3750, 1250
    assert at("WF1") == [2500, 5000] and at("WF2") == [1250, 3750, 6250] and len(fb) == 2 * (2 + 3 + 2) * 2
    b = next(m for m in fb if m["host"] == "wind column WF1" and m["start"][2] == 2500 and m["end"][1] < 6000)
    # inner flange mid-thickness x = −125 + 316 − 4 = 187; 50 into the girt x = −175; run 362 → y 5 638; length 362 √2
    assert b["start"] == [187, 6000, 2500] and b["end"] == [-175, 5638, 2500] and b["length"] == pytest.approx(362 * 2 ** 0.5, abs=1e-3)
    assert b["profile"] == "L50x5" and b["type"] == "brace"
    off = peb_building(BuildingInput(**B1, wc_braces_first=0))
    fb0 = [m for m in off["members"] if m["role"] == "flange_brace" and m["host"].startswith("wind column")]
    assert len(fb0) == 14 and all(m["wall"] == "last" for m in fb0)                      # switched off on the first wall only
    every3 = peb_building(BuildingInput(**B1, wc_braces_last=3))
    assert sorted({m["start"][2] for m in every3["members"] if m.get("host") == "wind column WL2"}) == [2500, 6250]   # 6250, then every third
    with pytest.raises(ValueError, match="whole number"):
        peb_building(BuildingInput(**B1, wc_braces_first=-1))
