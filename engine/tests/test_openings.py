# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 2 step 6: framed openings — building 1, side wall A, by hand.

Wall A girt pieces (rows 1 250 / 2 500 / 3 750 / 5 000; pieces −325 → 6 600, 5 400 → 12 600, 11 400 → 18 600, 17 400 → 24 325;
holes of the piece 5 400 → 12 600 at x 5 440, 6 000, 6 560, 11 440, 12 000, 12 560).
Door at x 7 000, width 4 000, height 4 000:
    rows 1 250, 2 500, 3 750 are cut (0 < z < 4 000); 5 000 is not
    piece 5 400 → 12 600 becomes 5 400 → 7 000 (1 600) and 11 000 → 12 600 (1 600)
      left keeps 5 440, 6 000, 6 560 and gets 7 000 − 40 = 6 960 → from its start: 40, 600, 1 160, 1 560
      right keeps 11 440, 12 000, 12 560 and gets 11 040 → 40, 440, 1 000, 1 560
    jambs at x 7 000 and 11 000, floor to the girt above the head (5 000); header at 4 000, 4 000 long
Window at x 14 000, width 2 000, sill 1 000, height 1 500 (head 2 500):
    only row 1 250 is cut; a girt row sits at the head (2 500) → no header; a sill at 1 000
    no girt row at or under the sill → jambs from the floor to 2 500
    piece 11 400 → 18 600 at 1 250 becomes 11 400 → 14 000 (2 600, holes 40, 600, 1 160, 2 560) and 16 000 → 18 600
Wall A then has 6 + 5 + 5 + 4 = 20 girt pieces (16 before).
"""

import pytest

from engine.peb.openings import apply_openings
from engine.peb.secondary import SecondaryInput, secondary_lines, secondary_members

LINES = secondary_lines(SecondaryInput(span=24000, eave_height=6000, roof_slope=0.1, length=24000))
ALL = secondary_members(LINES, [0, 6000, 12000, 18000, 24000], end_overhang=325)["members"]
GIRTS = [m for m in ALL if m["role"] == "girt"]
DOOR = {"wall": "A", "at": 7000, "width": 4000, "sill": 0, "height": 4000}
WINDOW = {"wall": "A", "at": 14000, "width": 2000, "sill": 1000, "height": 1500}


def xs(p):
    return sorted({h["x"] for h in p["holes"]})


def test_door():
    out = apply_openings(GIRTS, [DOOR], eave=6000)
    a = [p for p in out["girts"] if p["side"] == "A" and p["start"][2] == 1250]
    left = [p for p in a if p["start"][0] == 5400][0]
    right = [p for p in a if p["start"][0] == 11000][0]
    assert left["end"][0] == 7000 and left["length"] == 1600 and xs(left) == [40, 600, 1160, 1560]
    assert right["end"][0] == 12600 and right["length"] == 1600 and xs(right) == [40, 440, 1000, 1560]
    assert len([p for p in out["girts"] if p["side"] == "A" and p["start"][2] == 5000]) == 4          # above the door: untouched
    j = [m for m in out["members"] if m["role"] == "jamb"]
    assert [(m["start"], m["end"]) for m in j] == [([7000, 0, 0], [7000, 0, 5000]), ([11000, 0, 0], [11000, 0, 5000])]
    assert all(m["rotation"] == 270 and m["profile"] == "C200x65x20x2.0" for m in j)
    h = [m for m in out["members"] if m["role"] == "header"]
    assert len(h) == 1 and h[0]["start"] == [7000, 0, 4000] and h[0]["end"] == [11000, 0, 4000] and h[0]["length"] == 4000
    assert len([p for p in out["girts"] if p["side"] == "B"]) == 16                                     # wall B untouched


def test_window_and_counts():
    out = apply_openings(GIRTS, [DOOR, WINDOW], eave=6000)
    assert len([p for p in out["girts"] if p["side"] == "A"]) == 20
    w = [m for m in out["members"] if m["id"].startswith("O2")]
    assert {m["role"] for m in w} == {"jamb", "sill"}                                                   # head on a girt row
    j = [m for m in w if m["role"] == "jamb"]
    assert all(m["start"][2] == 0 and m["end"][2] == 2500 for m in j)
    s = [m for m in w if m["role"] == "sill"][0]
    assert s["start"] == [14000, 0, 1000] and s["end"] == [16000, 0, 1000]
    left = [p for p in out["girts"] if p["side"] == "A" and p["start"][2] == 1250 and p["start"][0] == 11400][0]
    assert left["end"][0] == 14000 and xs(left) == [40, 600, 1160, 2560]


def test_gable_door():
    """End wall (first): girts along y at x = −125 (endwall.py); door at y 9 000, 6 000 wide, 4 500 high → rows 1 250,
    2 500, 3 750 cut; jambs at y 9 000 and 15 000, floor to the 5 000 row, rotation 180 (out of the building, −X)."""
    from engine.peb.builtup_frame import default_sizes
    from engine.peb.endwall import end_wall
    g = end_wall("rafter", "first", 24000, 6000, 0.1, 0.0, default_sizes(24000))["girts"]
    out = apply_openings(g, [{"wall": "first", "at": 9000, "width": 6000, "sill": 0, "height": 4500}], eave=6000)
    j = [m for m in out["members"] if m["role"] == "jamb"]
    assert [(m["start"], m["end"]) for m in j] == [([-125, 9000, 0], [-125, 9000, 5000]), ([-125, 15000, 0], [-125, 15000, 5000])]
    assert all(m["rotation"] == 180 for m in j)
    row = [p for p in out["girts"] if p["z"] == 1250]
    assert all(not (9000 < (p["start"][1] + p["end"][1]) / 2 < 15000) for p in row)                     # nothing left in the door
    # row 1 250 pieces −200 → 6 600 (untouched), 5 412.5 → 12 600 (keeps 5 412.5 → 9 000), 11 400 → 18 587.5 (keeps
    # 15 000 → 18 587.5), 17 400 → 24 200 (untouched): 4 pieces
    assert len(row) == 4
    assert sorted((p["start"][1], p["end"][1]) for p in row)[1] == (5412.5, 9000)


@pytest.mark.parametrize("bad, msg", [
    ({**DOOR, "wall": "C"}, "A, B, first or last"),
    ({**DOOR, "width": 100}, "at least 300"),
    ({**DOOR, "height": 6500}, "under the eave"),
])
def test_refusals(bad, msg):
    with pytest.raises(ValueError, match=msg):
        apply_openings(GIRTS, [bad], eave=6000)
