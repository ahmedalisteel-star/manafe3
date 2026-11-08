# Manafe3 engine. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Components and cladding (C&C) wall pressures, ASCE 7-16 Ch. 30 Part 1 (low-rise, h ≤ 60 ft) — for wind columns now,
girts and purlins later (user decision 2026-11-08).

    p = qh · [(GCp) − (GCpi)]                                   Eq. 30.3-1; qh from bimsteelauto (Ch. 26, Kd 0.85)
    GCp, walls, Fig. 30.3-1: zone 4 (interior)  +1.0 / −1.1 at A ≤ 10 ft², +0.7 / −0.8 at A ≥ 500 ft²
                             zone 5 (corners)   +1.0 / −1.4 at A ≤ 10 ft², +0.7 / −0.8 at A ≥ 500 ft²
                             linear in log10(A) between; note 5: wall values × 0.9 when the roof angle θ ≤ 10°
    zone 5 = within a of a building corner (a as Fig. 28.3-1 note 9 / Fig. 30.3-1: bimsteelauto end_zone_width)
    effective wind area A = span × max(spacing, span / 3)       (user decision; §26.2 "effective wind area")
    minimum ±16 psf = 0.766 kPa                                 §30.2.2
VERIFIED = False for everything in this module (new code: the coefficients are TRANSCRIBED from Fig. 30.3-1 and the
hand-check in engine/tests/test_cc_wind.py re-does the arithmetic, not the transcription; a reviewer checks the figure).
"""

from __future__ import annotations

import math

FT2 = 0.3048 ** 2                      # m² per ft²
PSF = 4.4482216152605 / FT2 / 1000    # kN/m² per psf (1 lbf and 1 ft are defined exactly)
MIN_CC_KPA = 16 * PSF                  # 0.766 kN/m²
GCP_WALL = {"4": {"pos": (1.0, 0.7), "neg": (-1.1, -0.8)},
            "5": {"pos": (1.0, 0.7), "neg": (-1.4, -0.8)}}   # (A ≤ 10 ft², A ≥ 500 ft²)
VERIFIED = {"GCP_WALL": False, "interpolation": False, "theta_reduction": False, "minimum": False, "effective_area": False}


def effective_area(span_m: float, spacing_m: float) -> float:
    return span_m * max(spacing_m, span_m / 3.0)


def gcp_wall(zone: str, area_m2: float, theta_deg: float) -> tuple[float, float]:
    """(positive, negative) GCp of a wall zone at an effective area."""
    A = area_m2 / FT2
    t = min(1.0, max(0.0, (math.log10(A) - 1.0) / (math.log10(500.0) - 1.0)))
    out = []
    for sign in ("pos", "neg"):
        a, b = GCP_WALL[zone][sign]
        g = a + (b - a) * t
        out.append(g * 0.9 if theta_deg <= 10.0 else g)
    return out[0], out[1]


def cc_wall_pressure(qh: float, zone: str, area_m2: float, theta_deg: float, gcpi: tuple[float, float]) -> dict:
    """Worst inward (+) and outward (−) net pressure, kN/m², with the internal pressure that makes each worst."""
    gp, gn = gcp_wall(zone, area_m2, theta_deg)
    gi = max(abs(gcpi[0]), abs(gcpi[1]))
    p_in, p_out = qh * (gp + gi), qh * (gn - gi)
    return {"zone": zone, "A_m2": round(area_m2, 4), "A_ft2": round(area_m2 / FT2, 2), "GCp": [round(gp, 5), round(gn, 5)], "GCpi": gi,
            "inward": max(p_in, MIN_CC_KPA), "outward": min(p_out, -MIN_CC_KPA),
            "minimum_governs": p_in < MIN_CC_KPA or p_out > -MIN_CC_KPA, "VERIFIED": False}
