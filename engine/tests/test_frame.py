# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 0 hot-rolled portal-frame geometry (section="hot_rolled") against coordinates worked out by hand (written out below, not recomputed by the code).

Case 1: span 20 000, eave 6 000, slope 1:10, bays 2 x 6 000
    frame lines x = 0, 6 000, 12 000                     -> 3 frames, 12 members
    apex z = 6 000 + 0.1 x 20 000 / 2 = 6 000 + 1 000 = 7 000, at y = 10 000
    rafter length = sqrt(10 000^2 + 1 000^2) = sqrt(101 000 000) = 10 049.876 mm
    span <= 24 000 -> placeholders HEA400 / IPE500

Case 2: span 30 000, eave 8 000, slope 1:12, bays 4 x 7 500
    frame lines x = 0, 7 500, 15 000, 22 500, 30 000      -> 5 frames, 20 members
    apex z = 8 000 + 30 000 / 2 / 12 = 8 000 + 1 250 = 9 250, at y = 15 000
    rafter length = sqrt(15 000^2 + 1 250^2) = sqrt(226 562 500) = 15 051.993 mm
    span > 24 000 -> placeholders HEA500 / IPE600
"""

import pytest

from engine.peb.frame import FrameInput, portal_frame


def by_id(frame):
    return {m["id"]: m for m in frame["members"]}


def test_case1_span20m_two_bays():
    f = portal_frame(FrameInput(span=20000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=2, section="hot_rolled"))
    m = by_id(f)
    assert len(f["members"]) == 12
    assert [g["at"] for g in f["grids"]["x"]] == [0.0, 6000.0, 12000.0]
    assert [g["label"] for g in f["grids"]["x"]] == ["1", "2", "3"]
    assert f["grids"]["y"] == [{"label": "A", "at": 0.0}, {"label": "B", "at": 20000.0}]
    assert f["apex_height"] == 7000.0
    assert f["rafter_length"] == pytest.approx(10049.876, abs=0.001)
    # frame line 2 (x = 6 000), every member end by hand
    assert m["F2-CA"]["start"] == [6000.0, 0.0, 0.0] and m["F2-CA"]["end"] == [6000.0, 0.0, 6000.0]
    assert m["F2-CB"]["start"] == [6000.0, 20000.0, 0.0] and m["F2-CB"]["end"] == [6000.0, 20000.0, 6000.0]
    assert m["F2-RA"]["start"] == [6000.0, 0.0, 6000.0] and m["F2-RA"]["end"] == [6000.0, 10000.0, 7000.0]
    assert m["F2-RB"]["start"] == [6000.0, 20000.0, 6000.0] and m["F2-RB"]["end"] == [6000.0, 10000.0, 7000.0]
    # last frame line
    assert m["F3-RA"]["end"] == [12000.0, 10000.0, 7000.0]
    assert {m["F1-CA"]["profile"], m["F1-RA"]["profile"]} == {"HEA400", "IPE500"}
    assert m["F1-CA"]["role"] == "column" and m["F1-RA"]["role"] == "rafter"
    assert all(x["designed"] is False for x in f["members"])


def test_case2_span30m_four_bays():
    f = portal_frame(FrameInput(span=30000, eave_height=8000, roof_slope=1 / 12, bay_spacing=7500, n_bays=4, section="hot_rolled"))
    m = by_id(f)
    assert len(f["members"]) == 20
    assert [g["at"] for g in f["grids"]["x"]] == [0.0, 7500.0, 15000.0, 22500.0, 30000.0]
    assert f["apex_height"] == 9250.0
    assert f["rafter_length"] == pytest.approx(15051.993, abs=0.001)
    assert m["F5-CB"]["start"] == [30000.0, 30000.0, 0.0] and m["F5-CB"]["end"] == [30000.0, 30000.0, 8000.0]
    assert m["F4-RA"]["start"] == [22500.0, 0.0, 8000.0] and m["F4-RA"]["end"] == [22500.0, 15000.0, 9250.0]
    assert m["F1-RB"]["start"] == [0.0, 30000.0, 8000.0] and m["F1-RB"]["end"] == [0.0, 15000.0, 9250.0]
    assert m["F3-CA"]["profile"] == "HEA500" and m["F3-RA"]["profile"] == "IPE600"
    assert f["levels"] == [{"name": "Ground", "z": 0.0}, {"name": "Eave", "z": 8000.0}]


@pytest.mark.parametrize("bad", [
    dict(span=1000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=2),
    dict(span=20000, eave_height=6000, roof_slope=-0.1, bay_spacing=6000, n_bays=2),
    dict(span=20000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=0),
    dict(span=20000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=60),
])
def test_out_of_range_is_refused(bad):
    with pytest.raises(ValueError):
        portal_frame(FrameInput(**bad))
