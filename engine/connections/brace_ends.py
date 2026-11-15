# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 5 step 5b: the brace ends — rod X-braces through the frame web with a hillside washer and nut. NOT FOR ISSUE.
SI: mm, kN, MPa.

The user's decisions (2026-11-15, step 5b: 1a–6a, 7b, 8a, 9a):
    detail     the rod passes through a round hole in the host's web (hole d + 6: 26 mm for RD20, to allow the skew), a
               hillside washer (RD20: bearing face 60 mm OD, 12 mm thick) and a nut (ISO 4032 grade 8) on the far face —
               all settings, in "Unverified sources". Where the model puts the hole: roof braces 75 mm below the rafter's
               top flange (bracing.ROOF_BRACE_BELOW), wall / end-wall braces at the column's mid-depth; a wall brace that
               the model ends at the base (z = 0) passes through the column web base_hole_height (150 mm) above the base
               plate (user 2026-11-15).
    force      the analysis tension T alone (the step 1 rule for braces), split by the rod's angle to the web: the normal
               component Tn = T |u·n| goes through the washer into the web face; the in-plane component Tp = T √(1 − (u·n)²)
               is taken by the rod bearing on the hole edge — and so is a shear on the rod's threads.
    checks     rod     thread tension with that shear, AISC 360-16 J3.7 (J3-3a), the rod as a threaded part: Fnt = 0.75 Fu,
                       Fnv = 0.450 Fu (threads included, Table J3.2), Ab = the nominal body, φ 0.75; Fu by the rod's
                       diameter (the grade bands Phase 4 uses). The plain thread tension and the body yield are Phase 4's
                       member check (secondary_checks) — not repeated here.
               web at the washer   punching shear φ 0.75 × 0.6 Fu π D_washer tw (Claude's rule) and the washer's bearing
                       J7 φ 0.75 × 1.8 Fy Apb, Apb = π (D_washer² − d_hole²) / 4 (Claude's use of J7)
               web at the hole     bearing / tear-out J3.10 (pyaisc360) for Tp, the rod as the bolt, lc in the direction
                       of Tp (the rod pulls the hole toward its far end) to the nearer flange's inside face or member end,
                       minus d_hole / 2 (the member end counted as a free edge: conservative)
               the member's net section at the hole (user addition, 4a)   at the hole's station, every LRFD combination
                       of the frame line: the elastic net-section stress |P| / An + |M| c / In ≤ 0.9 Fy (the hole removed
                       from the web, In about the net centroid) and the net-web shear rupture φ 0.75 × 0.6 Fu (hw − d_hole)
                       tw ≥ |V|; the brace's in-plane components added to EVERY combination in the adverse sense
                       (conservative envelope — the frame lines do not carry the longitudinal case): axial T |u·a|, shear
                       T |u·dvec|, and the axial part's moment about the net centroid T |u·a| × |y_hole − y_c|.
    angles     NOT EVALUATED with the reason — the gusset (check_gusset + AISC D3 Table D3.1 U) is HANDOVER open item 10.
    status     DESIGNED / FAILS (with the fixes) / NOT EVALUATED; a brace end with any check not evaluated reads PARTIAL
               (never DESIGNED). The rod's weak-axis push on the host (Tn) is the eave transfer (step 5d), not here.
"""

from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass, field

from bimsteelauto_connections.bolts import get_grade

from ..design.inputs import plate_strength
from ..peb.bracing import ROOF_BRACE_BELOW
from .cleats import _host_at, hole_strength

BANNER = "NOT FOR ISSUE — brace ends (Phase 5 step 5b); hole / washer / nut sizes and Claude's rules VERIFIED False"
DESIGNED, FAILS, NOT_EVALUATED, PARTIAL = "DESIGNED", "FAILS", "NOT EVALUATED", "PARTIAL"
PHI = 0.75
VERIFIED = {"hole_washer_nut_sizes": False, "punching_rule": False, "j7_washer_bearing": False, "force_split": False,
            "net_section_envelope": False, "base_hole_height": False, "fnv_0_45_fu": False}
FIXES = {
    "rod": "a larger rod (RD24) or a higher rod grade",
    "web": "a thicker web locally (a reinforcing plate around the hole) or a larger washer",
    "net": "a thicker web or move the hole (closer to the section's centroid)",
}
ANGLE_NOTE = "angle brace: the gusset (check_gusset + AISC D3 Table D3.1 U from the bolt count) is HANDOVER open item 10"


@dataclass
class BraceEndSettings:
    """Every default the brace ends use — editable per job, listed on each result (sizes: Unverified sources)."""
    hole_extra: float = 6.0                                    # hole = rod d + this (26 mm for RD20)
    washers: dict = field(default_factory=lambda: {20.0: (60.0, 12.0)})   # rod d → (bearing-face OD, thickness), hillside
    nut: str = "ISO 4032 grade 8"
    base_hole_height: float = 150.0                            # a wall brace ending at the base: hole height above the plate
    max_angle_from_normal: float = 60.0                        # beyond it the hillside washer cannot seat → NOT EVALUATED

    def check(self) -> "BraceEndSettings":
        for k in ("hole_extra", "base_hole_height", "max_angle_from_normal"):
            v = getattr(self, k)
            if not (isinstance(v, (int, float)) and v > 0):
                raise ValueError(f"{k} must be > 0")
        if not self.max_angle_from_normal < 90.0:
            raise ValueError("max_angle_from_normal must be below 90°")
        self.washers = {float(k): (float(v[0]), float(v[1])) for k, v in self.washers.items()}
        return self

    @classmethod
    def from_dict(cls, d: dict | None) -> "BraceEndSettings":
        d = dict(d or {})
        bad = set(d) - set(cls.__dataclass_fields__)
        if bad:
            raise ValueError(f"unknown brace-end settings: {', '.join(sorted(bad))}")
        return cls(**d).check()


# ------------------------------------------------------------------------------------------------------- vectors

def _unit(v):
    L = math.sqrt(sum(c * c for c in v))
    return [c / L for c in v]


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]


def web_normal(host: dict) -> list[float]:
    """The web normal of a host: frame columns / rafters / end rafters lie in the frame plane (normal X); a wind column's
    depth runs across the end wall (along X), so its web is in the XZ plane (normal Y)."""
    return [0.0, 1.0, 0.0] if host["role"] == "wind_column" else [1.0, 0.0, 0.0]


def force_split(T: float, u, n) -> dict:
    """Tn (through the washer, normal to the web) and Tp (in the web plane, on the hole edge), kN."""
    c = abs(_dot(u, n))
    return {"cos": c, "angle_from_normal": math.degrees(math.acos(min(1.0, c))), "Tn": T * c,
            "Tp": T * math.sqrt(max(0.0, 1.0 - c * c))}


# ------------------------------------------------------------------------------------------------------- checks

def rod_rows(T: float, Tp: float, d: float, Fu: float) -> list[tuple]:
    """J3.7 on the rod's threads: φRnt = 0.75 × 0.75 Fu Ab, φRnv = 0.75 × 0.45 Fu Ab, φRnt' = min(φRnt, 1.3 φRnt −
    φRnt Tp / φRnv)."""
    Ab = math.pi * d * d / 4.0
    rt = PHI * 0.75 * Fu * Ab / 1000.0
    rv = PHI * 0.45 * Fu * Ab / 1000.0
    cap = min(rt, 1.3 * rt - rt * Tp / rv)
    return [("rod", "rod threads: tension with the in-plane shear", "AISC 360-16 J3.7 (J3-3a), Table J3.2", T, cap,
             T / cap if cap > 0 else math.inf),
            ("rod", "rod threads: shear (in-plane component)", "AISC 360-16 J3.6, Table J3.2", Tp, rv, Tp / rv)]


def washer_rows(Tn: float, Dw: float, d_hole: float, tw: float, Fy: float, Fu: float) -> list[tuple]:
    punch = PHI * 0.6 * Fu * math.pi * Dw * tw / 1000.0
    Apb = math.pi * (Dw * Dw - d_hole * d_hole) / 4.0
    brg = PHI * 1.8 * Fy * Apb / 1000.0
    return [("web", "web punching shear around the washer", "Claude's rule: φ 0.75 × 0.6 Fu π D tw", Tn, punch, Tn / punch),
            ("web", "washer bearing on the web", "AISC 360-16 J7 (Claude's use)", Tn, brg, Tn / brg)]


def hole_rows(Tp: float, d: float, lc: float, tw: float, Fu: float) -> list[tuple]:
    c = hole_strength(d, lc, tw, Fu)
    return [("web", "web bearing / tear-out at the hole", "AISC 360-16 J3.10", Tp, c, Tp / c if c > 0 else math.inf)]


def net_section(sec: dict, y_hole: float, d_hole: float) -> dict:
    """An, the net centroid y_c (from the bottom face), In, c_max of a built-up I with a d_hole hole in the web at y_hole
    (from the bottom face), mm units."""
    bt, tt, bb, tb, hw, tw = sec["bf_top"], sec["tf_top"], sec["bf_bot"], sec["tf_bot"], sec["hw"], sec["tw"]
    d = hw + tt + tb
    parts = [(bt * tt, d - tt / 2, bt * tt ** 3 / 12), (hw * tw, tb + hw / 2, tw * hw ** 3 / 12),
             (bb * tb, tb / 2, bb * tb ** 3 / 12), (-d_hole * tw, y_hole, -tw * d_hole ** 3 / 12)]
    A = sum(a for a, _, _ in parts)
    yc = sum(a * y for a, y, _ in parts) / A
    I = sum(i + a * (y - yc) ** 2 for a, y, i in parts)
    return {"A": A, "yc": yc, "I": I, "c": max(yc, d - yc), "d": d}


def net_rows(stations: list[tuple], add: dict, sec: dict, y_hole: float, d_hole: float, Fy: float, Fu: float) -> list[tuple]:
    """stations: [(combo, P, V, M)] at the hole (kN, kN·m); add: the brace components {P, V, M} (kN, kN·m) added adversely."""
    ns = net_section(sec, y_hole, d_hole)
    shear_cap = PHI * 0.6 * Fu * (sec["hw"] - d_hole) * sec["tw"] / 1000.0
    best_s, best_v = None, None
    for combo, P, V, M in ((c_, float(P_), float(V_), float(M_)) for c_, P_, V_, M_ in stations):
        Pt, Vt, Mt = abs(P) + add["P"], abs(V) + add["V"], abs(M) + add["M"]
        sig = Pt * 1000.0 / ns["A"] + Mt * 1e6 * ns["c"] / ns["I"]
        if best_s is None or sig > best_s[1]:
            best_s = (combo, sig)
        if best_v is None or Vt > best_v[1]:
            best_v = (combo, Vt)
    return [("net", "member net section at the hole: |P|/An + |M| c/In", "AISC 360-16 (elastic, Claude's method 4a)",
             best_s[1], 0.9 * Fy, best_s[1] / (0.9 * Fy), best_s[0]),
            ("net", "member net web shear rupture at the hole", "AISC 360-16 J4.2(b) form", best_v[1], shear_cap,
             best_v[1] / shear_cap, best_v[0])]


def edge_lc(p, a, dvec, to_top: float, to_bot: float, s: float, L: float, d_hole: float) -> float:
    """lc of the hole in the direction p (unit, in the web plane): to the nearer flange's inside face (to_top along +dvec,
    to_bot along −dvec) or member end (s from the start along a, L − s to the end), minus d_hole / 2."""
    ds = []
    pd, pa = _dot(p, dvec), _dot(p, a)
    if pd > 1e-9:
        ds.append(to_top / pd)
    elif pd < -1e-9:
        ds.append(to_bot / -pd)
    if pa > 1e-9:
        ds.append((L - s) / pa)
    elif pa < -1e-9:
        ds.append(s / -pa)
    return (min(ds) if ds else math.inf) - d_hole / 2


def stations_at(fres: dict, mid: str, s: float) -> list[tuple] | None:
    """[(combo, P, V, M)] at distance s along one Manafe3 member of a frame result (LRFD; the sub-members joined; linear
    between stations)."""
    marks = [m for m in fres["members"] if m["id"] == mid]
    if not marks:
        return None
    out = []
    for name, r in fres["results"].items():
        if r.get("set") != "LRFD":
            continue
        rows, off = [], 0.0
        for m in marks:
            for x, P, V, M in r["members"][m["mark"]]:
                rows.append((off + x, P, V, M))
            off += m["length"]
        rows.sort()
        if not rows:
            continue
        if s <= rows[0][0]:
            out.append((name, *rows[0][1:]))
            continue
        if s >= rows[-1][0]:
            out.append((name, *rows[-1][1:]))
            continue
        for r0, r1 in zip(rows, rows[1:]):
            if r0[0] <= s <= r1[0]:
                f = 0.0 if r1[0] == r0[0] else (s - r0[0]) / (r1[0] - r0[0])
                out.append((name, *(r0[k] + f * (r1[k] - r0[k]) for k in (1, 2, 3))))
                break
    return out


# ------------------------------------------------------------------------------------------------------- the building

def _row_dict(r):
    key, name, ref, dem, cap, U = r[:6]
    dem, cap, U = float(dem), float(cap), float(U)
    return {"name": name, "ref": ref, "key": key, "demand": round(dem, 3), "capacity": round(cap, 3),
            "U": round(U, 4) if math.isfinite(U) else math.inf, **({"combo": r[6]} if len(r) > 6 else {})}


def building_brace_ends(joints_result: dict, out: dict, analysis: dict, settings: BraceEndSettings | None = None) -> dict:
    """Every brace_end joint of a building_joints() result (its forces: the analysis tension) → checked brace ends."""
    from .welds import _frame_result

    st = (settings or BraceEndSettings()).check()
    mem = {m["id"]: m for m in out["members"] if m.get("id")}
    res = []
    for j in joints_result["joints"]:
        if j["type"] != "brace_end":
            continue
        b = mem[j["members"][0]["id"]]
        rec = {"joint": j["id"], "brace": b["id"], "role": b["role"], "profile": b["profile"], "status": NOT_EVALUATED}
        if b["profile"].startswith("L"):
            res.append({**rec, "missing": [ANGLE_NOTE]})
            continue
        m = re.fullmatch(r"RD(\d+(?:\.\d+)?)", b["profile"])
        missing = []
        if not m:
            missing.append(f"brace profile {b['profile']!r} (rods RD<d>)")
        hosts = [x for x in j["members"][1:] if "distance" in x]
        if not hosts:
            missing.append("host member")
        T = (j.get("forces") or {}).get("tension")
        if T is None:
            missing.append("brace tension (analysis)")
        if missing:
            res.append({**rec, "missing": missing})
            continue
        d = float(m[1])
        d_hole = d + st.hole_extra
        hm = mem[hosts[0]["id"]]
        p0 = list(j["point"])
        base_end = hm["role"] in ("column", "wind_column") and p0[2] < 1.0
        if base_end:
            p0[2] = st.base_hole_height
        host = _host_at(hm, p0)
        if host is None:
            res.append({**rec, "missing": ["host section / grade"]})
            continue
        far = b["end"] if math.dist(b["start"], j["point"]) < math.dist(b["end"], j["point"]) else b["start"]
        u = _unit([far[i] - p0[i] for i in range(3)])         # the rod pulls the host toward its far end
        n = web_normal(hm)
        a = _unit([hm["end"][i] - hm["start"][i] for i in range(3)])
        dvec = _unit(_cross(n, a))
        if dvec[2] < 0:
            dvec = [-c for c in dvec]
        sp = force_split(T, u, n)
        rec.update(T=T, host=hm["id"], host_role=hm["role"], split={k: round(v, 4) for k, v in sp.items()},
                   hole={"d_hole": d_hole, "at_base_height": st.base_hole_height if base_end else None})
        if sp["angle_from_normal"] > st.max_angle_from_normal:
            res.append({**rec, "missing": [f"the rod runs {sp['angle_from_normal']:.1f}° from the web normal (> "
                                            f"{st.max_angle_from_normal:g}°): a through-web hillside detail does not apply "
                                            "— a gusset / lug is needed"]})
            continue
        sec = host["sec"]
        try:
            Fu_rod = plate_strength(b.get("material", ""), d)["Fu"]
        except ValueError:
            Fu_rod = None
        Fy_w, Fu_w = get_grade(host["grade"], host["tw"])
        rows, notes = [], []
        if Fu_rod is None:
            notes.append(f"rod grade {b.get('material')!r} unknown: the rod checks NOT EVALUATED")
        else:
            rows += rod_rows(T, sp["Tp"], d, Fu_rod)
        wsh = st.washers.get(d)
        if wsh is None:
            notes.append(f"no hillside washer size for RD{d:g} in the settings: the washer checks NOT EVALUATED")
        else:
            rows += washer_rows(sp["Tn"], wsh[0], d_hole, host["tw"], Fy_w, Fu_w)
        # where the hole is in the depth: roof braces below the top flange, wall / end-wall braces at mid-depth
        if b["role"] == "roof_brace":
            to_top, to_bot = ROOF_BRACE_BELOW, sec["hw"] - ROOF_BRACE_BELOW
            y_hole = sec["d"] - sec["tf_top"] - ROOF_BRACE_BELOW
        else:
            to_top = to_bot = sec["hw"] / 2
            y_hole = sec["tf_bot"] + sec["hw"] / 2
        ip = [u[i] - _dot(u, n) * n[i] for i in range(3)]
        p = _unit(ip) if math.sqrt(_dot(ip, ip)) > 1e-9 else [0.0, 0.0, 0.0]
        lc = edge_lc(p, a, dvec, to_top, to_bot, host["s"], host["L"], d_hole)
        rows += hole_rows(sp["Tp"], d, lc, host["tw"], Fu_w)
        # the member's net section at the hole
        ns_rows = None
        if hm["role"] in ("column", "rafter"):
            fres, pref = _frame_result(analysis, hm["start"][0])
            mid_src = None if pref is None else pref + hm["id"].split("-", 1)[1]
            sts = stations_at(fres, mid_src, host["s"]) if fres else None
            if sts:
                ns = net_section(sec, y_hole, d_hole)
                Pa = T * abs(_dot(u, a))
                add = {"P": Pa, "V": T * abs(_dot(u, dvec)), "M": Pa * abs(y_hole - ns["yc"]) / 1000.0}
                ns_rows = net_rows(sts, add, sec, y_hole, d_hole, host["Fy"], get_grade(host["grade"], min(sec["tf_top"], sec["tf_bot"]))[1])
                rec["net_section"] = {"y_hole": round(y_hole, 1), "An": round(ns["A"], 1), "In": round(ns["I"], 0),
                                      "yc": round(ns["yc"], 2), "brace_added": {k: round(v, 3) for k, v in add.items()}}
        if ns_rows is None:
            notes.append("the member's net section at the hole NOT EVALUATED: no frame-line stations for this host "
                         "(wind columns / end rafters are not wired in step 5b)")
        else:
            rows += ns_rows
        checks = sorted((_row_dict(r) for r in rows), key=lambda r: -r["U"])
        bad = [r for r in checks if r["U"] > 1.0]
        status = FAILS if bad else (PARTIAL if notes else DESIGNED)
        rec.update(lc=round(lc, 1), checks=checks, status=status, notes=notes,
                   governing={k: checks[0][k] for k in ("name", "U")} if checks else None,
                   fixes=sorted({f"{r['name']}: {FIXES[r['key']]}" for r in bad}),
                   materials={"rod": {"grade": b.get("material"), "Fu": Fu_rod},
                              "web": {"grade": host["grade"], "t": host["tw"], "Fy": Fy_w, "Fu": Fu_w}})
        res.append(rec)
    counts: dict[str, int] = {}
    for r in res:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    return {"banner": BANNER, "designed": False, "settings": {**asdict(st), "washers": {str(k): v for k, v in st.washers.items()}},
            "verified": dict(VERIFIED), "brace_ends": res, "counts": counts}
