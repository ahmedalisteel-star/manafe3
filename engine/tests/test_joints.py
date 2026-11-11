# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 1: joint list and design forces (engine/connections/joints.py).

Independent values (by hand, not recomputed by the code under test):

Building 1 (24 m span, 4 bays of 6 m, eave 6 m, slope 1:10, main frames at both ends) — joints counted by hand:
    frame lines 5, each: 2 bases, 2 knees, 1 ridge, 2 rafter splices (haunch 2 400 + rafter 8 855 < 12 000: one splice per
    half, no transport split) = 7 → 35
    wind columns at y 6 000, 12 000, 18 000 on each end wall: 6 → 6 tops + 6 bases = 12
    X-braces: roof 2 braced bays × 2 slopes × 2 panels × 2 diagonals = 16, side walls 2 bays × 2 walls × 1 X × 2 = 8 →
    24 braces, 48 ends: every roof-brace end on a rafter (the eave node is the first purlin past the knee, user decision
    2026-11-11; before, it sat inside the column's outer flange) = 32, every wall-brace end on a column = 16
    cleats: purlin lines per slope = eave strut + 9 purlins + ridge purlin (11 860 mm between eave strut and ridge purlin /
    1 250 → 10 spaces); on each rafter the 9 purlins + ridge purlin = 10 → 5 × 2 × 10 = 100 on rafters; on each column
    the eave strut + 4 girts (1 250 … 5 000) = 5 → 5 × 2 × 5 = 50 on columns; gable girts per end wall: each wind column
    4 rows below the eave + the 6 250 row (roof at the column ≥ 6 600 ≥ 6 250 + 300) = 15, each corner (main) column
    4 rows = 8 → 23 per wall, 46 → 196 cleats; hosts: columns 50 + 16 = 66, rafters 100, wind columns 30
    total 35 + 12 + 48 + 196 = 291
End-rafter first wall: 4 frame lines (28 frame joints), wind columns 5 + 3 = 8 (16 joints), end rafter ridge 1 and one
    splice per end-rafter half (2), brace ends 48 + 2 end-wall diagonals × 2 = 52 → 28 + 16 + 3 + 52 + 196 = 295

Capacity at the ridge of line 3 (rafter 400 × 6, flanges 250 × 12, S355, all plates ≤ 16 mm: Fy 355), E = 200 000:
    Zx = 2·250·12·206 + 6·400²/4 = 1 476 000 mm³; Ix = 2(250·12³/12 + 3 000·206²) + 6·400³/12 = 286 688 000 mm⁴,
    Sx = Ix / 212 = 1 352 302 mm³; Mp = 355 Zx = 523.98 kN·m
    flange λ = 250 / 24 = 10.417 > λpf = 0.38 √(E/Fy) = 9.020 → F3 (web 400/6 = 66.7 ≤ 3.76 √(E/Fy) = 89.2, compact);
    kc = 4/√66.67 = 0.4899, λrf = 0.95 √(kc E / 0.7Fy) = 18.864
    Mn = Mp − (Mp − 0.7 Fy Sx)(λ − λpf)/(λrf − λpf) = 523.98 − 187.93 × 0.14192 = 497.31; φMn = 447.6 kN·m
    section strength (Lb = 0, user decision 2026-11-11): the same for +M and −M (doubly symmetric, no LTB)
    Shear G2.1: h/tw 66.67 > 1.10 √(5.34 E/Fy) = 60.33 → Cv1 = 0.9050; φVn = 0.9 · 0.6 · 355 · 424 · 6 · 0.9050 = 441.3 kN
    capacity rule f = 0.50: Mu ≥ 223.8 kN·m, Vu ≥ 220.7 kN
Capacity at the knee of line 3 (column top: hw 772.361 (796.361 − 24) × 8, flanges 250 × 12, S355): web h/tw 96.545 >
    λpw = 3.76 √(E/Fy) = 89.246 (Table B4.1b case 15, doubly symmetric) ≤ λrw = 5.70 √(E/Fy) = 135.293 → F4
    Ix = 2(250·12³/12 + 3 000·392.181²) + 8·772.361³/12 = 1 230 069 794 mm⁴, Sx = Ix / 398.181 = 3 089 226 mm³,
    Zx = 3 000·784.361 + 8·772.361²/4 = 3 546 168 mm³; Mp/My = 1.14791
    Rpc = 1.14791 − 0.14791 (96.545 − 89.246)/(135.293 − 89.246) = 1.12447 (F4-9b); Myc = 355 Sx = 1 096.68 kN·m
    FLB F4-13: kc = 4/√96.545 = 0.40709, λrf = 0.95 √(kc E / 0.7Fy) = 17.196, (10.417 − 9.020)/(17.196 − 9.020) = 0.170876
    Mn = 1 233.18 − (1 233.18 − 0.7·355·Sx = 767.67) × 0.170876 = 1 153.63; φMn = 1 038.3 kN·m
    (an earlier longhand took λpw from case 16 — the singly-symmetric formula — and got 1 028.8: that was the error)
End-rafter splice (span 30 m, first wall an end rafter): the end rafter (12 000 plan, 15 074.8 along the slope) is split in
    halves, so its splice is at y = 7 500 (and 22 500) — between the wind columns at 6 000 and 12 000; the end-rafter frame
    must have a node there.
Negative controls: a much larger moment in the MIDDLE of a member is not taken for the joint; a member with no station at
the joint, or no LRFD combination, reads NOT EVALUATED (no design force); the capacity branch fires on a light joint and
does not on a heavy one; f = None, or either switch off, gives the analysis force alone for that action; the end-rafter
frame without the splice node leaves the splice NOT EVALUATED.
"""

import json
import math
from collections import Counter

import pytest

from engine.connections.joints import (EVALUATED, NOT_EVALUATED, ConnectionSettings, _frame_info, _frame_joints,
                                       frame_joint_capacities, frame_joint_forces, joint_list)
from engine.peb.building import BuildingInput, peb_building, resolve

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)
PHI_MN_RIDGE = 447.6
PHI_VN_RIDGE = 441.3
PHI_MN_KNEE = 1038.3


@pytest.fixture(scope="module")
def b1():
    b, _ = resolve(BuildingInput(**B1))
    return b, peb_building(b)


def _by_id(out):
    return {m["id"]: m for m in out["members"] if m.get("id")}


def test_joint_counts_of_building_1_by_hand(b1):
    b, out = b1
    js = joint_list(b, out)
    assert Counter(j["type"] for j in js) == {"base": 10, "knee": 10, "ridge": 5, "rafter_splice": 10, "wind_column_top": 6,
                                             "wind_column_base": 6, "brace_end": 48, "cleat": 196}
    assert len(js) == 291 and len({j["id"] for j in js}) == 291
    mem = _by_id(out)

    def host_roles(t):
        return Counter(mem[m["id"]]["role"] for j in js if j["type"] == t for m in j["members"]
                       if mem.get(m["id"], {}).get("role") in ("column", "rafter", "wind_column", "end_rafter"))
    assert host_roles("cleat") == {"column": 66, "rafter": 100, "wind_column": 30}
    assert host_roles("brace_end") == {"rafter": 32, "column": 16}
    # every cleat holds at least one secondary piece (two at a lap / a butt joint of eave struts)
    assert all(len(j["members"]) >= 2 for j in js if j["type"] == "cleat")
    # frame joints: the members at the joint, their sections; the knee joins column top and rafter start
    k = next(j for j in js if j["id"] == "F3-KA")
    assert [m["id"] for m in k["members"]] == ["F3-CA", "F3-RA"] and k["members"][1]["station"] == 0.0
    assert k["members"][1]["section"]["d"] == pytest.approx(800 + 24)                    # haunch deep end: hw_knee 800
    r = next(j for j in js if j["id"] == "F3-R")
    assert {m["id"] for m in r["members"]} == {"F3-RA", "F3-RB"} and r["members"][0]["section"]["d"] == pytest.approx(424)
    assert next(j for j in js if j["id"] == "WF2-T")["members"][1]["id"] == "F1-RA"      # wind column under the rafter


def test_joint_counts_with_an_end_rafter_wall_by_hand():
    js = joint_list(BuildingInput(**B1, end_first="rafter"))
    c = Counter(j["type"] for j in js)
    assert c == {"base": 8, "knee": 8, "ridge": 4, "rafter_splice": 8, "wind_column_top": 8, "wind_column_base": 8,
                 "end_rafter_ridge": 1, "end_rafter_splice": 2, "brace_end": 52, "cleat": 196}
    assert len(js) == 295
    assert next(j for j in js if j["id"] == "WF1-T")["members"][1]["id"] == "EFRA"       # corner column under the end rafter


def test_settings():
    assert ConnectionSettings().capacity_fraction == 0.50
    assert ConnectionSettings.from_dict({"capacity_fraction": 0.6}).capacity_fraction == 0.6
    assert ConnectionSettings.from_dict({"capacity_fraction": None}).capacity_fraction is None
    s = ConnectionSettings.from_dict({"capacity_shear": False})
    assert s.capacity_moment is True and s.capacity_shear is False
    for bad in ({"capacity_fraction": 0}, {"capacity_fraction": 1.5}, {"fraction": 0.5}, {"capacity_shear": "no"}):
        with pytest.raises(ValueError):
            ConnectionSettings.from_dict(bad)


def _line3(b1):
    b, out = b1
    ms, info = _frame_info(b, 2)
    return b, out, ms, info


def _synthetic(info, M_end, V_end=5.0, P=10.0, M_mid=5000.0, skip=None):
    lay = info.layout
    members = {m.mark: [[0.0, P, V_end, M_end], [m.length / 2, P, 999.0, M_mid], [m.length, -P, -V_end, -M_end]]
               for m in lay.members if info.roles[m.mark] != "link" and m.mark != skip}
    return {"combos": [["D", "case"], ["LRFD: t", "LRFD"]],
            "results": {"LRFD: t": {"members": members, "reactions": {"BA": [3.0, 20.0, 0.0], "BB": [-3.0, -7.0, 0.0]}}}}


def _run(b1, res, f=0.50, **switches):
    b, out, ms, info = _line3(b1)
    js = _frame_joints(b, 2, info)
    frame_joint_forces(js, res)
    frame_joint_capacities(js, info, out, b.frame_xs()[2], ms, ConnectionSettings(f, **switches))
    return {j["id"]: j for j in js}


def test_capacity_rule_by_hand_and_the_mid_member_moment_is_not_the_joints(b1):
    js = _run(b1, _synthetic(_line3(b1)[3], M_end=10.0))
    r = js["F3-R"]
    assert r["status"] == EVALUATED
    # the ridge is the j end of both rafters: M there = -10 (the i end has +10); the 5 000 kN·m in mid-member is not taken
    assert r["forces"]["M_neg"]["value"] == 10.0 and r["forces"]["M_pos"]["combo"] is None
    assert r["forces"]["V_max"]["value"] == 5.0                                                  # not the mid 999
    cap = r["capacity"]
    assert cap["Fy"] == 355 and cap["section"]["Zx"] == pytest.approx(1476000.0)
    assert cap["phiMn_pos"] == pytest.approx(PHI_MN_RIDGE, rel=5e-3)
    assert cap["phiVn"] == pytest.approx(PHI_VN_RIDGE, rel=5e-3)
    # section strength, Lb = 0: −M (bottom flange in compression, 8.5 m to the last flange brace) has NO LTB reduction
    assert cap["Lb"] == 0.0 and cap["phiMn_neg"] == pytest.approx(PHI_MN_RIDGE, rel=5e-3)
    d = r["design"]
    assert d["Mu_pos"]["value"] == pytest.approx(0.5 * PHI_MN_RIDGE, rel=5e-3) and d["Mu_pos"]["criterion"] == "% of member capacity"
    assert d["Mu_neg"]["value"] == pytest.approx(0.5 * PHI_MN_RIDGE, rel=5e-3) and d["Mu_neg"]["analysis"] == 10.0
    # the knee: the column top is the shallower section (Zx 3 546 168 < the haunch's 3 716 000); F4 longhand
    kc = js["F3-KA"]["capacity"]
    assert kc["section_of"] == "CA" and kc["section"]["Zx"] == pytest.approx(3546168, rel=1e-5)
    assert kc["phiMn_pos"] == pytest.approx(PHI_MN_KNEE, rel=1e-3) and kc["phiMn_neg"] == pytest.approx(PHI_MN_KNEE, rel=1e-3)
    assert "F4-13" in kc["citations"]["Flexure"]
    assert d["Vu"]["value"] == pytest.approx(0.5 * PHI_VN_RIDGE, rel=5e-3)
    assert d["Pu"]["criterion"] == "analysis force" and d["Pu"]["capacity_based"] is None           # axial: analysis alone
    # the knee: column top (j end, M = -10) and rafter start (i end, M = +10) both scanned
    k = js["F3-KA"]["forces"]
    assert k["M_pos"]["member"] == "RA1" and k["M_neg"]["member"] == "CA"
    # the base: reactions — compression 20, and line B's uplift 7
    assert js["F3-BA"]["forces"]["compression"]["value"] == 20.0 and js["F3-BB"]["forces"]["uplift"]["value"] == 7.0
    assert js["F3-BA"]["forces"]["uplift"]["combo"] is None


def test_capacity_rule_does_not_fire_on_a_heavy_joint_and_f_none(b1):
    js = _run(b1, _synthetic(_line3(b1)[3], M_end=400.0))
    d = js["F3-R"]["design"]["Mu_neg"]
    assert d["value"] == 400.0 and d["criterion"] == "analysis force"                            # 400 > 0.5 × φMn
    js = _run(b1, _synthetic(_line3(b1)[3], M_end=10.0), f=None)
    d = js["F3-R"]["design"]
    assert d["Mu_neg"]["value"] == 10.0 and d["Mu_neg"]["capacity_based"] is None and d["Vu"]["value"] == 5.0


def test_moment_and_shear_switch_separately(b1):
    info = _line3(b1)[3]
    d = _run(b1, _synthetic(info, M_end=10.0), capacity_shear=False)["F3-R"]["design"]
    assert d["Mu_neg"]["criterion"] == "% of member capacity" and d["Vu"]["value"] == 5.0 and d["Vu"]["capacity_based"] is None
    d = _run(b1, _synthetic(info, M_end=10.0), capacity_moment=False)["F3-R"]["design"]
    assert d["Mu_neg"]["value"] == 10.0 and d["Mu_neg"]["capacity_based"] is None
    assert d["Vu"]["value"] == pytest.approx(0.5 * PHI_VN_RIDGE, rel=5e-3)
    # bases never take the rule (switches on)
    base = _run(b1, _synthetic(info, M_end=10.0))["F3-BA"]["design"]
    assert all(v["capacity_based"] is None for v in base.values())


def test_negative_control_missing_forces_read_not_evaluated(b1):
    info = _line3(b1)[3]
    js = _run(b1, _synthetic(info, M_end=10.0, skip="RA1"))          # the haunch segment has no results
    for jid in ("F3-KA", "F3-SA1"):
        assert js[jid]["status"] == NOT_EVALUATED and js[jid]["design"] is None and js[jid]["forces"] is None
        assert any("RA1" in m for m in js[jid]["missing"])
    assert js["F3-KB"]["status"] == EVALUATED                         # the other side still has its forces
    res = _synthetic(info, M_end=10.0)
    for rows in res["results"]["LRFD: t"]["members"].values():       # stations moved 5 mm off the member ends
        rows[0][0] += 5.0
        rows[-1][0] -= 5.0
    js = _run(b1, res)
    assert all(j["status"] == NOT_EVALUATED for jid, j in js.items() if not jid.startswith("F3-B"))
    res = _synthetic(info, M_end=10.0)
    res["combos"] = [["D", "case"]]                                  # no LRFD combination at all
    js = _run(b1, res)
    assert all(j["status"] == NOT_EVALUATED and j["design"] is None for j in js.values())


@pytest.mark.slow
def test_building_1_forces_of_frame_line_3_are_the_analysis_own(b1):
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.joints import building_joints
    from engine.peb.loads_input import LoadsInput

    b, out = b1
    li = LoadsInput(V=45, exposure="C")
    an = analyse_building(b, li)
    r = building_joints(b, li, analysis=an, out=out)
    json.dumps(r, allow_nan=False)                                                    # JSON-safe
    assert r["banner"].startswith("NOT FOR ISSUE") and not r["designed"]
    assert r["not_evaluated"] == 196                                                  # the cleats (step 5), nothing else
    assert all(j["status"] == EVALUATED for j in r["joints"] if j["type"] != "cleat")
    hand = {"base": 10, "knee": 10, "rafter_splice": 10, "ridge": 5, "wind_column_top": 6, "wind_column_base": 6, "brace_end": 48}
    assert r["counts"] == {**{t: {"joints": n, "evaluated": n, "not_evaluated": 0} for t, n in hand.items()},
                           "cleat": {"joints": 196, "evaluated": 0, "not_evaluated": 196},
                           "total": {"joints": 291, "evaluated": 95, "not_evaluated": 196}}
    assert "not a code clause" in r["capacity_rule"]["source"] and "Lb = 0" in r["capacity_rule"]["basis"]
    res = next(f for f in an["frames"] if f["line"] == "3")
    res = res.get("result") or next(f for f in an["frames"] if f["line"] == res["same_as"])["result"]
    lrfd = [c for c, s in res["combos"] if s == "LRFD"]
    ends = {"F3-KA": [("CA", -1), ("RA1", 0)], "F3-KB": [("CB", -1), ("RB1", 0)], "F3-SA1": [("RA1", -1), ("RA2", 0)],
            "F3-SB1": [("RB1", -1), ("RB2", 0)], "F3-R": [("RA2", -1), ("RB2", -1)]}
    js = {j["id"]: j for j in r["joints"]}
    for jid, mm in ends.items():
        rows = [res["results"][c]["members"][mk][k] for c in lrfd for mk, k in mm]   # the first / last station, by hand
        F = js[jid]["forces"]
        assert F["M_pos"]["value"] == pytest.approx(max(0.0, max(s[3] for s in rows)))
        assert F["M_neg"]["value"] == pytest.approx(max(0.0, -min(s[3] for s in rows)))
        assert F["V_max"]["value"] == pytest.approx(max(abs(s[2]) for s in rows))
        assert F["P_comp"]["value"] == pytest.approx(max(0.0, max(s[1] for s in rows)))
        assert F["P_tens"]["value"] == pytest.approx(max(0.0, -min(s[1] for s in rows)))
        mp = F["M_pos"]
        if mp["combo"]:
            mk = mp["member"]
            k = dict(mm)[mk]
            assert res["results"][mp["combo"]]["members"][mk][k][1:] == [mp["P"], mp["V"], mp["M"]]   # its own V and P
        d = js[jid]["design"]
        assert d["Mu_pos"]["value"] == pytest.approx(max(F["M_pos"]["value"], 0.5 * js[jid]["capacity"]["phiMn_pos"]))
    for side in "AB":
        reac = [res["results"][c]["reactions"][f"B{side}"] for c in lrfd]
        F = js[f"F3-B{side}"]["forces"]
        assert F["compression"]["value"] == pytest.approx(max(v[1] for v in reac))
        assert F["uplift"]["value"] == pytest.approx(max(0.0, -min(v[1] for v in reac)))
        assert F["shear"]["value"] == pytest.approx(max(abs(v[0]) for v in reac))
    assert js["F3-BA"]["forces"]["uplift"]["value"] > 0                               # building 1 is in net uplift (Phase 3)
    assert js["F3-R"]["capacity"]["phiMn_pos"] == pytest.approx(PHI_MN_RIDGE, rel=5e-3)
    # braces: the bracing system's LRFD diagonal force on both ends
    br = an["bracing"]["sets"]["LRFD"]
    assert all(j["forces"]["tension"] == br["roof_diagonal"] for j in r["joints"]
               if j["type"] == "brace_end" and _by_id(out)[j["id"][:-2]]["role"] == "roof_brace")
    assert all(math.isfinite(j["forces"]["V_out_of_plane"]) for j in r["joints"] if j["type"] == "wind_column_base")


@pytest.mark.slow
def test_end_rafter_splice_is_evaluated_at_its_own_node(monkeypatch):
    import copy

    import engine.analysis.endwall_analysis as ewa
    from engine.analysis.secondary_weight import secondary_kpa
    from engine.connections.joints import building_joints
    from engine.peb.loads_input import LoadsInput

    b, _ = resolve(BuildingInput(span=30000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4, end_first="rafter"))
    out = peb_building(b)
    li = LoadsInput(V=45, exposure="C")
    sec = secondary_kpa(out)
    assert ewa.end_rafter_splice_ys(out, "F") == [7500.0, 22500.0]                    # by hand (halves of the end rafter)

    def frame(o):
        return ewa.end_rafter_frame(o, "first", li, roof_secondary_kpa=sec["roof_kpa"], wall_secondary_kpa=sec["wall_kpa"])

    def run(o, ef):
        an = {"frames": [], "end_frames": [ef], "bracing": {}, "input": {"base": "pinned"}}
        return {j["id"]: j for j in building_joints(b, li, analysis=an, out=o)["joints"]}

    def own_rows(ef, y):
        return [row for r in ef["results"].values() if r["set"] == "LRFD" for row in r["rafter_stations"] if abs(row[0] - y) <= 1e-6]
    # 1. as generated: splices at 7 500 / 22 500, the end-rafter frame's own stations there
    ef = frame(out)
    js = run(out, ef)
    for jid, y in (("EFRA-S1", 7500.0), ("EFRB-S1", 22500.0)):
        rows = own_rows(ef, y)
        assert js[jid]["status"] == EVALUATED and rows
        assert js[jid]["forces"]["M_abs"] == pytest.approx(max(abs(r[3]) for r in rows))
        assert js[jid]["forces"]["V_abs"] == pytest.approx(max(abs(r[2]) for r in rows))
    # 2. a splice off every model node: EFRA split at 5 000 along the slope → y = 5 000 × 15 000 / 15 074.813 = 4 975.18
    #    (between the corner column at 125 and the wind column at 6 000; their quarter points are 1 593.75, 3 062.5, 4 531.25)
    o2 = copy.deepcopy(out)
    era = next(m for m in o2["members"] if m["id"] == "EFRA")
    L = math.dist(era["start"], era["end"])
    era["section"]["segments"][0]["length"] = 5000.0
    era["section"]["segments"][1]["length"] = L - 5000.0
    y = round(5000.0 * 15000.0 / L, 3)
    assert y == pytest.approx(4975.18, abs=0.01) and y in ewa.end_rafter_splice_ys(o2, "F")
    ef2 = frame(o2)
    j = run(o2, ef2)["EFRA-S1"]
    assert j["status"] == EVALUATED and j["forces"]["M_abs"] == pytest.approx(max(abs(r[3]) for r in own_rows(ef2, y)))
    # negative control: the same frame WITHOUT the splice node — NOT EVALUATED, never an interpolated value
    monkeypatch.setattr(ewa, "end_rafter_splice_ys", lambda o_, tag: [])
    ef0 = frame(o2)
    j0 = run(o2, ef0)["EFRA-S1"]
    assert j0["status"] == NOT_EVALUATED and j0["design"] is None and not own_rows(ef0, y)
    # the extra node does not change the frame: the ridge moment and the reactions agree
    assert run(o2, ef2)["EF-R"]["forces"]["M_abs"] == pytest.approx(run(o2, ef0)["EF-R"]["forces"]["M_abs"], rel=5e-3)
    c = next(k for k, r in ef2["results"].items() if r["set"] == "LRFD")
    for cid, v in ef2["results"][c]["reactions"].items():
        assert v == pytest.approx(ef0["results"][c]["reactions"][cid], rel=5e-3, abs=0.05)


# ------------------------------------------------------------------------------------------------- the sized fixture

def _sized():
    from engine.peb.builtup_frame import BuiltUpSizes
    from engine.peb.loads_input import LoadsInput
    p = __import__("pathlib").Path(__file__).resolve().parents[2] / "fixtures" / "manafe3" / "building1-sized.json"
    fx = json.loads(p.read_text(encoding="utf-8"))
    return BuildingInput(**fx["building"], sizes=BuiltUpSizes(**fx["sizes"])), LoadsInput(**fx["loads"])


def test_placeholder_warnings():
    from engine.connections.joints import placeholder_warnings
    from engine.peb.builtup_frame import default_sizes
    w = placeholder_warnings(BuildingInput(**B1))
    assert any("Main frames" in s for s in w) and any("Wind columns" in s for s in w)
    # the default sizes typed in explicitly are still the placeholder (negative control: not fooled by sizes != None)
    assert any("Main frames" in s for s in placeholder_warnings(BuildingInput(**B1, sizes=default_sizes(24000))))
    b, _ = _sized()
    w = placeholder_warnings(b)
    assert not any("Main frames" in s for s in w) and any("Wind columns" in s for s in w)
    assert any("End rafters" in s for s in placeholder_warnings(BuildingInput(**B1, end_first="rafter")))
    assert not any("End rafters" in s for s in placeholder_warnings(BuildingInput(**B1)))


@pytest.mark.slow
def test_sized_building_1_analysis_or_capacity_by_joint():
    """Building 1 with the Phase 4 sizes (fixtures/manafe3/building1-sized.json: knee 475, base 300, rafter 300, flanges
    200 × 10, webs 6). Knee capacity by hand (column top, d 489.189, hw 469.189 × 6, S355): h/tw 78.20 ≤ 89.25 compact web →
    F3; Zx = 2 000 · 479.189 + 6 · 469.189² / 4 = 1 288 585 mm³, Ix = 281 298 670 mm⁴, Sx = Ix / 244.5945 = 1 150 061 mm³;
    Mp = 457.45 kN·m; λ 10 > λpf 9.020; kc = 4/√78.198 = 0.45234, λrf = 18.126, (10 − 9.020)/(18.126 − 9.020) = 0.10766;
    Mn = 457.45 − (457.45 − 0.7 · 355 · Sx = 285.79) × 0.10766 = 438.97; φMn = 395.07 kN·m.
    Shear: h/tw 78.20 > 60.33 → Cv1 = 0.77156; φVn = 0.9 · 0.6 · 355 · 489.189 · 6 · 0.77156 = 434.13 kN."""
    from engine.analysis.building_analysis import analyse_building
    from engine.connections.joints import building_joints

    b0, li = _sized()
    b, _ = resolve(b0)
    out = peb_building(b)
    r = building_joints(b0, li, analysis=analyse_building(b, li), out=out)
    assert not any("Main frames" in s for s in r["warnings"])
    js = {j["id"]: j for j in r["joints"]}
    k = js["F3-KA"]["capacity"]
    assert k["section"]["d"] == pytest.approx(489.189, abs=1e-3)
    assert k["phiMn_neg"] == pytest.approx(395.07, rel=1e-3) and k["phiVn"] == pytest.approx(434.13, rel=1e-3)
    gov = Counter()
    for j in r["joints"]:
        if j["type"] not in ("knee", "ridge", "rafter_splice"):
            continue
        for key in ("Mu_pos", "Mu_neg", "Vu"):
            d = j["design"][key]
            assert d["value"] == pytest.approx(max(d["analysis"], d["capacity_based"]))      # the rule, every action
            gov[(j["frame_line"] in ("1", "5"), key, d["criterion"])] += 1
    # interior frames (2, 3, 4): the knee M+ and M−, the splice M− and the ridge M+ exceed half the section strength —
    # the analysis governs there (7 per line); the end frames (half the tributary width) and every Vu: the 50 % rule
    assert gov[(False, "Mu_pos", "analysis force")] == 3 * 3 and gov[(False, "Mu_neg", "analysis force")] == 3 * 4
    assert sum(v for (end, key, c), v in gov.items() if c == "analysis force") == 21
    assert not any(c == "analysis force" for (end, key, c) in gov if end or key == "Vu")
    assert js["F3-KA"]["design"]["Mu_neg"]["analysis"] / k["phiMn_neg"] > 0.5                   # 341.8 / 395.1 = 0.87
