# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 9: the Design… runner (engine/design/design_run.py) and its API job.

    settings    the governing code must be the code basis (or both), target 0.5 … 1.0, limits checked, unknown modes refused
    JSON        inf / nan → None (an unevaluated ratio is null, never a number), numpy floats → float
    weights     by hand: a built-up segment (web + flanges) × length × 7.85e-6; a Z200x65x20x2.0 piece A × L (A against
                the geometry module); RD20 π 20² / 4 × L; L50x5 (50 + 45) × 5 × L; PL8x100 8 × 100 × L
    sections    the greedy sizer on a known ratio function (ratio = 1e6 / (hw² tw)): ends at or below the target with
                every plate on its list and the lightest such set along its path
    overrides   the wind-column and end-rafter sections reach the generated members (and are refused when malformed)
    API         POST /peb/design starts a job and GET returns its result (the runner stubbed: the flow, not the engineering);
                a bad setting is a 422
    building    Check on building 1 (slow): every row's member exists in the building, governing rows one per member,
                the result serialises, NOT EVALUATED counted, an end-rafter wall's line has no main-frame rows
"""

import dataclasses
import json
import math

import pytest

from engine.design import design_run as dr
from engine.peb.building import BuildingInput, peb_building
from engine.peb.loads_input import LoadsInput

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)


def test_settings():
    s = dr.DesignSettings().check()
    assert s.codes == ["AISC", "ECP"] and s.uplift_method == "r_factor"
    for bad in (dict(code_basis="ECP", governing="AISC"), dict(target=1.2), dict(uplift_method="x"), dict(limits={"sway": -1}), dict(code_basis="BS")):
        with pytest.raises(ValueError):
            dr.DesignSettings(**bad).check()
    assert dr.DesignSettings(code_basis="ECP", governing="ECP").check().codes == ["ECP"]


def test_clean():
    import numpy as np
    c = dr.clean({"a": math.inf, "b": float("nan"), "c": np.float64(1.5), "d": (1, 2), "e": True, "f": None, "g": "x"})
    assert c == {"a": None, "b": None, "c": 1.5, "d": [1, 2], "e": True, "f": None, "g": "x"}
    json.dumps(c)


def test_member_weights_by_hand():
    from engine.design.cfs_section import centreline, properties
    seg = dict(length=6000, hw_start=300, hw_end=800, tw=8, bf_top=250, tf_top=12, bf_bot=250, tf_bot=12)
    assert dr.member_kg({"section": {"segments": [seg]}}) == pytest.approx((550 * 8 + 2 * 250 * 12) * 6000 * 7.85e-6)
    A = properties(centreline("Z", 200, 65, 20, 2), 2, 200)["A"]
    assert dr.member_kg({"profile": "Z200x65x20x2.0", "length": 6925}) == pytest.approx(A * 6925 * 7.85e-6)
    assert dr.member_kg({"profile": "RD20", "length": 1000}) == pytest.approx(math.pi * 100 * 1000 * 7.85e-6)
    assert dr.member_kg({"profile": "L50x5", "length": 1000}) == pytest.approx((50 + 45) * 5 * 1000 * 7.85e-6)
    assert dr.member_kg({"profile": "PL8x100", "start": [0, 0, 0], "end": [0, 0, 500]}) == pytest.approx(8 * 100 * 500 * 7.85e-6)
    out = peb_building(BuildingInput(**B1))
    w = dr.building_weight(out)
    assert w["kg"] == pytest.approx(sum(dr.member_kg(m) for m in out["members"]), abs=0.2)
    assert w["kg_m2"] == pytest.approx(w["kg"] / (24 * 24), abs=0.01) and w["plan_m2"] == 576.0


def test_size_section_greedy():
    f = lambda s: 1.0e7 / (s["hw"] ** 2 * s["tw"])                 # deeper / thicker → lower ratio (18.5 at the start)
    s, r = dr.size_section(f, {"hw": 300.0, "tw": 6.0, "bf": 150.0, "tf": 8.0}, 0.9)
    assert r <= 0.9 and r == pytest.approx(f(s))
    assert s["tw"] in dr.SECTION_LISTS["tw"] and s["bf"] in dr.SECTION_LISTS["bf"] and s["tf"] in dr.SECTION_LISTS["tf"] and s["hw"] % 25 == 0
    assert s["bf"] == 150.0 and s["tf"] == 8.0                      # flanges do nothing for this ratio: kept at the minimum
    down = dr._sec_step(s, "hw", -1)
    assert down is None or f(down) > 0.9 or dr._area(down) >= dr._area(s)   # no single step down keeps it ≤ target


def test_section_overrides_reach_the_members():
    out = peb_building(BuildingInput(**B1, end_first="rafter", wind_column={"hw": 350, "tw": 8, "bf": 180, "tf": 10},
                                     end_rafter={"hw": 450, "tw": 6, "bf": 200, "tf": 10}))
    wc = next(m for m in out["members"] if m["role"] == "wind_column")["section"]["segments"][0]
    er = next(m for m in out["members"] if m["role"] == "end_rafter")["section"]["segments"][0]
    assert (wc["hw_start"], wc["tw"], wc["bf_top"], wc["tf_top"]) == (350, 8, 180, 10)
    assert (er["hw_start"], er["tw"], er["bf_top"], er["tf_bot"]) == (450, 6, 200, 10)
    assert out["input"]["wind_column"]["hw"] == 350
    fb = next(m for m in out["members"] if m["role"] == "flange_brace" and m.get("host", "").startswith("wind column"))
    x_face = next(e["x_face"] for e in out["end_walls"] if e["end"] == "first")
    assert fb["start"][0] == pytest.approx(x_face + (350 + 20 - 5))   # inner flange mid-thickness of the deeper column
    with pytest.raises(ValueError):
        peb_building(BuildingInput(**B1, wind_column={"hw": -1, "tw": 6, "bf": 150, "tf": 8}))
    with pytest.raises(ValueError):
        peb_building(BuildingInput(**B1, end_rafter={"depth": 400}))


def test_api_job_flow(monkeypatch):
    from fastapi.testclient import TestClient
    import engine.api as api
    seen = {}

    def fake(b, li, s, progress=lambda m: None, workers=None):
        progress("stub")
        seen["s"] = s
        return {"banner": "NOT FOR ISSUE", "rows": [], "summary": {"max_ratio": None}}
    monkeypatch.setattr(dr, "check_building", fake)
    c = TestClient(api.app)
    body = {"building": {"span": 24000, "eave_height": 6000, "roof_slope": 0.1, "bay_spacing": 6000, "n_bays": 4},
            "loads": {"V": 45, "exposure": "C"}, "settings": {"code_basis": "AISC", "governing": "AISC"}, "action": "check"}
    job = c.post("/peb/design", json=body).json()["job"]
    import time
    for _ in range(50):
        st = c.get(f"/peb/design/{job}").json()
        if st["status"] != "running":
            break
        time.sleep(0.05)
    assert st["status"] == "done" and st["result"]["banner"] == "NOT FOR ISSUE" and seen["s"].code_basis == "AISC"
    assert c.post("/peb/design", json={**body, "settings": {"target": 2}}).status_code == 422
    assert c.post("/peb/design", json={**body, "loads": {"V": None}}).status_code == 422
    assert c.get("/peb/design/nope").status_code == 404


@pytest.mark.slow
def test_check_building_1():
    b = BuildingInput(**B1, end_first="rafter")
    r = dr.check_building(b, LoadsInput(V=45, exposure="C"), dr.DesignSettings(stability="prismatic"))
    json.dumps(r)
    ids = {m["id"] for m in peb_building(b)["members"]}
    assert all(row["id"] in ids for row in r["rows"])
    assert not any(row["id"].startswith("F1-") for row in r["rows"])          # line 1 is an end-rafter wall
    assert len(r["governing_ids"]) == len(set(r["governing_ids"]))
    kinds = {row["kind"] for row in r["rows"]}
    assert {"column", "rafter", "wind column", "end rafter", "purlin", "girt", "eave strut", "gable girt"} <= kinds
    assert {row["code"] for row in r["rows"]} == {"AISC", "ECP", "AISI"}
    s = r["summary"]
    assert s["weight"]["t"] > 10 and s["max_ratio"] < 1.0 and s["unverified_rows"] > 0 and s["unverified_items"]
    purl = next(row for row in r["rows"] if row["kind"] == "purlin")
    assert purl["uplift_method"] in ("r_factor", "strict") and purl["strict_ratio"] is not None
    assert any(k.endswith("|ECP") for k in r["calc"]) and all(r["calc"][k]["checks"] for k in r["calc"])
