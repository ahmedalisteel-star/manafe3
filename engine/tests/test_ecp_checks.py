# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 7: ECP 205-LRFD main-frame checks (engine/design/ecp_checks.py) — longhand.

    K chart      the sway equation's own limits: GA = GB → 0 gives K = 1, one end fixed (G → 0) and one pinned (G → ∞)
                 gives K = 2, GA = GB = 1 gives K = 1.32 (the textbook value of the chart)
    boundary     kN → t ÷ 9.80665, kN·m → t·cm × 100 / 9.80665, MPa → t/cm² ÷ 98.0665, mm → cm ÷ 10
    solve        the ECP solve is nominal stiffness, ≥ 4 elements, NO notional loads: its LRFD combination names carry no
                 [±N] twin and its sway differs from the DAM solve's
    one member   column A of frame line 3 of building 1 at its governing station, the clauses written out here, not
                 called: compression cl. 4.2 (eq. 4.4 λc, eq. 4.2 / 4.3 or 4.6 / 4.7 with Q, φ 0.80) at every station
                 (the member's φPn is the smallest), flexure cl. 5.1.3 class 2 local buckling eq. 5.16 (Mp ≤ 1.5 My,
                 Mr = 0.6 Fy Sx welded), beam-column eq. 7.1a / 7.1b
    must not pass  a class 3 section (Fy forced up so the web passes λr) reads NOT EVALUATED, ratio inf
"""

import math

import pytest

from engine.design import ecp_checks as ec
from engine.design.frame_checks import ChainTaper, EPS, strengths_by_mark
from engine.design.inputs import design_members, restraints
from engine.peb.building import BuildingInput, peb_building
from engine.peb.builtup_frame import builtup_frame_members, default_sizes
from engine.peb.loads_input import LoadsInput

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)
LI = LoadsInput(V=45, exposure="C")
E = 2100.0


def test_k_chart_limits():
    assert ec.k_sway(1e-9, 1e-9) == pytest.approx(1.0, abs=1e-3)
    assert ec.k_sway(1e-9, 1e9) == pytest.approx(2.0, abs=1e-3)
    assert ec.k_sway(1.0, 1.0) == pytest.approx(1.32, abs=0.005)
    assert ec.k_sway(10.0, 10.0) > ec.k_sway(10.0, 1.0) > ec.k_sway(1.0, 1.0)


def test_unit_boundary():
    assert ec._t(9.80665) == pytest.approx(1.0)
    assert ec._tcm(0.0980665) == pytest.approx(1.0)
    assert ec._tcm2(98.0665) == pytest.approx(1.0)
    assert ec._kNm(ec._tcm(123.4)) == pytest.approx(123.4)


@pytest.fixture(scope="module")
def line3():
    from engine.analysis.building_analysis import _line_setup
    from engine.analysis.secondary_weight import secondary_kpa
    b = BuildingInput(**B1)
    out = peb_building(b)
    ms = builtup_frame_members(24000, 6000, 0.1, 12000.0, "3", default_sizes(24000))
    info, fl, fy = _line_setup(b, LI, 2, secondary_kpa(out), 0.10, with_fy=True)
    res = ec.ecp_solve(info, fl)
    return info, fl, out, ms, res


def test_ecp_solve_is_nominal_without_notional(line3):
    from engine.analysis.solve import analyse_frame_line
    info, fl, out, ms, res = line3
    assert res["ecp_solve"] == {"stiffness": 1.0, "min_segments": 4, "notional": 0.0, "p_delta": True}
    lrfd = [c for c, s in res["combos"] if s == "LRFD"]
    assert lrfd and not any("N]" in c for c in lrfd)
    dam = analyse_frame_line(info, fl)
    c = next(c for c in lrfd if "W" in c)
    assert res["results"][c]["sway"] != pytest.approx(dam["results"][c]["sway"], rel=1e-3)


def test_column_A_longhand(line3):
    info, fl, out, ms, res = line3
    st = strengths_by_mark(ms)
    r = ec.ecp_frame_line(info, res, out, 12000.0, st)
    assert "NOT FOR ISSUE" in r["banner"] and not r["designed"]
    m = next(x for x in r["members"] if x["name"] == "column A")
    dm = next(d for d in design_members(info) if d["name"] == "column A")
    lay = {q.mark: q for q in info.layout.members}
    taper = ChainTaper("c", [(c["s0"], lay[c["mark"]].taper) for c in dm["chain"]])
    L = taper.length
    Fy = st["CA"]["Fy"] / 98.0665
    K = r["K"]["column A"]["K"]
    assert K == pytest.approx(ec.k_sway(r["K"]["column A"]["G_top"], 10.0), rel=1e-4) and K > 2.0     # pinned base, sway
    rs = restraints(out, info, 12000.0)["column A"]
    full = [0.0] + sorted(s for s in rs["top"] if any(abs(s - q) <= 50 for q in rs["bottom"])) + [L]
    KLy = max(b - a for a, b in zip(full, full[1:]))
    assert m["KL_in_plane"] == pytest.approx(K * L, abs=0.1) and m["KL_out_of_plane"] == pytest.approx(KLy, abs=0.1)

    def fcr(KL, rr, Q):                                                    # cl. 4.2, eq. 4.4, 4.2/4.3 (4.6/4.7 with Q)
        lc = (KL / rr) / math.pi * math.sqrt(Fy / E)
        return Fy * Q * (1 - 0.384 * Q * lc * lc) if lc * math.sqrt(Q) <= 1.1 else 0.648 * Fy / (lc * lc)
    phiPn = math.inf
    for k in range(21):
        s = min(max(L * k / 20, EPS), L - EPS)
        sec = ec._isec(taper.at(s))
        Q = ec.Q_factor(sec, Fy)
        phiPn = min(phiPn, 0.80 * sec.A * min(fcr(K * L / 10, sec.rx, Q), fcr(KLy / 10, sec.ry, Q)))
    assert m["phiPn_kN"] == pytest.approx(phiPn * 9.80665, abs=1e-3)                  # reported to 3 decimals
    # flexure at the governing station
    s, P, M = m["x"], m["forces"]["P"], m["forces"]["M"]
    sec = ec._isec(taper.at(s))
    cl = ec.classify(sec, Fy, "bending")
    assert cl["class"] == 2
    Sx, My = sec.Sx, Fy * sec.Sx
    Mp = min(Fy * sec.Zx, 1.5 * My)
    Mr = 0.60 * Fy * Sx                                                    # welded: FL = 0.6 Fy (eq. 5.7)
    cands = [Mp - (Mp - Mr) * (e["lambda"] - e["lp"]) / (e["lr"] - e["lp"]) for e in (cl["flange"], cl["web"]) if e["class"] == 2]
    Mn = min(min(cands), Mp)                                               # eq. 5.16 (Lb short: within L'p)
    fx = next(c for c in m["checks"] if c["name"] == "Flexure Mx")
    assert "eq. 5.16" in fx["governing"]
    assert fx["capacity"] == pytest.approx(0.85 * Mn * 9.80665 / 100, rel=1e-4)
    Pu, Mu = P / 9.80665, abs(M) * 100 / 9.80665
    p = Pu / phiPn
    ratio = p + 8 / 9 * Mu / (0.85 * Mn) if p >= 0.2 else p / 2 + Mu / (0.85 * Mn)
    bc = next(c for c in m["checks"] if c["name"] == "Beam-column")
    assert bc["demand"] == pytest.approx(ratio, abs=1e-3)
    assert m["ratio"] == pytest.approx(max(c["ratio"] for c in m["checks"]))
    assert 0.3 < m["ratio"] < 1.0


def test_class_3_not_evaluated(line3):
    info, fl, out, ms, res = line3
    st = {k: {**v, "Fy": 690.0, "Fu": 770.0} for k, v in strengths_by_mark(ms).items()}     # λr falls below the knee web's dw/tw
    r = ec.ecp_frame_line(info, res, out, 12000.0, st)
    col = next(x for x in r["members"] if x["name"] == "column A")
    assert col["ratio"] == math.inf and not col["passed"] and "NOT EVALUATED" in col["governing"]


def test_unequal_flanges_not_evaluated():
    from types import SimpleNamespace
    w = SimpleNamespace(d=600, tw=6, bf_top=200, tf_top=10, bf_bot=250, tf_bot=12)
    assert ec._isec(w) is None
    assert ec._isec(SimpleNamespace(d=600, tw=6, bf_top=200, tf_top=10, bf_bot=200, tf_bot=10)) is not None


@pytest.mark.slow
def test_frame_line_both_side_by_side():
    r = ec.frame_line_both(BuildingInput(**B1), LI, 2, governing="ECP")
    sb = r["side_by_side"]
    assert sb["governing_code"] == "ECP" and len(sb["members"]) == 4
    for row in sb["members"]:
        assert row["ratio"] == row["ECP"] and 0.1 < row["AISC"] < 1.0 and 0.1 < row["ECP"] < 1.0
    with pytest.raises(ValueError):
        ec.side_by_side(r["AISC"], r["ECP"], "BS5950")
