# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 1: the load inputs.

Hand values: Kd = 0.85 (ASCE 7-16 Table 26.6-1, main wind-force resisting system of a building); GCpi = ±0.18 for an
enclosed building, ±0.55 partially enclosed (Table 26.13-1). Sheeting defaults (user): single 0.07, sandwich 0.12 kN/m².
"""

import pytest
from fastapi.testclient import TestClient

from engine.api import app
from engine.peb.loads_input import LoadsInput


def test_defaults_and_derived_values():
    s = LoadsInput(V=45, exposure="C").summary()
    assert s["roof_sheeting"] == 0.07 and s["wall_sheeting"] == 0.07 and s["collateral"] == 0.10 and s["Lo"] == 0.96
    assert s["Kd"] == 0.85 and s["GCpi"] == [0.18, -0.18] and s["base"] == "pinned" and s["sets"] == ["LRFD", "ASD"]
    s2 = LoadsInput(V=45, exposure="B", roof_cladding="sandwich", wall_cladding="sandwich", enclosure="partially_enclosed").summary()
    assert s2["roof_sheeting"] == 0.12 and s2["wall_sheeting"] == 0.12 and s2["GCpi"] == [0.55, -0.55]
    assert LoadsInput(V=45, exposure="C", roof_cladding_kpa=0.09).roof_sheeting == 0.09        # typed value wins


@pytest.mark.parametrize("kw, msg", [
    (dict(exposure="C"), "wind speed V is required"),
    (dict(V=45), "exposure category B, C or D is required"),
    (dict(V=5, exposure="C"), "10 to 100 m/s"),
    (dict(V=45, exposure="C", base="hinged"), "pinned or fixed"),
    (dict(V=45, exposure="C", lrfd=False, asd=False), "LRFD, ASD or both"),
    (dict(V=45, exposure="C", collateral=-0.1), "collateral"),
])
def test_site_facts_are_never_invented(kw, msg):
    with pytest.raises(ValueError, match=msg):
        LoadsInput(**kw).check()


def test_api():
    c = TestClient(app)
    r = c.post("/peb/loads/check", json={"V": 45, "exposure": "C"})
    assert r.status_code == 200 and r.json()["Kd"] == 0.85
    bad = c.post("/peb/loads/check", json={})
    assert bad.status_code == 422 and "wind speed V is required" in bad.json()["detail"]
