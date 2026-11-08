# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 2 step 4: sag rods, X-bracing, flange braces — building 1 by hand.

Building 1: span 24 000, eave 6 000, slope 0.1 (cos = 1/√1.01, sin = 0.1/√1.01 = 0.0995037), frames 0 … 24 000 every 6 000;
frame sizes from the span rules (knee 800, rafter 400, haunch 2 400, flanges 250×12); purlin pitch 1 185.985, 11 lines a side.
Sag rods: bays 6 000 ≤ 7 500 → 1 row at mid-bay: x = 3 000, 9 000, 15 000, 21 000; per row 10 + 10 chain pieces + 1 ridge = 21
    → 84 rods, 4 nuts + 4 washers each → 336 + 336
    height 2H/3 = 133.333 above the roof; purlin hole y = H/6 = 33.333 from the section centre, Ø14 (M12 + 2)
    purlin 1 → 2 (both Z): web to web = 1 185.985 → cut 1 285.985 (+ 2 × 50), at x = 3 000 + 40
    eave strut (C, web 32.5 − 1 = 31.5 down-slope of its line) → purlin 1: 1 217.485 → cut 1 317.485, at x = 2 960
    ridge rod: y_A = 11 800.993 − 0.0995037 × 133.333 = 11 787.726; y_B = 24 000 − y_A → 424.548 → cut 524.548
X-bracing in bays 1 and 4 (rods RD20):
    roof nodes: round(11 859.851 / 6 000) = 2 panels → s = 0, 5 929.925 (purlin 5), 11 859.851
    diagonal in the roof plane: √(6 000² + 5 929.925²) = 8 435.876 (8 436² = 71 166 096; 71 164 010.5 is 2 085.5 less → 8 436 − 2 085.5/16 872);  4 per side per bay
    end point at s = 0, 87 below the roof (tf 12 + 75): y = 87 × 0.0995037 = 8.657, z = 6 000 − 87 × 0.9950372 = 5 913.432
    wall: 6 000 ≤ 1.5 × 6 000 → one X; plane y = (550 + 24)/2 = 287; top 5 900: √(6 000² + 5 900²) = 8 414.868
Flange braces (L50x5, pairs):
    rafter: s0 = 824·√1.01 = 828.110; haunch zone to 3 228.110 → purlins 1, 2 + the next (3): 3 × 2 sides × 3 interior frames × 2 = 36
      purlin 1: depth = 800 − 400 × 357.875/2 400 + 24 = 764.354; run = 764.354 − 6 + 50 = 808.354 → length 808.354·√2 = 1 143.185
    columns: top two girts (3 750, 5 000); 3 interior frames × 2 + 2 end frames × 1 (inward only) = 8 per girt per wall → 32
      girt 5 000: depth = 300 + 500 × 5/6 + 24 = 740.667; inner flange y = 734.667; run 784.667
"""

import math

import pytest

from engine.peb.bracing import BracingInput, flange_braces, roof_nodes, sag_rods, x_bracing
from engine.peb.builtup_frame import default_sizes
from engine.peb.secondary import SecondaryInput, secondary_lines, secondary_members

FR = [0, 6000, 12000, 18000, 24000]
LINES = secondary_lines(SecondaryInput(span=24000, eave_height=6000, roof_slope=0.1, length=24000))
INP = BracingInput(span=24000, eave_height=6000, roof_slope=0.1, frames=FR, sizes=default_sizes(24000), braced_bays=[0, 3])


def test_sag_rods():
    out = sag_rods(LINES, INP)
    assert out["rows"] == [3000, 9000, 15000, 21000]
    assert len(out["members"]) == 84
    assert out["fasteners"] == [{"item": "nut M12", "count": 336}, {"item": "washer M12", "count": 336}]
    row = [m for m in out["members"] if 2900 < m["start"][0] < 3100]
    a = [m for m in row if m["side"] == "A"]
    assert a[0]["cut_length"] == pytest.approx(1317.485, abs=1e-3) and a[0]["start"][0] == 2960
    assert a[1]["cut_length"] == pytest.approx(1285.985, abs=1e-3) and a[1]["start"][0] == 3040
    ridge = [m for m in row if m["side"] == "ridge"][0]
    assert ridge["start"][1] == pytest.approx(11787.726, abs=1e-3) and ridge["end"][1] == pytest.approx(12212.274, abs=1e-3)
    assert ridge["cut_length"] == pytest.approx(524.548, abs=1e-3)
    h = [x for x in out["holes"] if x["line"] == "RA1" and 2900 < x["x"] < 3100]
    assert sorted(x["x"] for x in h) == [2960, 3040] and all(x["y"] == pytest.approx(33.333, abs=1e-3) and x["d"] == 14 for x in h)
    ridge_holes = sorted(x["x"] for x in out["holes"] if x["line"] == "RA10" and 2900 < x["x"] < 3100)
    assert len(set(ridge_holes)) == 2                      # the ridge rod has its own hole beside the last chain rod's


def test_sag_rod_holes_reach_the_pieces():
    rods = sag_rods(LINES, INP)
    out = secondary_members(LINES, FR, end_overhang=325, extra_holes=rods["holes"])
    p1 = [m for m in out["members"] if m["line"] == "RA1"][0]    # piece −325 → 6 600
    sag = sorted(h["x"] for h in p1["holes"] if abs(h["y"] - 33.333) < 1e-3)
    assert sag == [2960 + 325, 3040 + 325]


def test_two_rows_above_7_5_m():
    inp = BracingInput(span=24000, eave_height=6000, roof_slope=0.1, frames=[0, 9000], sizes=default_sizes(24000))
    assert sag_rods(LINES, inp)["rows"] == [3000, 6000]


def test_roof_and_wall_bracing():
    out = x_bracing(LINES, LINES["walls"], INP)
    roof = [m for m in out if m["role"] == "roof_brace"]
    wall = [m for m in out if m["role"] == "wall_brace"]
    assert len(roof) == 16 and len(wall) == 8 and all(m["profile"] == "RD20" for m in out)
    ss = sorted(m["s"] for m in LINES["roof"] if m["side"] == "A")
    assert roof_nodes(ss, 6000) == [0, pytest.approx(5929.925, abs=1e-3), pytest.approx(11859.851, abs=1e-3)]
    a0 = [m for m in roof if m["side"] == "A" and m["bay"] == 0]
    assert a0[0]["start"] == [0, pytest.approx(8.657, abs=1e-3), pytest.approx(5913.432, abs=1e-3)]
    assert a0[0]["length"] == pytest.approx(8435.876, abs=1e-3)
    w = [m for m in wall if m["side"] == "A" and m["bay"] == 0]
    assert len(w) == 2 and w[0]["start"] == [0, 287, 0] and w[0]["end"] == [6000, 287, 5900]
    assert w[0]["length"] == pytest.approx(8414.868, abs=1e-3)
    assert {m["start"][1] for m in wall if m["side"] == "B"} == {24000 - 287}
    ang = x_bracing(LINES, LINES["walls"], BracingInput(**{**INP.__dict__, "brace_type": "angle"}))
    assert {m["profile"] for m in ang} == {"L75x6"}
    with pytest.raises(ValueError, match="bay 9 does not exist"):
        x_bracing(LINES, LINES["walls"], BracingInput(**{**INP.__dict__, "braced_bays": [8]}))


def test_tall_walls_get_two_panels():
    lines = secondary_lines(SecondaryInput(span=24000, eave_height=10000, roof_slope=0.1, length=24000))
    inp = BracingInput(span=24000, eave_height=10000, roof_slope=0.1, frames=FR, sizes=default_sizes(24000), braced_bays=[0])
    w = [m for m in x_bracing(lines, lines["walls"], inp) if m["role"] == "wall_brace" and m["side"] == "A"]
    assert len(w) == 4 and sorted({m["end"][2] for m in w} | {m["start"][2] for m in w}) == [0, 5000, 9900]   # node at the girt nearest 5 000


def test_flange_braces():
    out = flange_braces(LINES, INP)
    roof = [m for m in out if m["host"].startswith("rafter")]
    col = [m for m in out if m["host"].startswith("column")]
    # rafters: 3 interior frames × 2 sides × 3 positions × a pair = 36, + the 2 end frames' inward braces 2 × 2 × 3 = 12
    assert len(roof) == 48 and len(col) == 32
    ends = [m for m in roof if m["start"][0] in (FR[0], FR[-1])]
    assert len(ends) == 12 and all(FR[0] <= m["end"][0] <= FR[-1] for m in ends)              # every end brace points inside
    assert {m["line"] for m in roof if m["host"] == "rafter A"} == {"RA1", "RA2", "RA3"}
    b = [m for m in roof if m["line"] == "RA1" and m["start"][0] == 6000]
    assert len(b) == 2 and sorted(m["end"][0] for m in b) == [pytest.approx(6000 - 808.354, abs=1e-3), pytest.approx(6808.354, abs=1e-3)]
    assert b[0]["length"] == pytest.approx(1143.185, abs=1e-3)
    c = [m for m in col if m["host"] == "column A" and m["start"][0] == 6000 and m["start"][2] == 5000]
    assert len(c) == 2 and c[0]["start"][1] == pytest.approx(734.667, abs=1e-3) and c[0]["end"][1] == -50
    assert sorted(m["end"][0] for m in c) == [pytest.approx(6000 - 784.667, abs=1e-3), pytest.approx(6784.667, abs=1e-3)]
    end = [m for m in col if m["host"] == "column A" and m["start"][0] == 0]
    assert all(m["end"][0] > 0 for m in end) and len(end) == 2   # end column: inward only, 2 girts
    assert all(math.isclose(m["length"], abs(m["end"][0] - m["start"][0]) * math.sqrt(2), abs_tol=1e-2) for m in col)
