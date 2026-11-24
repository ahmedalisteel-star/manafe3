# Open item 17: apex haunch, old → new (stop rule, 2026-11-24)

NOT FOR ISSUE. **APPROVED by the user 2026-11-24 as reported here.** no existing test value has changed (every existing
fixture and request is OFF). Old = `fixtures/manafe3/building1-sized.json` (apex OFF); new =
`fixtures/manafe3/building1-apex.json` (the same building, loads and Phase 4 sizes + `apex_haunch_length` 1 600,
`hw_apex` 450 — the Building… defaults: 24 000 / 15 = 1 600; 1.5 × 300 = 450). Both runs: `tools/item17-compare.py`
(the full building analysis, joints, end plates, 5c stability braces, 5d eave transfer / wind-column tops, the kink
check and the AISC frame check with DG 25).

## User decisions 2026-11-24 (recorded)
- **D1 = A:** the apex segment is SHOP-WELDED to the last rafter piece (segment `joint: "shop"`): one shipping piece, no
  splice, no end plate. Web = one shaped plate (constant + taper) when the piece fits the plate length rule, else two
  plates with a CJP butt weld; bottom flange = two plates with a CJP weld at the kink. Same in BOM / NC.
- **D2:** engine OFF unless `apex_haunch_length` / `hw_apex` are sent; Building… sends ON for a new building, OFF for a
  saved project.
- **D3:** the 50 % minimum design force at the ridge joint is based on the RAFTER section just outside the apex haunch
  (not the deeper apex section); the joint is still designed for 100 % of the analysis forces of every combination.
- **D4:** no apex haunch on end-rafter (bearing) end walls; frame-type end walls get the same haunch as the other frames.
- **D5:** the web at the bottom-flange kink is checked for the kink force, both signs (J10.2; J10.3 where compressive),
  stiffener pair only if it fails; the distance kink → nearest flange brace is reported (no rule yet).

## Geometry (by hand, checked in `engine/tests/test_apex_haunch.py`)
| | old | new |
|---|---|---|
| rafter segments | 2 400 (475→300) + 9 162.382 (300) | 2 400 (475→300) + 7 562.382 (300) + 1 600 (300→450, shop) |
| field splices per rafter / joints | 1 / 291 | 1 / 291 (the shop joint is not a splice) |
| ridge depth (end plate) | 320 | 470 |
| bottom-flange kink | — | θ = atan(150 / 1 600) = 5.356° |
| frame weight (one frame line) | 1 668.47 kg | 1 679.77 kg (+11.30 = 2 × ½ × 150 × 1 600 × 6 × 7.85e-6) |
| wind columns at the ridge WF2 / WL2 top z | 6 868.354 | 6 717.606 (−150 × √1.01 = −150.748); WF1/3, WL1/3 unchanged |

## Rafters (AISC 360-16 LRFD, DG 25; governing at the knee end, x = 0, 1.2D + 1.6Lr (+C))
| members | old U | new U |
|---|---|---|
| F2–F4 RA / RB | 0.8294 | 0.8103 |
| F1, F5 RA / RB (end frames) | 0.4366 | 0.4274 |
| whole frame max (column) | 0.8965 | 0.8778 |
| serviceability max | 0.7964 | 0.7395 |
The stiffer apex moves moment from the knee to the ridge: ridge +M 147.009 → 159.355 kN·m (F3, analysis).

## Ridge end plates (5 joints, all DESIGNED both runs; F3-R shown, F1 / F5 alike)
| | old | new |
|---|---|---|
| plate depth (rafter section at the ridge) | 320 | 470 |
| bolts / plate (one size per type) | 4 × M24 8.8 / t 18 | 4 × M20 8.8 / t 15 (M20 = the main-frame minimum) |
| Mu+ (analysis) | 147.009 | 159.355 |
| Mu− (50 % rule, D3: rafter section, φMn 233.546) | 116.773 | 116.773 (unchanged) |
| Vu (50 % rule, φVn 368.064) | 184.032 | 184.032 (unchanged) |
| +M side (4E): bolts U / plate U | 0.5795 / 0.4829 | 0.6096 / 0.4948 |
| −M side (flush, DG 16 TO CONFIRM): bolts U / plate U | 0.6571 / 0.4908 | 0.5767 / 0.4507 |
| shear (compression-side bolts) U | 0.3767 | 0.5424 (M20 instead of M24) |
| flange weld (8 mm double fillet) U | 0.8681 | 0.8681 |
| governs | −M (flush) | +M (4E) |

## Ridge flange braces (ridge purlin, 200 mm from the apex, inside the haunch: ho 310 → 441.3)
| point | old: Mr / Prb / P_brace / U | new: Mr / Prb / P_brace / U |
|---|---|---|
| F2–F4 RA / RB | 73.691 / 4.754 / 1.883 / 0.1038 | 80.837 / 3.664 / 1.451 / 0.0800 |
| F1, F5 RA / RB | 43.686 / 2.818 / 2.329 / 0.1284 | 46.195 / 2.094 / 1.730 / 0.0954 |
Governing check both runs: bearing on the purlin web (AISI J3.3, VERIFIED False). All 82 points PARTIAL as before (the
frame-side end is not detailed — unchanged note).

## Wind-column tops at the ridge (WF2 / WL2; 5d)
| | old | new |
|---|---|---|
| column top z | 6 868.354 | 6 717.606 |
| reaction F (C&C) | 17.75 kN | 17.39 kN |
| governing (clip bolt shear) U | 0.4949 | 0.4848 |
| rafter bottom flange alone (rule 7a) U | 0.2167 (flange axial 138.5 kN) | 0.0804 (102.7 kN: deeper rafter) |
| vertical slot: δ down / up → length | 62.38 / 49.36 → 136 | 58.02 / 46.05 → 129 (still longer than the AISC long slot 40) |

## Kink check (D5, new; `engine/connections/kink.py`) — all 10 PASS
Inputs (Claude's, conservative, printed on every result): lb = 0, k = tf (fillet ignored), Qf = 1, E 200 000; full
resultant 2|C| sin(θ/2) normal to the flange; C = −M / ho + P × A_bot / A, ho 310. φRn: J10.2 = 106.5 kN, J10.3 = 234.967 kN.
| kink | flange in compression: C / Ru / U J10.2 / U J10.3 | flange in tension: C / Ru / U J10.2 |
|---|---|---|
| F2–F4 A / B | 253.081 / 23.649 / 0.2221 / 0.1006 (0.9D + 1.0WA) | −477.023 / 44.574 / 0.4185 (1.2D + 1.6Lr) |
| F1, F5 A | 160.267 / 14.976 / 0.1406 / 0.0637 | −249.492 / 23.313 / 0.2189 |
| F1, F5 B | 120.308 / 11.242 / 0.1056 / 0.0478 | −249.492 / 23.313 / 0.2189 |
No stiffener pair. J10-2 / J10-4 are Claude's transcription (VERIFIED["J10"] False); the tests check the arithmetic.
**Kink → nearest flange brace (along the rafter; reported, no rule — the user decides):**
| rafters | toward the ridge | toward the eave |
|---|---|---|
| F1, F5 RA / RB | 1 444.6 (ridge purlin RA10 / RB10) | 4 498.4 (purlin line 5) |
| F2–F4 RA / RB | 1 444.6 (ridge purlin RA10 / RB10) | 6 870.4 (purlin line 3) |

## Also moved (not in the stop-rule list, reported)
- **Eave transfer (5d, open item 13):** old 4 DESIGNED / 4 FAILS → new 6 DESIGNED / 2 FAILS (the knee forces drop):
  P310-a / P321-a 1.0664 → 1.0413 (still FAIL), P316-a / P327-a 1.0076 → 0.9841 (now DESIGNED), the others ≈ 0.59.

## Fabrication in the app (`app/manafe3/builtup-parts.js`, tested in `tests/bin/test-manafe3-apex.mjs`)
Building 1 apex rafter: assemblies s1 (knee haunch) and s2 + s3 (one piece). Piece web ONE plate `BUW6 300-300-450`,
134.781 kg, NC contour = the piece outline; top flange one plate 9 161.882; bottom flange 7 562.382 + 1 560.725 (CJP).
**`MAX_PLATE_LENGTH` = 12 000 mm, confirmed by the user 2026-11-24** (the same as the transport rule). Above it the web is two plates, the second CJP-welded to the main web.

## What this cannot close
- J10 inputs lb = 0 / k = tf are conservative judgements, not clauses; J10-2 / J10-4 not compared with the printed spec.
- DG 25 on the apex taper stays NOT VERIFIED (as the knee haunch).
- The plumb-cut end of a TAPERED end segment is drawn with the end vertices at x1 + k·v (segmentPlates, since Phase 1):
  the apex web outline is 3 450 mm² (0.16 kg) larger than the exact plumb cut — pre-existing, not changed here.
- The CJP welds are stated (`cjp: true` on the parts, the engine's butt-splice note), not designed (full strength).

# Open item 17b: flange brace at the kink, old → new (stop rule, 2026-11-24)

NOT FOR ISSUE. **APPROVED by the user 2026-11-24 as reported here.** Old = `building1-apex.json` with
`kink_flange_braces=False` (= item 17 as committed, `d13ec662`); new = `building1-apex.json` (default True).
`tools/item17-compare.py OUT.json 17b`; the bottom-flange segment rows: each segment checked alone (the DG 25 member
input with its stations limited to that segment and M < 0, i.e. the bottom flange in compression) — a reporting run,
not a new rule.

**User decision 2026-11-24 (17b):** apex haunch ON → a rafter flange-brace pair at the purlin nearest the bottom-flange
kink on its EAVE side; the step 5c detail and rules (L50x5, 1 M12 per end, the same group and merge rules); none with
the apex OFF.

**Correction to item 17's distance table:** it measured from the kink's TOP-flange point. From the bottom-flange point
(where the braces end): toward the ridge 1 413.1 (was 1 444.6), toward the eave 6 901.9 on F2–F4 (was 6 870.4) and
4 529.9 on F1 / F5 (was 4 498.4). `kink.nearest_flange_brace` now measures from the bottom-flange point.

## Position and count (by hand, `test_apex_haunch.py::test_kink_flange_braces_17b`)
Purlins at 1 185.985 spacing → RA8 / RB8 at s 9 487.881 (RA9 10 673.866 is past the kink at 10 459.851). Brace bottom end
(depth 320) y 9 472.138, z 6 630.643; 45°, run 365, length 516.188. Count 136 → 152 (+16: frames 2–4 × 2 sides × 2,
frames 1 / 5 × 2 sides × 1, inside the building). Kink → the new brace 972.0 mm (hand 971.97). Negative controls:
apex OFF (`building1-sized.json`) and the switch off: 136, no RA8 / RB8 brace; every other brace identical.

## Rafter bottom flange (inner flange) — Lb and U, rafter A (B is the mirror)
| frame | segment old → new (mm along the design member) | Lb | U (segment, H1) | flexure U | combo |
|---|---|---|---|---|---|
| F2–F4 | 3 086.8 – 11 400.7 | 8 313.9 | 0.6812 (F3) / 0.6817 (F2, F4) | 0.6702 | 0.9D + 1.0WA |
| → F2–F4 | 3 086.8 – 9 016.7 | 5 929.9 | 0.4275 / 0.4279 | 0.4166 | 0.9D + 1.0WA |
| → F2–F4 | 9 016.7 – 11 400.7 | 2 384.0 | 0.3653 | 0.3543 | 0.9D + 1.0WA |
| F1, F5 | 5 458.8 – 11 400.7 | 5 941.9 | 0.3208 | 0.3207 | 0.9D + 1.0WB + BRB |
| → F1, F5 | 5 458.8 – 9 016.7 | 3 557.9 | 0.2320 | 0.2318 | 0.9D + 1.0WB + BRB |
| → F1, F5 | 9 016.7 – 11 400.7 | 2 384.0 | 0.2134 | 0.2133 | 0.9D + 1.0WB + BRB |
The member results (governing at the knee end, 1.2D + 1.6Lr): F2–F4 0.8103 → 0.8107, F1 / F5 0.4274 → 0.4276, frame max
0.8778 → 0.8783 (the braces' own weight in the secondary load); serviceability 0.7395 unchanged. The segment next to
the knee (1 894.2 – 3 086.8): 0.6460 → 0.6463.

## Flange-brace points (rafter A; 82 → 92 points, all PARTIAL as before — the frame-side end is not detailed)
| point (s along the flange) | old: Lbr / Prb / P_brace / U | new: Lbr / Prb / P_brace / U |
|---|---|---|
| F3 RA3 (3 060.4) | 8 301.9 / 11.821 / 9.365 / 0.5162 | 5 929.9 / 11.827 / 9.773 / 0.5386 |
| F3 **RA8 (8 990.4) NEW** | — | 5 929.9 / 5.126 / 4.236 / 0.2335 |
| F3 RA10 ridge (11 362.4) | 8 301.9 / 3.664 / 1.451 / 0.0800 | 2 372.0 / 3.662 / 1.840 / 0.1014 |
| F1 RA5 (5 432.4) | 5 930.0 / 1.830 / 3.025 / 0.1667 | 3 558.0 / 1.599 / 2.897 / 0.1597 |
| F1 **RA8 (8 990.4) NEW** | — | 3 558.0 / 3.163 / 5.730 / 0.3158 |
| F1 RA10 ridge (11 362.4) | 5 930.0 / 2.094 / 1.730 / 0.0954 | 2 372.0 / 2.093 / 2.103 / 0.1159 |
Governing everywhere: bearing on the purlin web (AISI J3.3, VERIFIED False). Why RA3 and the ridge brace go UP: the
shorter Lbr makes Δo = Lbr / 500 smaller, so the slip amplification (1 + slip / Δo, item 16.5) is larger.

## Cleats at these purlins (5a re-run with the flange-brace force; counts 186 DESIGNED / 10 FAILS both)
| cleat | old U | new U | governing |
|---|---|---|---|
| CL43 F3 RA8 | 0.5432 | 0.6324 | cleat axial + bending (1.2D + 1.6Lr + 0.5W + flange brace) |
| CL41 F1 RA8 | 0.2246 | 0.2925 | cleat axial + bending |
| CL18 F3 RA3 | 0.7618 | 0.7808 | weld metal 6 mm |
| CL53 F3 RA10 | 0.3545 | 0.3637 | cleat axial + bending |
| CL28 F3 RA5 / CL16 F1 RA3 / CL26 F1 RA5 / CL51 F1 RA10 | 0.5432 / 0.3003 / 0.4360 / 0.4165 | 0.5432 / 0.3004 / 0.4392 / 0.4182 | — |

## Weight
Frame (built-up) 1 679.77 kg per frame line — unchanged. Flange braces 307.6 → 338.4 kg (+30.8 kg for the building:
16 × 0.516 m of L50x5); building 16 694.9 → 16 725.7 kg.
