# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 4 step 1: design inputs taken from the MODEL — plate strengths, design members, restraint points, and the one
moment-sign boundary into bimsteelauto's checks.

Plate strengths (VERIFIED False — each value carries its source; the user confirms against the printed standards):
    S275, S355        EN 10025-2 Table 7: ReH by thickness (≤ 16, ≤ 40 mm), Rm minimum (3 ≤ t ≤ 100 mm)
    A572 Gr 50        ASTM A572/A572M Table 2: Fy 345, Fu 450 MPa
    St 37, St 44, St 52  ECP 205-LRFD Table 1.1 (t ≤ 40, ≤ 100 mm), t/cm² × 98.0665 → MPa; values as transcribed in the
                      user's ecp-steel-code skill engine — to be replaced by the ecp205-lrfd library (Phase 4 step 7);
                      St 37 Fu 3.7 t/cm² there, Claude remembered 3.6: TO CONFIRM against the printed table
    S350GD            EN 10346: ReH 350, Rm 420 MPa (cold-formed)
    A built-up section's Fy = the LOWEST of its plates' (a thick flange may fall in a lower band) — stated, conservative.

Design members: a column (one analysis member), a rafter HALF (its analysis segments chained from the knee to the ridge —
splices are NOT brace points). Restraint points are distances along the design member's centroid chain from its start
(column base, rafter knee end), found by projecting the model's members onto the chain:
    outer flange ("top" of the section: rafter top flange, column outer flange)  — purlins, ridge purlin, eave strut;
                                                                                    girts on that wall
    inner flange ("bottom": rafter bottom flange, column inner flange)            — flange braces hosted by the member at
                                                                                    this frame line
    the member's ends are always brace points (bimsteelauto BracingSpec adds them).

Moment sign — THE boundary (CLAUDE.md: convert in exactly one function): PyNite's Mz is + for tension on the member's
LOCAL +y face (hogging + on a rafter; checked on a simply supported beam in tests). bimsteelauto design/members.py
takes Mz ≥ 0 as "top flange in compression" (sagging +) and passes PyNite's value through unchanged — on its own
pipeline that inverts the flange choice (finding 2026-11-08, reported to the user; bimsteelauto not modified).
bsa_moment() gives bimsteelauto the sign it expects, with PyNite's own local-y rule (an exactly vertical member's local
y is −X going up — a constant-depth column B would otherwise flip).
"""

from __future__ import annotations

import math

KGF = 98.0665            # MPa per t/cm²

# grade → list of (t_max mm, Fy MPa, Fu MPa, source)
GRADES: dict[str, list[tuple[float, float, float, str]]] = {
    "S275": [(16, 275, 410, "EN 10025-2 Tab. 7"), (40, 265, 410, "EN 10025-2 Tab. 7")],
    "S355": [(16, 355, 470, "EN 10025-2 Tab. 7"), (40, 345, 470, "EN 10025-2 Tab. 7")],
    "A572 Gr 50": [(100, 345, 450, "ASTM A572 Tab. 2")],
    "St 37": [(40, 2.40 * KGF, 3.70 * KGF, "ECP 205 Tab. 1.1 (skill transcription; Fu TO CONFIRM)"), (100, 2.15 * KGF, 3.40 * KGF, "ECP 205 Tab. 1.1")],
    "St 44": [(40, 2.80 * KGF, 4.40 * KGF, "ECP 205 Tab. 1.1"), (100, 2.55 * KGF, 4.10 * KGF, "ECP 205 Tab. 1.1")],
    "St 52": [(40, 3.60 * KGF, 5.20 * KGF, "ECP 205 Tab. 1.1"), (100, 3.35 * KGF, 4.90 * KGF, "ECP 205 Tab. 1.1")],
    "S350GD": [(4, 350, 420, "EN 10346")],
}
VERIFIED = {"GRADES": False, "restraints": False, "bsa_moment": False}


def plate_strength(grade: str, t: float) -> dict:
    if grade not in GRADES:
        raise ValueError(f"unknown steel grade {grade!r}; known: {', '.join(GRADES)}")
    for tmax, fy, fu, src in GRADES[grade]:
        if t <= tmax + 1e-9:
            return {"grade": grade, "t": t, "Fy": round(fy, 2), "Fu": round(fu, 2), "source": src}
    raise ValueError(f"{grade}: no strength listed for t = {t} mm (table stops at {GRADES[grade][-1][0]} mm) — give Fy / Fu explicitly")


def section_strength(seg: dict) -> dict:
    """Fy / Fu of a built-up segment: the lowest over its three plates."""
    plates = [("web", seg["tw"]), ("top flange", seg["tf_top"]), ("bottom flange", seg["tf_bot"])]
    rows = [(name, plate_strength(seg["grade"], t)) for name, t in plates]
    name, gov = min(rows, key=lambda r: r[1]["Fy"])
    return {"Fy": gov["Fy"], "Fu": min(r[1]["Fu"] for r in rows), "governed_by": f"{name} t = {gov['t']:g}", "source": gov["source"]}


# --------------------------------------------------------------------------------------------- design members and braces

def local_y(i, j) -> tuple[float, float]:
    """PyNite's local +y in the frame plane (Member3D.T) — the same rule as app/manafe3/frame-analysis.js localY."""
    dx, dy = j[0] - i[0], j[1] - i[1]
    L = math.hypot(dx, dy)
    if abs(dx) <= 1e-9 * L:
        return (-1.0, 0.0) if dy > 0 else (1.0, 0.0)
    nx, ny = -dy / L, dx / L
    return (-nx, -ny) if ny < 0 else (nx, ny)


def bsa_moment(i, j, top_normal, M: float) -> float:
    """PyNite Mz (+ = tension on local +y) → bimsteelauto Mz (+ = the section's TOP flange in compression).
    top_normal: the outward normal of the section's top face (rafter: up; column: out of the building)."""
    ly = local_y(i, j)
    s = 1.0 if ly[0] * top_normal[0] + ly[1] * top_normal[1] > 0 else -1.0
    return -s * M


def design_members(info) -> list[dict]:
    """The design members of a frame line (frame_model.FrameModelInfo), each a chain of analysis members."""
    lay = info.layout
    by_role: dict[str, list] = {}
    for m in lay.members:
        r = info.roles[m.mark]
        if r != "link":
            by_role.setdefault(r, []).append(m)
    out = []
    for role, ms in by_role.items():
        kind, side = role.split()
        if kind == "rafter":
            ms = sorted(ms, key=lambda m: int(m.mark[2:]))        # RA1 (at the knee), RA2, … toward the ridge
            top_n = (0.0, 1.0)
        else:
            top_n = (-1.0, 0.0) if side == "A" else (1.0, 0.0)     # the column's outer face
        chain, s0 = [], 0.0
        for m in ms:
            chain.append({"mark": m.mark, "i": m.i_point, "j": m.j_point, "s0": s0, "length": m.length})
            s0 += m.length
        out.append({"name": role, "kind": kind, "side": side, "id": info.marks[ms[0].mark], "chain": chain,
                    "length": s0, "top_normal": top_n})
    return out


def _project(chain: list[dict], p: tuple[float, float], tol: float) -> float | None:
    """Distance along the chain of point p's projection, if p lies beside the chain within tol (mm) of its line."""
    best = None
    for c in chain:
        (xi, yi), (xj, yj) = c["i"], c["j"]
        L = math.hypot(xj - xi, yj - yi)
        ux, uy = (xj - xi) / L, (yj - yi) / L
        t = (p[0] - xi) * ux + (p[1] - yi) * uy
        d = abs(-(p[0] - xi) * uy + (p[1] - yi) * ux)
        if -1e-6 <= t <= L + 1e-6 and d <= tol and (best is None or d < best[1]):
            best = (c["s0"] + min(max(t, 0.0), L), d)
    return None if best is None else best[0]


def restraints(out: dict, info, x_frame: float, tol: float = 1500.0) -> dict:
    """{design member name: {"top": [...], "bottom": [...], "length": L}} — mm along the chain, sorted, interior only
    (the ends are added by BracingSpec)."""
    dms = design_members(info)
    res = {d["name"]: {"top": set(), "bottom": set(), "length": d["length"], "sources": {"top": [], "bottom": []}} for d in dms}
    roof = ("purlin", "ridge_purlin", "eave_strut")
    for m in out["members"]:
        r = m["role"]
        if r in roof or r == "girt":
            if not (min(m["start"][0], m["end"][0]) - 1 <= x_frame <= max(m["start"][0], m["end"][0]) + 1):
                continue                                         # this piece does not cross the frame line
            side = m["side"]
            targets = [f"rafter {side}"] if r in roof else [f"column {side}"]
            face, p = "top", (m["start"][1], m["start"][2])
        elif r == "flange_brace":
            if abs(m["start"][0] - x_frame) > 1:
                continue
            targets, face, p = [m["host"]], "bottom", (m["start"][1], m["start"][2])
        else:
            continue
        for d in dms:
            if d["name"] not in targets:
                continue
            s = _project(d["chain"], p, tol)
            if s is not None and 1.0 < s < d["length"] - 1.0:
                res[d["name"]][face].add(round(s, 1))
                res[d["name"]]["sources"][face].append(m.get("id", r))
    return {k: {"top": sorted(v["top"]), "bottom": sorted(v["bottom"]), "length": round(v["length"], 1),
                "sources": {f: sorted(set(v["sources"][f])) for f in ("top", "bottom")}} for k, v in res.items()}
