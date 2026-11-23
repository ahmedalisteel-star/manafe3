# Open item 16: connections and sizes, old → new (stop rule, 2026-11-22)

NOT FOR ISSUE. The code is in the working tree, not committed; no existing test value has been changed yet.
Old = `main` at f30fbb4f; new = the item 16 code. Both runs are the same building with the same analysis.

## What was coded (user decisions 2026-11-18)
- 16.1 / 16.4 per-line gauge: `Sections.lines {line or piece id: profile}` (engine `secondary.py`, API `sections.lines`).
  The kind, H, B and D must match the role's profile; an id the building does not have is refused. The pieces carry
  their gauge, so the checks, the sizing, the connections, MTO and NC read the members. `building_lines` takes the
  bay's own piece for an eave strut and the thinnest piece for a lapped line. Browser: `specWithProposal` writes
  `proposed.line_profiles` into `spec.line_profiles`; `buildingRequest` sends `sections.lines`; Apply's proposal table
  lists them ("Cold-formed lines"). A Building… resubmit keeps them while the role keeps its depth, otherwise drops
  and lists them.
- 16.2: PL10x100 cleats on the strut-purlin lines at the braced-bay frame lines, 24 in building 1 (RA/RB 1, 5, 10 at
  frames 1, 2, 4, 5; `building.STRUT_CLEAT`). Sizing gives a strut purlin at least 1.8 mm
  (`sizing.STRUT_PURLIN_T_MIN`). The cleats take the strut forces from the same source as the member checks
  (`cfs_checks.strut_setup / attach_struts`), with the same-direction pairing: C&C with no strut force; Case B (WoutB)
  with ± caseB × the wind factor; the minimum with D only (0.9D, 1.2D), ±. One weld leg per cleat type: PL8 6 mm,
  PL10 8 mm.
- 16.3: a cleat carrying two gauges takes the thinner piece's t and grade.
- 16.5: Δo = Lbr / 500, with Lbr the App. 6 length of the brace group (was the shorter segment). `web_washers`
  defaults to on (mf 1.00) in CleatSettings and StabilitySettings.

## Flange brace + strut force: user decision 2026-11-22, "concurrent forces, same combination"
For each cleat combination: the strut force PLUS the flange-brace force of that same combination, worse sign. The
frame combinations are matched by their D, Lr and wind factors: C&C with no brace case; Case B with WB + BRA / BRB;
the minimum with BRmin and the same D. Every combination is checked with both signs.

| Cleat | Building | old (main) | coded 2026-11-22 a.m. (envelope added) | **new (same combination)** | governing (combination) |
|---|---|---|---|---|---|
| CL7 / CL9 (RA1, frames 2 / 4) | sized fixture, Z200x2.0, PL10 | 1.401 FAILS (PL8) | 1.032 | **0.926 DESIGNED** | weld metal 8 mm (1.2D+1.6Lr+0.5W Case B + strut); web 0.855 |
| CL62 / CL64 (RB1) | sized fixture | 1.401 FAILS (PL8) | 1.032 | **0.892 DESIGNED** | weld metal 8 mm (same); web 0.822 |
| CL7 / CL9 | design-side, Z250x1.8, PL10 | 1.692 FAILS (PL8, Z250x1.5) | 1.217 | **1.118 FAILS** | weld metal 8 mm (same); base metal 0.978, web 0.947, cleat section 0.912 |
| CL62 / CL64 | design-side | 1.692 FAILS | 1.217 | **1.075 FAILS** | weld metal 8 mm (same); base metal 0.939, web 0.910, cleat section 0.892 |

The flange-brace force of that combination at these cleats is about 22.3 kN (envelope 22.29–22.40); the strut Case B
share is 13.448 kN × the wind factor.

### Options for the design-side CL7 / 9 / 62 / 64 (not applied: your choice)
| Option | CL7 / 9 governing U | CL62 / 64 governing U | Note |
|---|---|---|---|
| as coded: PL10, 8 mm weld | 1.118 (weld metal) | 1.075 (weld metal) | FAILS |
| PL10, 10 mm weld | 0.978 (base metal; weld metal 0.894) | 0.939 (base metal; weld metal 0.860) | above the J2.2b maximum for PL10 (t − 2 = 8 mm) that the cap rule of 2026-11-16 applies |
| PL12, 10 mm weld (= J2.2b max) | 0.947 (web bearing; weld metal 0.873, base metal 0.798) | 0.910 (web bearing; weld metal 0.839, base metal 0.766) | the 24 strut cleats become PL12; on the sized fixture CL7 0.905, CL62 0.871 (weld 8 mm there) |

## Applied (user 2026-11-23): PL12 + 10 mm fillet both sides on all 24 strut cleats

### Sized fixture (Z200x65x20x2.0): the 24 strut cleats

| Cleat | Line | old (main, PL8) | PL10 + 8 mm | **PL12 + 10 mm** | governing (new) | combination |
|---|---|---|---|---|---|---|
| CL6 / CL10 / CL61 / CL65 | RA1 / RB1 | 0.671 DESIGNED | 0.523 DESIGNED | **0.523 DESIGNED** | bearing / tearout - web | 1.2D + 1.0 BRmin (dead load only) + strut +N |
| CL7 / CL9 | RA1 | 1.401 FAILS | 0.926 DESIGNED | **0.855 DESIGNED** | bearing / tearout - web | 1.2D+1.6Lr+0.5W Case B + strut +N |
| CL26 / CL30 | RA5 | 0.273 DESIGNED | 0.440 DESIGNED | **0.440 DESIGNED** | bearing / tearout - web | 1.2D+1.0W+0.5Lr Case B + strut +N |
| CL27 / CL29 / CL82 / CL84 | RA5 / RB5 | 0.698 DESIGNED | 0.494 DESIGNED | **0.494 DESIGNED** | bearing / tearout - web | 1.2D+1.6Lr+0.5W (C&C) +N |
| CL51 / CL55 / CL106 / CL110 | RA10 / RB10 | 0.180 DESIGNED | 0.420 DESIGNED | **0.420 DESIGNED** | bearing / tearout - web | 0.9D+1.0W Case B + strut +N |
| CL52 / CL54 / CL107 / CL109 | RA10 / RB10 | 0.456 DESIGNED | 0.447 DESIGNED | **0.447 DESIGNED** | bearing / tearout - web | 0.9D+1.0W Case B + strut +N |
| CL62 / CL64 | RB1 | 1.401 FAILS | 0.892 DESIGNED | **0.822 DESIGNED** | bearing / tearout - web | 1.2D+1.6Lr+0.5W Case B + strut +N |
| CL81 / CL85 | RB5 | 0.257 DESIGNED | 0.414 DESIGNED | **0.414 DESIGNED** | bearing / tearout - web | 1.2D + 1.0 BRmin (dead load only) + strut +N |

Weld legs: {'PL8x100': 6.0, 'PL12x100': 10.0}; counts {'DESIGNED': 174, 'FAILS': 22} → {'DESIGNED': 186, 'FAILS': 10}

### Design-side (Z250x65x20x1.5 base, strut purlins 1.8): the 24 strut cleats

| Cleat | Line | old (main, PL8) | PL10 + 8 mm | **PL12 + 10 mm** | governing (new) | combination |
|---|---|---|---|---|---|---|
| CL6 / CL10 | RA1 | 0.827 DESIGNED | 0.624 DESIGNED | **0.580 DESIGNED** | bearing / tearout - web | 1.2D + 1.0 BRmin (dead load only) + strut +N |
| CL7 / CL9 | RA1 | 1.692 FAILS | 1.118 FAILS | **0.947 DESIGNED** | bearing / tearout - web | 1.2D+1.6Lr+0.5W Case B + strut +N |
| CL26 / CL30 | RA5 | 0.353 DESIGNED | 0.530 DESIGNED | **0.489 DESIGNED** | bearing / tearout - web | 1.2D+1.0W+0.5Lr Case B + strut +N |
| CL27 / CL29 / CL82 / CL84 | RA5 / RB5 | 0.964 DESIGNED | 0.612 DESIGNED | **0.549 DESIGNED** | bearing / tearout - web | 1.2D+1.6Lr+0.5W (C&C) +N |
| CL51 / CL55 / CL106 / CL110 | RA10 / RB10 | 0.234 DESIGNED | 0.488 DESIGNED | **0.468 DESIGNED** | bearing / tearout - web | 0.9D+1.0W Case B + strut +N |
| CL52 / CL54 / CL107 / CL109 | RA10 / RB10 | 0.704 DESIGNED | 0.527 DESIGNED | **0.497 DESIGNED** | bearing / tearout - web | 0.9D+1.0W Case B + strut +N |
| CL61 / CL65 | RB1 | 0.827 DESIGNED | 0.594 DESIGNED | **0.580 DESIGNED** | bearing / tearout - web | 1.2D + 1.0 BRmin (dead load only) + strut +N |
| CL62 / CL64 | RB1 | 1.692 FAILS | 1.075 FAILS | **0.910 DESIGNED** | bearing / tearout - web | 1.2D+1.6Lr+0.5W Case B + strut +N |
| CL81 / CL85 | RB5 | 0.338 DESIGNED | 0.472 DESIGNED | **0.460 DESIGNED** | bearing / tearout - web | 1.2D + 1.0 BRmin (dead load only) + strut +N |

Weld legs: {'PL8x100': 6.0, 'PL12x100': 10.0}; counts {'DESIGNED': 172, 'FAILS': 24} → {'DESIGNED': 178, 'FAILS': 18}

### Flange-side base metal (hand check)
Flange-side base metal of the 10 mm fillet at the 24 strut cleats (user hand check 2026-11-23; rafter top flange tf 10 mm S355, E70): weld metal 0.75 × 0.6 × 482 × 7.07 = 1534 N/mm per line < base metal rupture 0.75 × 0.6 × 490 × 10 = 2205 N/mm and yield 1.0 × 0.6 × 355 × 10 = 2130 N/mm, so the weld metal governs; no separate row while tf ≥ the leg. Guard: a host flange tf below the fixed leg → the cleat reads NOT EVALUATED with that reason (test_cleats::test_thin_host_flange_guard, negative control F2-RA at tf 8).

## Eave-strut cleats: the item 7 panel force between two braced bays (user 2026-11-22)
The panel force max(drag, 0.005 × ΣPr) of the between-bay pieces RA0-2 / RA0-3 (RB0-2 / RB0-3) now enters, with the
member check's families. Its largest value is 0.442 kN (A) / 0.449 kN (B) at the design-side sizes, and 0.445 / 0.451
kN on the fixture.

| Cleat (pieces) | fixture old → new | design-side old → new | governing (new) |
|---|---|---|---|
| CL1 / CL5 / CL56 / CL60 (end frames, braced-bay piece) | 0.160 → 0.506 | 0.210 → 0.506 | weld metal 6 mm (1.2D + BRmin + strut) |
| CL2 / CL4 / CL57 / CL59 (braced-bay piece + between-bay piece) | 0.267 → 0.639 | 0.260 → 0.852 | web bearing (1.2D + BRmin + strut) |
| CL3 / CL58 (two between-bay pieces: panel force only) | 0.268 → 0.268 | 0.260 → 0.260 | cleat compression + bending (1.2D+1.6Lr+0.5W C&C) |

The panel force does not govern any of them: CL3 / CL58 are unchanged, and CL2 / 4 / 57 / 59 are governed by the
braced-bay piece's strut force.

## Cleats, design-side sizes (status count old → new)
DESIGNED 172 / FAILS 24 → 174 / 22 (same-combination rule). Strut cleats: CL6 / 10 / 61 / 65 0.827 → 0.833;
CL26 / 30 / 81 / 85 0.353 → 0.544; CL27 / 29 / 82 / 84 0.964 → 0.612; CL51 / 55 / 106 / 110 0.234 → 0.521;
CL52 / 54 / 107 / 109 0.704 → 0.577. Braced-bay eave-strut cleats CL2 / 4 / 57 / 59 0.260 → 0.852 (P_split now in;
web bearing at 1.5 mm). Still failing, not item 16 (flange-brace forces on 1.5 mm webs, open items 9.2 / 12): CL8, 12–14,
17–19, 63, 67–69, 72–74, girts CL127 / 129 / 147 / 149.
Sized fixture (Z200x2.0): DESIGNED 174 / FAILS 22 → 186 / 10 (same-combination rule).

## Other values that move (tests to update after your OK)
- `test_stability_braces` building 1: flange-brace counts {FAILS (AISI) 30, FAILS 4, PARTIAL 48} → {PARTIAL 82}; the
  slip-factor assert moves from L_short to Lbr; cleat counts {DESIGNED 174, FAILS 22} → {DESIGNED 186, FAILS 10}; weld leg PL8 6 mm, PL10 8 mm.
- `test_item15` sizing: the strut purlins RA1 / RA5 / RA10 / RB1 / RB5 / RB10 go to Z250x65x20x1.8 ("changed": False →
  True; line_profiles gains them).
- `test_welds`: F2 / F4-BA uplift −47.088 → −47.081 kN. The 24 PL10 cleats add about 8.7 kg to the roof dead load
  (cleats count in `secondary_weight`).
- `test_design_run` (decision 7): main case roof_type = through_fastened; the no-roof_type strict run stays as the
  negative control.
- Design-side flange braces: the first-purlin points F1 / F5 at s 688.6 (RA1, 1.8 mm) still fail at 1.0137, and at
  s 1874.6 (RA2, 1.5 mm) at 1.0154, FAILS (AISI). The other 74 are PARTIAL.

### Sized fixture (building1-sized.json, Z200x65x20x2.0 / C200x65x20x2.0) — all 82 flange-brace points (governing U = web bearing, AISI J3.3 VERIFIED False)

| points | s mm | Lbr mm | slip factor old → new | U old → new | status old → new |
|---|---|---|---|---|---|
| F1-RA, F1-RB, F5-RA, F5-RB (4) | 688.6 | 1186 | 2.4523 → 1.8432 | 1.6258 → 0.9166 | FAILS → PARTIAL |
| F2-RA, F2-RB, F4-RA, F4-RB (4) | 688.6 | 1186 | 2.4523 → 1.8432 | 1.5486 → 0.8731 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F3-RA, F3-RB (2) | 688.6 | 1186 | 2.4523 → 1.8432 | 1.5484 → 0.8729 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F1-CA, F5-CA, F1-CB, F5-CB (4) | 5000 | 1250 | 2.0000 → 1.8000 | 1.4184 → 0.9576 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F2-CA, F3-CA, F4-CA, F2-CB, F3-CB, F4-CB (6) | 5000 | 1250 | 2.0000 → 1.8000 | 1.3493 → 0.9109 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F2-RA, F2-RB, F3-RA, F3-RB, F4-RA, F4-RB (6) | 3060.4 | 8301.9 | 1.8432 → 1.1205 | 1.2310 → 0.5613 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F1-CA, F5-CA, F1-CB, F5-CB (4) | 3750 | 3750 | 1.8000 → 1.2667 | 1.0437 → 0.5509 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F1-RA, F1-RB, F5-RA, F5-RB (4) | 1874.6 | 1186 | 1.8432 → 1.8432 | 1.0200 → 0.7651 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F2-CA, F3-CA, F4-CA, F2-CB, F3-CB, F4-CB (6) | 3750 | 3750 | 1.8000 → 1.2667 | 0.9955 → 0.5254 | PARTIAL → PARTIAL |
| F2-RA, F2-RB, F3-RA, F3-RB, F4-RA, F4-RB (6) | 1874.6 | 1186 | 1.8432 → 1.8432 | 0.9759 → 0.7320 | PARTIAL → PARTIAL |
| F1-RA, F1-RB, F5-RA, F5-RB (4) | 3060.4 | 2372 | 1.8432 → 1.4216 | 0.6393 → 0.3698 | PARTIAL → PARTIAL |
| F1-RA, F5-RA (2) | 5432.4 | 5929.9 | 1.4216 → 1.1686 | 0.2975 → 0.1834 | PARTIAL → PARTIAL |
| F1-RB, F5-RB (2) | 5432.4 | 5929.9 | 1.4216 → 1.1686 | 0.2031 → 0.1252 | PARTIAL → PARTIAL |
| F1-RA, F1-RB, F5-RA, F5-RB (4) | 11362.3 | 5929.9 | 1.1686 → 1.1686 | 0.1712 → 0.1284 | PARTIAL → PARTIAL |
| WF2, WL2 (2) | 3750 | 2500 | 1.4000 → 1.4000 | 0.1426 → 0.1070 | PARTIAL → PARTIAL |
| F2-RA, F2-RB, F3-RA, F3-RB, F4-RA, F4-RB (6) | 11362.3 | 8301.9 | 1.1205 → 1.1205 | 0.1384 → 0.1038 | PARTIAL → PARTIAL |
| WF1, WF3, WL1, WL3 (4) | 3750 | 2500 | 1.4000 → 1.4000 | 0.1152 → 0.0864 | PARTIAL → PARTIAL |
| WF2, WL2 (2) | 1250 | 2500 | 1.8000 → 1.4000 | 0.1098 → 0.0641 | PARTIAL → PARTIAL |
| WF1, WF3, WL1, WL3 (4) | 1250 | 2500 | 1.8000 → 1.4000 | 0.0984 → 0.0574 | PARTIAL → PARTIAL |
| WF2, WL2 (2) | 6250 | 2500 | 2.6172 → 1.4000 | 0.0878 → 0.0352 | PARTIAL → PARTIAL |
| WF1, WF3, WL1, WL3 (4) | 6250 | 2500 | 1.4000 → 1.4000 | 0.0013 → 0.0010 | PARTIAL → PARTIAL |

Counts: {'PARTIAL': 48, 'FAILS': 4, 'FAILS (AISI J3.3 unverified, item 9.2)': 30} → {'PARTIAL': 82}

### Design-side sizes (Z250x65x20x1.5 base, strut purlins RA/RB 1, 5, 10 at 1.8; C200x65x20x1.5, braced-bay eave struts 1.8) — all 82 flange-brace points (governing U = web bearing, AISI J3.3 VERIFIED False)

| points | s mm | Lbr mm | slip factor old → new | U old → new | status old → new |
|---|---|---|---|---|---|
| F1-RA, F1-RB, F5-RA, F5-RB (4) | 688.6 | 1186 | 2.4523 → 1.8432 | 2.1518 → 1.0137 | FAILS → FAILS (AISI J3.3 unverified, item 9.2) |
| F2-RA, F2-RB, F4-RA, F4-RB (4) | 688.6 | 1186 | 2.4523 → 1.8432 | 2.0483 → 0.9652 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F3-RA, F3-RB (2) | 688.6 | 1186 | 2.4523 → 1.8432 | 2.0480 → 0.9651 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F2-RA, F2-RB, F3-RA, F3-RB, F4-RA, F4-RB (6) | 3060.4 | 8301.9 | 1.8432 → 1.1205 | 1.6279 → 0.7446 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F1-CA, F5-CA, F1-CB, F5-CB (4) | 5000 | 1250 | 2.0000 → 1.8000 | 1.4080 → 0.9532 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F1-RA, F1-RB, F5-RA, F5-RB (4) | 1874.6 | 1186 | 1.8432 → 1.8432 | 1.3500 → 1.0154 | FAILS (AISI J3.3 unverified, item 9.2) → FAILS (AISI J3.3 unverified, item 9.2) |
| F2-CA, F3-CA, F4-CA, F2-CB, F3-CB, F4-CB (6) | 5000 | 1250 | 2.0000 → 1.8000 | 1.3385 → 0.9063 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F2-RA, F2-RB, F3-RA, F3-RB, F4-RA, F4-RB (6) | 1874.6 | 1186 | 1.8432 → 1.8432 | 1.2907 → 0.9710 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F1-CA, F5-CA, F1-CB, F5-CB (4) | 3750 | 3750 | 1.8000 → 1.2667 | 1.0360 → 0.5484 | FAILS (AISI J3.3 unverified, item 9.2) → PARTIAL |
| F2-CA, F3-CA, F4-CA, F2-CB, F3-CB, F4-CB (6) | 3750 | 3750 | 1.8000 → 1.2667 | 0.9875 → 0.5228 | PARTIAL → PARTIAL |
| F1-RA, F1-RB, F5-RA, F5-RB (4) | 3060.4 | 2372 | 1.8432 → 1.4216 | 0.8461 → 0.4908 | PARTIAL → PARTIAL |
| F1-RA, F5-RA (2) | 5432.4 | 5929.9 | 1.4216 → 1.1686 | 0.3993 → 0.2046 | PARTIAL → PARTIAL |
| F1-RB, F5-RB (2) | 5432.4 | 5929.9 | 1.4216 → 1.1686 | 0.2730 → 0.1398 | PARTIAL → PARTIAL |
| F1-RA, F1-RB, F5-RA, F5-RB (4) | 11362.3 | 5929.9 | 1.1686 → 1.1686 | 0.2303 → 0.1435 | PARTIAL → PARTIAL |
| F2-RA, F2-RB, F3-RA, F3-RB, F4-RA, F4-RB (6) | 11362.3 | 8301.9 | 1.1205 → 1.1205 | 0.1865 → 0.1161 | PARTIAL → PARTIAL |
| WF2, WL2 (2) | 3750 | 2500 | 1.4000 → 1.4000 | 0.1426 → 0.1070 | PARTIAL → PARTIAL |
| WF1, WF3, WL1, WL3 (4) | 3750 | 2500 | 1.4000 → 1.4000 | 0.1152 → 0.0864 | PARTIAL → PARTIAL |
| WF2, WL2 (2) | 1250 | 2500 | 1.8000 → 1.4000 | 0.1098 → 0.0641 | PARTIAL → PARTIAL |
| WF1, WF3, WL1, WL3 (4) | 1250 | 2500 | 1.8000 → 1.4000 | 0.0984 → 0.0574 | PARTIAL → PARTIAL |
| WF2, WL2 (2) | 6250 | 2500 | 2.6172 → 1.4000 | 0.0878 → 0.0352 | PARTIAL → PARTIAL |
| WF1, WF3, WL1, WL3 (4) | 6250 | 2500 | 1.4000 → 1.4000 | 0.0013 → 0.0010 | PARTIAL → PARTIAL |

Counts: {'PARTIAL': 42, 'FAILS': 4, 'FAILS (AISI J3.3 unverified, item 9.2)': 36} → {'PARTIAL': 74, 'FAILS (AISI J3.3 unverified, item 9.2)': 8}
