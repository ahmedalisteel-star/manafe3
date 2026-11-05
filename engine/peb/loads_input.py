# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Phase 3 step 1: the job's load inputs ("Loads…" form, kept in the model as state.m3loads).

Decisions (user, 2026-11-05):
    sheeting      single skin 0.07 kN/m², sandwich panel 0.12 kN/m² (50 mm PU, 0.5 / 0.5 mm facings), per m² of the SLOPING
                  roof / of wall; editable per job
    collateral    0.10 kN/m² per HORIZONTAL PLAN, its own load case "C": in every gravity combination, NOT in the uplift
                  combinations (LRFD 0.9D + 1.0W, ASD 0.6D + 0.6W)
    roof live     Lo = 0.96 kN/m², reduced by ASCE 7-16 §4.8 from each member's tributary area (bimsteelauto) — never typed
    wind          ASCE 7-16 Ch. 28 envelope (bimsteelauto loads/wind.py): V (m/s), exposure, enclosure, Kzt, risk category.
                  V and exposure have NO default — they are site facts; the run is refused until they are given
    combinations  ASCE 7-16 LRFD and ASD; strength results from LRFD, deflection and drift from ASD (labelled)
    bases         pinned by default, fixed as an option
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from bimsteelauto.spec import EnclosureClassification, ExposureCategory, ProjectSite, RiskCategory

CLADDING = {"single": 0.07, "sandwich": 0.12}   # kN/m², user decision 2026-11-05


@dataclass(frozen=True)
class LoadsInput:
    V: float | None = None                  # m/s, 3-s gust at 10 m, Exposure C (ASCE 7-16 Fig. 26.5-1) — required
    exposure: str | None = None             # "B" | "C" | "D" — required
    enclosure: str = "enclosed"             # "enclosed" | "partially_enclosed" | "partially_open" | "open"
    Kzt: float = 1.0
    risk: str = "II"
    roof_cladding: str = "single"           # "single" | "sandwich"
    roof_cladding_kpa: float | None = None  # None → the decision's value for the type
    wall_cladding: str = "single"
    wall_cladding_kpa: float | None = None
    collateral: float = 0.10                # kN/m² of plan
    Lo: float = 0.96                        # kN/m², unreduced roof live load
    base: str = "pinned"                    # "pinned" | "fixed"
    lrfd: bool = True
    asd: bool = True

    def check(self) -> None:
        p = []
        if self.V is None:
            p.append("basic wind speed V is required (a site fact; ASCE 7-16 Fig. 26.5-1 or the local code map)")
        elif not (10 <= self.V <= 100):
            p.append("basic wind speed V must be 10 to 100 m/s")
        if self.exposure not in ("B", "C", "D"):
            p.append("exposure category B, C or D is required (a site fact)")
        if self.enclosure not in [e.value for e in EnclosureClassification]:
            p.append("enclosure must be enclosed, partially_enclosed, partially_open or open")
        if not (1.0 <= self.Kzt <= 3.0):
            p.append("Kzt must be 1.0 to 3.0")
        if self.risk not in ("I", "II", "III", "IV"):
            p.append("risk category must be I, II, III or IV")
        for lab, kind, v in (("roof", self.roof_cladding, self.roof_cladding_kpa), ("wall", self.wall_cladding, self.wall_cladding_kpa)):
            if kind not in CLADDING:
                p.append(f"{lab} sheeting must be single or sandwich")
            if v is not None and not (0.0 <= v <= 2.0):
                p.append(f"{lab} sheeting load must be 0 to 2 kN/m²")
        if not (0.0 <= self.collateral <= 2.0):
            p.append("collateral must be 0 to 2 kN/m²")
        if not (0.0 < self.Lo <= 5.0):
            p.append("roof live load Lo must be above 0 and at most 5 kN/m²")
        if self.base not in ("pinned", "fixed"):
            p.append("bases must be pinned or fixed")
        if not (self.lrfd or self.asd):
            p.append("choose LRFD, ASD or both")
        if p:
            raise ValueError("; ".join(p))

    @property
    def roof_sheeting(self) -> float:
        return self.roof_cladding_kpa if self.roof_cladding_kpa is not None else CLADDING[self.roof_cladding]

    @property
    def wall_sheeting(self) -> float:
        return self.wall_cladding_kpa if self.wall_cladding_kpa is not None else CLADDING[self.wall_cladding]

    def site(self) -> ProjectSite:
        """bimsteelauto's site record (it checks its own ranges too)."""
        self.check()
        return ProjectSite(basic_wind_speed=self.V, exposure_category=ExposureCategory(self.exposure),
                           enclosure_classification=EnclosureClassification(self.enclosure),
                           risk_category=RiskCategory(self.risk), Kzt=self.Kzt)

    def summary(self) -> dict:
        self.check()
        s = self.site()
        return {**asdict(self), "roof_sheeting": self.roof_sheeting, "wall_sheeting": self.wall_sheeting,
                "Kd": s.Kd, "GCpi": list(s.GCpi), "sets": [x for x, on in (("LRFD", self.lrfd), ("ASD", self.asd)) if on]}
