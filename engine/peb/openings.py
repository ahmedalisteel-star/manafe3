# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Phase 2 step 6: framed openings (doors, windows). Geometry only, NOT designed.

User decision (2026-11-05): framed openings per wall — girts cut at the opening, C jambs + header (+ sill for windows).
Claude's set-out (flagged to the user, editable):
    an opening = { wall: A | B (side walls) | first | last (end walls), at: start along the wall (x on side walls, y on
    end walls), width, sill (0 = a door), height }
    * girt rows with sill < z < head are cut between the jambs; each new end gets 2 holes 40 mm from it (to the jamb's
      cleat); holes that fell in the opening go
    * jambs (C, the eave-strut section) at both sides, from the floor (doors) or the girt row at or below the sill
      (windows; the floor when there is none) to the first girt row at or above the head (the eave when there is none)
    * header (C) at the head and, for windows, a sill (C) at the sill, between the jambs — unless a girt row already sits
      at that height
    * jambs, header and sill lie in the girt plane, depth out of the building like the girts
"""

from __future__ import annotations

from .secondary import HOLE, LAP_END_EDGE, gauge

JAMB_ROT = {"A": 270.0, "B": 90.0, "first": 180.0, "last": 0.0}    # vertical members: depth out of the building


def _r(v: float) -> float:
    return round(v + 0.0, 3)


def _check(o: dict) -> None:
    if o["wall"] not in JAMB_ROT:
        raise ValueError("an opening's wall must be A, B, first or last")
    if not (o["width"] >= 300 and o["height"] >= 300 and o["sill"] >= 0):
        raise ValueError("an opening must be at least 300 × 300 mm, with its sill at 0 or above")


def apply_openings(girts: list[dict], openings: list[dict], eave: float, jamb: str = "C200x65x20x2.0", bolt: str = "M12") -> dict:
    """girts: wall girt pieces (secondary_members side-wall girts with side A/B, endwall gable girts with id G F… / G L…),
    each with start/end/holes. Returns the new girt list and the opening members."""
    d0 = HOLE[bolt]
    out_members = []
    pieces = list(girts)
    for n, o in enumerate(openings, 1):
        _check(o)
        wall, t0, t1, sill = o["wall"], o["at"], o["at"] + o["width"], o["sill"]
        head = sill + o["height"]
        if head >= eave and wall in ("A", "B"):
            raise ValueError(f"opening {n}: its head ({head:g}) must be under the eave ({eave:g})")
        ax = 0 if wall in ("A", "B") else 1
        mine = [p for p in pieces if _wall_of(p) == wall]
        if not mine:
            raise ValueError(f"opening {n}: wall {wall} has no girts")
        rows = sorted({p["start"][2] for p in mine})
        face = mine[0]["start"][1 - ax]                  # the girt line (y on side walls, x on end walls)
        g, rot = mine[0]["profile"], mine[0]["rotation"]
        kept = []
        for p in pieces:
            z = p["start"][2]
            ta, tb = sorted((p["start"][ax], p["end"][ax]))
            if _wall_of(p) != wall or not (sill < z < head) or tb <= t0 or ta >= t1:
                kept.append(p)
                continue
            for lo, hi in ((ta, min(tb, t0)), (max(ta, t1), tb)):
                if hi - lo > 2 * LAP_END_EDGE:
                    kept.append(_part(p, ax, lo, hi, t0, t1, gauge(p["profile"]), d0))
        pieces = kept
        z_lo = 0.0 if sill == 0 else max([r for r in rows if r <= sill] or [0.0])
        z_hi = min([r for r in rows if r >= head] or [eave])
        for t in (t0, t1):
            out_members.append(_member(f"O{n}-J{1 if t == t0 else 2}", "jamb", jamb, ax, face, t, t, z_lo, z_hi, JAMB_ROT[wall], vertical=True))
        if head not in rows:
            out_members.append(_member(f"O{n}-H", "header", jamb, ax, face, t0, t1, head, head, rot))
        if sill > 0 and sill not in rows:
            out_members.append(_member(f"O{n}-S", "sill", jamb, ax, face, t0, t1, sill, sill, rot))
    return {"girts": pieces, "members": out_members}


def _wall_of(p: dict) -> str:
    if p.get("role") == "gable_girt":
        return "first" if p["id"].startswith("GF") else "last"
    return p.get("side", "")


def _point(ax: int, face: float, t: float, z: float) -> list[float]:
    return [_r(t), _r(face), _r(z)] if ax == 0 else [_r(face), _r(t), _r(z)]


def _part(p: dict, ax: int, lo: float, hi: float, t0: float, t1: float, g: float, d0: float) -> dict:
    """The piece of girt p between lo and hi (t along the wall), in p's own direction, with its holes kept and 2 new
    holes 40 mm from each end that the opening made."""
    fwd = p["end"][ax] > p["start"][ax]
    s0 = p["start"][ax]
    world = [(s0 + h["x"] if fwd else s0 - h["x"], h) for h in p["holes"]]
    a, b = (lo, hi) if fwd else (hi, lo)                   # the new start and end, in p's direction
    def local(t):
        return t - a if fwd else a - t
    holes = [{**h, "x": _r(local(t))} for t, h in world if lo < t < hi]
    for cut, inward in ((t0, -1), (t1, 1)):                # a cut end: t0 is a right end, t1 a left end
        if lo - 1e-6 <= cut <= hi + 1e-6 and (cut == hi if inward < 0 else cut == lo):
            t = cut + inward * LAP_END_EDGE
            holes += [{"face": "web", "x": _r(local(t)), "y": _r(sy * g / 2), "d": d0} for sy in (-1, 1)]
    q = {**p, "id": p["id"] + ("a" if lo < t0 else "b"), "holes": sorted(holes, key=lambda h: (h["x"], h["y"])), "length": _r(hi - lo)}
    q["start"] = _point(ax, p["start"][1 - ax], a, p["start"][2])
    q["end"] = _point(ax, p["start"][1 - ax], b, p["start"][2])
    return q


def _member(mid, role, prof, ax, face, ta, tb, za, zb, rot, vertical=False):
    return {"id": mid, "role": role, "profile": prof, "start": _point(ax, face, ta, za), "end": _point(ax, face, tb, zb),
            "rotation": rot, "position": "bottom", "designed": False, "length": _r(abs(zb - za) if vertical else abs(tb - ta))}
