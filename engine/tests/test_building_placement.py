# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Field fixes 6 (uneven bays) and 7 (span reference) — engine/peb/building.py resolve(); values by hand.

    bays        R1 block 1's site spacings 6600 6000 6000 6500 6000 5500 6000 6000 6000 5400 (A … L, 60 000 mm): the frame
                lines and grids at the cumulative positions; every main-frame column on its line; the analysis' tributary
                width of line B = (6600 + 6000) / 2 = 6.3 m
    span ref    centreline: steel span = span + d_base (d_base = hw_base + 2 tf), y_shift = -d_base / 2, so column A's base
                centreline lands on y = 0; grid with inset 100: steel span = span - 200, y_shift = +100; outside: unchanged
    negative    a bay of 2500 mm is refused with its number; an unknown reference is refused
"""

import pytest

from engine.peb.building import BuildingInput, peb_building, resolve

R1_BAYS = (6600, 6000, 6000, 6500, 6000, 5500, 6000, 6000, 6000, 5400)              # R1 site grids A B C D E F G H J K L
R1_X = (0, 6600, 12600, 18600, 25100, 31100, 36600, 42600, 48600, 54600, 60000)      # their x, by hand


def b1(**kw):
    return BuildingInput(**{"span": 24000, "eave_height": 6000, "roof_slope": 0.1, "bay_spacing": 6000, "n_bays": 4, **kw})


def test_uneven_bays_positions():
    b = b1(bays=R1_BAYS, span=27600, eave_height=5400, roof_slope=0.0435)
    assert b.frame_xs() == list(map(float, R1_X))
    out = peb_building(b)
    assert [g["at"] for g in out["grids"]["x"]] == list(map(float, R1_X))
    xs = sorted({round(m["start"][0], 3) for m in out["members"] if m["role"] == "column"})
    assert xs == list(map(float, R1_X))                                   # one main frame per line, both ends main frames
    assert out["input"]["bays"] == list(map(float, R1_BAYS)) and out["input"]["n_bays"] == 10
    # purlins run the whole length: their pieces' x span 0 … 60 000 (+ the end overhangs)
    pur = [m for m in out["members"] if m["role"] == "purlin"]
    assert min(min(m["start"][0], m["end"][0]) for m in pur) < 0 < 60000 < max(max(m["start"][0], m["end"][0]) for m in pur)


def test_uneven_bays_tributary():
    from engine.analysis.building_analysis import _line_setup
    from engine.analysis.secondary_weight import secondary_kpa
    from engine.peb.loads_input import LoadsInput
    b = b1(bays=(6600, 6000, 6000))
    info, fl = _line_setup(b, LoadsInput(V=45, exposure="C"), 1, secondary_kpa(peb_building(b)), 0.10)
    assert fl.tributary_m == pytest.approx(6.3)                           # (6600 + 6000) / 2
    info0, fl0 = _line_setup(b, LoadsInput(V=45, exposure="C"), 0, secondary_kpa(peb_building(b)), 0.10)
    assert fl0.tributary_m == pytest.approx(3.3)                          # end line: half of 6600


def test_span_reference():
    out0 = peb_building(b1())
    z = resolve(b1())[0].sizes
    d = z.hw_base + 2 * z.tf
    r, y0 = resolve(b1(span_ref="centreline"))
    assert r.span == pytest.approx(24000 + d) and y0 == pytest.approx(-d / 2)
    out = peb_building(b1(span_ref="centreline"))
    assert out["y_shift"] == pytest.approx(-d / 2) and out["grids"]["y"][1]["at"] == 24000 and out["input"]["span"] == pytest.approx(24000 + d)
    ca = next(m for m in out["members"] if m["role"] == "column" and m["side"] == "A")
    cb = next(m for m in out["members"] if m["role"] == "column" and m["side"] == "B")
    # the columns' outer faces are on y = 0 and the steel span in steel coordinates; after the shift the base centrelines
    # are at 0 + d/2 - d/2 = 0 and (24000 + d) - d/2 - d/2 = 24000
    assert ca["start"][1] + d / 2 + out["y_shift"] == pytest.approx(0.0, abs=1e-6)
    assert cb["start"][1] - d / 2 + out["y_shift"] == pytest.approx(24000.0, abs=1e-6)
    r, y0 = resolve(b1(span_ref="grid", grid_inset=100))
    assert r.span == 23800 and y0 == 100
    assert peb_building(b1(span_ref="outside"))["y_shift"] == 0.0 and out0["input"]["span"] == 24000
    assert resolve(r)[0] == r                                             # idempotent


def test_refused():
    with pytest.raises(ValueError, match="bay 2"):
        peb_building(b1(bays=(6000, 2500, 6000)))
    with pytest.raises(ValueError, match="span reference"):
        peb_building(b1(span_ref="inside"))


def test_api_takes_bays_and_reference():
    from fastapi.testclient import TestClient
    from engine.api import app
    c = TestClient(app)
    body = {"span": 24000, "eave_height": 6000, "roof_slope": 0.1, "bay_spacing": 6600, "n_bays": 2, "bays": [6600, 6000], "span_ref": "grid", "grid_inset": 100}
    r = c.post("/peb/building", json=body)
    assert r.status_code == 200, r.text
    d = r.json()
    assert [g["at"] for g in d["grids"]["x"]] == [0.0, 6600.0, 12600.0] and d["y_shift"] == 100.0 and d["input"]["span"] == 23800
    assert c.post("/peb/building", json={**body, "bays": [6600, 2000]}).status_code == 422