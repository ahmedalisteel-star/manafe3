# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 2 step 3: lapped pieces, holes and cleats against hand values.

Building 1: span 24 000, eave 6 000, slope 0.1, 4 bays of 6 000 (frames x = 0 … 24 000); end overhang 325 (end-wall girt
line: column flange 250/2 + girt depth 200); laps 10 % = 600 each side; M12 → 14 mm holes; Z200x65x20x2.0: gauge
200 − 2·(20 + 25) = 110 → holes at y = ±55.
    Z line, side A (ℓ = x):
      piece 1: −325 → 6 600 (6 925); holes ℓ 0, 5 440 (next start + 40), 6 000, 6 560 (own end − 40) → x 325, 5 765, 6 325, 6 885
      piece 2: 5 400 → 12 600 (7 200); holes ℓ 5 440, 6 000, 6 560, 11 440, 12 000, 12 560 → x 40, 600, 1 160, 6 040, 6 600, 7 160
      piece 4: 17 400 → 24 325 (6 925)
    side B runs from x = 24 000 towards 0: its piece 1 starts at x = 24 325
    eave strut (C, butt): piece 1 −325 → 5 995 (6 320), holes ℓ 0 and 5 975 → x 325, 6 300; piece 2 6 005 → 11 995 (5 990),
      holes x 20, 5 970
    cleats: one per line per frame; Z: PL8 × 180 high (200 − 20), holes up 45 and 155 (100 ∓ 55), 25 below its top edge;
      C at an interior frame: 4 holes at along ±25
Mixed bays 6 000 / 7 500 / 6 000 (frames 0, 6 000, 13 500, 19 500): at frame 6 000 the piece of bay 1 runs 750 past it
(10 % of 7 500) and the piece of bay 2 starts 600 before it (10 % of 6 000): piece 1 −325 → 6 750, piece 2 5 400 → 14 100.
A fixed lap of 500: piece 2 of building 1 = 5 500 → 12 500 (7 000).
"""

import pytest

from engine.peb.secondary import SecondaryInput, gauge, secondary_lines, secondary_members, z_pieces


def build1(**kw):
    lines = secondary_lines(SecondaryInput(span=24000, eave_height=6000, roof_slope=0.1, length=24000))
    return secondary_members(lines, [0, 6000, 12000, 18000, 24000], end_overhang=325, **kw)


def pieces(out, line):
    return [m for m in out["members"] if m["line"] == line]


def hx(m):
    return sorted({h["x"] for h in m["holes"]})


def test_z_line_side_a():
    out = build1()
    p = pieces(out, "RA1")
    assert [m["length"] for m in p] == [6925, 7200, 7200, 6925]
    assert p[0]["start"][0] == -325 and p[0]["end"][0] == 6600 and p[1]["start"][0] == 5400 and p[3]["end"][0] == 24325
    assert hx(p[0]) == [325, 5765, 6325, 6885]
    assert hx(p[1]) == [40, 600, 1160, 6040, 6600, 7160]
    assert {h["y"] for h in p[1]["holes"]} == {-55, 55} and all(h["d"] == 14 and h["face"] == "web" for h in p[1]["holes"])
    assert len(p[1]["holes"]) == 12 and gauge("Z200x65x20x2.0") == 110


def test_laps_line_up_through_both_pieces():
    p = pieces(build1(), "RA1")
    world = lambda m: {round(m["start"][0] + h["x"], 3) for h in m["holes"]}
    shared = world(p[0]) & world(p[1])
    assert shared == {5440, 6000, 6560}              # the two lap ends and the frame: bolted through both pieces


def test_side_b_runs_back():
    p = pieces(build1(), "RB1")
    assert p[0]["start"][0] == 24325 and p[0]["end"][0] == 17400 and p[0]["length"] == 6925
    assert hx(p[0]) == [325, 5765, 6325, 6885]       # the same pattern from its own start


def test_eave_strut_butt_joints():
    p = pieces(build1(), "RA0")
    assert p[0]["profile"] == "C200x65x20x2.0"
    assert [m["length"] for m in p] == [6320, 5990, 5990, 6320]
    assert p[0]["end"][0] == 5995 and p[1]["start"][0] == 6005
    assert hx(p[0]) == [325, 6300] and hx(p[1]) == [20, 5970]


def test_cleats():
    out = build1()
    z = [c for c in out["cleats"] if c["line"] == "RA1"]
    assert len(z) == 5 and [c["x"] for c in z] == [0, 6000, 12000, 18000, 24000]
    assert z[0]["height"] == 180 and z[0]["profile"] == "PL8x100" and z[0]["side"] == "up" and z[0]["host"] == "rafter A"
    assert sorted(h["up"] for h in z[2]["holes"]) == [45, 155] and all(h["along"] == 0 for h in z[2]["holes"])
    c = [c for c in out["cleats"] if c["line"] == "RA0"]
    assert c[0]["host"] == "column A" and c[0]["side"] == "back"
    assert sorted((h["along"], h["up"]) for h in c[1]["holes"]) == [(-25, 45), (-25, 155), (25, 45), (25, 155)]
    assert len(c[0]["holes"]) == 2
    g = [c for c in out["cleats"] if c["line"] == "GA1"]
    assert g and g[0]["host"] == "column A"
    # geometry: a Z cleat starts t/2 + 4 = 5 mm up-slope of the line on the roof and rises 180 along the roof normal
    import math
    cs, sn = 1 / math.sqrt(1.01), 0.1 / math.sqrt(1.01)
    k = z[1]
    assert k["start"][1] == pytest.approx(k["base"][1] + 5 * cs, abs=1e-3) and k["start"][2] == pytest.approx(k["base"][2] + 5 * sn, abs=1e-3)
    assert k["end"][1] == pytest.approx(k["start"][1] - 180 * sn, abs=2e-3) and k["end"][2] == pytest.approx(k["start"][2] + 180 * cs, abs=2e-3)   # start and end each rounded to 0.001
    # a girt cleat (wall A, girts point out of the building): 5 mm above the girt line, 180 outwards (−Y)
    gc = g[1]
    assert gc["start"] == [6000, 0, gc["base"][2] + 5] and gc["end"] == [6000, -180, gc["base"][2] + 5]
    # the eave strut (C) cleat sits at the back of its web: −(65/2 + 4) = −36.5 along u
    ce = c[1]
    assert ce["start"][1] == pytest.approx(ce["base"][1] - 36.5 * cs, abs=1e-3)


def test_mixed_bays_and_fixed_lap():
    ps = z_pieces([0, 6000, 13500, 19500], 325, None)
    assert (ps[0]["a"], ps[0]["b"]) == (-325, 6750) and (ps[1]["a"], ps[1]["b"]) == (5400, 14100)
    p = pieces(build1(fixed_lap=500), "RA1")
    assert p[1]["start"][0] == 5500 and p[1]["length"] == 7000


def test_bolt_size_and_refusals():
    out = build1(bolt="M16")
    assert all(h["d"] == 18 for m in out["members"] for h in m["holes"])
    with pytest.raises(ValueError, match="M12 or M16"):
        build1(bolt="M20")
    with pytest.raises(ValueError, match="fixed lap"):
        build1(fixed_lap=50)
