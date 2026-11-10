# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 2 step 5: end walls — building 1 (span 24 000, eave 6 000, slope 0.1; span-rule sizes: rafter web 400, flanges
250×12) by hand.

End rafter + wind columns at the first frame (x = 0):
    end-wall plane x = −250/2 = −125; spaces ceil(24 000 / 6 000) = 4 → columns at y = 125 (corner), 6 000, 12 000, 18 000,
    23 875 (corner); rotation 180 (section hangs into the building)
    wind column placeholder (user): web 300 (tw 6), flanges 150×8, S355; cap plate PL10 between its top and the rafter
    rafter depth 400 + 24 = 424; with the cap (424 + 10)·√1.01 = 436.165 vertically under the roof
    tops: y 6 000: 6 600 − 436.165 = 6 163.835; y 12 000: 7 200 − 436.165 = 6 763.835; y 125: 6 012.5 − 436.165 = 5 576.335
    top cut across the flanges (u = +Y at the first end): +0.1 at y 125 / 6 000, 0 under the apex, −0.1 at 18 000 / 23 875
    cap plate over y 6 000: PL10x190 (150 + 40), x −145 → 211 (the column −125 … −125 + 316, + 20 each side), mid-plane 5 along
      the roof normal (−0.0995037, 0.9950372): y 5 999.502, z 6 168.810
    end rafters: (0, 0, 6 000) → apex (0, 12 000, 7 200), line 12 059.851 > 12 m → 2 segments of 12 059.8507 / 2 = 6 029.925; plumb cuts 0.1
    gable girts at x = −125 (rotation 270, out of the building): rows 1 250 … 5 000 full width −200 → 24 200, and 6 250
      above the eave where 6 000 + 0.1·min(y, 24 000 − y) ≥ 6 550 → y 5 500 … 18 500
      full row, supports 125 / 6 000 / 12 000 / 18 000 / 23 875 (spacings 5 875, 6 000, 6 000, 5 875), laps 10 %:
        piece 1 −200 → 6 600 (6 800); piece 2 6 000 − 587.5 = 5 412.5 → 12 600 (7 187.5); piece 4 17 400 → 24 200 (6 800)
        piece 1 holes from its start: 125 + 200 = 325, 5 412.5 + 40 + 200 = 5 652.5, 6 200, 6 600 − 40 + 200 = 6 760
      row 6 250: supports 6 000, 12 000, 18 000 → 5 500 → 12 600 (7 100), 11 400 → 18 500 (7 100)
      18 pieces in all
Main frame at the first frame: interior wind columns only (6 000, 12 000, 18 000), under the main rafter (constant 424 there:
    s = 6 000·√1.01 = 6 029.9 is past the haunch end 3 228.1) → the same tops.
Last frame (x = 24 000): plane x = 24 125, columns rotation 0, girts rotation 90.
"""

import pytest

from engine.peb.builtup_frame import default_sizes
from engine.peb.endwall import end_wall, wind_column_ys
from engine.sections.builtup import BuiltUpMember

Z = default_sizes(24000)


def test_end_rafter_and_wind_columns():
    w = end_wall("rafter", "first", 24000, 6000, 0.1, 0.0, Z)
    cols = [m for m in w["members"] if m["role"] == "wind_column"]
    assert [c["start"][1] for c in cols] == [125, 6000, 12000, 18000, 23875]
    assert all(c["start"][0] == -125 and c["rotation"] == 180 and c["start"][2] == 0 for c in cols)
    tops = {c["start"][1]: c["end"][2] for c in cols}
    assert tops[6000] == pytest.approx(6163.835, abs=1e-3) and tops[12000] == pytest.approx(6763.835, abs=1e-3)
    assert tops[125] == pytest.approx(5576.335, abs=1e-3)
    s = cols[1]["section"]["segments"][0]
    assert (s["hw_start"], s["hw_end"], s["tw"], s["bf_top"], s["tf_top"], s["grade"]) == (300, 300, 6, 150, 8, "S355")
    assert [c["section"]["cut_end_u"] for c in cols] == [0.1, 0.1, 0, -0.1, -0.1]
    cap = [m for m in w["members"] if m["id"] == "WF2-CAP"][0]
    assert cap["profile"] == "PL10x190" and cap["start"] == [-145, pytest.approx(5999.502, abs=1e-3), pytest.approx(6168.810, abs=1e-3)]
    assert cap["end"][0] == 211 and len([m for m in w["members"] if m["role"] == "cap_plate"]) == 5
    raf = [m for m in w["members"] if m["role"] == "end_rafter"]
    assert len(raf) == 2 and raf[0]["start"] == [0, 0, 6000] and raf[0]["end"] == [0, 12000, 7200]
    assert [x["length"] for x in raf[0]["section"]["segments"]] == [pytest.approx(6029.925, abs=1e-3)] * 2
    assert raf[0]["section"]["cut_start"] == 0.1 and raf[0]["section"]["cut_end"] == 0.1
    for m in w["members"]:
        if "section" in m:
            BuiltUpMember.from_dicts(m["section"]["segments"])
        assert m["designed"] is False


def test_gable_girts():
    g = end_wall("rafter", "first", 24000, 6000, 0.1, 0.0, Z)["girts"]
    assert len(g) == 18 and all(x["start"][0] == -125 and x["rotation"] == 270 for x in g)
    row1 = [x for x in g if x["z"] == 1250]
    assert [x["length"] for x in row1] == [6800, 7187.5, 7187.5, 6800]
    assert row1[0]["start"][1] == -200 and row1[-1]["end"][1] == 24200
    assert sorted({h["x"] for h in row1[0]["holes"]}) == [325, 5652.5, 6200, 6760]
    top = [x for x in g if x["z"] == 6250]
    assert [(x["start"][1], x["end"][1]) for x in top] == [(5500, 12600), (11400, 18500)]


def test_main_frame_end_wall_and_last_end():
    w = end_wall("frame", "first", 24000, 6000, 0.1, 0.0, Z)
    cols = [m for m in w["members"] if m["role"] == "wind_column"]
    assert [c["start"][1] for c in cols] == [6000, 12000, 18000] and not [m for m in w["members"] if m["role"] == "end_rafter"]
    assert cols[0]["end"][2] == pytest.approx(6163.835, abs=1e-3)
    assert w["supports"] == [125, 6000, 12000, 18000, 23875]
    last = end_wall("rafter", "last", 24000, 6000, 0.1, 24000.0, Z)
    assert last["x_face"] == 24125 and all(m["rotation"] == 0 for m in last["members"] if m["role"] == "wind_column")
    assert [m["section"]["cut_end_u"] for m in last["members"] if m["role"] == "wind_column"] == [-0.1, -0.1, 0, 0.1, 0.1]   # u = −Y there
    assert all(x["rotation"] == 90 for x in last["girts"])
    assert wind_column_ys(30000, 250, "rafter") == [125, 6000, 12000, 18000, 24000, 29875]
    with pytest.raises(ValueError, match="frame or rafter"):
        end_wall("open", "first", 24000, 6000, 0.1, 0.0, Z)
