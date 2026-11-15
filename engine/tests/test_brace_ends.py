# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 5b: the brace ends (engine/connections/brace_ends.py). Independent values written out longhand below;
NOT recomputed by the code under test. RD20 rod S355 (Fu 470 at d 20, EN 10025-2 band ≤ 40), host web 6 mm S355JR
(library: Fy 355, Fu 490), hole 26, hillside washer 60 OD.

    SPLIT       u = (0.6, 0.8, 0), web normal X: Tn = 0.6 T, Tp = 0.8 T
    ROD         Ab = π 20² / 4 = 314.159; φRnt = 0.75 × 0.75 × 470 × 314.159 = 83.0559 kN; φRnv = 0.75 × 0.45 × 470 ×
                314.159 = 49.8335 kN. T 21.128, Tp 13.104: 1.3 × 83.0559 − 83.0559 × 13.104 / 49.8335 = 86.1325 → cap
                83.0559, U 0.254381; Tp 40: 107.9727 − 66.6667 = 41.3060 → U 0.511500; shear 40 / 49.8335 = 0.802673
    WASHER      punching 0.75 × 0.6 × 490 × π × 60 × 6 = 249.379 kN; J7 Apb = π (60² − 26²) / 4 = 2296.50 →
                0.75 × 1.8 × 355 × 2296.50 = 1100.60 kN
    HOLE        lc 62: min(2.4 × 20 × 6 × 490 = 141 120, 1.2 × 62 × 6 × 490 = 218 736) × 0.75 = 105.84 kN;
                lc 20: 1.2 × 20 × 6 × 490 × 0.75 = 52.92 kN
    LC          a roof hole 75 below the top flange's inside face, pulled straight toward it: 75 − 13 = 62; pulled along
                the member toward its end 1000 mm away: 1000 − 13 = 987; at 45° between both: min(75 / 0.7071, 1000 /
                0.7071) − 13 = 93.066
    NET         200 × 10 flanges, hw 475, tw 6 (d 495): A 6850, I 288 844 270.8 (test_welds). Hole 26 at mid-depth:
                An 6694, yc 247.5, In = I − 6 × 26³ / 12 = 288 835 482.8. Hole at y 400: yc = (6850 × 247.5 − 156 × 400)
                / 6694 = 243.94607; In = 288 844 270.8 + 6850 × 3.55393² − 8788 − 156 × 156.05393² = 285 122 960 (± 5)
                Stress (mid hole): P 100 + 10, M 200 + 1 kN·m: 110 000 / 6694 + 201e6 × 247.5 / 288 835 482.8
                = 16.4326 + 172.2350 = 188.668 MPa → U 188.668 / 319.5 = 0.590510; shear rupture 0.75 × 0.6 × 490 ×
                (475 − 26) × 6 = 594.027 kN, V 50 + 5 → U 0.092588
"""

from __future__ import annotations

import copy
import math

import pytest

from engine.connections import brace_ends as B

SEC = {"bf_top": 200.0, "tf_top": 10.0, "bf_bot": 200.0, "tf_bot": 10.0, "hw": 475.0, "tw": 6.0, "d": 495.0}


def _rows(rows):
    return {r[1]: r for r in rows}


def test_force_split():
    s = B.force_split(10.0, [0.6, 0.8, 0.0], [1.0, 0.0, 0.0])
    assert s["Tn"] == pytest.approx(6.0) and s["Tp"] == pytest.approx(8.0) and s["angle_from_normal"] == pytest.approx(53.1301, abs=1e-4)
    w = B.force_split(10.0, [0.6, 0.8, 0.0], B.web_normal({"role": "wind_column"}))
    assert w["Tn"] == pytest.approx(8.0) and w["Tp"] == pytest.approx(6.0)


def test_rod_rows():
    r = _rows(B.rod_rows(21.128, 13.104, 20.0, 470.0))
    t = r["rod threads: tension with the in-plane shear"]
    assert t[4] == pytest.approx(83.0559, rel=1e-5) and t[5] == pytest.approx(0.254381, rel=1e-5)
    r2 = _rows(B.rod_rows(21.128, 40.0, 20.0, 470.0))
    assert r2["rod threads: tension with the in-plane shear"][5] == pytest.approx(0.511500, rel=1e-5)
    assert r2["rod threads: shear (in-plane component)"][5] == pytest.approx(0.802673, rel=1e-5)


def test_washer_and_hole_rows():
    w = _rows(B.washer_rows(16.0, 60.0, 26.0, 6.0, 355.0, 490.0))
    assert w["web punching shear around the washer"][4] == pytest.approx(249.379, rel=1e-5)
    assert w["washer bearing on the web"][4] == pytest.approx(1100.60, rel=1e-5)
    assert B.hole_rows(13.0, 20.0, 62.0, 6.0, 490.0)[0][4] == pytest.approx(105.84, rel=5e-4)
    assert B.hole_rows(13.0, 20.0, 20.0, 6.0, 490.0)[0][4] == pytest.approx(52.92, rel=5e-4)   # tear-out governs


def test_edge_lc():
    a, dv = [0.0, 1.0, 0.0], [0.0, 0.0, 1.0]
    assert B.edge_lc([0.0, 0.0, 1.0], a, dv, 75.0, 400.0, 5000.0, 6000.0, 26.0) == pytest.approx(62.0)
    assert B.edge_lc([0.0, 1.0, 0.0], a, dv, 75.0, 400.0, 5000.0, 6000.0, 26.0) == pytest.approx(987.0)
    h = 1 / math.sqrt(2)
    assert B.edge_lc([0.0, h, h], a, dv, 75.0, 400.0, 5000.0, 6000.0, 26.0) == pytest.approx(93.066, abs=1e-3)
    assert B.edge_lc([0.0, 0.0, -1.0], a, dv, 75.0, 400.0, 5000.0, 6000.0, 26.0) == pytest.approx(387.0)   # the other flange


def test_net_section_and_rows():
    mid = B.net_section(SEC, 247.5, 26.0)
    assert mid["A"] == pytest.approx(6694.0) and mid["yc"] == pytest.approx(247.5) and mid["I"] == pytest.approx(288835482.8, abs=1.0)
    off = B.net_section(SEC, 400.0, 26.0)
    assert off["yc"] == pytest.approx(243.94607, abs=1e-5) and off["I"] == pytest.approx(285122960.0, abs=5.0)
    r = _rows(B.net_rows([("A", -100.0, 50.0, -200.0), ("B", 10.0, 1.0, 5.0)], {"P": 10.0, "V": 5.0, "M": 1.0}, SEC, 247.5,
                         26.0, 355.0, 490.0))
    s = r["member net section at the hole: |P|/An + |M| c/In"]
    assert s[3] == pytest.approx(188.668, abs=1e-3) and s[5] == pytest.approx(0.590510, abs=1e-5) and s[6] == "A"
    v = r["member net web shear rupture at the hole"]
    assert v[4] == pytest.approx(594.027, rel=1e-6) and v[5] == pytest.approx(0.092588, abs=1e-6)


def test_stations_at():
    fres = {"members": [{"id": "F1-RA", "mark": "R1", "length": 1000.0}, {"id": "F1-RA", "mark": "R2", "length": 1000.0}],
            "results": {"C1": {"set": "LRFD", "members": {"R1": [(0.0, 1.0, 2.0, 3.0), (1000.0, 3.0, 4.0, 5.0)],
                                                           "R2": [(0.0, 3.0, 4.0, 5.0), (1000.0, 7.0, 8.0, 9.0)]}},
                        "S1": {"set": "ASD", "members": {}}}}
    assert B.stations_at(fres, "F1-RA", 500.0) == [("C1", 2.0, 3.0, 4.0)]
    assert B.stations_at(fres, "F1-RA", 1500.0) == [("C1", 5.0, 6.0, 7.0)]
    assert B.stations_at(fres, "F1-RA", 9999.0) == [("C1", 7.0, 8.0, 9.0)]
    assert B.stations_at(fres, "nope", 5.0) is None


def test_settings():
    with pytest.raises(ValueError):
        B.BraceEndSettings(max_angle_from_normal=95.0).check()
    with pytest.raises(ValueError):
        B.BraceEndSettings.from_dict({"bad": 1})
    assert B.BraceEndSettings.from_dict({"washers": {"24": [70, 14]}}).washers == {24.0: (70.0, 14.0)}


def _building1_joints():
    from engine.connections.joints import joint_list
    from engine.peb.building import peb_building, resolve
    from engine.tests.test_joints import _sized
    b0, li = _sized()
    b, _ = resolve(b0)
    out = peb_building(b)
    jr = {"joints": joint_list(b, out)}
    for j in jr["joints"]:
        if j["type"] == "brace_end":
            j["forces"] = {"tension": 21.128}
    return jr, out


def test_building_1_without_frame_stations_is_partial_never_designed():
    jr, out = _building1_joints()
    r = B.building_brace_ends(jr, out, {"frames": []})
    assert r["counts"] == {"PARTIAL": 48}
    x = next(x for x in r["brace_ends"] if x["role"] == "roof_brace")
    assert any("net section" in n for n in x["notes"]) and x["governing"]["U"] < 1.0
    assert x["hole"]["d_hole"] == 26.0
    base = [x for x in r["brace_ends"] if x["hole"]["at_base_height"] == 150.0]
    assert len(base) == 8 and all(x["role"] == "wall_brace" for x in base)


def test_negative_controls():
    jr, out = _building1_joints()
    jr2 = copy.deepcopy(jr)
    j0 = next(j for j in jr2["joints"] if j["type"] == "brace_end")
    j0["forces"] = None
    out2 = copy.deepcopy(out)
    bid = next(j for j in jr2["joints"] if j["type"] == "brace_end" and j["members"][0]["id"] != j0["members"][0]["id"])["members"][0]["id"]
    for m in out2["members"]:
        if m.get("id") == bid:
            m["profile"] = "L75x6"
    r = B.building_brace_ends(jr2, out2, {"frames": []})
    by = {x["joint"]: x for x in r["brace_ends"]}
    assert by[j0["id"]]["status"] == B.NOT_EVALUATED and "brace tension" in by[j0["id"]]["missing"][0]
    ang = [x for x in r["brace_ends"] if x["profile"] == "L75x6"]
    assert len(ang) == 2 and all(x["status"] == B.NOT_EVALUATED and "open item 10" in x["missing"][0] for x in ang)
    assert all("checks" not in x for x in r["brace_ends"] if x["status"] == B.NOT_EVALUATED)
    # the rod too close to the web plane for a hillside washer → NOT EVALUATED (roof 38.3°, wall 44.5° from the normal)
    tight = B.building_brace_ends(jr, out, {"frames": []}, B.BraceEndSettings(max_angle_from_normal=30.0))
    assert tight["counts"] == {"NOT EVALUATED": 48} and "gusset" in tight["brace_ends"][0]["missing"][0]
    # no washer size for the rod → the washer rows are missing, never a pass
    nw = B.building_brace_ends(jr, out, {"frames": []}, B.BraceEndSettings(washers={}))
    assert all(x["status"] == B.PARTIAL and any("washer" in n for n in x["notes"]) for x in nw["brace_ends"])
    # a large in-plane force on a short tear-out → FAILS with the fix
    big = copy.deepcopy(jr)
    for j in big["joints"]:
        if j["type"] == "brace_end":
            j["forces"] = {"tension": 200.0}
    f = B.building_brace_ends(big, out, {"frames": []})
    assert f["counts"] == {"FAILS": 48} and all(x["fixes"] for x in f["brace_ends"])


@pytest.mark.slow
def test_building_1_brace_ends_with_analysis():
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.joints import building_joints
    from engine.peb.building import peb_building, resolve
    from engine.tests.test_joints import _sized
    b0, li = _sized()
    b, _ = resolve(b0)
    out = peb_building(b)
    an = analyse_building(b, li)
    jr = building_joints(b0, li, analysis=an, out=out)
    r = B.building_brace_ends(jr, out, an)
    assert r["counts"] == {"DESIGNED": 48}
    worst = max(r["brace_ends"], key=lambda x: x["governing"]["U"])
    assert worst["role"] == "wall_brace" and worst["governing"]["name"].startswith("member net section")
    assert worst["governing"]["U"] == pytest.approx(0.9732, abs=2e-3)
    roof = [x for x in r["brace_ends"] if x["role"] == "roof_brace"]
    assert all(x["T"] == pytest.approx(21.128, abs=1e-3) for x in roof)
    # the hole at a wall brace is at the column's mid-depth (the net centroid): the brace adds no moment there
    for x in (x for x in r["brace_ends"] if x["role"] == "wall_brace"):
        assert x["net_section"]["brace_added"]["M"] == pytest.approx(0.0, abs=1e-3)
