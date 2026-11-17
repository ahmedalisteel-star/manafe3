# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Open item 7 (engine/analysis/brace_axial.py): the bracing's axial forces in the frame lines and the struts. Longhand
values for building 1 (sized fixture: bays 6000, braced bays 1 and 4, wall X 6000 × 5900, roof slope 0.1):

    T            LRFD wall diagonal 21.075 = minimum_scale × T_caseB → T_caseB 18.8602 (open item 6's split)
    COLUMN ΔP    sin α = 5900 / √(6000² + 5900²) = 5900 / 8414.868 = 0.701140 → ΔP_caseB = 18.8602 × 0.701140 = 13.2237 kN
                 (= open item 6's base value 13.224); the minimum 21.075 × 0.701140 = 14.7765 kN
    ROOF X       V = per_braced_bay / 2 = 15.027 (governing) → V_caseB = 15.027 / minimum_scale = 13.4478 kN per slope
    CHORD        nodes (plan y, side A) 1188.557, 5908.954, 11809.451; cos θ = 1 / √1.01 = 0.995037
                 s1 = 4720.397 / 0.995037 = 4743.94, s2 = 10620.894 / 0.995037 = 10673.87
                 node 0: 13.4478 × 4743.94 / 6000 = 10.6326 kN; node 1: 13.4478 × 5929.93 / 6000 = 13.2908 kN
                 (N at the ridge 23.923 kN = 13.4478 × 10673.87 / 6000)
    STATICS      the unfactored case BRA alone: Σ vertical reactions = −Σ Fy of its point loads; Σ horizontal = 0
    STRUT 1c     eave strut between braced bays (bays 2, 3): max(drag through the bay = 0 (bimsteelauto), 0.005 × Pr of
                 frame line 3's column on that side, the same D / Lr / wind factors) — Pr read from the frame analysis
"""

from __future__ import annotations

import dataclasses
import math

import pytest

from engine.analysis.brace_axial import brace_loads, split


def _b1():
    from engine.analysis.bracing_system import longitudinal_bracing
    from engine.analysis.endwall_analysis import _geom, longitudinal_feed
    from engine.peb.building import peb_building, resolve
    from engine.tests.test_joints import _sized
    b0, li = _sized()
    b, _ = resolve(b0)
    out = peb_building(b)
    braces = [m for m in out["members"] if m["role"] in ("roof_brace", "wall_brace")]
    bs = longitudinal_bracing(_geom(out["input"]), braces, [j - 1 for j in out["braced_bays"]], longitudinal_feed(out, li))
    return b0, li, out, bs


def test_split_and_column_dP():
    assert split(21.075, 1.25, 1.0)["caseB"] == pytest.approx(16.86) and split(None, 1.0, 1.0) is None
    _, _, out, bs = _b1()
    r = brace_loads(out, bs)
    k = bs["minimum_scale"]
    assert r["T"]["caseB"] == pytest.approx(21.075 / k, abs=1e-6) and r["T"]["caseB"] == pytest.approx(18.8602, abs=1e-3)
    ln = r["lines"][1]                                              # frame line 2 (x 6000)
    col = [p for p in ln["points"] if p["kind"] == "column" and p["case"] == "BRA"]
    assert len(col) == 2 and {p["side"] for p in col} == {"A", "B"}
    assert all(p["dP"] == pytest.approx(13.2237, abs=1e-3) and p["z"] == 5900.0 for p in col)       # = item 6's 13.224
    assert all(p["dP"] == pytest.approx(14.7765, abs=1e-3) for p in ln["points"] if p["kind"] == "column" and p["case"] == "BRminA")
    # wind along +x: the tension diagonal of bay 1 runs from the base at x 0 up to x 6000 → line 2's columns (BRA = +x)
    assert ln["cases"]["BRA"]["direction"] == "+x" and r["lines"][0]["cases"]["BRA"]["direction"] == "-x"
    assert not any(p["kind"] == "column" and p["case"] == "BRB" for p in ln["points"])   # the other direction: no column load
    assert 2 not in r["lines"]                                       # NEGATIVE CONTROL: line 3 has no brace and no chord


def test_chord_forces_and_struts():
    _, _, out, bs = _b1()
    r = brace_loads(out, bs)
    assert r["V"]["caseB"] == pytest.approx(13.4478, abs=1e-3)
    ln = r["lines"][1]
    ch = {p["y"]: p["dN"] for p in ln["points"] if p["kind"] == "chord" and p["case"] == "BRB" and p["side"] == "A"}
    assert ch[1188.557] == pytest.approx(10.6326, abs=2e-3) and ch[5908.954] == pytest.approx(13.2908, abs=2e-3)
    assert sum(ch.values()) == pytest.approx(13.4478 * 10673.87 / 6000, abs=3e-3)                     # 23.923 at the ridge
    # +x compresses the lower-x chord: line 2 is bay 1's higher-x chord → tension in BRA (+x), compression in BRB (−x)
    assert ln["cases"]["BRA"]["chord_sign"] == -1 and ln["cases"]["BRB"]["chord_sign"] == 1
    st = r["struts"]
    assert st["eave"][1]["P"] == pytest.approx(15.027) and st["eave"][4]["P"] == pytest.approx(15.027)
    # between two braced bays (user 1c): the panel-bracing rule on the columns of frame line 3 (never NOT EVALUATED)
    assert all(st["eave"][k]["between"] and st["eave"][k]["panel_lines"] == [3] for k in (2, 3))
    assert len(st["purlin_nodes"]) == 4 and all(z["P"] == pytest.approx(15.027) for z in st["purlin_nodes"])
    # NEGATIVE CONTROL: no Case B / minimum split → no loads, a reason instead of zeros
    r0 = brace_loads(out, {**bs, "minimum_scale": None})
    assert r0["lines"] == {} and "why" in r0


def test_frame_loads_and_signature():
    from engine.analysis.building_analysis import _line_setup, _signature
    from engine.analysis.secondary_weight import secondary_kpa
    from engine.peb.building import peb_building, resolve
    b0, li, out, _ = _b1()
    b, _ = resolve(b0)
    sec = secondary_kpa(peb_building(b))
    _, fl2 = _line_setup(b, li, 1, sec, 0.10)
    _, fl3 = _line_setup(b, li, 2, sec, 0.10)
    _, fl4 = _line_setup(b, li, 3, sec, 0.10)
    assert {"BRA", "BRB", "BRminA", "BRminB"} <= set(fl2.cases) and fl3.points == () and "BRA" not in fl3.cases
    wb = [n for n, f, s in fl2.combinations if s == "LRFD" and ("WB+" in f or "WB-" in f) and not any(k.startswith("BR") for k in f)]
    br = [n for n, f, s in fl2.combinations if any(k.startswith("BR") and not k.startswith("BRmin") for k in f)]
    assert len(br) == 2 * len(wb) and sum("BRmin" in n for n, _, _ in fl2.combinations) == 4
    assert _signature(fl2) == _signature(fl4) and _signature(fl2) != _signature(fl3)      # lines 2 / 4 one solve, 3 its own
    # NEGATIVE CONTROL: the setting off → no points, no new cases or combinations (the frame as before)
    _, off = _line_setup(dataclasses.replace(b, brace_axial=False), li, 1, sec, 0.10)
    assert off.points == () and len(off.combinations) == len(fl2.combinations) - len(br) - 4 and _signature(off) == _signature(fl3)


@pytest.mark.slow
def test_frame_line_statics_and_item6_pairing():
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.longitudinal import braced_base, paired_cases
    from engine.peb.building import peb_building, resolve
    b0, li, _, _ = _b1()
    b, _ = resolve(b0)
    out = peb_building(b)
    an = analyse_building(b, li, workers=1)
    fr = {f["line"]: f for f in an["frames"]}
    assert fr["4"]["same_as"] == "2" and fr["3"]["same_as"] == "3" and fr["4"]["brace"]["cases"]["BRA"]["direction"] == "-x"
    res = fr["2"]["result"]
    pts = [p for p in res["point_loads"] if p["case"] == "BRA"]
    R = res["results"]["BRA"]["reactions"]
    assert sum(v[1] for v in R.values()) == pytest.approx(-sum(p["Fy"] for p in pts), abs=0.02)       # vertical statics
    assert sum(v[0] for v in R.values()) == pytest.approx(-sum(p["Fx"] for p in pts), abs=0.02)       # horizontal (≈ 0)
    assert -sum(p["Fy"] for p in pts) == pytest.approx(2 * 13.2237 + sum(-p["Fy"] for p in pts if p["mark"].startswith("R")), abs=0.01)
    # item 6 at base F2-BA: its landing diagonal (base at x 6000, top at x 0) is the tension one for −x = BRB on line 2;
    # the BRA (+x) combinations — the column's own ΔP — are never paired with −T sin α (no double count)
    j = {"type": "base", "point": [6000.0, 0.0, 0.0]}
    col = next(m for m in out["members"] if m.get("id") == "F2-CA")
    rec = braced_base(j, col, out, an)
    names = {c["combo"] for c in rec["cases"]}
    assert not any(" + 1BRA" in n or " + 0.5BRA" in n or "BRminA" in n for n in names)
    br = [c for c in rec["cases"] if c.get("direction")]
    assert br and all(c["direction"] == "-x" for c in br)
    worst = min(rec["cases"], key=lambda c: c["Pu"])
    assert worst["combo"].endswith("+ 1BRB") and worst["T_brace"] == pytest.approx(18.8602, abs=1e-3)
    frame_alone = next(c for c in rec["cases"] if c["combo"] == worst["combo"].rsplit(" + ", 1)[0])
    # the same diagonal force and α in both pairs; the difference is the roof-X chord's vertical share at this base
    assert worst["Pu"] - frame_alone["Pu"] == pytest.approx(worst["Ry_frame"] - frame_alone["Ry_frame"], abs=1e-6)
    assert worst["Ry_frame"] < frame_alone["Ry_frame"]                     # BRB: chord compression → its vertical lifts


@pytest.mark.slow
def test_eave_strut_between_braced_bays_panel_rule():
    from engine.analysis.building_analysis import analyse_building
    from engine.design.cfs_checks import COMBOS_ROOF, cfs_checks
    from engine.peb.building import resolve
    b0, li, _, _ = _b1()
    b, _ = resolve(b0)
    an = analyse_building(b, li, workers=1)
    res = next(f for f in an["frames"] if f["line"] == "3")["result"]
    cf = cfs_checks(b0, li)
    es = {r["id"]: r for r in cf["eave_struts"]}
    for sid, side in (("RA0-2", "A"), ("RB0-3", "B")):
        r = es[sid]
        assert r["ratio"] is not None and math.isfinite(r["ratio"]) and r.get("status") != "NOT EVALUATED"
        for cn, f in COMBOS_ROOF["LRFD"].items():
            want = (f.get("D", 0.0), f.get("Lr", 0.0), max(f.get("Win", 0.0), f.get("Wout", 0.0)))
            pr = max(max(st[1] for st in rr["members"]["C" + side]) for n, rr in res["results"].items() if rr["set"] == "LRFD"
                     and (res["factors"][n].get("D", 0.0), res["factors"][n].get("Lr", 0.0),
                          max((v for k, v in res["factors"][n].items() if k.startswith("W")), default=0.0)) == want)
            assert r["P_strut_by_combo"][cn] == pytest.approx(0.005 * max(pr, 0.0), abs=1e-3)
        assert r["P_strut_by_combo"]["1.2D+1.6Lr+0.5W"] > 0.3                              # never 0
    # braced bays: the wall-panel shear 15.027 (decision 3a); NEGATIVE CONTROL: the setting off → the old drag (0)
    assert es["RA0-1"]["P_strut_kN"] == pytest.approx(15.027)
    off = {r["id"]: r for r in cfs_checks(dataclasses.replace(b0, brace_axial=False), li)["eave_struts"]}
    assert off["RA0-1"]["P_strut_kN"] == 0.0 and "P_strut_by_combo" not in off["RA0-2"]
