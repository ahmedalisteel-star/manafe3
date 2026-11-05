# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Built-up portal frames (Phase 1) against geometry worked out by hand.

Case A: span 24 000, eave 6 000, slope 1:10, 1 bay of 6 000
    span rules: hw_knee = ceil(24 000/30/50)·50 = ceil(16)·50 = 800; hw_rafter = max(300, 400) = 400; haunch 2 400;
                flanges 250×12 (20 m < span ≤ 30 m); web 8 (deepest > 600) on column and haunch, 6 on the rafter
    column A: (0,0,0) → (0,0,6000), rotation 270, one segment 6000: 300 → 800, end cut −0.1 (the roof line)
    column depth at the eave d = 800 + 2·12 = 824 → rafter A starts at y = 824, z = 6000 + 0.1·824 = 6082.4
    apex (0, 12000, 7200); rafter line = √(11 176² + 1 117.6²) = 11 176·√1.01 = 11 231.741
    rafter segments: haunch 2 400 (800 → 400, tw 8) + rafter 11 231.741 − 2 400 = 8 831.741 (400, tw 6) ≤ 12 m: one piece
    rafter B: (0, 24 000 − 824 = 23 176, 6082.4) → apex;  ends cut plumb: +0.1 at both ends
Case B: span 36 000, eave 8 000, slope 1:12, 2 bays of 7 500
    hw_knee = ceil(1 200/50)·50 = 1 200; hw_rafter 600; haunch 3 600; flanges 300×16; rafter web 6 (600 ≤ 600)
    d = 1 200 + 32 = 1 232; rafter A starts (x, 1 232, 8 000 + 1 232/12 = 8 102.667); apex z = 8 000 + 18 000/12 = 9 500
    rafter line = 16 768·√(1 + 1/144) = 16 826.121; after the haunch 13 226.121 > 12 m → 2 segments of 6 613.061
"""

import math

import pytest

from engine.peb.builtup_frame import BuiltUpSizes, default_sizes
from engine.peb.frame import FrameInput, portal_frame
from engine.sections.builtup import BuiltUpMember


def by_id(f):
    return {m["id"]: m for m in f["members"]}


def segs(m):
    return [(s["length"], s["hw_start"], s["hw_end"], s["tw"], s["bf_top"], s["tf_top"]) for s in m["section"]["segments"]]


def test_span_rules():
    assert default_sizes(24000) == BuiltUpSizes(hw_knee=800, hw_base=300, hw_rafter=400, haunch_length=2400, bf=250, tf=12)
    assert default_sizes(36000) == BuiltUpSizes(hw_knee=1200, hw_base=300, hw_rafter=600, haunch_length=3600, bf=300, tf=16)
    z = default_sizes(15000)                               # 500 → ceil to 500; rafter max(300, 250) = 300; flanges 200×10
    assert (z.hw_knee, z.hw_rafter, z.bf, z.tf) == (500, 300, 200, 10)
    assert default_sizes(24100).hw_knee == 850             # 803.3 rounds UP to 850


def test_case_a_24m():
    f = portal_frame(FrameInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=1))
    m = by_id(f)
    assert f["section"] == "builtup" and len(f["members"]) == 8
    ca, ra, rb, cb = m["F1-CA"], m["F1-RA"], m["F1-RB"], m["F1-CB"]
    assert ca["start"] == [0, 0, 0] and ca["end"] == [0, 0, 6000] and ca["rotation"] == 270
    assert cb["start"] == [0, 24000, 0] and cb["rotation"] == 90
    assert segs(ca) == [(6000, 300, 800, 8, 250, 12)]
    assert ca["section"]["cut_start"] == 0 and ca["section"]["cut_end"] == -0.1
    assert ra["start"] == [0, 824, 6082.4] and ra["end"] == [0, 12000, 7200]
    assert rb["start"] == [0, 23176, 6082.4] and rb["end"] == [0, 12000, 7200]
    assert f["rafter_length"] == pytest.approx(11231.741, abs=1e-3)
    assert segs(ra) == [(2400, 800, 400, 8, 250, 12), (pytest.approx(8831.741, abs=1e-3), 400, 400, 6, 250, 12)]
    assert ra["section"]["cut_start"] == 0.1 and ra["section"]["cut_end"] == 0.1
    assert all(x["designed"] is False and x["material"] == "S355" for x in f["members"])
    assert ca["profile"] == "BU 300-800x8 250x12/250x12" and ra["profile"] == "BU 400-800x8 250x12/250x12 +1"


def test_case_b_36m_two_bays_rafter_split_for_transport():
    f = portal_frame(FrameInput(span=36000, eave_height=8000, roof_slope=1 / 12, bay_spacing=7500, n_bays=2))
    m = by_id(f)
    assert len(f["members"]) == 12
    ra = m["F3-RA"]
    assert ra["start"] == [15000, 1232, pytest.approx(8102.667, abs=1e-3)] and ra["end"] == [15000, 18000, 9500]
    s = segs(ra)
    assert s[0] == (3600, 1200, 600, 8, 300, 16)
    assert len(s) == 3 and s[1][0] == pytest.approx(6613.061, abs=1e-3) and s[2][0] == pytest.approx(6613.061, abs=1e-3)
    assert s[1][1:] == (600, 600, 6, 300, 16) and s[2][1:] == (600, 600, 6, 300, 16)
    assert math.isclose(sum(x[0] for x in s), 16826.121, abs_tol=2e-3)
    assert segs(m["F2-CB"]) == [(8000, 300, 1200, 8, 300, 16)]


def test_every_member_obeys_the_splice_and_minimum_rules():
    for span in (12000, 24000, 36000, 60000):
        f = portal_frame(FrameInput(span=span, eave_height=7000, roof_slope=0.1, bay_spacing=6000, n_bays=1))
        for mem in f["members"]:
            bm = BuiltUpMember.from_dicts(mem["section"]["segments"])   # raises on unequal webs / widths / minimums
            assert all(x.length <= 12000 + 1e-6 for x in bm.segments)


def test_sizes_override_and_refusals():
    z = BuiltUpSizes(hw_knee=900, hw_base=350, hw_rafter=450, haunch_length=3000, bf=260, tf=14)
    f = portal_frame(FrameInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=1, sizes=z))
    m = by_id(f)
    assert segs(m["F1-CA"]) == [(6000, 350, 900, 8, 260, 14)]
    assert segs(m["F1-RA"])[0] == (3000, 900, 450, 8, 260, 14)
    assert m["F1-RA"]["start"][1] == 928                   # 900 + 2·14
    with pytest.raises(ValueError, match="haunch .* must be shorter than the rafter"):
        portal_frame(FrameInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=1, sizes=BuiltUpSizes(800, 300, 400, 20000, 250, 12)))
    with pytest.raises(ValueError, match="shop minimum"):
        portal_frame(FrameInput(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=1, sizes=BuiltUpSizes(800, 300, 400, 2400, 250, 6)))


def test_api_defaults_and_sizes():
    from fastapi.testclient import TestClient

    from engine.api import app
    c = TestClient(app)
    d = c.post("/peb/frame/defaults", json={"span": 24000}).json()
    assert d["sizes"]["hw_knee"] == 800 and d["designed"] is False
    body = {"span": 24000, "eave_height": 6000, "roof_slope": 0.1, "bay_spacing": 6000, "n_bays": 1, "sizes": d["sizes"]}
    r = c.post("/peb/frame", json=body)
    assert r.status_code == 200 and r.json()["members"][1]["start"] == [0, 824, 6082.4]
    hot = c.post("/peb/frame", json={**body, "section": "hot_rolled", "sizes": None}).json()
    assert hot["members"][0]["profile"] == "HEA400"
    bad = c.post("/peb/frame", json={**body, "sizes": {**d["sizes"], "tf": 6}})
    assert bad.status_code == 422 and "shop minimum" in bad.json()["detail"]
