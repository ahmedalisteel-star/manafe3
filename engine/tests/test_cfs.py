# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 6: cold-formed sections from geometry, the finite strip, purlin / girt / eave-strut lines — independent checks.

    finite strip   a flat plate, both long edges supported (w = 0): the minimum over the half-wavelength is k = 4.00 at a = b
                   (closed form σcr = k π² E / 12 (1 − ν²) (t / b)²); one edge free: k = 0.425 + (b / a)² at a = 20 b
    properties     against sectionproperties (a finite-element solid section with the true corners — an independent tool):
                   A, Ix, Iz, Ixz, J, Cw and the shear centre within 0.5 %
    global         a long C200 column / beam against the closed forms from the properties: min(π² E Iz / L², flexural-
                   torsional) and Mcr = ro A √(σey σt) (classical, Cb = 1) within 1 % at 6 and 9 m
    mode split     Z200x65x20x2.0: two minima, local (a ≈ 110 mm) before distortional (a ≈ 565 mm)
    beam           single span wL²/8, wL/2, 5wL⁴/384EI; three equal spans 0.100 wL² over the support and 0.080 wL² in the
                   end span; a cantilever w a² / 2; four uneven spans against bimsteelauto continuous_beam_forces (PyNite)
    one line       the eave strut of bay 2 of building 1 (a simple span, 6 m, sag rod at mid-bay), longhand: the loads from
                   the job inputs, the Ch. 30 zone-2 pressure at its effective area, M = w L² / 8, Cb over the 3 m brace
                   segment = 12.5 / 9.625, and the DSM curves (App. 1 Eqs. 1.2.2) written out here, not called
    negative       a roof above 7°: the roof wind is NOT evaluated → ratio inf, not passed (the walls still are)
"""

import math

import pytest

from engine.design import cfs_section as cs
from engine.design.cfs_checks import COMBOS_ROOF, beam_line, building_lines, cfs_checks, check_line, section_data
from engine.peb.building import BuildingInput, peb_building
from engine.peb.loads_input import LoadsInput

LI = LoadsInput(V=45, exposure="C")
B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)


# ---------------------------------------------------------------------------------------------- finite strip

def test_plate_buckling_closed_forms():
    b, t = 100.0, 1.0
    nodes = [(b * i / 8, 0.0) for i in range(9)]
    st = [1.0] * 9
    scr = math.pi ** 2 * cs.E_CFS / (12 * (1 - cs.NU ** 2)) * (t / b) ** 2
    curve = cs.signature(nodes, t, st, lengths=[50, 80, 100, 120, 150, 200], fixed=[2, 34])
    (a, lam), = cs.minima(nodes, t, st, curve, [2, 34])
    assert lam / scr == pytest.approx(4.0, rel=1e-3)
    assert a == pytest.approx(b, rel=1e-2)
    k_free = cs.load_factor(nodes, t, 20 * b, st, [2]) / scr
    assert k_free == pytest.approx(0.425 + (1 / 20) ** 2, rel=2e-3)


@pytest.mark.parametrize("name", ["C200x65x20x2.0", "Z200x65x20x2.0", "C250x75x20x2.5"])
def test_properties_against_sectionproperties(name):
    from sectionproperties.analysis import Section
    from sectionproperties.pre.library import cee_section, zed_section
    g = cs.parse_name(name)
    t = g["t"]
    geom = (cee_section(d=g["H"], b=g["B"], l=g["D"], t=t, r_out=2 * t, n_r=16) if g["kind"] == "C"
            else zed_section(d=g["H"], b_l=g["B"], b_r=g["B"], l=g["D"], t=t, r_out=2 * t, n_r=16))
    geom.create_mesh(mesh_sizes=[t * t * 0.5])
    s = Section(geom)
    s.calculate_geometric_properties()
    s.calculate_warping_properties()
    ixx, iyy, ixy = s.get_ic()
    (xs, _), (cx, _) = s.get_sc(), s.get_c()
    p = cs.properties(cs.centreline(g["kind"], g["H"], g["B"], g["D"], t), t, g["H"])   # inside radius t: r_out 2t
    for mine, ref in ((p["A"], s.get_area()), (p["Ix"], ixx), (p["Iz"], iyy), (p["J"], s.get_j()), (p["Cw"], s.get_gamma())):
        assert mine == pytest.approx(ref, rel=5e-3)
    if g["kind"] == "Z":
        assert abs(p["Ixz"]) == pytest.approx(abs(ixy), rel=5e-3)
        assert abs(p["xs"]) < 1e-6
    else:
        assert p["xs"] == pytest.approx(xs - cx, rel=5e-3)


def test_global_buckling_against_closed_forms():
    name, Fy = "C200x65x20x2.0", 350.0
    p = cs.cfs_section(name, Fy)["props"]
    E, G = cs.E_CFS, cs.E_CFS / (2 * (1 + cs.NU))
    A = p["A"]
    rx2, ry2, x0 = p["Ix"] / A, p["Iz"] / A, p["xs"]
    ro2 = rx2 + ry2 + x0 * x0
    beta = 1 - x0 * x0 / ro2
    for L in (6000.0, 9000.0):
        st = (G * p["J"] + math.pi ** 2 * E * p["Cw"] / L ** 2) / (A * ro2)
        sex = math.pi ** 2 * E * rx2 / L ** 2
        Fft = ((sex + st) - math.sqrt((sex + st) ** 2 - 4 * beta * sex * st)) / (2 * beta)
        P = min(math.pi ** 2 * E * p["Iz"] / L ** 2, Fft * A)
        M = math.sqrt(ro2) * A * math.sqrt(math.pi ** 2 * E * ry2 / L ** 2 * st)
        assert cs.Pcre(name, Fy, L) == pytest.approx(P, rel=1e-2)
        assert cs.Mcre(name, Fy, L) == pytest.approx(M, rel=1e-2)
    # below the curve's peak the global value is held at the peak (a lower bound — the curve there is local / distortional)
    s = cs.cfs_section(name, Fy)
    assert cs.Mcre(name, Fy, 300) == pytest.approx(cs.Mcre(name, Fy, s["bending"]["a_global_from"]))
    assert cs.Mcre(name, Fy, 300) > s["bending"]["distortional"]["value"]


def test_mode_split_z200():
    s = cs.cfs_section("Z200x65x20x2.0", 350.0)
    for key in ("bending", "compression"):
        loc, dist = s[key]["local"], s[key]["distortional"]
        assert loc and dist, key
        assert 60 < loc["a"] < 250 and 300 < dist["a"] < 1000 and loc["a"] < dist["a"]
    assert s["bending"]["local"]["value"] / s["My"] == pytest.approx(1.614, abs=0.01)
    assert s["bending"]["distortional"]["value"] / s["My"] == pytest.approx(1.411, abs=0.01)


# ---------------------------------------------------------------------------------------------- the beam

def test_beam_closed_forms():
    EI, L, w = 2.0e12, 6000.0, 1.5
    st = beam_line([0, L], [0, L], [w], EI)
    assert max(s[1] for s in st) == pytest.approx(w * L * L / 8)
    assert max(abs(s[2]) for s in st) == pytest.approx(w * L / 2)
    assert max(s[3] for s in st) == pytest.approx(5 * w * L ** 4 / (384 * EI))
    st = beam_line([0, L, 2 * L, 3 * L], [0, L, 2 * L, 3 * L], [w] * 3, EI, n=201)
    assert -min(s[1] for s in st) == pytest.approx(0.100 * w * L * L, rel=1e-6)
    assert max(s[1] for s in st[:201]) == pytest.approx(0.080 * w * L * L, rel=2e-3)
    a = 1500.0
    st = beam_line([-a, 0, L], [0, L], [w, w], EI)
    assert -min(s[1] for s in st[:21]) == pytest.approx(w * a * a / 2)


def test_beam_against_bimsteelauto():
    from bimsteelauto.design.purlins import CFShape, ColdFormedSection, continuous_beam_forces
    sec = ColdFormedSection(name="Z", shape=CFShape.Z, t=2, H=200, B=65, Dlip=20, A=713.5, Ix=4.27e6, Sx=42700, Se_top=40000, Se_bot=40000)
    spans = (5000.0, 7000.0, 6000.0, 4500.0)
    f = continuous_beam_forces(spans, 2.0, sec)
    xs = [0.0]
    for s in spans:
        xs.append(xs[-1] + s)
    st = beam_line(xs, xs, [2.0] * 4, 203000.0 * 4.27e6)
    assert -min(s[1] for s in st) / 1e6 == pytest.approx(f.M_hogging, rel=1e-3)
    assert max(s[1] for s in st) / 1e6 == pytest.approx(f.M_sagging, rel=1e-2)       # sampling of the span
    assert max(abs(s[3]) for s in st) == pytest.approx(abs(f.delta_max), rel=1e-2)


# ---------------------------------------------------------------------------------------------- one line by hand

def _dsm_longhand(My, Mcre, Mcrl, Mcrd):
    if Mcre >= 2.78 * My:
        Mne = My
    elif Mcre > 0.56 * My:
        Mne = 10 / 9 * My * (1 - 10 * My / (36 * Mcre))
    else:
        Mne = Mcre
    ll = math.sqrt(Mne / Mcrl)
    Mnl = Mne if ll <= 0.776 else (1 - 0.15 * (Mcrl / Mne) ** 0.4) * (Mcrl / Mne) ** 0.4 * Mne
    ld = math.sqrt(My / Mcrd)
    Mnd = My if ld <= 0.673 else (1 - 0.22 * (Mcrd / My) ** 0.5) * (Mcrd / My) ** 0.5 * My
    return min(Mnl, Mnd)


@pytest.fixture(scope="module")
def b1_lines():
    out = peb_building(BuildingInput(**B1))
    return out, building_lines(out, LI)


def test_eave_strut_by_hand(b1_lines):
    from bimsteelauto.loads.wind import envelope_pressures
    from engine.analysis.endwall_analysis import _geom
    out, lines = b1_lines
    ln = next(x for x in lines if x["id"] == "RA0-2")
    assert ln["supports"] == [6000.0, 12000.0] and ln["braces"] == [6000.0, 9000.0, 12000.0] and ln["laps"] == []
    c = 1 / math.sqrt(1.01)
    trib = 1186.0 / 2 * 1.0                                          # half the first purlin pitch along the roof
    assert ln["trib"] == pytest.approx(trib, abs=1.0)
    trib = ln["trib"]
    A = cs.cfs_section("C200x65x20x2.0", 350.0)["props"]["A"]
    D = (0.07 * trib / 1000 + A * 1e-6 * 77.0) * c
    C = 0.10 * trib / 1000 * c * c
    Lr = 0.96 * trib / 1000 * c * c                                  # At = 0.593 × 6 × c = 3.5 m² < 18.58: R1 = R2 = 1
    w = envelope_pressures(_geom(out["input"]), LI.site())
    A_ft2 = 6.0 * max(trib / 1000, 2.0) / 0.3048 ** 2                 # 12 m² (span / 3 governs)
    gcp = -2.3 + (-1.4 + 2.3) * math.log10(A_ft2 / 10) / math.log10(50)   # zone 2 (eave strip), Fig. 30.3-2A
    Wout = w.qh * (gcp - 0.18) * trib / 1000
    assert A_ft2 > 100                                               # positive GCp flat at +0.2 beyond 100 ft²
    Win = max(w.qh * (0.2 + 0.18), 0.766084) * trib / 1000           # 0.36 kPa < 16 psf: the §30.2.2 minimum governs
    assert ln["cases"]["D"][0] == pytest.approx(D, rel=1e-6)
    assert ln["cases"]["C"][0] == pytest.approx(C, rel=1e-6)
    assert ln["cases"]["Lr"][0] == pytest.approx(Lr, rel=1e-6)
    assert ln["cases"]["Wout"][0] == pytest.approx(Wout, rel=1e-6)
    assert ln["cases"]["Win"][0] == pytest.approx(Win, rel=1e-6)
    sd = section_data("C200x65x20x2.0", "S350GD")
    r = check_line(ln, sd, COMBOS_ROOF, 150)
    L = 6.0
    # gravity: 1.2 (D + C) + 1.6 Lr + 0.5 Win, the sheeted (top) flange in compression → Mne = My
    Mg = (1.2 * (D + C) + 1.6 * Lr + 0.5 * Win) * L * L / 8
    phiMg = 0.9 * _dsm_longhand(sd["My"], math.inf, sd["Mcrl"], sd["Mcrd"]) / 1e6
    # uplift: 0.9 D + 1.0 Wout, the free flange over the 3 m segment: M/Mmax at its quarter points 0.4375, 0.75, 0.9375
    Mu = abs(0.9 * D + Wout) * L * L / 8
    Cb = 12.5 / (2.5 + 3 * 0.4375 + 4 * 0.75 + 3 * 0.9375)
    assert Cb == pytest.approx(1.2987, abs=1e-4)
    phiMu = 0.9 * _dsm_longhand(sd["My"], Cb * cs.Mcre("C200x65x20x2.0", 350.0, 3000.0), sd["Mcrl"], sd["Mcrd"]) / 1e6
    ratio = max(Mg / phiMg, Mu / phiMu)
    assert Mg / phiMg > Mu / phiMu                                   # gravity governs this strut
    assert r["forces"]["M"] == pytest.approx(Mg, abs=2e-3)
    assert r["ratio"] == pytest.approx(ratio, abs=2e-4)
    assert r["combo"] == "1.2D+1.6Lr+0.5W" and r["x"] == pytest.approx(9000.0)
    defl = next(x for x in r["checks"] if x["name"].startswith("Deflection"))
    d = 5 * (D + C + Lr) * 6000.0 ** 4 / (384 * 203395.3 * sd["Ix"])  # ASD D + Lr
    assert defl["demand"] == pytest.approx(d, abs=2e-3) and defl["capacity"] == pytest.approx(40.0)


def test_supplier_override_and_unknown_key(b1_lines):
    _, lines = b1_lines
    ln = next(x for x in lines if x["id"] == "RA0-2")
    base = check_line(ln, section_data("C200x65x20x2.0", "S350GD"), COMBOS_ROOF, 150)
    sd = section_data("C200x65x20x2.0", "S350GD", {"C200x65x20x2.0": {"Mcrd": 10.0e6}})
    assert sd["source"]["Mcrd"] == "supplier" and sd["source"]["Mcrl"].startswith("geometry")
    worse = check_line(ln, sd, COMBOS_ROOF, 150)
    assert worse["ratio"] > base["ratio"]
    with pytest.raises(ValueError, match="unknown key"):
        section_data("C200x65x20x2.0", "S350GD", {"C200x65x20x2.0": {"Se": 1.0}})


def test_steep_roof_wind_not_evaluated():
    out = peb_building(BuildingInput(**{**B1, "roof_slope": 0.15}))     # 8.5° > 7°: Fig. 30.3-2A does not apply
    lines = building_lines(out, LI)
    roof = next(x for x in lines if x["kind"] == "purlin")
    wall = next(x for x in lines if x["kind"] == "girt")
    r = check_line(roof, section_data(roof["profile"], roof["grade"]), roof["combos"], 150)
    assert r["ratio"] == math.inf and not r["passed"]
    r = check_line(wall, section_data(wall["profile"], wall["grade"]), wall["combos"], 150)
    assert math.isfinite(r["ratio"])


@pytest.mark.slow
def test_whole_building_step6():
    r = cfs_checks(BuildingInput(**B1), LI)
    assert len(r["purlins"]) == 20 and len(r["eave_struts"]) == 8 and len(r["girts"]) == 8 and len(r["gable_girts"]) == 10
    allr = [x["ratio"] for g in ("purlins", "eave_struts", "girts", "gable_girts") for x in r[g]]
    assert all(math.isfinite(v) for v in allr)
    assert r["max_ratio"] == max(allr) and 0.5 < r["max_ratio"] < 1.0
    p1 = next(x for x in r["purlins"] if x["id"] == "RA1")
    # a = 2400 (bimsteelauto end_zone_width); per span: the end spans reach into the gable strips
    assert p1["zones"] == ["3", "2", "2", "3"]                         # s 1186: the eave strip — corners at the gable ends
    p3 = next(x for x in r["purlins"] if x["id"] == "RA3")
    assert p3["zones"] == ["2", "1", "1", "2"]                         # s 3558: outside the eave strip
    p10 = next(x for x in r["purlins"] if x["id"] == "RA10")
    assert p10["zones"] == ["2", "1", "1", "2"]                        # θ 5.7° ≤ 7°: no ridge strip (user 2026-11-09)
    g1 = next(x for x in r["girts"] if x["id"] == "GA1")
    assert g1["zones"] == ["5", "4", "4", "5"]
    assert "NOT FOR ISSUE" in r["banner"]


# ---------------------------------------------------------------------------------------------- step 6 decisions (user, 2026-11-09)

def test_sag_rows_tied_off(b1_lines):
    from engine.design.cfs_checks import tied_rows
    out, lines = b1_lines
    ok, bad = tied_rows(out)
    assert ok == pytest.approx([3000.0, 9000.0, 15000.0, 21000.0]) and bad == []
    ln = next(x for x in lines if x["id"] == "RA3")
    assert {3000.0, 9000.0, 15000.0, 21000.0} <= set(round(v, 1) for v in ln["braces"])
    # negative control: without the ridge ties no row counts, and the purlins lose those brace points
    cut = {**out, "members": [m for m in out["members"] if m["role"] != "ridge_tie"]}
    ok, bad = tied_rows(cut)
    assert ok == [] and len(bad) == 4
    ln = next(x for x in building_lines(cut, LI) if x["id"] == "RA3")
    assert not ({3000.0, 9000.0} & set(round(v, 1) for v in ln["braces"]))
    # nor without the chain reaching the eave strut on one slope
    eave_y = {m["side"]: m["start"][1] for m in out["members"] if m["role"] == "eave_strut"}
    cut = {**out, "members": [m for m in out["members"] if not (m["role"] == "sag_rod" and m["side"] == "A"
                                                                and min(abs(m["start"][1] - eave_y["A"]), abs(m["end"][1] - eave_y["A"])) < 300)]}
    assert tied_rows(cut)[0] == []


def test_r_factor_limits_by_hand(b1_lines):
    from engine.design.cfs_checks import R_VERIFIED, r_factor
    out, lines = b1_lines
    ln = next(x for x in lines if x["id"] == "RA1")
    sd = section_data(ln["profile"], ln["grade"])
    rf = r_factor(ln, sd, tied_ok=True)
    assert R_VERIFIED is False and rf["VERIFIED"] is False
    assert rf["system"] == "continuous" and rf["R"] == 0.70 and rf["applicable_from_model"]
    vals = [c["value"] for c in rf["conditions"]]
    assert vals[:8] == [200.0, 20.0, 100.0, round(200 / 65, 3), (65 - 2 * (2 + 2)) / 2, 6000.0, 350.0, 600.0]   # lap 10 % of 6 m
    assert len(rf["to_confirm"]) == 4
    # a lap shorter than 1.5 d fails the limit → not applicable from the model
    short = {**ln, "laps": [(s - 250.0, s + 250.0) for s in ln["supports"][1:-1]]}
    assert not r_factor(short, sd, tied_ok=True)["applicable_from_model"]
    assert not r_factor(ln, sd, tied_ok=False)["applicable_from_model"]
    es = next(x for x in lines if x["id"] == "RA0-2")
    rf = r_factor(es, section_data(es["profile"], es["grade"]), tied_ok=True)
    assert rf["system"] == "simple" and rf["R"] == 0.65                 # C, 6.5 in < 200 mm ≤ 8.5 in


def test_r_factor_capacity_by_hand(b1_lines):
    from engine.design.cfs_checks import r_factor
    out, lines = b1_lines
    ln = dict(next(x for x in lines if x["id"] == "RA1"))
    sd = section_data(ln["profile"], ln["grade"])
    ln["rfactor"] = r_factor(ln, sd, tied_ok=True)
    strict = check_line(ln, sd, COMBOS_ROOF, 150)
    rfac = check_line(ln, sd, COMBOS_ROOF, 150, "r_factor")
    assert strict["uplift_method"] == "strict" and rfac["uplift_method"] == "r_factor"
    assert rfac["ratio"] < strict["ratio"]
    # Mnlo longhand: Mne = My, local curve
    My, Mcrl = sd["My"], sd["Mcrl"]
    Mnlo = (1 - 0.15 * (Mcrl / My) ** 0.4) * (Mcrl / My) ** 0.4 * My if math.sqrt(My / Mcrl) > 0.776 else My
    f = next(c for c in rfac["checks"] if c["name"].startswith("Flexure"))
    assert "R-factor" in f["note"]                                   # uplift governs, by the R-factor
    assert f["capacity"] == pytest.approx(0.9 * 0.70 * Mnlo / 1e6, abs=1e-3)
    # not applicable → the strict result exactly
    ln["rfactor"] = r_factor(ln, sd, tied_ok=False)
    assert check_line(ln, sd, COMBOS_ROOF, 150, "r_factor")["ratio"] == strict["ratio"]
    with pytest.raises(ValueError):
        check_line(ln, sd, COMBOS_ROOF, 150, "rfactor")
