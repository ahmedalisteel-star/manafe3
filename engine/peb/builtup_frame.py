# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 1 portal frame with welded built-up members: tapered columns, a haunch at the knee, rafters. NOT a design.

Sizes come from span rules (user decision 2026-11-05, HANDOVER.md "Phase 1 plan"); every one can be overridden from the
form, and every member carries `designed: False` until Phases 3-4:
    knee web depth   hw_knee   = span / 30, rounded UP to 50 mm                     (24 m → 800)
    rafter web depth hw_rafter = max(300, 0.5 · hw_knee)                             (24 m → 400)
    column           one tapered segment, web 300 at the base → hw_knee at the eave
    haunch           span / 10 long (along the rafter) from the column face, web hw_knee → hw_rafter (equal webs at the splice)
    rafter           hw_rafter, constant to the ridge; split into equal segments when longer than 12 m (transport)
    flanges          span ≤ 20 m 200×10, ≤ 30 m 250×12, else 300×16 — the same plates on every member (splice rule)
    web thickness    6 mm if the segment's deepest web ≤ 600 mm, else 8 mm;  grade S355
Geometry (Manafe3 axes: X along the building, Y across the span, Z up; mm):
    column lines A (y = 0) and B (y = span) are the columns' OUTER flange faces; "straight top" with the column turned so
    the section hangs into the building (rotation 270 on A, 90 on B); the column top follows the roof line (end cut −slope)
    the eave height is where the roof line meets the outer column face; the roof line is the rafters' top flange face
    a rafter starts at its column's inner flange face at the eave and ends at the apex; both ends are cut plumb (end cut
    = slope, vertical faces) — splices and the knee/ridge connections are points only until Phase 5
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

from ..sections.builtup import BuiltUpMember

MAX_SEGMENT = 12000.0   # transport length, mm


@dataclass(frozen=True)
class BuiltUpSizes:
    hw_knee: float
    hw_base: float
    hw_rafter: float
    haunch_length: float
    bf: float
    tf: float
    grade: str = "S355"


def default_sizes(span: float) -> BuiltUpSizes:
    hw_knee = math.ceil(span / 30.0 / 50.0) * 50.0
    bf, tf = (200.0, 10.0) if span <= 20000 else (250.0, 12.0) if span <= 30000 else (300.0, 16.0)
    return BuiltUpSizes(hw_knee=hw_knee, hw_base=300.0, hw_rafter=max(300.0, 0.5 * hw_knee), haunch_length=span / 10.0, bf=bf, tf=tf)


def web_t(hw_max: float) -> float:
    return 6.0 if hw_max <= 600 else 8.0


def _r(v: float) -> float:
    return round(v + 0.0, 3)


def _seg(length: float, hw0: float, hw1: float, z: BuiltUpSizes) -> dict:
    return dict(length=_r(length), hw_start=_r(hw0), hw_end=_r(hw1), tw=web_t(max(hw0, hw1)),
                bf_top=z.bf, tf_top=z.tf, bf_bot=z.bf, tf_bot=z.tf, grade=z.grade, straight="top")


def _split(length: float, hw: float, z: BuiltUpSizes) -> list[dict]:
    n = max(1, math.ceil(length / MAX_SEGMENT - 1e-9))
    return [_seg(length / n, hw, hw, z) for _ in range(n)]


def _taper_split(length: float, hw0: float, hw1: float, z: BuiltUpSizes) -> list[dict]:
    """A tapered run cut into equal segments no longer than 12 m (the web stays linear: equal webs at each splice)."""
    n = max(1, math.ceil(length / MAX_SEGMENT - 1e-9))
    return [_seg(length / n, hw0 + (hw1 - hw0) * i / n, hw0 + (hw1 - hw0) * (i + 1) / n, z) for i in range(n)]


def builtup_frame_members(span: float, eave: float, slope: float, x: float, line: str, z: BuiltUpSizes) -> list[dict]:
    """The four members of one frame line at x."""
    d_top = z.hw_knee + 2 * z.tf                       # column overall depth at the eave
    y0 = d_top                                         # rafter A starts at column A's inner face
    z0 = eave + slope * y0
    apex = (x, span / 2.0, eave + slope * span / 2.0)
    rafter_len = math.hypot(span / 2.0 - y0, apex[2] - z0)
    if z.haunch_length >= rafter_len:
        raise ValueError(f"the haunch ({z.haunch_length:g} mm) must be shorter than the rafter ({rafter_len:.0f} mm)")
    col_segs = _taper_split(eave, z.hw_base, z.hw_knee, z)
    raf_segs = [_seg(z.haunch_length, z.hw_knee, z.hw_rafter, z)] + _split(rafter_len - z.haunch_length, z.hw_rafter, z)
    out = []
    for side, y_col, rot, y_raf in (("A", 0.0, 270.0, y0), ("B", span, 90.0, span - y0)):
        out.append(dict(id=f"F{line}-C{side}", role="column", frame_line=line, side=side, rotation=rot,
                        start=[_r(x), _r(y_col), 0.0], end=[_r(x), _r(y_col), _r(eave)],
                        section=dict(segments=col_segs, cut_start=0.0, cut_end=_r(-slope))))
        out.append(dict(id=f"F{line}-R{side}", role="rafter", frame_line=line, side=side, rotation=0.0,
                        start=[_r(x), _r(y_raf), _r(z0)], end=[_r(c) for c in apex],
                        section=dict(segments=raf_segs, cut_start=_r(slope), cut_end=_r(slope))))
    for m in out:
        BuiltUpMember.from_dicts(m["section"]["segments"])   # the splice and minimum rules, or a plain refusal
        m.update(material=z.grade, designed=False, profile=mark(m["section"]["segments"]))
    return out


def mark(segs: list[dict]) -> str:
    hws = [v for s in segs for v in (s["hw_start"], s["hw_end"])]
    s = segs[0]
    depth = f"{min(hws):g}" if min(hws) == max(hws) else f"{min(hws):g}-{max(hws):g}"
    more = f" +{len(segs) - 1}" if len(segs) > 1 else ""
    return f"BU {depth}x{s['tw']:g} {s['bf_top']:g}x{s['tf_top']:g}/{s['bf_bot']:g}x{s['tf_bot']:g}{more}"


def sizes_dict(z: BuiltUpSizes) -> dict:
    return asdict(z)
