# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Built-up (welded) I members: tapered or constant segments joined at splice points.

The section properties are bimsteelauto's (`bimsteelauto.sections.WeldedI` / `TaperedMember`): this module does not
re-derive them. What it adds is the Manafe3 member as the user types it:

* depths are the **web plate depth** hw (what the web is cut to). bimsteelauto works with the OVERALL depth
  d = hw + tf_top + tf_bot; the conversion happens only in `Segment.welded_i`.
* a member is a list of **segments** (column, haunch, rafter …). Inside a segment only the web depth varies, linearly
  (bimsteelauto's taper convention); flanges, web thickness and grade are constant. A change of plates = a new segment.
* at every **splice** (segment boundary) the two segments must have the same web depth and the same top and bottom
  flange widths (user decision 2026-11-05); thicknesses may change.
* shop minimums: web 6 mm, flange 8 mm.

Units: mm, mm², mm³, mm⁴. x is measured along the member's line from its start.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from bimsteelauto.sections import SectionError, TaperedMember, WeldedI

MIN_WEB_T = 6.0
MIN_FLANGE_T = 8.0
GRADES = ("S275", "S355", "A572 Gr 50", "St 37", "St 44", "St 52")
STRAIGHT = ("top", "bottom", "centre")   # which flange lies on the member's line (PEB standard per role; see frame.py)
STEEL_DENSITY = 7850.0                   # kg/m³
_TOL = 1e-6                              # mm


class BuiltUpError(ValueError):
    """A built-up member that cannot be made; the message says which segment or splice and why."""


@dataclass(frozen=True)
class Segment:
    length: float
    hw_start: float          # web plate depth at the segment start, mm
    hw_end: float            # web plate depth at the segment end, mm
    tw: float
    bf_top: float
    tf_top: float
    bf_bot: float
    tf_bot: float
    grade: str = "S355"
    straight: str = "top"

    def check(self, label: str) -> None:
        p = []
        if not (self.length > 0):
            p.append(f"length must be positive ({self.length})")
        for n in ("hw_start", "hw_end", "bf_top", "bf_bot"):
            if not (getattr(self, n) > 0):
                p.append(f"{n} must be positive ({getattr(self, n)})")
        if self.tw < MIN_WEB_T:
            p.append(f"web {self.tw} mm is under the shop minimum {MIN_WEB_T:g} mm")
        for n in ("tf_top", "tf_bot"):
            if getattr(self, n) < MIN_FLANGE_T:
                p.append(f"{'top' if n == 'tf_top' else 'bottom'} flange {getattr(self, n)} mm is under the shop minimum {MIN_FLANGE_T:g} mm")
        for n in ("bf_top", "bf_bot"):
            if getattr(self, n) > 0 and getattr(self, n) <= self.tw:
                p.append(f"{n} {getattr(self, n)} must be wider than the web {self.tw}")
        if self.grade not in GRADES:
            p.append(f"grade {self.grade!r} is not one of {', '.join(GRADES)}")
        if self.straight not in STRAIGHT:
            p.append(f"straight flange {self.straight!r} must be top, bottom or centre")
        if p:
            raise BuiltUpError(f"{label}: " + "; ".join(p))

    def welded_i(self, hw: float) -> WeldedI:
        """bimsteelauto's section for web plate depth hw (overall d = hw + tf_top + tf_bot)."""
        return WeldedI(d=hw + self.tf_top + self.tf_bot, tw=self.tw,
                       bf_top=self.bf_top, tf_top=self.tf_top, bf_bot=self.bf_bot, tf_bot=self.tf_bot)

    def tapered(self) -> TaperedMember:
        return TaperedMember(start=self.welded_i(self.hw_start), end=self.welded_i(self.hw_end), length=self.length)

    def hw_at(self, x: float) -> float:
        return self.hw_start + (self.hw_end - self.hw_start) * x / self.length


@dataclass(frozen=True)
class BuiltUpMember:
    segments: tuple[Segment, ...]

    def __post_init__(self) -> None:
        if not self.segments:
            raise BuiltUpError("a built-up member needs at least one segment")
        for i, s in enumerate(self.segments):
            s.check(f"segment {i + 1}")
        for i in range(len(self.segments) - 1):
            a, b = self.segments[i], self.segments[i + 1]
            where = f"splice {i + 1} (segment {i + 1} | segment {i + 2})"
            if abs(a.hw_end - b.hw_start) > _TOL:
                raise BuiltUpError(f"{where}: web depths differ ({a.hw_end:g} | {b.hw_start:g} mm); a splice joins equal webs")
            if abs(a.bf_top - b.bf_top) > _TOL:
                raise BuiltUpError(f"{where}: top flange widths differ ({a.bf_top:g} | {b.bf_top:g} mm)")
            if abs(a.bf_bot - b.bf_bot) > _TOL:
                raise BuiltUpError(f"{where}: bottom flange widths differ ({a.bf_bot:g} | {b.bf_bot:g} mm)")
        for s in self.segments:
            try:
                s.tapered()
            except SectionError as e:   # bimsteelauto's own refusal, passed on with its words
                raise BuiltUpError(str(e)) from e

    @classmethod
    def from_dicts(cls, rows: list[dict]) -> "BuiltUpMember":
        return cls(tuple(Segment(**r) for r in rows))

    @property
    def length(self) -> float:
        return sum(s.length for s in self.segments)

    @property
    def splices(self) -> list[float]:
        """x of each splice along the member."""
        out, x = [], 0.0
        for s in self.segments[:-1]:
            x += s.length
            out.append(x)
        return out

    def locate(self, x: float) -> tuple[int, float]:
        """(segment index, x inside it). A splice belongs to the segment that STARTS there; the member end to the last."""
        if not (-_TOL <= x <= self.length + _TOL):
            raise BuiltUpError(f"x = {x:g} mm is outside the member (0 to {self.length:g} mm)")
        x0 = 0.0
        for i, s in enumerate(self.segments):
            if x < x0 + s.length - _TOL or i == len(self.segments) - 1:
                return i, min(max(x - x0, 0.0), s.length)
            x0 += s.length
        raise AssertionError("unreachable")

    def section_at(self, x: float) -> WeldedI:
        i, xs = self.locate(x)
        return self.segments[i].tapered().at(xs)

    def properties_at(self, x: float) -> dict:
        i, xs = self.locate(x)
        seg = self.segments[i]
        s = seg.tapered().at(xs)
        return {
            "x": x, "segment": i + 1, "hw": seg.hw_at(xs), "d": s.d,
            "A": s.A, "Ix": s.Ix, "Iy": s.Iy, "Zx": s.Zx,
            "Sx_top": s.Sx_top, "Sx_bot": s.Sx_bot, "Sx": min(s.Sx_top, s.Sx_bot),
            "y_bar": s.y_bar, "mass_per_m": s.A * 1e-6 * STEEL_DENSITY,
        }

    def stations(self, n_per_segment: int = 4) -> list[float]:
        """Ends and splices plus n-1 evenly spaced points inside each segment."""
        xs, x0 = [], 0.0
        for s in self.segments:
            xs += [x0 + s.length * k / n_per_segment for k in range(n_per_segment)]
            x0 += s.length
        return xs + [x0]

    def mass_axis(self) -> float:
        """kg, ∫ A dx along the member's line × 7850. Exact for linear tapers (A linear in hw). Plate weights by plate
        outline (a sloping flange is a little longer than its segment) are the app's BOM, step 3."""
        return sum(s.tapered().weight for s in self.segments)

    def to_dicts(self) -> list[dict]:
        return [asdict(s) for s in self.segments]
