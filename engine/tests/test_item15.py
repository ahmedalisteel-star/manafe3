# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Open item 15 (user decisions 2026-11-18): R-factor gate by roof_type, I6.2.3 for the strut lines, the same-direction
pairing, the analytical Lcrd, sizing on the same lines with a per-line gauge. Hand values (longhand, not the code):

    Section inputs Z200x65x20x2.0, S350GD (the engine's finite strip, independently tested in test_cfs): My 14.946,
        Mcrl 24.118, Mcrd 21.095 kN·m; A 713.5 mm²; Ix 4 270 187 mm⁴.
    DSM (App. 1, written out): Mnlo = (1 − 0.15 (Mcrl/My)^0.4)(Mcrl/My)^0.4 My = 14.812; Mnd = (1 − 0.22 (Mcrd/My)^0.5)
        (Mcrd/My)^0.5 My = 13.116 → sheeted flange φMn = 0.9 × 13.116 = 11.804; R-factor simple span Z, d 200 ≤ 8.5 in:
        R 0.65 → φMn = 0.9 × 0.65 × 14.812 = 8.665 kN·m.
    I6.2.3 (from memory, VERIFIED False), x 0.33: d 7.8740, b 2.5591, t 0.07874 in, A 1.10593 in²; C1 = 0.79 × 0.33 + 0.54
        = 0.8007; C2 = 1.17 t + 0.93 = 1.02213; C3 = 2.5 b − 1.63 d + 22.8 = 16.3630; Pn = C1 C2 C3 A = 14.810 kips =
        65.88 kN → φPn = 0.85 × 65.88 = 56.00 kN (strong axis DSM 106.2 kN does not govern). x 0.50: C1 0.935 → 65.39 kN.
    Pex = π² × 203 395.3 × 4 270 187 / 6000² = 238.12 kN; B1(13.448) = 1.05986, B1(15.027) = 1.06736, B1(6.724) = 1.02906.
    A synthetic simple span, L 6000: D 0.2, C 0.1, Lr 0.3, C&C wind 0, Case B uplift −1.0 kN/m; strut force governing
        15.027 = 1.11743 × Case B 13.448 (item 6 split; minimum = governing):
      Case B 0.9D + 1.0W: q = 0.18 − 1.0 = −0.82 → M = 0.82 × 36 / 8 = 3.69 kN·m (free flange, R-factor):
        U = 13.448 / 56.00 + 1.05986 × 3.69 / 8.665 = 0.2402 + 0.4513 = 0.6915  (governs)
      minimum + D only, 1.2D: q 0.24 → M 1.08 (sheeted): U = 15.027 / 56.00 + 1.06736 × 1.08 / 11.804 = 0.3660 — the
        collateral and Lr in the cases are NOT used (a D-only family)
      C&C alone (no strut force): 1.2D + 1.2C + 1.6Lr: q 0.84 → M 3.78 → 3.78 / 11.804 = 0.3202
    Case B pressure (building 1): qh 0.9484, GCpi +0.18: 2E 0.9484 (−1.07 − 0.18) = −1.1855, 2: (−0.69 − 0.18) → −0.8251
        kN/m²; RA1 tributary 1186.0 mm → −1.4060 / −0.9786 kN/m.
    Lcrd (compression, flange + simple lip on the centreline): Z200x65x20x2.0 b 63, d 19, t 2, ho 200: Ixf 3820.0, Iyf
        70 643, Ixyf 8736.6, xof − hxf = b → Lcrd = (13 297 × (3820.0 − 1080.5) × 63²)^(1/4) = 616.6 mm;
        Z250x65x20x1.5 b 63.5, d 19.25, t 1.5, ho 250: Ixf 2962.2, Iyf 54 341, Ixyf 6771.3 → 761.6 mm.
Negative controls: roof_type None / standing seam → strict and the bare-section DSM; an I6.2.3 limit failed → the
bare DSM; x changes C1; a line without a strut force has one family only; the Lcrd reading is not used where the
finite strip finds a minimum; within 5 % of the minimum where one exists (Z200x65x20x2.0).
"""

import json
import math
import pathlib

import pytest

from engine.design import cfs_section as cs
from engine.design.cfs_checks import COMBOS_ROOF, check_line, r_factor, section_data

Z = "Z200x65x20x2.0"


def _line(profile=Z, roof_type="through_fastened", x=0.33, strut=True):
    ln = {"id": "T1", "kind": "purlin", "profile": profile, "grade": "S350GD", "nodes": [0.0, 6000.0], "supports": [0.0, 6000.0],
          "braces": [0.0, 6000.0], "trib": 1000.0, "laps": [],
          "cases": {"D": [0.2], "C": [0.1], "Lr": [0.3], "Win": [0.0], "Wout": [0.0], "WoutB": [-1.0]},
          "roof_type": roof_type, "fastener_x": x}
    if strut:
        ln["P_split"] = {"governing": 15.027, "caseB": 13.448, "minimum": 15.027, "split": True}
    return ln


def _check(ln, method="r_factor"):
    sd = section_data(ln["profile"], ln["grade"])
    ln = dict(ln, rfactor=r_factor(ln, sd, tied_ok=True))
    return check_line(ln, sd, COMBOS_ROOF, 150, method), sd


def _dsm_hand(sd):
    My, Mcrl, Mcrd = sd["My"], sd["Mcrl"], sd["Mcrd"]
    Mnlo = (1 - 0.15 * (Mcrl / My) ** 0.4) * (Mcrl / My) ** 0.4 * My
    Mnd = (1 - 0.22 * (Mcrd / My) ** 0.5) * (Mcrd / My) ** 0.5 * My
    return Mnlo, Mnd


def _i623_hand(sd, x):
    d, b, t, A = 200 / 25.4, 65 / 25.4, 2.0 / 25.4, sd["A"] / 25.4 ** 2
    return 0.85 * (0.79 * x + 0.54) * (1.17 * t + 0.93) * (2.5 * b - 1.63 * d + 22.8) * A * 4448.2216152605


def test_case_b_pairing_and_minimum_dead_only():
    r, sd = _check(_line())
    Mnlo, Mnd = _dsm_hand(sd)
    phiR, phiS = 0.9 * 0.65 * Mnlo, 0.9 * min(Mnlo, Mnd)
    phiP = _i623_hand(sd, 0.33)
    assert phiR / 1e6 == pytest.approx(8.665, abs=2e-3) and phiS / 1e6 == pytest.approx(11.804, abs=2e-3)
    assert phiP / 1e3 == pytest.approx(56.00, abs=0.02)
    Pex = math.pi ** 2 * 203395.3 * sd["Ix"] / 6000.0 ** 2
    B1 = lambda P: 1 / (1 - P * 1e3 / Pex)
    u_b = 13.448e3 / phiP + B1(13.448) * 3.69e6 / phiR
    u_min = 15.027e3 / phiP + B1(15.027) * 1.08e6 / phiS
    u_cc = 3.78e6 / phiS
    assert u_b == pytest.approx(0.6915, abs=1e-3) and u_min == pytest.approx(0.3660, abs=1e-3) and u_cc == pytest.approx(0.3202, abs=1e-3)
    assert r["pairing"]["Case B + strut"] == pytest.approx(u_b, abs=1e-3)
    assert r["pairing"]["minimum + D"] == pytest.approx(u_min, abs=1e-3)     # C and Lr in the cases are not used
    assert r["pairing"]["C&C"] == pytest.approx(u_cc, abs=1e-3)              # no strut force with C&C
    assert r["ratio"] == pytest.approx(u_b, abs=1e-3) and r["family"] == "Case B + strut" and r["combo"] == "0.9D+1.0W"
    assert r["uplift_method"] == "r_factor" and r["i623"]["applied"] and r["axial"]["phiPn_kN"] == pytest.approx(phiP / 1e3, abs=0.01)
    assert r["axial"]["C1"] == pytest.approx(0.8007) and r["axial"]["Pn_strong_DSM_kN"] > r["axial"]["Pn_weak_I623_kN"]
    assert len(r["i623"]["to_confirm"]) == 5 and r["i623"]["VERIFIED"] is False
    # the I6.4.1 row: outside the U, PARTIAL, not passed
    assert any("I6.4.1" in c["name"] and c["ratio"] == math.inf for c in r["checks"]) and not r["passed"]
    assert r["status"] == "PARTIAL - I6.4.1 anchorage NOT EVALUATED"


def test_cc_line_with_zero_axial_has_one_family():
    r, sd = _check(_line(strut=False))
    Mnlo, Mnd = _dsm_hand(sd)
    assert r["pairing"] is None and r["axial"] is None and r["family"] == "C&C"
    assert r["ratio"] == pytest.approx(3.78e6 / (0.9 * min(Mnlo, Mnd)), abs=1e-3)       # 0.3202, gravity, no P
    assert not any(c["name"].startswith("Axial") for c in r["checks"])


def test_roof_type_negative_controls_and_i623_fallback():
    base, sd = _check(_line())
    for rt, flag in ((None, "not given"), ("standing_seam", "I6.2.2 not implemented")):
        r, _ = _check(_line(roof_type=rt))
        assert r["uplift_method"] == "strict" and not r["i623"]["applied"] and any(flag in f for f in r["flags"])
        assert r["axial"]["method"].startswith("DSM, bare section") and r["axial"]["phiPn_kN"] < 0.3 * base["axial"]["phiPn_kN"]
        assert r["ratio"] > base["ratio"] and not any("I6.4.1" in c["name"] for c in r["checks"])
    # x changes C1 (x 0.50: C1 0.935, φPn 65.39)
    r5, _ = _check(_line(x=0.5))
    assert r5["axial"]["C1"] == pytest.approx(0.935) and r5["axial"]["phiPn_kN"] == pytest.approx(_i623_hand(sd, 0.5) / 1e3, abs=0.01)
    assert r5["axial"]["phiPn_kN"] == pytest.approx(65.39, abs=0.05) and r5["ratio"] < base["ratio"]
    # a checkable I6.2.3 limit fails (Z150: d 5.9 in < 6 in, d/b 2.31 < 2.8) → the bare-section DSM
    r150, _ = _check(_line(profile="Z150x65x20x2.0"))
    assert not r150["i623"]["applied"] and r150["i623"]["why_not"] == "a checkable I6.2.3 condition fails"
    bad = {c["name"] for c in r150["i623"]["conditions"] if not c["ok"]}
    assert bad == {"6 in ≤ d ≤ 12 in (152–305 mm)", "2.8 ≤ d / b < 5"} and r150["axial"]["method"].startswith("DSM, bare section")


def test_lcrd_reading_and_its_negative_control():
    assert cs.lcrd("Z", 200, 65, 20, 2.0) == pytest.approx(616.6, abs=0.2)
    assert cs.lcrd("Z", 250, 65, 20, 1.5) == pytest.approx(761.6, abs=0.3)
    z2 = cs.cfs_section(Z, 350.0)
    d = z2["compression"]["distortional"]
    assert d["source"] == "FSM second minimum"                     # a minimum exists → Lcrd NOT used
    at = cs.load_factor(list(z2["_nodes"]), 2.0, cs.lcrd("Z", 200, 65, 20, 2.0), list(z2["_sc"])) * z2["Py"]
    assert abs(at / d["value"] - 1) < 0.05                          # the user's 5 % control (+0.9 %)
    z15 = cs.cfs_section("Z250x65x20x1.5", 350.0)
    dd = z15["compression"]["distortional"]
    assert "Lcrd" in dd["source"] and dd["a"] == pytest.approx(761.6, abs=0.3) and dd["value"] > 0
    assert "VERIFIED False" in z15["compression"]["note"]
    assert z15["bending"]["distortional"]["source"] == "FSM second minimum"     # bending unchanged (it has a minimum)
    assert "Lcrd" in section_data("Z250x65x20x1.5", "S350GD")["source"]["Pcrd"]


def test_case_b_line_loads_building_1():
    from engine.design.cfs_checks import building_lines
    from engine.peb.building import BuildingInput, peb_building, resolve
    from engine.peb.builtup_frame import BuiltUpSizes
    from engine.peb.loads_input import LoadsInput
    fx = json.loads((pathlib.Path(__file__).resolve().parents[2] / "fixtures" / "manafe3" / "building1-sized.json").read_text(encoding="utf-8"))
    assert fx["building"]["roof_type"] == "through_fastened"
    b = BuildingInput(**fx["building"], sizes=BuiltUpSizes(**fx["sizes"]))
    out = peb_building(resolve(b)[0])
    ln = next(x for x in building_lines(out, LoadsInput(**fx["loads"])) if x["id"] == "RA1")
    assert ln["trib"] == pytest.approx(1186.0, abs=0.5)
    for (x0, x1), z, w in zip(zip(ln["nodes"], ln["nodes"][1:]), ln["zones_caseB"], ln["cases"]["WoutB"]):
        e = x0 < 4800 or x1 > 24000 - 4800
        assert z == ("2E" if e else "2")
        assert w == pytest.approx((-1.1855 if e else -0.8251) * 1.186, abs=2e-3)


@pytest.mark.slow
def test_sizing_sees_the_strut_force_per_line_gauge():
    from engine.design.sizing import size_cold_formed
    from engine.tests.test_joints import _sized
    b0, li = _sized()
    r = size_cold_formed(b0, li)
    assert r["roof_type"] == "through_fastened"
    pur, es = r["roles"]["purlin"], r["roles"]["eave_strut"]
    assert pur["to"] == "Z250x65x20x1.5" and es["to"] == "C200x65x20x1.5"
    # the strut lines are checked WITH their axial (the old sizing never saw it): RA5's governing row is H1.2
    assert pur["strut_lines"]["RA5"]["governing"].startswith("RA5: Axial + bending")
    assert not any(v["changed"] for v in pur["strut_lines"].values())          # the strut purlins pass on the base
    # the braced-bay eave struts: C200x1.5 above the target → the next GAUGE of the same depth / flange / lip, C200x1.8
    assert r["line_profiles"] == {k: "C200x65x20x1.8" for k in ("RA0-1", "RA0-4", "RB0-1", "RB0-4")}
    t = es["strut_lines"]["RA0-1"]["tried"]
    assert t[0][0] == "C200x65x20x1.5" and t[0][1] > 0.90 and t[1][0] == "C200x65x20x1.8" and t[1][1] <= 0.90
    # negative control: lines without a wind strut force set the base and are never in line_profiles
    assert set(es["base_lines"]) == {"RA0-2", "RA0-3", "RB0-2", "RB0-3"} and not set(es["base_lines"]) & set(r["line_profiles"])
    # C200x1.8 R-factor capacity longhand: My 13.549, Mcrl 17.665 → Mnlo 12.552 → 0.9 × 0.65 × 12.552 = 7.343 kN·m
    sd = section_data("C200x65x20x1.8", "S350GD")
    Mnlo = (1 - 0.15 * (sd["Mcrl"] / sd["My"]) ** 0.4) * (sd["Mcrl"] / sd["My"]) ** 0.4 * sd["My"]
    assert 0.9 * 0.65 * Mnlo / 1e6 == pytest.approx(7.343, abs=2e-3)
