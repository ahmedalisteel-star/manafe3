# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Open item 17: the apex haunch (user decisions 2026-11-18 / -24) against values worked out by hand.

Building 1 apex (fixtures/manafe3/building1-apex.json = building1-sized.json + apex_haunch_length 1600, hw_apex 450):
    knee 475, tf 10 → column depth at the eave 495 → rafter A starts at y 495; apex y 12 000
    rafter line = (12 000 − 495) × √1.01 = 11 505 × 1.00498756 = 11 562.382
    past the knee haunch: 11 562.382 − 2 400 = 9 162.382 ≤ 12 000 → ONE shipping piece = constant 7 562.382 + apex 1 600
    (shop-welded, joint "shop"): segments (2 400, 475 → 300), (7 562.382, 300), (1 600, 300 → 450, shop)
    defaults: 24 000 / 15 = 1 600 (≥ 1 500, already a multiple of 100); 1.5 × 300 = 450 (a multiple of 50)
    span 20 000: 1 333.3 → 1 300 → the 1 500 minimum; span 24 750: 1 650 → 16.5 → HALF UP 1 700 (Python's round would
    give 1 600: the browser's Math.round gives 1 700 — negative control); hw_rafter 350: 525 → 10.5 → 550
    rafter depth (overall, tf 10 + 10): outside the apex 320; at the ridge 450 + 20 = 470; 800 before the ridge
    (mid-apex) 300 + 150 × 800 / 1 600 + 20 = 395
    wind column at the ridge (y 12 000, frame-type end walls): the rafter 150 mm deeper there, measured square to the
    roof → the column top drops 150 × √1.01 = 150.748 mm; the columns at y 6 000 / 18 000 (outside the haunch) unchanged
    joints: 291 as without the haunch — the shop joint is NOT a rafter splice (10 splices: one per rafter half)
Kink (D5, AISC J10, Claude's conservative inputs lb = 0, k = tf):
    θ = atan(150 / 1 600) = 5.35582°; web tw 6, Fy 355, tf 10, d at the kink 320, ho = 300 + 10 = 310
    J10.2 φRn = 1.00 × 355 × 6 × (5 × 10) = 106 500 N = 106.5 kN
    J10.3 φRn = 0.75 × 0.80 × 6² × √(200 000 × 355 × 10 / 6) = 21.6 × √118 333 333 = 21.6 × 10 878.113 = 234 967 N
    bottom flange force M = −100 kN·m (bottom flange in compression), P = 0: C = 100 000 / 310 = 322.581 kN
    kink force 2 × 322.581 × sin(2.67791°) = 645.161 × 0.0467213 = 30.143 kN
D3 (ridge capacity basis): with the apex, the RAFTER section outside the haunch — d 320, Zx = 200 × 10 × 310 + 6 × 300² / 4
    = 620 000 + 135 000 = 755 000 mm³ — not the apex section (d 470, Zx 200 × 10 × 460 + 6 × 450² / 4 = 1 223 750)
"""

import dataclasses
import json
import math
import pathlib

import pytest

from engine.peb.builtup_frame import BuiltUpSizes, apex_defaults, builtup_frame_members, sizes_dict, with_apex_ratio
from engine.peb.building import BuildingInput, peb_building, resolve

FIX = pathlib.Path(__file__).resolve().parents[2] / "fixtures" / "manafe3"


def _fx(name):
    fx = json.loads((FIX / name).read_text(encoding="utf-8"))
    return BuildingInput(**fx["building"], sizes=BuiltUpSizes(**fx["sizes"])), fx


def _rafter(z):
    return next(m for m in builtup_frame_members(24000, 6000, 0.1, 12000.0, "3", z) if m["id"] == "F3-RA")


def test_fixture_and_rafter_segments_by_hand():
    b, fx = _fx("building1-apex.json")
    b0, fx0 = _fx("building1-sized.json")
    assert {k: v for k, v in fx["sizes"].items() if k not in ("apex_haunch_length", "hw_apex")} == fx0["sizes"]
    assert fx["building"] == fx0["building"] and fx["loads"] == fx0["loads"]
    segs = _rafter(b.sizes)["section"]["segments"]
    assert [(s["length"], s["hw_start"], s["hw_end"], s.get("joint")) for s in segs] == [
        (2400.0, 475.0, 300.0, None), (pytest.approx(7562.382, abs=1e-3), 300.0, 300.0, None), (1600.0, 300.0, 450.0, "shop")]
    assert sum(s["length"] for s in segs) == pytest.approx(11505 * math.sqrt(1.01), abs=1e-3)
    assert all(s["tw"] == 6 and s["bf_bot"] == 200 and s["tf_top"] == 10 for s in segs)
    # OFF (negative control): the sized fixture keeps its two segments, no joint, and its sizes dict has no apex keys
    segs0 = _rafter(b0.sizes)["section"]["segments"]
    assert [(s["length"], s["hw_end"]) for s in segs0] == [(2400.0, 300.0), (pytest.approx(9162.382, abs=1e-3), 300.0)]
    assert not any("joint" in s for s in segs0)
    assert "hw_apex" not in sizes_dict(b0.sizes) and sizes_dict(b.sizes)["hw_apex"] == 450


def test_defaults_rounding_and_ratio():
    assert apex_defaults(24000, 300) == {"apex_haunch_length": 1600, "hw_apex": 450}
    assert apex_defaults(20000, 300)["apex_haunch_length"] == 1500            # 1 300 → the minimum
    assert apex_defaults(24750, 300)["apex_haunch_length"] == 1700            # 16.5 → half up (not half-even 1 600)
    assert apex_defaults(24000, 350)["hw_apex"] == 550                        # 10.5 → half up
    z = BuiltUpSizes(hw_knee=475, hw_base=300, hw_rafter=350, haunch_length=2400, bf=200, tf=10, apex_haunch_length=1600, hw_apex=450)
    assert with_apex_ratio(z).hw_apex == 550
    off = dataclasses.replace(z, apex_haunch_length=0.0, hw_apex=None)
    assert with_apex_ratio(off) == off                                         # OFF: nothing follows


def test_sizing_step_keeps_the_ratio():
    from engine.design.sizing import step
    b, _ = _fx("building1-apex.json")
    z = step(b.sizes, "hw_rafter", +1)                                         # 300 → 325: hw_apex 487.5 → 500 (half up)
    assert z.hw_rafter == 325 and z.hw_apex == 500
    assert step(b.sizes, "tf", +1).hw_apex == 450                              # other variables leave it alone


def test_refusals():
    b, _ = _fx("building1-apex.json")
    z = b.sizes
    for bad, msg in ((dataclasses.replace(z, hw_apex=250), "must not be less"),
                     (dataclasses.replace(z, apex_haunch_length=9200), "overlaps"),
                     (dataclasses.replace(z, hw_apex=None), "needs hw_apex"),
                     (dataclasses.replace(z, apex_haunch_length=0.0), "without an apex haunch length")):
        with pytest.raises(ValueError, match=msg):
            builtup_frame_members(24000, 6000, 0.1, 0.0, "1", bad)
    from engine.sections.builtup import BuiltUpError, BuiltUpMember
    segs = _rafter(z)["section"]["segments"]
    with pytest.raises(BuiltUpError, match="one top flange plate"):
        BuiltUpMember.from_dicts(segs[:2] + [{**segs[2], "tf_top": 12}])
    with pytest.raises(BuiltUpError, match="first segment"):
        BuiltUpMember.from_dicts([{**segs[0], "joint": "shop"}] + segs[1:])
    m = BuiltUpMember.from_dicts(segs)
    assert m.field_splices == [2400.0] and len(m.splices) == 2


def test_joints_rafter_depth_and_wind_columns():
    from engine.connections.joints import joint_list
    from engine.peb.bracing import BracingInput, rafter_depth
    b, _ = _fx("building1-apex.json")
    b, _ = resolve(b)
    out = peb_building(b)
    js = joint_list(b, out)
    assert len(js) == 291 and sum(j["type"] == "rafter_splice" for j in js) == 10
    ridge = next(j for j in js if j["id"] == "F3-R")
    assert all(mm["section"]["d"] == 470.0 for mm in ridge["members"])      # the ridge plate sees the apex depth
    bi = BracingInput(span=24000, eave_height=6000, roof_slope=0.1, frames=[0.0], sizes=b.sizes)
    s_r = 12000 * math.sqrt(1.01)
    assert rafter_depth(s_r, bi) == pytest.approx(470.0)
    assert rafter_depth(s_r - 800, bi) == pytest.approx(395.0)
    assert rafter_depth(s_r - 1600.001, bi) == pytest.approx(320.0, abs=1e-3)
    wc = {m["id"]: m["end"][2] for m in out["members"] if m["role"] == "wind_column"}
    b0, _ = _fx("building1-sized.json")
    wc0 = {m["id"]: m["end"][2] for m in peb_building(resolve(b0)[0])["members"] if m["role"] == "wind_column"}
    for k in wc:
        assert wc0[k] - wc[k] == pytest.approx(150 * math.sqrt(1.01) if k in ("WF2", "WL2") else 0.0, abs=1e-3)
    # NEGATIVE CONTROL: the same segments with the joint taken off → a field splice each side (20 splices)
    from engine.analysis.frame_model import frame_line_model
    from engine.connections.joints import _frame_joints
    ms = builtup_frame_members(24000, 6000, 0.1, 12000.0, "3", b.sizes)
    info = frame_line_model(ms, 24000, 6000, 0.1, (6000.0,) * 4)
    assert info.shop == frozenset({"RAS2", "RBS2"})
    for m in ms:
        for s in m["section"]["segments"]:
            s.pop("joint", None)
    info2 = frame_line_model(ms, 24000, 6000, 0.1, (6000.0,) * 4)
    assert info2.shop == frozenset() and sum(j["type"] == "rafter_splice" for j in _frame_joints(b, 2, info2)) == 4


def test_end_rafter_wall_has_no_apex_haunch():
    """D4: an end-rafter (bearing) wall keeps its constant end rafter and its wind columns; frame lines 2-5 get the haunch."""
    b, _ = _fx("building1-apex.json")
    b0, _ = _fx("building1-sized.json")
    b, b0 = (resolve(dataclasses.replace(x, end_first="rafter"))[0] for x in (b, b0))
    out, out0 = peb_building(b), peb_building(b0)
    er = [m for m in out["members"] if m["role"] == "end_rafter"]
    assert er and not any(s.get("joint") for m in er for s in m["section"]["segments"])
    assert [m["section"] for m in er] == [m["section"] for m in out0["members"] if m["role"] == "end_rafter"]
    wf = lambda o: {m["id"]: m["end"] for m in o["members"] if m["role"] == "wind_column" and m["id"].startswith("WF")}
    assert wf(out) == wf(out0)
    assert any(s.get("joint") == "shop" for m in out["members"] if m["role"] == "rafter" for s in m["section"]["segments"])


def test_ridge_capacity_basis_is_the_rafter_section():
    """D3 (user 2026-11-24): the 50 % minimum at the ridge from the rafter section outside the haunch; 100 % of the
    analysis forces still apply (design_force takes the larger)."""
    from engine.connections.joints import APEX_BASIS, ConnectionSettings, _frame_info, _frame_joints, frame_joint_capacities
    res = {}
    for name in ("building1-apex.json", "building1-sized.json"):
        b, _ = _fx(name)
        b, _ = resolve(b)
        ms, info = _frame_info(b, 2)
        js = [j for j in _frame_joints(b, 2, info) if j["type"] == "ridge"]
        F = {"M_pos": {"value": 1.0}, "M_neg": {"value": 1.0}, "V_max": {"value": 1.0}, "P_comp": {"value": 0.0}, "P_tens": {"value": 0.0}}
        for j in js:
            j["forces"] = F
        frame_joint_capacities(js, info, peb_building(b), b.frame_xs()[2], ms, ConnectionSettings())
        res[name] = js[0]
    cap = res["building1-apex.json"]["capacity"]
    assert cap["section"]["d"] == 320.0 and cap["section"]["Zx"] == pytest.approx(755000.0, abs=1.0)
    assert cap["section_of"] in ("RA2", "RB2") and APEX_BASIS in cap["basis"]
    # the same rafter section as without the haunch → the same capacity and design moment (negative control: no note there)
    cap0 = res["building1-sized.json"]["capacity"]
    assert cap0["section"]["Zx"] == pytest.approx(755000.0, abs=1.0) and APEX_BASIS not in cap0["basis"]
    assert cap["phiMn_pos"] == pytest.approx(cap0["phiMn_pos"]) and cap["phiVn"] == pytest.approx(cap0["phiVn"])
    d, d0 = res["building1-apex.json"]["design"], res["building1-sized.json"]["design"]
    assert d["Mu_pos"] == d0["Mu_pos"]


def test_kink_longhand():
    from engine.connections import kink as K
    assert K.web_local_yielding(355, 6, 10) == pytest.approx(106.5)
    assert K.web_crippling(355, 6, 10, 320) == pytest.approx(234.967, abs=1e-3)
    C = K.flange_force(-100.0, 0.0, 310.0, 2000.0, 5800.0)
    assert C == pytest.approx(322.581, abs=1e-3)
    th = math.atan(150 / 1600)
    assert math.degrees(th) == pytest.approx(5.35582, abs=1e-5)
    assert K.kink_force(C, th) == pytest.approx(30.143, abs=1e-3)
    # axial share: P = 58 kN compression, A_bot / A = 2 000 / 5 800 → +20 kN on the flange
    assert K.flange_force(0.0, 58.0, 310.0, 2000.0, 5800.0) == pytest.approx(20.0)
    kk = {"theta_deg": math.degrees(th), "ho": 310.0, "A_bot": 2000.0, "A": 5800.0, "tw": 6.0, "tf_bot": 10.0, "d": 320.0}
    r = K.check_kink(kk, [{"M": -100.0, "P": 0.0, "combo": "c1", "member": "RA3"}], 355)
    assert r["status"] == K.PASSES and not r["stiffener_pair"] and len(r["checks"]) == 2
    assert r["governing"]["check"].startswith("J10.2") and r["governing"]["ratio"] == pytest.approx(30.143 / 106.5, abs=1e-4)
    # NEGATIVE CONTROLS: a tension flange (M > 0) runs J10.2 only, never crippling; a large force fails → stiffener pair
    rt = K.check_kink(kk, [{"M": 100.0, "P": 0.0, "combo": "c2", "member": "RA3"}], 355)
    assert [c["check"] for c in rt["checks"]] == ["J10.2 web local yielding (flange in tension)"]
    rf = K.check_kink(kk, [{"M": -400.0, "P": 0.0, "combo": "c3", "member": "RA3"}], 355)
    assert rf["status"] == K.FAILS and rf["stiffener_pair"] and rf["governing"]["ratio"] > 1.0
    assert K.check_kink(kk, [], 355)["status"] == K.NOT_EVALUATED


def test_kink_nothing_without_the_haunch():
    from engine.connections.kink import building_kinks
    b0, _ = _fx("building1-sized.json")
    r = building_kinks(b0, None, analysis={"frames": []})
    assert r["kinks"] == [] and "no apex haunch" in r["note"]


def test_kink_flange_braces_17b():
    """Open item 17b (user 2026-11-24): apex ON → a flange-brace pair at the purlin nearest the kink on its EAVE side.

    By hand: purlin spacing (12 000 × √1.01 − 200) / 10 = 11 859.851 / 10 = 1 185.985 → RA8 at s 9 487.881, RA9 at
    10 673.866; the kink at s 12 059.851 − 1 600 = 10 459.851 → RA8 (the last purlin with s ≤ the kink).
    Brace bottom end (rafter depth 320 outside the haunch, 315 to the flange mid-thickness): the roof point y = 9 487.881 /
    1.0049876 = 9 440.794, z = 6 944.079; along the roof normal (−0.0995037, 0.9950372) × −315 → y 9 472.138,
    z 6 630.643; run 315 + 50 = 365 at 45° → length 365 √2 = 516.188. Count: interior frames 2, 3, 4 × 2 sides × 2 = 12,
    end frames 1, 5 × 2 sides × 1 (inside the building only) = 4 → 16 more braces (136 → 152).
    Kink → that brace along the roof: 10 459.851 − 9 487.881 = 971.970."""
    from engine.connections.joints import _frame_info
    from engine.connections.kink import _kinks, nearest_flange_brace
    b, _ = _fx("building1-apex.json")
    b0, _ = _fx("building1-sized.json")
    fb = lambda bb: [m for m in peb_building(resolve(bb)[0])["members"] if m["role"] == "flange_brace"]
    on, off, sized = fb(b), fb(dataclasses.replace(b, kink_flange_braces=False)), fb(b0)
    assert (len(on), len(off), len(sized)) == (152, 136, 136)
    new = [m for m in on if m["line"] in ("RA8", "RB8")]
    assert len(new) == 16 and not [m for m in off + sized if m["line"] in ("RA8", "RB8")]   # NEGATIVE CONTROLS
    a3 = [m for m in new if m["line"] == "RA8" and m["start"][0] == 12000.0]
    assert len(a3) == 2 and all(m["start"] == [12000.0, pytest.approx(9472.138, abs=1e-3), pytest.approx(6630.643, abs=1e-3)] for m in a3)
    assert sorted(m["end"][0] for m in a3) == [11635.0, 12365.0] and all(m["length"] == pytest.approx(516.188, abs=1e-3) for m in a3)
    assert all(m["profile"] == "L50x5" for m in new)
    assert sorted(m["start"][0] for m in new if m["line"] == "RB8") == [0.0, 6000.0, 6000.0, 12000.0, 12000.0, 18000.0, 18000.0, 24000.0]
    # the other braces are the same with and without (only the 16 added)
    key = lambda m: (m["host"], m["line"], tuple(m["start"]), tuple(m["end"]))
    assert sorted(map(key, off)) == sorted(map(key, [m for m in on if m["line"] not in ("RA8", "RB8")]))
    bb = resolve(b)[0]
    out = peb_building(bb)
    ms, info = _frame_info(bb, 2)
    for kk in _kinks(ms, info):
        assert nearest_flange_brace(kk, out, 12000.0, 0.1)["eave"]["distance_along_rafter"] == pytest.approx(971.97, abs=0.1)
