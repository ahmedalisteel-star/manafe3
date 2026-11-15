# HANDOVER — Manafe3 (منافع)

Read this and `CLAUDE.md` first, on either PC. Then `.\start-work.ps1`.

## Where we are

**Phase 0 done (2026-11-05):** the DetailCraft fork runs as Manafe3, the Python engine answers, two PCs work from git.
**Phase 1 done (2026-11-05, ENG04-PC):** welded built-up members — tapered or constant, in segments joined at splice
points — in the model, 3D, Properties panel, parts/marks/BOM, plate cut list, DSTV NC per plate, IFC4 out and back in,
engine section properties along the length, and "PEB frame…" now builds built-up frames with a haunch at the knee.

**Phase 2 done (2026-11-05, ENG04-PC):** "Building…" makes the whole PEB building — built-up frames, lapped Z purlins and
girts, C eave struts, sag rods, rod/angle X-bracing, flange braces, end walls (main frame or end rafter, with wind columns),
framed openings, cleats — with part marks, BOM, cut list, plate list, DSTV NC, a C/Z punch list and IFC out and back in.

**Phase 3 done (2026-11-07, ENG04-PC):** loads and analysis — PEB › "Loads…" (kept in the model) and PEB › "Analysis…":
every frame line (P-Delta, LRFD + ASD + every load case unfactored), the end walls, the longitudinal bracing; N / V / M and
deflected-shape diagrams, base reactions with a CSV for the foundation designer, a STAAD.Pro `.std` per frame line.
Everything NOT FOR ISSUE: analysis only, no member design.

## Next task

**Phase 5 — connections. Plan APPROVED by the user (2026-11-10), below ("Phase 5 plan"). Steps 1 (joints and design
forces), 2 and 2b (base plates, anchors, anchor reinforcement) and 3 (knee / ridge / splice end plates) done in the
engine (2026-11-12); step 3 with its follow-ups APPROVED AS DONE by the user (2026-11-12); step 4 (flange-to-web
welds, the column-to-plate weld, the shear lug, the stiffener welds) APPROVED AS DONE by the user (2026-11-15, "Step 4 —
what was built" below). Open items 5 and 6 CLOSED (2026-11-15: bimsteelauto 0.15.4; the longitudinal pairing at the
braced-bay bases, `engine/connections/longitudinal.py`). Still open: the shear-lug breakout NOT EVALUATED (waiting for the
user's ACI 318-19 17.11.3 page); open item 7 (Phase 4 member checks under the brace axial forces) and open item 8
(pedestal / footing input for the ACI concrete anchor checks), both before step 7. NEXT: step 5 — decisions asked first,
WAIT for the answers. Open for the user: the "Unverified sources" list below (DG 1, ISO 4.6, ACI 17.5.2.1(b), DG 16,
the AISC tables, the stiffener rules).**

Phase 4 (for the record): **Phase 4 — member design. Plan APPROVED by the user (2026-11-08) with additions A and B; in progress — step 1 done,
the bimsteelauto sign fix and end-frame braces done; step 2 (Direct Analysis Method) done; step 3 (main-frame checks) done
in the engine — DG 25 NOT VERIFIED until the user has the printed guide; step 4 (serviceability) done in the engine;
the R1 field fixes list done (2026-11-09, below); step 5 done in the engine; step 6 (purlins / girts / eave struts,
AISI S100-16 DSM, properties and buckling from the geometry) done in the engine, with the user's decisions (R-factor,
zones by slope, tied-off sag rods); step 7 (ECP 205-LRFD side by side, main frames) done in the engine — its K chart
and G rules TO CONFIRM, ch. 6 / mono-symmetric flexure to be added to ecp205-lrfd; step 8 (sizing loop) done in the engine; step 9 (PEB ›
"Design…" in the browser) and step 10 done (2026-11-10). PHASE 4 DONE — NOT FOR ISSUE until the user confirms the open
items (DG 25, the AISI R table, the ECP K / G rules). The repository is PUBLIC and Apache-2.0 (2026-11-10).
Next: the user's confirmations; then Phase 5 (connections) as planned.**

## Phase 5 plan (approved 2026-11-10)

**Decisions (user, 2026-11-10):**
- **Knee, ridge and rafter splices:** extended end plates **4E / 4ES / 8ES from `bimsteelauto_connections` only**. A joint
  these do not fit reads NOT EVALUATED (ratio inf, never a pass). AISC Design Guide 16 flush / multi-row types: roadmap,
  when the user has the printed guide.
- **Design force** = the larger of the analysis force and **50 % of the member's design capacity** (the library's
  `CAPACITY_FRACTION`); a project setting, editable per job.
- **Bolts:** grades **8.8 and 10.9** now, **M12 to M30**. Grade 4.6 is NOT in bimsteelauto_connections: roadmap, the
  user's decision later. End-plate bolts **pretensioned**, secondary bolts **snug-tight**.
- **Anchors and concrete:** anchor grade and concrete strength are editable defaults (**C30/37** as in Job units).
  **Pedestal size is the user's input per building; blank = anchor check NOT EVALUATED.** Never invent a value.
- **Code:** AISC only for connections now; ECP later.
- **Do NOT modify `bimsteelauto_connections`.** If a step seems to need a change there, stop and ask the user.

**Steps** (each: hand-checked independent test, a negative control, commit after green):

| # | Step | Status |
|---|---|---|
| 1 | Joint list and design forces from the model and the analysis (bases, knees, ridge, rafter splices, wind-column tops and bases, brace ends, cleats) | **done** (engine) — `engine/connections/joints.py`, `test_joints.py` |
| 2 | Base plates and anchors incl. net uplift; replaces the field-fix-10 placeholders; **2b: anchor reinforcement (hairpins / ties) as the first fix for shear breakout** | **done** (engine) — `engine/connections/baseplates.py`, `test_baseplates.py` |
| 3 | Knee / ridge / splice end plates: plate, bolts, welds, column-side checks | **done** (engine; approved by the user 2026-11-12) — `engine/connections/endplates.py`, `test_endplates.py` |
| 4 | Flange-to-web welds of built-up members; **+ the column-to-base-plate weld, the shear lug, the stiffener welds** (user 2026-11-11 / 12) | **done** (engine; approved by the user 2026-11-15) — `engine/connections/welds.py`, `test_welds.py`; open: braced-bay bases PARTIAL (item 6), lug breakout (ACI 17.11.3), library base metal (item 5) |
| 5 | Purlin / girt cleats, brace gussets and rod ends (replaces the U = 0.6 placeholder); **+ flange braces (2 % of the flange force), sag rods and ridge ties as standard-detail joints; + the roof-bracing EAVE TRANSFER as an automatic check (haunch-end weak-axis bending, knee bolt shear along the building, column top) — on a failure, report it and suggest an eave-panel strut** (user 2026-11-11) | |
| 6 | Wind-column top with vertical slotted holes (new slot hole type in model, NC, IFC) | |
| 7 | Build the parts in the model; cleats and cap plates welded into their assemblies | |
| 8 | PEB > "Connections..." in the browser: Check, Design, Apply as one undo step, calc sheets, NOT FOR ISSUE | |
| 9 | R1 regression, HANDOVER, end-work | |

**Step 1 — what was built (2026-11-11):** `engine/connections/joints.py`. NOT FOR ISSUE.
- `joint_list(b)` — every joint from the MODEL: base, knee, ridge, rafter_splice (frame lines), wind_column_top / _base
  (incl. an end-rafter wall's corner columns), end_rafter_ridge / _splice, brace_end (roof / side-wall / end-wall X), cleat;
  the members joined (frame joints: analysis mark, station, section at the joint). Host of a brace end / cleat = the
  nearest primary member line (the generator's cleat "host" labels are wrong on an end-rafter wall). Not joints yet:
  sag rods, ridge ties, flange braces.
- `building_joints(b, li, analysis=, settings=)` — LRFD forces: frame joints from the DAM strength solve, member-end
  stations within 1 mm of the joint, both members at a knee: largest +M and −M with their V and P, largest |V|, largest
  compression and tension, each with combination and member; bases from the reactions (compression, uplift, |H|, |M|);
  wind columns from their member-check forces (+ uplift / in-plane H from the end-rafter frame); end-rafter ridge and
  splices from that frame's stations; braces = the tension-only diagonal force. **Cleats: NOT EVALUATED** (cold-formed
  support reactions come with step 5).
- **End-rafter splices (fix 2026-11-11):** the end-rafter frame now has a node at every end-rafter splice
  (`endwall_analysis.end_rafter_splice_ys`). With today's generator (end rafter split in halves, wind columns equally
  spaced) the splice always fell on a strength-model quarter-point node already — the step-1 code had marked these
  joints NOT EVALUATED without looking. The node covers every other splice position (test: a splice moved to y 4 975.2).
- **Capacity rule (user decisions 2026-11-10 / 11).** SOURCE: a project setting, NOT a code clause (AISC 360-16 has no
  general minimum); default 0.50 = `bimsteelauto_connections.CAPACITY_FRACTION`; stated on every result
  (`capacity_rule.source`). Only at knee / ridge / rafter-splice joints; `ConnectionSettings(capacity_fraction,
  capacity_moment, capacity_shear)` — moment and shear switch separately; None = analysis only. Basis = the SECTION
  strength of the shallower section at the joint (smaller Zx): yielding + local buckling, NO LTB (Lb = 0; bimsteelauto
  `available_strengths` with Lb = Lc = 1 mm), Fy = the lowest plate of that piece. Axial, bases, wind columns, end
  rafters, braces: the analysis force alone.
- **Building 1 (V 45, C) — 291 joints: 95 EVALUATED, 196 NOT EVALUATED.** By type: base 10/10, knee 10/10, rafter
  splice 10/10, ridge 5/5, wind-column top 6/6, wind-column base 6/6, brace end 48/48 evaluated; cleat 0 of 196 (all NOT
  EVALUATED). End-rafter variant: 295 joints, cleats the only NOT EVALUATED.
- **Why the 50 % rule governs at every frame joint of building 1** (25 joints, Mu+, Mu− and Vu): the frames are the span-rule
  PLACEHOLDER sizes, oversized for this load. Line 3 knee: governing −M 345.3 kN·m (V 60.9, P 93.7) under LRFD 1.2D +
  1.6Lr (+C) [−N] at the column top; φMn = 1 038.2 kN·m (column top, shallower than the haunch: Zx 3 546 168 < 3 716 000;
  F4, compression-flange local buckling F4-13 governs — longhand 1 038.3); M/φMn = 0.333; Phase 4 ratio of column A AT
  that section 0.3505 (H1-1b, P/Pc 0.036). The highest M/φMn of any frame joint is 0.333 (knee), the splice 0.31, the ridge
  0.27; V/φVn ≤ 0.15. Forces are not low (they are the analysis' own, checked in the slow test) and the capacity is right
  (longhand); the members are heavy: Phase 4 sizing takes building 1's frames from 2 551 to 1 669 kg per frame (ratio
  0.39 → 0.89), after which the analysis forces will govern most joints.
- **Roof-bracing eave end — a Phase 2 generator defect, FIXED by the user's decision (2026-11-11):** the eave node was the
  eave strut line (s = 0, the roof line at the column's OUTER face), and "75 mm below the rafter's top flange" put the
  rod end at (x 0, y 8.66, z 5 913.4) — inside the 12 mm outer flange of column F1-CA, 815 mm outboard of the rafter's
  start (y 824); 8 ends on building 1. **Now (`bracing.roof_brace_lines`): the roof X uses the purlin lines from the FIRST
  PURLIN PAST THE KNEE** (s > (hw_knee + 2 tf) √(1 + slope²)) to the ridge purlin; building 1: eave node s 1 185.985,
  rod end (0, 1 188.756, 6 031.442) in the rafter web (host F1-RA), 360 mm inboard of the column's inner face. **Tie rule
  (user 2026-11-11, `bracing.NODE_TIE`):** node candidates within 1 mm of the same distance from the 45° target → the purlin
  nearer the eave (it was decided by the 0.001 mm rounding of the lines). Building 1's 45° target is such a tie (592.993 /
  592.992) → the next node is 5 929.925: first diagonal 7 648.854, deepest roof panel still 5 929.9 → roof / wall diagonal
  forces unchanged (21.37 / 21.32 kN LRFD). Joints unchanged in number (291; 95 evaluated, 196 cleats NOT EVALUATED);
  brace-end hosts rafters 32 / columns 16 (were 24 / 24). Fewer than two purlin lines past the knee on a slope → refused.
- **Eave transfer — DECIDED (user 2026-11-11): option (a), an automatic check in step 5** (below). Why: at each eave of a braced bay the roof truss must hand its
  reaction to the wall X (top in the column web plane, 100 mm below the eave): **15.2 kN LRFD on building 1** (30.4 kN
  per braced bay / 2 side walls). From the first-purlin node it travels through the rafter's haunch end (weak-axis shear
  and bending, ≈ 15.2 kN × 0.36 m ≈ 5.5 kN·m), the knee end plate (bolt shear along the building) and the column top
  (weak axis, down to the wall X top). The eave strut does NOT carry it (no diagonal in the eave panel). Neither the
  2D frame analysis nor the member checks see these out-of-plane actions — before the move the same gap existed with the
  node at the column. Step 5 checks the transfer automatically (haunch-end weak-axis bending, knee bolt shear along the
  building, column top); if it fails, the result says so and suggests an eave-panel strut (from the first-purlin node
  to the column top / wall X top).
- **Sized fixture (user 2026-11-11):** `fixtures/manafe3/building1-sized.json` — building 1 with the Phase 4 step 8 frame
  sizes (knee 475, base 300, rafter 300, flanges 200 × 10, webs 6). Full check: interior lines 0.893 (column, H1-1b, AISC
  prismatic; DG 25 0.894), rafters 0.84; end frames 0.47; serviceability 0.80. Joints: **analysis force governs 21 of the
  75 capacity-rule actions** — on each interior frame (2, 3, 4) the knee Mu+ (217.7 vs 0.5 × 395.0) and Mu− (341.8),
  the splice Mu− (140.5 vs 0.5 × 233.5) and the ridge Mu+ (146.9); **the 50 % rule governs the other 54**: every action of
  the end frames 1 and 5 (half the tributary width), the splice Mu+, the ridge Mu−, and **every Vu** (V/φVn ≤ 0.19 on PEB
  frames — the shear rule will nearly always govern the end-plate bolt shear).
- **Placeholder warning (user 2026-11-11):** `placeholder_warnings(b)` → `building_joints()["warnings"]`: main frames on
  the span-rule sizes (sizes not given, or equal to `default_sizes` of the typed span), wind columns / end rafters on the
  generator's section. Step 8 shows them in the browser.
- Tests (`test_joints.py`, 9): counts of building 1 and of an end-rafter variant by hand (291 / 295, hosts), settings
  (switches, refusals), the ridge φMn (F3, 447.6, the same for −M: no LTB) and φVn (G2.1, 441.3) longhand, the KNEE φMn
  (F4-13, 1 038.3) longhand, the 50 % rule; not firing on a heavy joint, f = None, moment / shear switched separately,
  bases never; negative controls (a 5 000 kN·m mid-member moment is not the joint's; missing stations, stations 5 mm off
  the joint, no LRFD combination → NOT EVALUATED); slow: line 3 against the analysis' own end stations and reactions,
  the exact counts by type; the end-rafter splice at its own node (30 m span; moved splice; WITHOUT the node → NOT
  EVALUATED; the node changes neither the ridge moment nor the reactions).

**Step 2 — what was built (2026-11-11):** `engine/connections/baseplates.py`, every main-frame and wind-column base. NOT FOR ISSUE.
- **User decisions (2026-11-11):** anchor grade default **F1554 Gr 36** (editable; ISO 8.8 / 10.9, F1554 55 / 105 offered);
  rod layout per building, default **inside the flanges** (2 rods each side of the web), outside (field-fix-10 layout)
  available; **anchors in shear, no friction credit, plate washers WELDED** (a note on every result, carried to the
  detail); breakout / pryout failures name the mode and suggest a larger edge distance / pedestal, anchor reinforcement
  (hairpins or ties) or a shear lug — **no shear-lug check yet** (later item); anchors **designed** (smallest rod M16 … M36,
  then the shortest embedment).
- Engineering = bimsteelauto_connections, unchanged: `design_base_plate` (DG 1 Sect. 3.1–3.4 + J8: bearing, eccentricity,
  net uplift, thickness; Eq. 3.4.5–3.4.7 for rods outside the flanges) and `check_anchors` (ACI 318-19 Ch. 17).
- **New model, rods inside the flanges (user-approved):** `inside_rod_plate` — the plate cantilevers from the web face,
  lever = rod to web face, 45° spread → the two rods of one side share min(2 lever + s, d − 2 tf); φ Fy b_eff t²/4 ≥ T ×
  lever. **The DG 1 section / example that gives it is TO CONFIRM against the printed guide** (only Sect. 3.1–3.4 are
  transcribed in bimsteelauto; believed Sect. 3.2, tensile axial loads) — VERIFIED False.
- Cases per frame base (forces from step 1, analysis alone): largest compression with its H, largest uplift with its H,
  largest |H| with its V; wind columns: largest P / uplift with the largest V (conservative pairing). Pinned uplift → all 4
  rods share T; with a moment the tension row (2 rods).
- **Claude's detailing rules — TO CONFIRM (constants in the module):** 4 rods, ISO metric thread areas with F1554 Gr 36
  strengths (F1554 is supplied in inch sizes: which does the user buy?); holes / plate washers DG 1 Table 2.3 as tabulated
  in the upstream app (not re-read from the guide; its 2-1/2 in. row repeats the 2 in. hole — a likely slip, never
  reached ≤ M36); clearance rod centre to a steel face = washer/2 + 8 (assumed weld leg) + 5, rounded up to 5; spacing ≥ 4d
  (ACI 17.9.1) and ≥ washer + 10; inside: plate = footprint + 25 each side; outside: rods c beyond the flanges, plate edge
  c; embedment 150 mm upward in 25 mm steps to pedestal depth − 100; A2/A1 from the largest similar rectangle in the
  pedestal (≤ 4). Plate palette = the library's (12 … 70 mm). Plate grades: S275 / S355 / A572 Gr 50 → the library's
  names; **St 37 / 44 / 52 → NOT EVALUATED** (not in the library; no invented mapping). Note: the library's S355 plate
  Fy is 355 to 40 mm (EN 1993-1-1 Table 3.1), Manafe3's member inputs use EN 10025-2 (345 above 16 mm).
- Statuses: DESIGNED; **PLATE DESIGNED - ANCHORS NOT EVALUATED** (no pedestal: the rods are sized on steel only and the
  concrete modes are not shown as checked); FAILS (with the fixes; reported at the SMALLEST rod whose steel passes, at the
  deepest embedment that fits — concrete shear breakout barely depends on the rod); NOT EVALUATED (no forces, an unknown
  grade, rods that do not fit). `app_params` = the app's base-plate parameters for steps 7 / 8.
- **Building 1 (placeholder frames):** no pedestal → 16 bases "PLATE DESIGNED - ANCHORS NOT EVALUATED", M16, 12 mm plates
  (inside layout 375 × 300, rods 65 × 90). Pedestal 600 × 500 × 700: 6 frame bases FAIL on **concrete shear breakout**
  (U 1.80 under the 65 kN thrust; fixes listed); 1 300 × 700 × 900: all 16 DESIGNED (M16, hef 150, interaction ≤ 0.94).
  The 65 kN thrust in shear breakout is what a PEB base usually needs a shear lug or hairpins for — the shear-lug check is
  the next item to decide.
- Not checked yet (stated): the column-to-base-plate weld (proposal: with the welds of step 4), the shear lug, the
  pedestal itself (reinforcement, bearing on the footing), the grout.
- Tests (`test_baseplates.py`, 8): DG 1 rows and clearances, both layouts by hand, the inside-rod plate longhand (and the
  flange cap), anchor steel tension / shear longhand (φNsa 188.40, φVsa 78.37 kN), no pedestal → concrete NOT EVALUATED,
  small pedestal → FAILS naming shear breakout with the fixes, large → DESIGNED, St 37 / no forces → NOT EVALUATED,
  settings refused, outside layout on the library's tension interface; building 1 end to end (slow). (Superseded by 2b
  below: the default grade, minimums and statuses changed.)

**Step 2b — the user's answers and anchor reinforcement (2026-11-11):**
- **Rods are metric; default anchor grade ISO 4.6** — added to bimsteelauto_connections at the user's request (route:
  library branch + public push, user-approved): **bimsteelauto 0.15.2** (`feature/anchor-grade-4-6` b0424c1, merged to
  `main` e7c9de9, pushed; Manafe3 re-pinned). 4.6: fya 240, futa 400 MPa (ISO 898-1:2013 Table 3: ReL 240, Rm 400, A 22 %)
  — **values from memory of the standard, `GRADE_SOURCES["4.6"]["checked_against_source"] = False`**; **NOT ductile** (user:
  brittle until the supplier's certificate shows reduction of area ≥ 30 %, ACI 318-19 2.3) → φ 0.65 tension / 0.60 shear.
  F1554 grades are offered ONLY with inch rods (5/8 … 1-1/2 in., the library's UNC areas). Library suite: 1053 passed (the
  known `test_fc_adapter` failure; `test_bsa_dxf` needs ezdxf, not in Manafe3's env).
- **St 37 / 44 / 52 plates** — also in 0.15.2 (`bolts._PLATE_GRADES` ST37 / ST44 / ST52, the ecp205-lrfd values ×
  98.0665, both thickness bands).
- **Detailing rules ACCEPTED**, except the embedment: **main-frame columns ≥ M20 and hef ≥ 300 mm, wind columns ≥ M16 and
  ≥ 150 mm, 50 mm steps** — all settings (`BaseSettings.rod_min_frame / rod_min_wind / hef_min_frame / hef_min_wind /
  hef_step / hef_cover`). **Anchor type stated on every result: HEADED** (hex head / heavy hex nut; the library's pullout
  uses that bearing area); hooked refused.
- **Shear lug and the column-to-plate weld → step 4** (with the welds).
- **Anchor reinforcement — the first fix for shear breakout** (`anchor_reinforcement`, ACI 318-19 **17.5.2.1(b)**, φ 0.75 —
  clause numbering TO CONFIRM against the printed code): when ONLY the concrete breakout in shear fails, hairpins (2 legs
  each, ≤ 4, bars 10 / 12 / 16 / 20 B500, fy 500 from Job units) with φ As fy ≥ Vua replace it; 17.8 is re-run with φVn =
  min(rod steel, reinforcement, pryout). ld per Table 25.4.2.3 (simplified; db ≤ 20: / 2.1, ψg 1.15 for B500) reported.
  **Status "DESIGNED WITH ANCHOR REINFORCEMENT - DEVELOPMENT NOT EVALUATED"**: legs within 0.5 ca1, development on both
  sides of the breakout surface and the Table's spacing / cover conditions are listed TO CHECK — never a pass. A pryout or
  any other failure is not "fixed" by hairpins (FAILS with the fixes).
- **Building 1 (placeholder frames, V 45, C), fresh analysis:**
  - no pedestal: 10 frame bases 4 × M20 4.6, plate 375 × 300 × 12, rods 80 × 100 (inside); 6 wind-column bases 4 × M16,
    370 × 200 × 12, rods 65 × 90 — all "PLATE DESIGNED - ANCHORS NOT EVALUATED" (rod steel ≤ 0.57).
  - **pedestal 600 × 500 × 700:** end frames (F1, F5) DESIGNED, M20, hef 300, max interaction 0.983 (shear breakout);
    interior frames (F2–F4, thrust 64.8 kN) **1 hairpin T12 each** (As 226 ≥ 173 mm², φVn 84.8 kN, ld 600 mm), max
    interaction 0.885 — "development NOT EVALUATED"; wind columns DESIGNED, M16, hef 150, max 0.443.
- Tests (`test_baseplates.py`, 12): + rod lists (metric / inch, minimums, hef steps), M20 layout and inside-rod plate
  (9.055 mm), 4.6 steel modes longhand (φNsa 254.80, φVsa 112.90 kN), the hairpin design and ld longhand, 17.8 cases,
  hairpins do not fix pryout, reinforcement off → FAILS naming it, a shallow pedestal → NOT EVALUATED, hooked refused, St 37
  (Fy 235.36) through the inside-rod plate, building 1 end to end (slow: 10 DESIGNED + 6 with hairpins on 600 × 500 × 700).

**Step 3 decisions (user, 2026-11-12 — confirmed list):**
1. Forces: step 1's design forces (the 50 % rule on Mu+, Mu−, Vu at knee / ridge / splice). Axial tension CONCURRENT with
   the moment (the same combination; step 1 stores it), the worst pair: Mu_eq = max(|M|, f × φMn) + T (d − tf)/2;
   compression not credited.
2. Knee: extended above AND below; ONE plate and ONE bolt layout for both signs; the result names the sign that governs
   the bolts and the one that governs the plate.
3. Ridge and rafter splices: extended below the bottom flange only, FLUSH at the top; the −M side = the DG 16 flush
   unstiffened case (two-bolt, then four-bolt), Yp WRITTEN FROM MEMORY (VERIFIED False, section TO CONFIRM from the
   user's photos of DG 16), thick-plate procedure, prying cross-checked; a failing flush side is reported with fixes.
4. Extended configurations from the library (AISC 358 Yp, VERIFIED): 4E → 4ES → 8ES.
5. Bolts 8.8, pretensioned BEARING-type, threads INCLUDED, no slip check (slip-critical: roadmap, cranes); ≥ M20 on
   main-frame end plates, M16 on secondary joints (settings), up to M30; ONE bolt size and grade per joint type; 8.8
   failing up to M30 → 10.9, reported.
6. Shear: each moment sign separately; the compression-side bolts first; if they fail, ALL bolts with the J3.7
   interaction (the method is reported); J3.10 bearing / tear-out on every ply.
7. Plate stock (setting) 12, 15, 16, 18, 20, 22, 25, 30, 35, 40, 50; ONE thickness per joint type; plate grade = the frame's.
8. Geometry defaults: bp = bf + 50 ↑10, g 100 (≤ M24) / 140, pf = max(40, d + 12), de 1.5 d, pb 3 d; checks: gauge vs plate
   and column-flange edge (Table J3.4M), web wrench clearance, pitch clears the flange weld + nut.
9. Welds: flanges FULL STRENGTH (since 2026-11-15: the DESIGN strength 0.9 Fy bf tf, replacing the nominal Fy bf tf —
   user decision, open item 5), web its yield (0.9 Fy tw) over the tension-bolt zone + the shear; double fillets; a full-strength
   fillet over 12 mm (setting) → CJP, said so; minimum legs AISC 360-16 Table J2.4 (thinner part); ONE weld size per joint
   type; E70XX (482 MPa). The t − 2 maximum does not apply (welds on the plate face, not along an edge) — so the library's
   size_fillet_weld (edge rule, thicker-part minimum) is not used for these T-joints. (Superseded 2026-11-12: the library 0.15.3 tee mode is used — see "Step 3 follow-ups".)
10. 4ES / 8ES end-plate stiffeners sized; their welds NOT EVALUATED until step 4.
11. Column side (knee): J10.1 / .2 / .3 / .6; J10.4 NOT APPLICABLE (the flange-level stiffeners restrain the flanges);
    J10.5 NOT APPLICABLE (one-sided connection — the library runs it; listed, not used). Transverse stiffeners at both rafter
    flange levels at EVERY knee (standard detail), sized up by J10.7 / J10.8; panel zone φVpanel = min(J10.6, G2.1 shear
    buckling of the panel web, kv from the stiffener spacing); a shortfall → diagonal stiffener As = (Vu − φVpanel) /
    (φ Fy cos θ), shown in the calc (doubler as an option); stiffener welds NOT EVALUATED until step 4.
12. Every default listed on each result as an editable setting; statuses DESIGNED / FAILS (with fixes) / NOT EVALUATED.

**Step 3 — what was built (2026-11-12):** `engine/connections/endplates.py` (`design_joint`, `building_endplates`). NOT FOR ISSUE.
- Library parts used unchanged: 4E / 4ES / 8ES Yp, DG 4 thick-plate thickness, no-prying bolt moment, bolt strengths,
  prying (`evaluate_bolt_row`), J10 (`check_column_side`); pyaisc360 J3.10, J3-3a, G2.1. Manafe3 parts flagged
  (`endplates.VERIFIED`, all False): DG 16 flush Yp, T-joint fillets, Table J2.4 / J3.3M / J3.4M values, column
  stiffeners and the diagonal, the end-plate stiffener, the clearances, the web tension-zone weld rule, J10.4 / J10.5.
- One size per joint type: each joint designed, then the per-type maxima (bolt size + grade, plate, weld legs) imposed on
  every joint of the type and re-checked until stable.
- **Building 1, placeholder frames:** 25 joints DESIGNED; every type 4E, M24 8.8, plate 16; flange fillets 10, web 8 (ridge
  5); knee transverse stiffeners 12 mm (J10.7 force: J10.1 flange bending governs), no panel-zone diagonal needed; shear
  max 0.80 (compression-side bolts).
- **Building 1, sized frames (fixture):** 25 DESIGNED; 4E, M24 8.8, plate 18; flange fillets 8, web 5; interior knees
  transverse stiffeners 16 mm and a **panel-zone diagonal pair 12 mm** (Vu 701.3 > φVpanel 562.7: As = 138.6 × 10³ /
  (0.9 × 355 × 0.708) = 612 mm²); at the ridge and splices the **flush top side governs** (four-bolt flush).
- Tests (`test_endplates.py`, 9): DG 16 arithmetic longhand (2729.94 / 3614.82), extended rows by hand, the full-strength
  flange weld (8 mm, 736.07 kN) and the CJP switch, J2.4 by the thinner part, the CONCURRENT pair (never max M with max T
  of another combination; the 50 % rule + concurrent T), the shear fallback to all bolts with J3-3a (F'nt 337.9 MPa), a
  knee with one layout for both signs, J10.4 / J10.5 not applicable, G2.1 kv / Cv1 / φV and the diagonal formula by hand,
  the flush ridge, the 10.9 escalation at 200 kN·m (8.8 φMnp 191.1, 10.9 238.9 by hand) and its negative control, NOT
  EVALUATED cases, settings refused; the sized building end to end — one size per type, stiffeners at every knee (slow).

**Step 3 follow-ups (2026-11-12, user request):**
- **Library fillet routine fixed:** bimsteelauto 0.15.3 (main `3a2bf3f`, pushed with the user's approval):
  `size_fillet_weld(joint="tee", min_leg_by="thinner")` — no J2.2b t − 2 edge maximum on a T-joint, Table J2.4 minimum by
  the thinner part; both default to the old behaviour. Manafe3's `tjoint_fillet` and `j24_min_leg` are removed; the
  adapter `fillet_or_cjp` only carries the settings (leg list, one size per type, the CJP switch above 12 mm).
- **DG 16 mark:** every ridge / rafter-splice result carries `not_for_issue = "NOT FOR ISSUE: DG 16 flush unverified"`
  (and the building result lists the joints) while `VERIFIED["flush_Yp_DG16"]` is False; knees are not marked.
- A failing joint names each failing check (`failed_checks`) instead of a generic sentence.
- Building 1 (sized) unchanged with the library routine: 25 DESIGNED, 4E M24 8.8, plate 18, flange fillets 8, web 5,
  interior-knee stiffeners 16 mm and the diagonal pair 12 mm (As 612.3 mm²); 15 ridge / splice joints marked.
- **Decision → test** (`engine/tests/test_endplates.py`, hand values in its docstring):

| # | Step 3 decision | Test(s) |
|---|---|---|
| 1 | Concurrent (M, T) pairs per sign; compression not credited; 50 % rule | `test_concurrent_pair_not_max_with_max` |
| 2 | Knee: one layout for both signs, the governing sign by Mu | `test_knee_both_signs_by_hand`, `test_knee_one_layout_both_signs_and_column_side` |
| 3 | Order 4E → 4ES → 8ES, smallest bolt first; M20 minimum on main frames | `test_config_and_bolt_order_by_hand`, `test_defaults_bolt_minimum_plate_width_gauge_stiffener` |
| 4 | Ridge / splice: flush top side (two-bolt, then four-bolt), extended bottom | `test_ridge_flush_side_by_hand`, `test_ridge_flush_top_and_grade_escalation` |
| 5 | DG 16 flush from memory, NOT FOR ISSUE mark | `test_flush_yield_lines_arithmetic`, `test_dg16_mark_only_while_unverified` |
| 6 | 8.8 → 10.9 only when allowed | `test_ridge_flush_top_and_grade_escalation` |
| 7 | Shear: compression-side bolts, else all bolts with J3.7 | `test_shear_fallback_to_all_bolts_with_J3_7` |
| 8 | Welds: full-strength flange, web tension zone + shear, tee joint, CJP above 12 mm | `test_welds_by_hand`, `test_cjp_switch_above_12mm_by_hand`, `test_web_weld_and_tee_joint_by_hand` |
| 9 | Clearances (edge, wrench, pitch, column flange edge) → FAILS named | `test_clearances_by_hand` |
| 10 | 4ES / 8ES end-plate stiffener | `test_defaults_bolt_minimum_plate_width_gauge_stiffener`, `test_config_and_bolt_order_by_hand` |
| 11 | Column side: J10.1–3 / J10.6, J10.4 / J10.5 not applied, stiffeners at every knee, G2.1, diagonal / doubler | `test_column_side_J10_and_stiffeners_by_hand`, `test_knee_one_layout_both_signs_and_column_side` |
| 12 | Every default listed; DESIGNED / FAILS / NOT EVALUATED; one size per type | `test_not_evaluated_and_settings`, `test_sized_building_1_end_plates_one_per_type` (slow) |

**Step 4 decisions (user, 2026-11-12):**
1. Flange-to-web demand q = V·Q/I at each station (envelope of the LRFD combinations; tapered: no credit for the sloping
   flange's vertical component) PLUS the local concentrated loads at flange-brace and purlin points. Shop butt splices of
   flange and web plates are CJP — stated, not designed.
2. Default ONE-SIDED continuous fillet (SAW, PEB practice); both sides automatically in the end zones (item 4) and wherever
   q exceeds the one-sided capacity. Setting `shop_min_leg` = 5 mm; leg = max(J2.4 minimum by the thinner part,
   shop_min_leg, demand).
3. One leg per member segment.
4. Within one depth of a knee / ridge / splice end plate: full-strength web weld, both sides (as the step 3 web weld).
5. Column-to-base-plate weld: uplift and shear on the weld; compression by bearing. AISC M2.6 (unmilled base plates up to
   50 mm) and J1.4 listed as unverified; the result states "base plate <= 50 mm, unmilled"; a plate over 50 mm → NOT
   EVALUATED.
6. Shear in both directions: strong-axis shear on the web welds, weak-axis shear (bracing reactions) on the flange welds;
   uplift shared by weld length; elastic method, vector sum, no directional increase.
7. Shear lug only as the fix when the anchors fail in shear / breakout; per-job setting, default hairpins.
8. Lug: flat plate; ACI 318-19 17.11 (bearing, breakout) and DG 1 (lug bending, lug weld) — both VERIFIED False.
9. With a lug, the lug takes all the shear; the anchors tension only.
10. Column transverse stiffeners welded to the flanges and the web to develop the FULL stiffener strength As × Fy (they
    also take the horizontal component of the diagonal stiffener).
11. Diagonal stiffener welds: As·Fy; doubler welds: its shear strength (J10.6).
12. Non-seismic: AISC 358 is reference only (unverified). End-plate stiffeners: double fillets developing the stiffener's
    strength; CJP only when the fillet needed is over 12 mm (the flange rule).
13. E70XX and the same leg list everywhere; one weld size per joint type; NOT FOR ISSUE; weld symbols in step 7.

**Step 4 — what was built (2026-11-12):** `engine/connections/welds.py` (`building_welds`, `WeldSettings`); the stiffener
welds hooked into `endplates.column_side` / `endplate_stiffener`. NOT FOR ISSUE.
- From the libraries: pyaisc360 J2.4 weld metal and J2-2 base metal, `min_weld_size` (Table J2.4), `get_grade`. Manafe3:
  the shared base metal of double fillets (0.45 Fu t / 2 per line, the user's rule) and, for a plate pulled ACROSS the
  weld (θ 90°: a stiffener into a flange or an end plate), J4.1 min(0.9 Fy t, 0.75 Fu t) shared the same way (Claude).
- Flange-to-web: per station and per LRFD combination q = VQ/I + the local loads of the SAME combination (purlins on
  rafters, girts on columns: w × spacing, w = |dV/dx|; flange braces 2 % of |M|/(d − tf)), spread over lb = t_cleat + 5k
  (83 mm in building 1), vector sum, applied at every station (conservative); one leg per segment; end zones of one depth
  at every knee / ridge / splice, both sides, developing 0.9 × 0.6 Fy tw. Frame columns and rafters, WIND COLUMNS (the
  forces of their member check: C&C 1.0 W simple beam, gable girts, flange braces) and END-WALL RAFTERS (the end-rafter
  frame's LRFD rafter stations; end zones at the end-rafter ridge / splices).
- Base weld: the cases of step 2 (compression, uplift, shear; wind columns paired conservatively as in step 2); braced
  bays: the wall-brace force T cos α (weak axis) and T sin α (uplift), paired ONLY with the frame reaction of the same
  combination — in building 1 the bracing is one longitudinal-wind case and the frame lines have only transverse wind, so
  the 8 braced-bay bases read "PARTIAL - brace case NOT EVALUATED" (never DESIGNED) with the reason.
- Shear lug only with `shear_fix = "lug"` and failing anchors (building 1: no pedestal → anchors not evaluated → no lug);
  f'c from the base-plate settings; the 17.11.3 breakout NOT EVALUATED (U = inf) until the user sends the page.
- Column transverse stiffeners (after the user's review, 2026-11-12): width bs = floor5((bf − tw)/2 − 5) (90 mm for
  bf 200, tw 6; the J10.8 minimum bs + tw/2 ≥ bf/3 is a check only), also in the step 3 sizing. Load path (Claude's
  equilibrium, replacing "Rst + the diagonal's horizontal part", which counted the diagonal twice): the pair carries
  F = max(Rst, ΔV) across its flange contact (thickness, flange welds); of Puf, Puf − F goes from the column flange
  straight into the web, so the stiffener web welds carry F_web = min(F, φVpanel − (Puf − F)) (with a doubler the panel
  takes Vu) and the corner F − F_web goes into the diagonal (its end welds sized for max(As_req Fy, corner / cos θ)); the
  COLUMN WEB under the stiffener web welds on both faces: min(1.0 × 0.6 Fy tw, 0.75 × 0.6 Fu tw) per mm → FAILS "doubler
  or thicker web". Knee stiffeners are FULL DEPTH between the column flanges (web weld d − 2 tf − 2 clip; user
  2026-11-15: they bound the panel zone and the diagonal runs corner to corner); setting `stiffener_depth = "half"` (the
  J10.8 half-depth minimum) is kept only as an option for non-knee stiffeners with no diagonal.
- When only the column side fails, the knee result shows the FIRST end-plate layout that passes everything else (not the
  last layout tried) — Claude's decision, accepted by the user 2026-11-15.
- **Building 1 knees (full-depth stiffeners): all 10 DESIGNED.** Interior knees: stiffeners 90 × 15 × 469.2, 10 mm
  fillets to the flanges, 5 mm to the web; F 601.41, F_web 462.82, corner 138.59 → the 6 mm web 1078.3 N/mm, U 0.844;
  diagonal pair 12 mm, 5 mm end welds. End knees: 90 × 12 × 469.2, 5 / 5 mm; the web 745.5 N/mm, U 0.583. (Half depth
  would have failed: 2156.7 and 1491.1 > 1278 — kept as the negative control.)
- End-plate stiffeners (4ES / 8ES): double fillets developing the DESIGN strength (0.9 Fy ts into the plate, 0.6 Fy ts
  along the flange), CJP above 12 mm.
- Building 1: end plates 25 DESIGNED; flange-to-web 26 members (20 frame + 6 wind columns) one-sided 5 mm (largest
  U 0.31); base welds 5 mm; 8 braced-bay bases PARTIAL (open item 6).
- Tests `test_welds.py` (10, hand values in its docstring); the step 3 tests updated where the welds replaced
  "NOT EVALUATED" and where the stiffener now sizes for its contact (`test_endplates.py`).

**Unverified sources — to check by the user (one list; status as of 2026-11-12):**

| Item | What was assumed | What the user checks | Status |
|---|---|---|---|
| DG 1 inside-rod plate model (step 2) | plate cantilever from the web face, 45° spread, φ Fy b_eff t²/4 ≥ T × lever | DG 1 2nd ed. Sect. 3.2 / Example 4.6 (the user's copy) | VERIFIED False |
| ISO 4.6 anchor values (bimsteelauto 0.15.2) | fya 240, futa 400 MPa, A 22 % (ISO 898-1:2013 Table 3, from memory); NOT ductile | the printed ISO 898-1 Table 3; a reduction-of-area value from the supplier for ductility | checked_against_source False |
| ACI 318-19 17.5.2.1(b) anchor reinforcement (step 2b) | hairpins replace the shear breakout, φ 0.75; ld by Table 25.4.2.3 (simplified, ψg 1.15) | the clause numbers and the ld conditions in the printed ACI 318-19 | VERIFIED False |
| DG 16 flush (governs ridge/splice) (step 3) | two- / four-bolt flush unstiffened Yp as written in `flush_Yp`; it governs the ridge and splice plates of building 1 | the DG 16 table and section (photos), line by line | VERIFIED False; results marked "NOT FOR ISSUE: DG 16 flush unverified" |
| AISC Tables J3.3M / J3.4M, J2.4 (step 3) | standard holes, minimum edge distances (metric, from memory); minimum fillet legs = the library's `min_weld_size` (3 / 5 / 6 / 8 mm) | the printed AISC 360-16 tables | VERIFIED False |
| Column stiffeners J10.7 / J10.8 and the diagonal (step 3) | widths / thicknesses / half depth; As = (Vu − φVpanel)/(φ Fy cos θ) | the printed J10.7 / J10.8 and the diagonal practice | VERIFIED False |
| J10.4 / J10.5 not applicable at a one-sided knee (step 3) | J10.5 needs forces on both flanges; J10.4 restrained by the stiffeners | AISC 360-16 J10.4 / J10.5 | confirmed by the user 2026-11-12 (reading); VERIFIED False until checked in the code text |
| AISC 358 end-plate stiffener (step 3) | ts ≥ tw, hst/ts ≤ 0.56 √(E/Fy), Lst = hst / tan 30°; REFERENCE ONLY (non-seismic, user 2026-11-12); its welds by the Manafe3 rule (step 4: develop the design strength, CJP above 12 mm) | AISC 358-16 Sect. 6 | VERIFIED False |
| AISC 360-16 M2.6 / J1.4 (step 4) | unmilled base plates up to 50 mm bear without milling; compression by bearing, the weld takes uplift and shear; over 50 mm → NOT EVALUATED | the printed M2.6 and J1.4 | VERIFIED False |
| ACI 318-19 17.11 shear lug (step 4) | 17.11.2 bearing φ 0.65 × 1.7 f'c Aef Ψbrg (Ψ: 1 + Pu/(n Nsa) ≤ 1 tension, 1 + 4Pu/(Abp f'c) ≤ 2 compression); 17.11.3 breakout NOT EVALUATED | the printed 17.11.2 / 17.11.3 and Fig. R17.11.3.1 (the user sends them) | VERIFIED False |
| AISC DG 1 shear lug (step 4) | lug bending t ≥ √(4 Mu / (0.9 Fy B)), Mu = Vu (G + h/2); the lug weld: shear + the moment as a couple over t | DG 1 2nd ed. (the lug section) | VERIFIED False |
| Step 4 rules by Claude | local-load spread lb = t_cleat + 5k; the end zone develops 0.9 × 0.6 Fy tw; the stiffener corner clip 20 mm (setting); weak-axis base shear = the wall brace's T cos α; J4.1 for plates pulled across a weld; stiffener thickness for its flange contact; grout 50 mm (setting) | the user's call | VERIFIED False |
| J4.1 for welds loaded across their axis (step 4; library 0.15.4 `base_mode="tension"`) | a plate pulled across a double fillet (a stiffener into a flange or an end plate, a diagonal end): its limit is J4.1 min(0.9 Fy t, 0.75 Fu t), shared by the two lines — Claude's reading, not the user's shear rule | AISC 360-16 J2.4 / J4.1 | VERIFIED False |
| ASCE 7-16 Ch. 28 envelope limits (open item 6) | low-rise: mean roof height h ≤ 60 ft (18 m) and h ≤ the least horizontal dimension (§26.2 / §28.1.2), from memory; not met → the longitudinal pairing NOT EVALUATED | the printed §26.2 definition and §28.1.2 | VERIFIED False |
| Fig. 28.3-1 torsional-case exception (open item 6) | "one-story buildings with h ≤ 30 ft (9.1 m), buildings two stories or less framed with light-frame construction, and buildings two stories or less designed with flexible diaphragms need not be designed for the torsional load cases" — from memory; Manafe3 uses one-story h ≤ 9.144 m or a stated flexible diaphragm (the user wrote 9 m) | the printed Fig. 28.3-1 note | VERIFIED False |
| Longitudinal pairing rule (open item 6) | Case B brace force × the combination's wind factor with the frame reaction of the same combination; the §28.3.4 minimum family with dead load only | the user's decision; the physics by Claude | VERIFIED False |
| Stiffener-to-diagonal corner load path (step 4) | F = max(Rst, ΔV); the web welds carry min(F, φVpanel − (Puf − F)); the corner F − F_web into the diagonal; the column web takes the web welds from both faces | the user's call (statics by Claude) | VERIFIED False |
| Shared base metal of double fillets (step 4) | 0.45 Fu t / 2 per line (user rule) | done in bimsteelauto 0.15.4 (`t_shared`, opt-in; Manafe3 uses it) | closed 2026-11-15 |
| Web weld tension zone, clearance rules (step 3) | zone = innermost tension row + 2 d; nut corner + 5 mm | Claude's detailing rules — the user's call | VERIFIED False |
| bimsteelauto_connections limits found (step 3) | `size_fillet_weld`: fixed by 0.15.3 tee mode (the default stays thicker-part minimum + edge maximum); `check_column_side` always runs J10.5 (Manafe3 lists it as not applicable) | whether to change the library defaults / J10.5 (the user's decision) | fillet: fixed 2026-11-12; defaults and J10.5: open |

## Field fixes from the first real project (R1) — done (2026-11-08 / 09)

The user's list (P1 bugs → P2 PEB generator → P5 clash → P6 views → P8 agent API → P3 crane → P4 concrete → P7 drawings
→ regression project R1), worked in that order; Phase 4 resumes at step 5 afterwards. Tests: `tests/bin/test-manafe3-fieldfixes.mjs`.

### Field fixes — decisions taken (Claude; ordinary detailing / UI choices, editable)
- **1 Grids:** "Building grids" in the Building form: **merge** (default) / none / replace (asks first; never remembered).
  Merge: every existing line stays; an incoming line within 1 mm of an existing one IS that line; a new position keeps
  its label, or label′ (3′, 3″ …) when the label is taken. Levels are always merged (same z ±1 mm or same name = kept).
  Footings and your own members were never removed (only `gen: 'peb'` members are regenerated) — now tested.
- **2 / 15 Concrete:** a member's material is concrete when it reads C20…C100, C30/37, "… fcu / fck", "concrete", "RC"
  or B25 (`app/manafe3/materials.js`); everything else is steel. Such a part weighs 0 kg as steel, carries
  `concreteM3` (= profile area × length) and a warning; status bar and model summary show steel kg · rebar kg ·
  concrete m³ (members + footings). Left out of the steel clash check. BOM rows still list the part (0 kg).
- **3 Load:** on the model's 'load' event (and a new Model) the selection resets, the Name field is rewritten even when
  focused, and every Manafe3 panel resets (`app/manafe3/panels.js`: Analysis results cleared, Building / Loads forms
  closed — they refill from the open model).
- **4 Move / rotate / mirror:** the app's own transform (transform.js) was ALREADY right for rotations and moves —
  rotate 90° about Z, 37° about an off-grid point and a move keep all 648 parts of building 1 (roll u / v, centre,
  every hole; frame columns, wind columns and jambs included). The field report most likely came from editing
  coordinates without the transform (an agent has no transform tool yet: item 26 adds one that calls transformRefs).
  Real defect found and fixed: a MIRROR treated a lipped C (CFC) as an I (kept v) instead of turning it over like a
  channel. A Z's mirror image is a Z of the other hand, which no profile here describes: a mirrored Z stays a Z of the
  same hand at the image place (stated, not changed).
- **5 Placement:** "Placement on site" in the Building form: origin X, Y, Z (where the first frame line meets span line A,
  and the building's ground) and plan rotation (any angle, about Z, counter-clockwise). Applied in the app through
  transform.js (`placementXf`), so every member keeps its roll. Grid lines are placed for multiples of 90° only (grids
  here are x = c / y = c lines); at other angles the members are placed and the status bar says the grids were not added.
- **6 Uneven bays:** "Uneven bays" overrides number × spacing: "6600 6000 …" or a site-grid range "A-L" / "A to L"
  (spacings of those lines on whichever axis has both labels; the frame lines take those labels). Engine
  `BuildingInput.bays`, `frame_xs()`; analysis tributary widths follow (line B of 6600 / 6000 = 6.3 m, tested).
  The origin is NOT moved to the first grid automatically: set origin X/Y to grid A's position.
- **7 Span reference:** outside (default, as before) / centreline (column centrelines AT THE BASE: steel span = span +
  hw_base + 2 tf) / grid (grid lines `grid_inset` outside the steel). Engine `resolve()` gives the steel span and a
  `y_shift` the app applies with the placement; sizes come from the TYPED span.
- **8 Several buildings:** `state.m3buildings = [{ id B1…, name, spec }]`; members tagged `gen: 'peb:<id>'`. An older
  file's single `m3building` and `'peb'` members read as B1 and are re-tagged on the next edit. The Building form has a
  building picker (opens on the selected member's building), a Name and "Delete this building". `applyBuilding` without
  an id makes a NEW building; with `{ id }` it regenerates only that one. Levels of a second building with a taken
  name get the building's name ("Eave F&S-2"). Analysis… has a building picker. Still open: a button in the
  Properties panel ("Edit this building") — the picker preselection covers it for now.
- **9 Footings:** Building form "Footings: none / pads" (default none): a pad (FOOTING_DEFAULTS 2000 × 2000 × 600 —
  placeholder, NOT designed) centred under the base section of every main-frame column (F<n>-CA/CB) and wind column
  (WF/WL<n>) of THAT building that has no footing yet; door jambs get none. PEB › "Remove footings with no column":
  a footing is kept while any column's base point lies in its plan within 1 000 mm of its top (`app/manafe3/peb-footings.js`).
- **10 Base plates:** PEB > "Base plates for all PEB columns": one per main-frame / wind column without one; placeholder
  sizes from the base section (plate (d + 200) x (bf + 100) x 20, 4 rods at sx = d + 100, sy = bf; rods, grout, weld from
  BASEPLATE_DEFAULTS) - NOT designed (Phase 5). The connection sees the built-up column's base section; the plate joins the
  bottom segment's assembly; the anchor bolt plan sheet appears in Drawings.
- **16 Clashes:** the Clashes panel groups by type (the two members' generator roles, kept on each generated member as
  `m3role`) and has "Hide clashes at generated connection points (until Phase 5)": both members generated AND a joint the
  generator leaves as a point (`app/manafe3/clash-groups.js` GENERATED_JOINTS - the user's list plus what building 1
  showed: brace ends at rafters / columns, flange braces at purlins / girts and in pairs, wind-column top and cap plate
  under the rafter, eave strut on the column). Anything else, or any member you placed, always shows. Found and fixed:
  20 false clashes in building 1 - a tapered segment's web was checked as its bounding box against its own sloping
  flange; plates of ONE built-up segment are no longer checked against each other (a splice between segments still is).
- **17 Elevations:** the drawing set already made GA elevations on both grid axes; the gap was the app's Elevation VIEW,
  which listed only the y lines (upstream assumed letters on y). It now lists every grid line of both axes
  (`app/manafe3/views.js`; x lines are seen from +x like the elevX sheets), so R1's A-L (x lines) appear. The view tabs
  of a workspace layout list them too.
- **26 Agent tools:** why `window.detailcraftControl.list()` returned []: the host's assistant switch is OFF by default
  (Settings > Assistants; `list()` filters every tool out until the person turns it on and picks groups). Not changed in
  code: turning assistants on stays the person's. Added Manafe3 tools on the same control (`app/manafe3/agent-tools.js`):
  peb_buildings, peb_building_set (new or regenerate by id; placement, bays, span reference, footings, base plates),
  members_add (several, one step), members_transform (move / rotate / mirror through transform.js; a building takes the
  footings under its columns along), members_delete (a filter is required and `expect` must equal the match count - call
  with -1 to count), clash_groups, sheets_export (chosen sheets as one PDF or a DXF zip), model_replace. Each edit = one
  undo step "Assistant: ...".
- **27 model.replace(label, text):** a new model as ONE undoable step (history kept; load() still clears it); emits 'load'
  so the panels refresh; a bad file changes nothing.
- **11-13 Crane runway (geometry only):** PEB > "Crane runway..." per building (`app/manafe3/crane.js`, inputs kept on
  the building as `crane`). Per side and bay range: bracket (catalog, default HEA300) square off the column's INNER face at
  the frame line, top at the girder underside, length = rail offset + wider flange / 2 + 50; girder = the existing
  BUILT-UP member type, constant depth, unequal flanges (default web 700 x 8, top 250 x 12, bottom 200 x 10), straight top
  on top of steel = rail top - rail height, frame to frame; rail PL50x50 on the girder; end stops PL20x200 x 250 high
  150 inside each end. The rail line is measured from the inner face AT BRACKET LEVEL on the real tapered column; the
  flange-to-face clearance at the girder TOP is checked (< 25 mm reported). R1 block 2 (fixture `r1-block2.json`,
  span 28 900 c/c read as COLUMN CENTRELINES - to confirm): rail line y 977.96, clearance 148 mm by hand, 48 members, no
  clash with the tapered columns. Every model with crane members shows "Crane members are geometry only - not analysed
  or designed." (build problems, Analysis note). Crane loads stay on the roadmap.
  Found and fixed on the way: the clash check tested a tapered web (shaped plate) as its bounding box; it now uses the
  web's true strip at each station - building 1's clashes 327 -> 260, every one removed was a box artefact.
- **14 Metric footings:** PEB > "Job units..." (kept in the model as `m3units`): footings imperial (default, as before)
  or metric - BS 4449 B500 bars 8-32 mm (upstream's bar table, BS 8666:2020 bends), named T16 / Y16 / O16 / H16 (the same
  bar; default T), concrete C25/30, C30/37 (default), C35/45 with fck / fcu (EN 206 Table 12), written on the footing as
  'C30/37 fck30 fcu37'. Metric: new PEB pads get H16 @ 250 mats and H20 starters (upstream's EU defaults); labels and
  the bending schedule use the job's bar mark. Footings already placed keep their bars. The app's own footing tool keeps
  its Settings > steel (US / EU) defaults.
- **15 RC members:** stay on the roadmap; the concrete-material warning, weight and clash exclusion are item 2's.
- **18 / 19 / 24 / 23 Drawings:** the Drawings dialog has two panels added from JS (`app/manafe3/drawings-ui.js`):
  "Drawing settings" (kept in the model as `m3drawings`, cleaned by `drawings.js cleanDrawingSettings`): text x
  (0.5-3), dimension text height (mm), line weights x, hide marks on GA plans, GA sheets' paper (default **A1**; assembly
  sheets keep the set's paper), and for the sheet shown its own paper, scale (else the largest standard scale that fits)
  and drawing number; the title block gains Client, Project, Job no. and Status (For approval (default) / For
  construction / For fabrication / As built) and a Revision used until a sheet is issued. The issue note now defaults
  to the status (was "Issued for fabrication"). "Export sheets": tick several -> one merged PDF or a DXF zip (also the
  agent's sheets_export). Without Manafe3 settings drawings.js draws exactly as upstream (its tests unchanged).
- **22:** GA elevations on all grid lines in both directions - already so in the drawing set (tested with item 17).
- **20, 21, 25 -> Phase 6** (the brief's fallback): GA-00 3D view sheet with area labels and steel summary, the typical
  frame section sheet per building, and the "Approval set" / "Shop drawings" presets.

### Field fixes — status

| Item | Status | Where / why |
|---|---|---|
| 1 grids none / merge / replace | done | peb-building.js `mergeLines`; levels merged |
| 2 weight by material | done | materials.js; concrete as m³, never steel kg |
| 3 refresh on load | done | panels.js; Name field forced |
| 4 move / rotate / mirror | done | transform already right; CFC mirror fixed |
| 5 placement origin + rotation | done | `placementXf`; grids for multiples of 90° only |
| 6 uneven bays / from site grids | done | engine `bays`; "A-L", "14-7" |
| 7 span reference | done | engine `resolve()`: outside / centreline / grid |
| 8 several buildings | done | `m3buildings`, gen `peb:<id>`; Properties-panel button not built (picker instead) |
| 9 footings / remove orphans | done | peb-footings.js |
| 10 base plates + anchor sheet | done | base section stand-in; placeholders |
| 11, 12 crane runway, built-up girders | done | crane.js; R1 block 2 checked |
| 13 crane warning | done | build problems + Analysis note |
| 14 metric rebar, C-grades | done | units.js, Job units… |
| 15 RC member type | roadmap | warning / weight / clash exclusion done with 2 |
| 16 clash groups + generated filter | done | clash-groups.js; + true web strips (327 → 260 false clashes gone) |
| 17 elevations on lettered grids | done | views.js, view3d x-axis elevations |
| 18, 19, 23, 24 drawings | done | drawings.js settings, drawings-ui.js |
| 22 elevations all grid lines | done | already in the drawing set |
| 20, 21, 25 | moved to Phase 6 | 3D sheet, typical frame sheet, presets |
| 26 agent tools | done | agent-tools.js (assistants still off by default: the person's switch) |
| 27 model.replace | done | model.js |
| R1 regression | done | tests/bin/test-manafe3-r1.mjs |

**R1 (2026-11-09):** both blocks rebuilt from engine fixtures (`fixtures/manafe3/r1-block1.json`, `r1-block2.json`) on the
site grids — bays from the grids, span = COLUMN CENTRE TO CENTRE (27.6 / 28.9 m; CONFIRMED by the user 2026-11-09),
girts from +4.00. Every frame column on its grid intersection, no grid line added, crane runway on block 2 with no clash
against the tapered columns, no concrete in the steel. Totals with the engine's span-rule placeholder sizes (NOT designed;
no footings, base plates or connections): Store 19.4 t, F&S-1 27.3 t, F&S-2 54.7 t incl. crane 8.4 t — **101.4 t =
36.4 kg/m²** over 2 788.5 m² (the user's earlier baseline 86.5 t / 31.0 kg/m² came from different placeholder sizes).
Expect a change again once Phase 4 sizing is in.
Browser check (2026-11-09, headless Chrome, `node tools/manafe3-smoke.mjs` with the app running): Building… (placement,
pads, a second building at 90°, the picker), Crane runway…, Job units…, base plates / footing clean-up, the Analysis
picker, the Drawings settings and tick-box export (PDF and DXF zip) and the Elevation view on an x grid line all work with
no page error. The 4 load messages are not Manafe3's: the offline bootstrap-icons stylesheet and three upstream shell
scripts the fork does not ship (app-devices-studio.js, skill-packs.js, app-addons-account.js).

### Phase 4 plan (approved 2026-11-08)

**Decisions (user, 2026-11-08):**
- **Both codes, side by side**; a project setting chooses which GOVERNS: **AISC 360-16 LRFD** for GCC / Oman jobs
  (default), **ECP 205-LRFD** for Egypt jobs.
- ECP: the user's repo **https://github.com/ahmedalisteel-star/ecp205-lrfd** as a pinned git dependency (add a
  `pyproject.toml` on a `packaging` branch if missing) — NOT the skills-folder copy. Every equation keeps its clause
  reference; Claude confirms equations WITH THE USER against the printed code; **never commit the HBRC PDF**.
- **Check + sizing loop**: target utilisation **0.90** (never above 1.00). Plates **6, 8, 10, 12, 14, 16, 18, 20, 22, 25 mm**
  (web min 6, flange min 8); flange widths **150, 180, 200, 220, 250, 300 mm**; web depths in **25 mm** steps.
- Limits (editable per job): **wind sway H/100**, **rafter vertical under roof live L/180**, **purlins and girts L/150**.
  No cranes now (keep a hook).
- **Direct Analysis Method.**
- No supplier catalogue yet: **Z / C properties computed from their geometry** with the vendored AISI S100 engine
  (DSM / EWM); a supplier table loaded later overrides them.
- **A. Tapered members per AISC Design Guide 25** (compression and LTB of web-tapered segments), not prismatic formulas
  alone — VERIFIED False until hand-checked.
- **B. Slender elements:** AISC **E7** (slender compression elements), **F5** (slender web in flexure), **G2 shear
  buckling WITHOUT tension field action** — thin PEB webs checked correctly.

| # | Step | Tests (independent) |
|---|---|---|
| 1 | Design inputs from the MODEL: plate strengths by grade and thickness, design members (rafter halves across splices), restraint points (outer flange: purlins / girts; inner: flange braces), the moment-sign boundary into bimsteelauto (`engine/design/inputs.py`) | **done** — `test_design_inputs.py` |
| 2 | Direct Analysis Method for the LRFD set (`engine/analysis/solve.py`): every stiffness × 0.8 (a `FrameAnalysis` subclass scales E and G — bimsteelauto has no stiffness setting), τb = 1 checked by αPr/Pns ≤ 0.5 (else C2.3(c): + 0.001·Yi), notional 0.002·Yi as horizontal twins of every D / C / Lr load in EVERY LRFD combination along its net lateral load (gravity-only: both ways); ASD and cases on the nominal stiffness | **done** — `test_dam.py`: movement × 1.25 with forces unchanged, notional statics longhand, direction, τb by hand, C2.3(c) forced, service set unchanged |
| 3 | Main frames AISC 360-16: station checks incl. **DG 25** for tapered segments (A) and **E7 / F5 / G2 without TFA** (B), Lb from step 1 along the whole design member | **done** (engine) — `engine/design/frame_checks.py`, `test_frame_checks.py`; limit states longhand in bimsteelauto 0.14.3 – 0.15.1 |
| 4 | Serviceability (ASD): sway H/100, rafter L/180 under Lr; editable; crane hook | **done** (engine) — `engine/design/serviceability.py`, `test_serviceability.py` |
| 5 | Wind columns (C&C), end rafter, side- and end-wall bracing, eave struts | **done** (engine) except eave struts (moved to step 6) — `engine/design/secondary_checks.py`, `test_secondary_checks.py` |
| 6 | Purlins / girts AISI S100: properties from geometry (DSM / EWM, vendored engine), supplier-table override; C&C zones; L/150 | **done** (engine) incl. eave struts — `engine/design/cfs_section.py`, `cfs_checks.py`, `test_cfs.py` (one line by hand: the bay-2 eave strut) |
| 7 | ECP 205-LRFD from the ecp205-lrfd dependency (ton / cm inside, one boundary), side by side; the governing code from the project setting | **done** (engine, main frames) — `engine/design/ecp_checks.py`, `test_ecp_checks.py` (column A of line 3 longhand); equations to confirm with the user listed below |
| 8 | Sizing loop: target 0.90, ≤ 1.00, the plate / width / depth lists above, re-analyse until stable | **done** (engine) — `engine/design/sizing.py`, `test_sizing.py`: building 1 converges, minimums kept |
| 9 | Browser "Design…" + project design settings (governing code, limits, target); utilisation colours, tables, HTML calc sheets (NOT FOR ISSUE until verified) | **done** — `engine/design/design_run.py`, `POST /peb/design`, `app/manafe3/design.js` / `design-ui.js`; `test_design_run.py`, `test-manafe3-design.mjs`, smoke |
| 10 | HANDOVER, `end-work.ps1` | **done** (2026-11-10) |

**Findings and fixes (2026-11-08):**
- **bimsteelauto moment sign — FIXED in bimsteelauto (user decision) and re-pinned.** PyNite gives Mz + for tension on
  the local +y face (sagging NEGATIVE on a simply supported beam); `design.members.check_member` reads Mz ≥ 0 as "top
  flange in compression", and the extraction passed PyNite's value through — the compression flange (Lb, Sxc, flange
  slenderness) was chosen backwards, unconservative at the haunch under gravity. bimsteelauto `fix/moment-sign`
  (c7faf80) merged to `main` (c8caa70) as 0.14.1: ONE conversion, `analysis.frame.design_moment_factor` (PyNite's
  `Member3D.T` rule incl. the vertical right-hand column), in the 2D and 3D extraction; `tests/test_moment_sign.py`
  (simple beam → top flange, haunch under gravity → bottom flange; both fail on the old code); CHANGELOG 0.14.1 says to
  re-check member results of earlier runs (Jobs 16 and 17). bimsteelauto suite: 985 passed (the 1 failure,
  `test_fc_adapter`, needs a `design_result.json` from `run_frame_example.py` — the same before the fix).
  Manafe3 pins c8caa70; since then **M + = the member's TOP flange in compression** (rafter top, column outer) in every
  Manafe3 result; Manafe3 no longer converts (its interim `bsa_moment` removed); the browser draws M on the tension side
  from the member's role (`frame-analysis.js sideOf`).
- **End frames now get inward flange braces** (user decision): rafters at the same positions as the interior frames
  (purlins over the haunch + the next), the inward brace only; end columns already had theirs. An end-RAFTER wall has no
  main frame, so none there. Building 1: 376 members (was 364). The app fixture `fixtures/manafe3/building1.json` is a
  frozen engine snapshot from Phase 2 (its counts are checked by hand in `test-manafe3-building.mjs`) — not regenerated.
- **ECP 205 grades CONFIRMED by the user** (printed code, Sect. 1.3.3 / Table 1.1; Sect. 1.3.2 constants E 2100, G 810
  t/cm², density 7.85 t/m³, ν 0.3, α 1.2e-5 /°C) → VERIFIED True in `engine/design/inputs.py`; St 37 Fu = 3.70 (the skill
  engine was right). The ecp205-lrfd repo already holds the same values (materials.STEEL_GRADES, core.E / G / NU /
  DENSITY / ALPHA_T) — no change there. EN 10025-2 / ASTM A572 / EN 10346 values stay VERIFIED False until confirmed.
- **bimsteelauto 0.14.2** (user decision): `ModelSettings.stiffness_factor` (default 1.0) and `ModelSettings.min_segments`
  (default 1) — branch `feature/stiffness-factor` (08d3bd2) merged to `main` (8c8d3cb); `tests/test_model_settings.py`
  (bimsteelauto suite 990 passed). Manafe3 re-pinned; its stiffness subclass is GONE: the strength solve uses
  `stiffness_factor = 0.8`, `min_segments = 4` (`solve.strength_layout`).
- **P-δ (AISC C2.1)**: every member of the strength solve is split into ≥ 4 elements (constant rafter segments, rigid
  arms; the end frame's rafter spans and wind columns too). Test: a braced pin-ended column at P/Pe1 = 0.30 under a
  small lateral load matches B1·wL²/8 within 2 % (measured: 1 element 1.225, 2 → 1.355, 4 → 1.433, 8 → 1.441, exact 1.441).
- **End-rafter frame on the DAM too**: strength = 0.8 stiffness, 4 elements per member, notional loads, P-Delta; cases
  and ASD first order on the nominal stiffness (a braced frame; exact statics kept).
- **PyNite never re-activates a tension-only member** it has switched off (`Analysis._check_TC_convergence` checks
  active members only): under a gravity-heavy combination the posts' shortening switches BOTH rods of an X off and the
  bay is silently a mechanism (test `test_pynite_never_reactivates_a_tension_only_member` pins it). So the end frame's
  strength set models, per sway direction, only the diagonal that lengthens, as an ordinary axial member; each
  combination takes the model of the sign of its factored rafter-level H; rod tension = max(model, H / cos θ), a model
  compression is flagged "slack". (The service set keeps the tension-only switch: wind dominates there.)
- **Tests split**: `@pytest.mark.slow` on the frame-solve tests (22); `start-work.ps1` runs `-m "not slow"` (105 tests,
  ~10 s), `end-work.ps1` runs everything (127, ~10 min) before pushing.

**Step 3 decisions (user, 2026-11-08):**
1. **E7 fixed in bimsteelauto** — bimsteelauto's compression check built pyaisc360's `CompressionMember` with no plate
   elements, so E7 never applied (every element taken nonslender). Branch `fix/e7-slender` (ca09aa5) merged to `main`
   (548bef4) as **0.14.3**: `_e7_effective_area` deducts the web (h, tw, case 5) and each flange (bf/2, tf, case 2 with kc)
   through pyaisc360's E7 functions at the governing Fcr (pyaisc360's own `effective_area()` cannot take a built-up flange:
   it does not pass h/tw for kc). `tests/test_e7_slender.py` longhand E3/E4/E7: the 800×8 / 250×12 section (h/tw 97, S355)
   gives Ae/Ag 0.719, φPn 2557 kN vs 3555 kN before (negative control); stocky unchanged; E7-2 threshold; singly-symmetric
   flanges separately. CHANGELOG re-check note for Jobs 16 and 17 extended (compression overstated for slender webs).
   bimsteelauto suite 996 passed (+ the known `test_fc_adapter` file failure). New bimsteelauto coverage gap recorded:
   singly-symmetric compression uses the doubly symmetric E4 branch. Manafe3 re-pinned to 548bef4.
2. **DG 25 goes in bimsteelauto** (a module for nonprismatic members). The user has no DG 25 copy yet: elastic buckling
   loads by TWO independent numerical methods, VERIFIED False, NOT FOR ISSUE; confirm the equations against the printed
   guide when the user has it.
3. The PyNite tension-only workaround (lengthening diagonal per sway direction, rod = max(model, H / cos θ)) is
   **APPROVED**.

**Step 3 — what was built (2026-11-08):**
- **bimsteelauto `verify/slender-webs`** (8a223f1): F4 (h/tw 97) and F5 (h/tw 163) in all three Lb zones and G2.1 shear
  buckling (Cv1 0.63 / 0.38, φ 0.90, no tension field), all longhand from the plates, within 0.2 %. The 2026-09-01
  verification had compared a compact (F2) section only. VERIFIED gains compression_E7, flexure_F4_noncompact_web,
  flexure_F5_slender_web and shear_G2_1_web_buckling.
- **bimsteelauto 0.15.0 `feature/dg25-nonprismatic`** (355c55b), new module `design/nonprismatic.py`.
  - Elastic buckling of a segment with the varying section integrated along it: in plane under P(x); out of plane
    flexural-torsional under P(x) (singly-symmetric shear-centre offset); LTB under M(x) (Wagner term).
  - Two independent methods: cubic Hermite FE (16 elements, converged within 3e-5) and a sine-series Ritz.
  - Closed forms reproduced: Euler; the exactly solvable column I ∝ x⁴, Pcr = π²E√(I1·I2)/L² (derived longhand); AISC
    E4 singly symmetric; uniform-moment LTB of a doubly and a singly symmetric beam, including Wagner.
  - Application, opt-in `MemberDesignInput.stability = "dg25"` (bimsteelauto's default stays prismatic):
    - compression: Fe = γe·fr per station (in plane K = 1 over the member, out of plane over the segment), then E3 and E7;
    - LTB: Fe = κ·γLTB·fr, mapped to the Lb that gives it in the dispatched F2-4 / F4-5 / F5-4, Cb = 1. κ = Fe,AISC /
      Fe,exact of the section keeps AISC's margin.
  - A prismatic member reproduces AISC exactly: uniform moment in F2, F4 (singly symmetric, both signs) and F5; axial
    E3/E4/E7. Under a moment gradient, elastic Cb ≈ 1.85 against F1-1's 1.67; inelastic 3 % below AISC.
  - The governing station is re-run with Ritz; the difference is printed in its note.
  - `pipeline.OPT_IN_MODULES`: gated modules the pipeline does not call carry their flags themselves.
- **bimsteelauto 0.15.1 `feature/dg25-restraints`** (ad33eb6): the OTHER flange's brace points inside a
  compression-flange segment become rigid lateral restraints AT THAT FLANGE.
  - Example: purlins on the top flange inside a rafter's bottom-flange segment.
  - It is a penalty of 1e6·EIy/L³, scaled on the physical stiffness (scaling on K's diagonal ill-conditioned the
    eigenproblem: mixed mm / rad dofs).
  - The sign is pinned by physics: a compression-flange restraint is a full brace, a tension-flange one adds less than
    5 %.
  - `dg25_other_flange=False` gives the bare segment.
  - **To confirm with the user / DG 25: whether the guide's procedure takes such restraints.**
- **Manafe3 `engine/design/frame_checks.py`:** one design member per column / rafter half. `ChainTaper` gives the
  section at the station; splice stations are nudged into their own piece. Inputs and checks:
  - forces from the strength (DAM) solve's LRFD combinations;
  - Lb from the step 1 restraints; Fy = the lowest plate of the whole design member; K = 1;
  - `check_member(stability="dg25")`, with the prismatic ratio alongside;
  - the result carries the NOT FOR ISSUE banner and the open flags (DG 25, EN / ASTM grades, restraints).

  Building 1 line 3 (default sizes): rafters 0.329 (prismatic 0.390), columns 0.351 (FLB governs, both methods); 8 s
  for the four members. Tests (`test_frame_checks.py`): chain sections; force / bracing / Fy plumbing on a synthetic
  result; shear longhand through the chain; a section that must fail; frame line 3 (slow, the governing forces are
  the analysis' own, Ritz within 1 %).
- **Open for the user:** confirm DG 25 against the printed guide (the γe / Fe = γe·fr application, the κ calibration,
  the Lb,eq mapping, and the other-flange restraints).

**Phase 4 — summary (2026-11-10).** Every member of a PEB building is checked and can be sized, NOT FOR ISSUE:
- main frames AISC 360-16 LRFD (Direct Analysis Method, DG 25 for tapered members, E7 / F5 / G2 without TFA) and ECP 205-LRFD
  side by side (its own nominal P-Δ solve, sway K chart); serviceability H/100, L/180, L/150 (editable);
- wind columns (C&C, flange braces from the girts), end rafters, rod / angle bracing (AISC);
- purlins, girts, gable girts, eave struts to AISI S100-16 by DSM with properties and finite-strip buckling from the
  profile geometry; R-factor (I6.2.1) default for sizing, the strict rule beside it;
- the sizing loop (frames re-analysed until stable; cold-formed by the R-factor; wind columns and end rafters on held
  forces) and PEB › Design… in the browser.
- **Open for the user (each result says so):** DG 25 (four items), the AISI S100 Table I6.2.1-1 R values and limits, the
  ECP K / G rules (chart, G at the knee and base, rafter K, full brace points), ch. 6 / mono-symmetric flexure in
  ecp205-lrfd, the EN / ASTM grade values, the R-factor readings (Se Fy = Mnlo; the larger of two valid methods).

**Step 9 — what was built (2026-11-10):** PEB › "Design…" per building. NOT FOR ISSUE.
- **Engine** `engine/design/design_run.py`: `check_building(b, li, DesignSettings)` — main frames by every code asked for
  (sizing.evaluate: every distinct frame line, end-rafter walls skipped), wind columns, end rafters, bracing, cold-formed
  lines (uplift mode AND strict beside); rows keyed by the MODEL member id (pieces of a purlin line, every frame line of a
  group, every brace of a type) with ratio (None = NOT EVALUATED), governing check + clause, combination, station, code,
  VERIFIED and its flags; summary (steel t and kg/m² from every generated member, max ratio per member type,
  serviceability, NOT EVALUATED count, the unconfirmed items); per-member calc data. `size_building`: frames (step 8),
  cold-formed (R-factor), wind columns and end rafters (`size_end_walls`, same plate lists, web ≥ 300, held forces), then
  a full Check of the proposal; weights before / after. JSON-safe (`clean`: inf → null).
- **Generator:** `BuildingInput.wind_column` / `end_rafter` section overrides {hw, tw, bf, tf} (refused when malformed);
  `BuiltUpSizes.tw_column / tw_haunch / tw_rafter`; the end-rafter analysis and the wind-column check read the generated
  sections (no longer the WIND_COLUMN constant, which stays the default).
- **API:** `POST /peb/design {building, loads, settings, action}` → `{job}` (a thread), `GET /peb/design/{job}` → progress /
  result / error; the last few runs kept; BuildingRequest takes wind_column / end_rafter, SizesIn the tw_*.
- **Browser** (`app/manafe3/design.js` DOM-free, `design-ui.js`): settings (code basis AISC / ECP / both, governing code,
  target, sway / rafter / purlin limits, uplift R-factor default with strict beside, stability), "Keep as project settings"
  (`state.m3design`, saved with the model); Check; Size members → proposal table (now → proposed) and weight before /
  after, **Apply = ONE undo step** (the building regenerated with the new sizes through applyBuilding, the crane entry
  kept), Cancel changes nothing; 3D colours (blue < 0.5, green 0.5–0.90, orange 0.90–1.00, red > 1.00, grey NOT EVALUATED)
  through a new `view.setColors(map)` hook, legend; results table (sort, filter, ratio band, code; a row click selects the
  member; ticks for calc sheets); summary; calc sheets per member (data, section, restraints, loads, forces, every check
  with clause, demand, capacity, ratio, basis; R-factor limits; NOT FOR ISSUE banner listing the open flags) → one HTML
  document opened for printing to PDF (selected or all).
- **Upstream files changed** (MANAFE3-CHANGES.md): `app/view3d.js` (setColors), `app/model.js` (m3design), `app/detailcraft.js`
  (mount).
- **Results (V 45 m/s, C — placeholder site wind):** building 1 (end-rafter first wall, Check, prismatic) 20.5 t,
  35.6 kg/m², max 0.73 (a gable girt by the R-factor; frames AISC 0.52); Size → 14.8 t (25.7 kg/m²), max 0.892; R1: block 1 (27.6 m c/c, 10 bays) Check 46.3 t, 27.6 kg/m2, max 1.87 (side-wall girts in the 6.6 m end bay; frames 0.43 / 0.47); Size (41 min) -> 46.3 t, 27.6 kg/m2, max 0.896: girts Z250x65x20x3, purlins Z200x65x20x1.8, eave struts C200x65x20x1.8, gable girts lighter; the FRAMES stayed at the span-rule sizes although their ratios are 0.47 — not yet examined (serviceability steering suspected): TO LOOK AT. Block 2 (28.9 m c/c, 7 bays, 10 m eave; crane loads NOT analysed) Check 45.9 t, 42.0 kg/m2, max 3.07 (gable girts; side girts 1.72; columns 0.77, wind columns 0.97); Size (23 min) -> 41.1 t, 37.6 kg/m2: frames lighter (knee 700, base 375, rafter 300, webs 6 — columns 0.90, rafters 0.74), wind columns 300 x 180x8, purlins Z200x65x20x2, eave struts C200x65x20x1.8 — but NO ladder profile (up to Z300x65x20x3) brings the girts / gable girts to 0.90: they keep Z200 and the proposal does NOT pass (max 3.07). TO LOOK AT: the tall gable's girt spans / cantilevers to the roof, a deeper or heavier ladder, or more wind columns / sag rods on the walls.
- **Tests:** `test_design_run.py` (settings, JSON, member weights by hand, the section sizer, overrides reaching the members,
  the API job flow, building 1 Check — slow), `test-manafe3-design.mjs` (23: colour bands, settings, governing rows, colour
  map by name, table, proposal, Apply as one undo step, request, settings saved, calc sheets); `tools/manafe3-smoke.mjs` now
  opens Design…, runs Check with the engine, colours, a row, calc sheets (`--size` also sizes and cancels): Check 112 s,
  286 rows, no new browser errors.

**Public repository pass (2026-11-10, user request):**
- Scan of the working tree and the WHOLE git history: no live secret (two false positives: a base64 run in an upstream
  showcase fixture, a dummy "sk-ant-api03-THISISASECRETKEY…" in an upstream MCP test); no client or job names; no code
  PDFs (the PDFs / DWGs are DetailCraft's own test fixtures); nothing needs the private peb folder (only `/health` says
  whether it is configured). The private folder's PATH was in HANDOVER and `.env.local.example`: removed from the current
  files — it is still in the git history (not a secret; rewriting history would need a force push: the user's call).
  The two PC names and user folder names stay in CLAUDE.md / HANDOVER / `.env.local.example` (maintainer workflow); the
  author's email is in the commit metadata only.
- **Licence (user decision 2026-11-10):** everything Apache-2.0. 110 file headers now read `Copyright 2026 Ahmed Ali.
  Licensed under the Apache License, Version 2.0 (see LICENSE).`; `pyproject.toml` license = "Apache-2.0"; NOTICE gains
  the Manafe3 line; TRADEMARKS gains a Manafe3 name / logo section; LICENSE, NOTICE (DetailCraft), TRADEMARKS (DetailCraft),
  MANAFE3-CHANGES kept; CLAUDE.md's header rule updated.
- README for public users: the logo and the Surah Al-Hadid verse kept verbatim; "What is Manafe3"; install with
  `git clone https://github.com/ahmedalisteel-star/manafe3.git` (no GitHub login); licences and names; the two-PC
  section marked "maintainer only".
- A fresh clone + `uv sync --locked` with every git credential switched off and an empty uv cache: works (bimsteelauto
  and ecp205-lrfd are public); the imports run.
- GitHub Actions re-added (`.github/workflows/tests.yml`): fast engine tests + Manafe3's app tests on every push and PR;
  the full engine suite and the whole app suite on `main`.

**Step 8 — what was built (2026-11-09):** `engine/design/sizing.py`. NOT FOR ISSUE.
- **Main frames** (`size_frames(b, li, code="AISC"|"ECP", stability="dg25", target=0.90)`): the generator's own
  parameters (BuiltUpSizes, the same on every frame line): bf, tf (one flange plate on every member — the splice rule),
  hw_knee, hw_base, hw_rafter, and NEW web overrides `tw_column / tw_haunch / tw_rafter` (None keeps the 6 / 8 mm rule).
  Lists: plates 6 … 25 (web ≥ 6, flange ≥ 8), widths 150 … 300, depths in 25 mm steps; hw_base, hw_rafter ≥ 300 and ≤
  hw_knee; haunch length and grade as given. The loop: analyse every DISTINCT frame line (the governing code's own
  solve) and check it fully with serviceability; on those forces held (stations scaled to the new member lengths) quick
  checks on each member's governing combinations (top 3 |M|, top 2 P): raise the variable with the best ratio drop per
  kg until ≤ target, then lower the biggest savings while ≤ target; serviceability above the target steered by the knee
  + rafter I; re-analyse; stop when the sizes repeat (an oscillation ends with the lightest full-checked set ≤ 1.00); at
  most 8 rounds. The reported result is always the FULL check.
- **Building 1** (V 45, C; AISC, prismatic in the test): 6 rounds, ~4 min — knee 475, base 300, rafter 300, flanges
  200×10, webs 6 / 6 / 6: full ratio 0.893, serviceability 0.80, **1669 kg per frame (defaults 2551 kg, ratio 0.39)**.
- **Cold-formed roles** (`size_cold_formed`): purlin, eave strut, girt — one profile each, building-wide — the lightest of
  Claude's ladder (the generated flange and lip kept; depths 150 … 300 × t 1.5 … 3.0, by area; no supplier catalogue
  yet) ≤ 0.90. **Sized by the R-FACTOR mode (user decision 2026-11-09: industry practice), with the strict-rule ratio of
  the chosen profile beside it; the R-factor results are NOT FOR ISSUE until the user confirms the R values from the
  printed AISI S100-16 Table I6.2.1-1** (banner on the result). Building 1: purlin Z250x65x20x1.5 (0.89), eave strut
  C200x65x20x1.8 (0.70), girt Z225x65x20x1.5 (0.85); by the strict rule it would take Z300x65x20x2.5 / C300x65x20x3 /
  Z300x65x20x1.5. A profile outside the R-factor limits (e.g. Z175: d/b 2.69 < 2.8) falls back to the strict rule.
- Not yet: the sizes are not written back into the model (step 9 wires "Design…"); wind columns / end rafters are not
  sized (their sections are fixed constants today).
- Tests (`test_sizing.py`, 7): the ladders and minimums, the web overrides, one frame's weight by hand, the force remap,
  the cold-formed ladder order, building 1 converges with every plate on its list (slow), the cold-formed sizing by
  R-factor with the strict ratio beside it and the banner (slow).

**Step 7 — what was built (2026-11-09):** `engine/design/ecp_checks.py`, main-frame columns and rafters to ECP 205-LRFD (2008)
through the user's **ecp205-lrfd** library (git dependency pinned at 7c459d7, `main`; MIT; ton / cm / t/cm² inside, ONE
boundary in `ecp_checks`: kN ÷ 9.80665, kN·m × 100 / 9.80665, MPa ÷ 98.0665, mm ÷ 10). NOT FOR ISSUE.
- **User decisions (2026-11-09):** (1) the SAME ASCE 7-16 LRFD combinations as the AISC side — ECP checks the resistance
  side only; ECP 201 stays refused. (2) Its OWN second-order solve (`ecp_solve`): nominal stiffness, P-Δ, ≥ 4 elements,
  NO notional loads (no B2 on top); in-plane K of the columns from the sway alignment chart. (3) Class 3 sections,
  unequal flanges and h/tw > 260 read NOT EVALUATED (ratio inf) until ch. 6 (slender webs, effective properties) and
  mono-symmetric I flexure are added to ecp205-lrfd on a branch and confirmed by the user from the printed code.
- **Claude's readings — TO CONFIRM with the user against the printed ECP 205 (`ecp_checks.VERIFIED`, all False):**
  the sway chart as the Jackson–Mooreland equation (GA GB (π/K)² − 36) / (6 (GA + GB)) = (π/K) / tan(π/K) (cl. 2.2.1.3 /
  its figure); G at the knee = (Ic/Lc) / (Ir/Lr) with the column's LARGEST I, the rafter's SMALLEST I and Lr = the whole
  sloping rafter (both halves — symmetric sway); G base 10 pinned / 1 fixed; rafters K = 1 over knee-to-ridge; out of
  plane K = 1 between FULL brace points (purlin / girt AND a flange brace at the same point, ± 50 mm, plus the ends — on
  building 1 the rafter's out-of-plane length is 8.48 m, conservative); a tapered member's φPn = the smallest over 21
  stations of its own section.
- Checks (library functions, clause on every row): Table 2.12 classification (welded), cl. 4.2 compression (φ 0.80, Q),
  cl. 5.1.3 flexure (φ 0.85; Lb = the compression flange's brace segment, Cb eq. 5.2 from that segment's quarter-point
  moments), cl. 5.2.2 shear (Aw = d tw), cl. 7.1 eq. 7.1a / 7.1b (tension: cl. 7.3 with cl. 3.1, Ae = Ag).
- `side_by_side(aisc, ecp, governing="AISC"|"ECP")` and `frame_line_both(b, li, i, governing=)` (both solves, both
  checks). The governing code becomes a project setting in step 9.
- Building 1, frame line 3 (V 45, C): ECP columns 0.561 / rafters 0.486 against AISC 0.351 / 0.329; column K = 3.41
  (pinned base, G_top from the knee), φPn governed by in-plane elastic buckling at the base section.
- Not yet on the ECP side: wind columns, end rafters, bracing, cold-formed members (ECP ch. 13 is not in the library;
  AISI stays for those).
- Tests (`test_ecp_checks.py`, 7): the K chart's limits (1.0, 2.0, 1.32 at G = 1), the unit boundary, the ECP solve has no
  notional twins and differs from the DAM solve, **column A of line 3 longhand** (λc, eq. 4.2 / 4.3 with Q over every
  station; class 2 eq. 5.16 with Mp ≤ 1.5 My and Mr = 0.6 Fy Sx; eq. 7.1a / 7.1b), a class 3 section and unequal flanges
  NOT EVALUATED, both codes on a whole frame line (slow).

**Step 6 — what was built (2026-11-09):** purlins, ridge purlins, side-wall girts, gable girts and eave struts, AISI S100-16
by the Direct Strength Method, LRFD strength + ASD deflection, NOT FOR ISSUE. `cfs_checks(b, li, supplier=, limits=)`; also
inside `secondary_checks` (its `cold_formed` entry; `eave_struts` there are now these lines).
- **Sections from their geometry** (`engine/design/cfs_section.py`): the name gives H, B, D, t; centreline with rounded
  corners. Gross properties by thin-walled line integrals (A, Ix, Iz, Ixz, J, shear centre, Cw) — **against
  sectionproperties within 0.25 %** (C200, Z200, C250; a test). Elastic buckling by **my own finite strip** (Cheung's
  method written from the theory: linear membrane, Hermite bending, the three geometric slopes; simply supported ends,
  one half-wave): local = the first minimum of the signature curve, distortional = the second; global = the curve at the
  unbraced length, and below the curve's peak after the distortional minimum the value AT the peak (a rigorous lower
  bound: the curve there is a local / distortional mode, the global one is above it). Checks: a plate with both edges
  supported gives k = 4.000, one edge free k = 0.428 (0.425 + (b/a)²); a long C200 column / beam matches the closed-form
  flexural / flexural-torsional load and Mcr = ro A √(σey σt) within 0.1 % at 6 and 9 m (2.6 % low at 3 m, where a
  distortional mode mixes in — conservative). Z200x65x20x2.0 at Fy 350: Mcrl 1.61 My (a = 110 mm), Mcrd 1.41 My (565 mm).
  E = 29 500 ksi (AISI, not AISC's 29 000). ~4 s per profile, cached.
- **Claude's assumptions (listed on every result):** inside bend radius = t (the names carry none); lips at 90°; equal
  flanges; bending about the geometric axis (restrained — the sheeting holds the section); distortional without the
  sheeting's rotational restraint (k_phi = 0, conservative); DSM pre-qualification limits not checked.
- **Lines** from the generated building: purlins and girts continuous over every frame, the **laps modelled** (where two
  pieces overlap: 2 EI, 2 × flexure and shear strength — the lap ends govern), the overhangs as cantilevers; gable girts
  continuous over the end-wall supports; eave struts (butt joints) one simple span per bay + the bracing's eave-strut
  force (bimsteelauto's drag model: 0 when the braced bays are the end bays, as in building 1 and R1's default).
- **Loads**: D (sheeting × tributary + self weight) and C (collateral, plan) and Lr (§4.8 reduced on the member's own
  tributary plan area) as normal components; **C&C wind from bimsteelauto's VERIFIED Figs. 30.3-1 / 30.3-2A** (against
  Struware), **each span in its own zone** at its own effective area. **Roof zones (user decision 2026-11-09):** the
  figure from the building's own slope — θ ≤ 7° Fig. 30.3-2A: edge strips of width a (bimsteelauto end_zone_width, 2400
  on building 1) along the eaves and gable ends only, NO ridge strip → zone 2; where they meet → zone 3; elsewhere zone 1
  (1' not used — accepted). Ridge strips belong to 7° < θ ≤ 20° (Fig. 30.3-2B) and steeper: their coefficients are not
  in bimsteelauto and are not transcribed from memory → roof wind NOT evaluated (ratio inf) until typed in from the
  printed ASCE 7-16. Walls: within a of a corner → 5, else 4.
  Combinations ASCE 7-16 LRFD 1.4D; 1.2D+1.6Lr+0.5W; 1.2D+1.0W+0.5Lr; 0.9D+1.0W (collateral not with uplift); ASD D+Lr,
  D+0.6W, 0.6D+0.6W for L/150 (`ServiceLimits.purlin`); girts 1.0W / 0.6W in and out.
- **Strength:** M + compresses the sheeted flange → braced, Mne = My. M − compresses the free flange → braced at frames,
  **sag-rod rows — only where tied off at the ridge (a ridge tie at the row) and at the eave (the chain on both slopes
  reaches the eave strut), checked per row on the model (user decision 2026-11-09; `tied_rows`)** — and line ends; Mcre × Cb, Cb =
  12.5 Mmax / (2.5 Mmax + 3 MA + 4 MB + 3 MC) over the brace segment (F2.1; 1 on a cantilever). Mn = min(Mnl, Mnd), φ 0.90
  (vendored direct_strength curves). Shear: vendored aisi_s100 (φ 0.90 throughout — VERIFIED False against S100-16 G2.1);
  H2 (M/φMnlo)² + (V/φVn)²; eave strut H1.2 P/φcPn + B1 M/φbMn, Pn by DSM with Pcre at the bay (sag rods not counted),
  B1 = 1/(1 − P/Pex). Deflection with the gross Ix (stated: slightly unconservative for slender webs).
- **Supplier table** (`supplier={profile: {...}}`): A, Ix, Sx, J, Cw, r_inside, Mcrl, Mcrd, Pcrl, Pcrd, Fy, Fu override the
  geometry; each value is marked `supplier` / `geometry` on the result; unknown keys are refused.
- **Building 1** (V 45, C): purlins 0.78 (uplift, sag-rod segment 3 m, Cb 1.18), girts 0.94 (suction, 6 m unbraced inner
  flange, Cb 1.91), gable girts 0.86, eave struts 0.56; deflection ≤ 0.58. **R1 geometry** (same placeholder wind): purlins
  1.13 (eave strip, 6.6 m bay), girts 1.43 (6.6 m end bay, zone 5) — the default Z200x2.0 is too light there under the
  strict brace-point rule; step 8 (sizing) will choose.
- **R-factor (user decision 2026-11-09, built):** `cfs_checks(..., uplift_method="r_factor")` (default stays "strict"):
  AISI S100-16 I6.2.1 for purlins and girts under uplift / suction (combinations with Wout), free flange between supports,
  φMn = 0.90 R Se Fy with Se Fy taken as the DSM Mnlo (Claude's reading, TO CONFIRM); the LARGER of this and the
  brace-point value WITHOUT the sag rods (user 2026-11-09: taking the larger is fine only between two valid methods). **R table and limits TRANSCRIBED FROM MEMORY — `R_VERIFIED = False`; the user confirms them from the
  printed Table I6.2.1-1** (`R_TABLE`, `R_LIMITS` in `cfs_checks.py`): simple span C/Z 0.70 (d ≤ 6.5 in), 0.65 (≤ 8.5 in),
  C 0.40 / Z 0.50 (≤ 11.5 in); continuous C 0.60, Z 0.70; limits d ≤ 11.5 in, 60 ≤ d/t ≤ 170, 2.8 ≤ d/b ≤ 5.5,
  16 ≤ flange flat w/t ≤ 43, span ≤ 33 ft, lap ≥ 1.5 d each side of every interior support, Fy ≤ 60 ksi. Every line
  reports R and each limit (value, ok) in both modes, plus anti-roll (sag rods tied off) for roof lines; what the model
  cannot know is listed "to confirm" (flanges held at the supports, panel steel / thickness / ribs, fasteners,
  insulation). A line failing a checkable limit falls back to the strict rule.
- **Uplift brace points (user decision 2026-11-09):** under uplift / suction (combinations with Wout) the sag rods do NOT
  brace the compression (bottom / inner) flange — they sit a third of the depth below the top flange. The free flange
  is then braced at the supports, the line's ends and only by an anti-roll / flange brace on THAT flange
  (`line["free_flange_braces"]`, none generated today). The tied-off sag rows still count in the gravity combinations.
  **Building 1 now: strict max 2.13 (eave struts 2.13, purlins 1.78: free flange over the whole 6 m bay; girts 0.94
  unchanged); R-factor 0.73 (purlins 0.67, eave struts 0.60, girts 0.66).** The bay-2 eave strut longhand test now has
  uplift governing: Lb 6 m, Cb = 12.5 / 11, ratio 1.82. Also open: whether the inflection point may count as a brace point in
  the gravity hogging zone (not used now).
- Not checked yet (gaps, stated): minor-axis bending (the slope component to the sag rods, girt self weight), web
  crippling at the cleats, purlins acting as roof-bracing struts (axial), sheeting / fastener checks.
- Tests (`test_cfs.py`, 12): the closed forms above, properties vs sectionproperties, beam closed forms (wL²/8, 0.100 /
  0.080 wL², cantilever) and against bimsteelauto `continuous_beam_forces`, **the bay-2 eave strut of building 1 longhand**
  (loads from the inputs, the zone-2 pressure at 12 m², M = wL²/8, Cb = 12.5 / 9.625 = 1.2987, the DSM curves written out
  in the test: ratio 0.5005, gravity governs; deflection 5wL⁴/384EI), the supplier override, a roof above 7° that must
  not pass, the whole building (slow); after the decisions (+3): sag-rod rows tied off (negative controls: no ridge tie,
  a slope's chain not reaching the eave strut), the R-factor limits by hand (d/t 100, d/b 3.077, flange w/t 28.5, lap
  600 ≥ 300; a short lap and untied rods make it inapplicable), the R-factor capacity 0.9 × 0.70 × Mnlo longhand and the
  exact strict fallback.

**Step 5 — what was built (2026-11-09):** `engine/design/secondary_checks.py` (`secondary_checks(b, li)`), AISC 360-16 LRFD,
NOT FOR ISSUE.
- Wind columns: simple beams under C&C wall pressure (LRFD 1.0 W, inward and outward), M(x) = w x (L − x)/2; axial 1.2 × own
  weight + on an end-rafter wall the frame's largest LRFD column load (envelope, conservative). Outer flange (girt side)
  braced at every gable girt; INNER flange at the ends only (no flange braces on wind columns) — suction governs (building 1
  WF3: 0.745, the largest of step 5).
- End rafters: each half one design member over the wind-column tops; the end-rafter frame now returns the rafter's
  station forces (`rafter_stations`, design sign = −PyNite Mz, tested: sagging + mid-span, hogging − over a wind column);
  top flange braced at purlins / eave strut / ridge purlin, bottom at the wind-column tops.
- Bracing (tension only, the largest LRFD force): rods RD<d> AISC J3.6 / Table J3.2 φ 0.75 × 0.75 Fu Ab and D2-1 on the body;
  angles L<b>x<t> D2-1 / D2-2 with U = 0.6 (Table D3.1 case 8 placeholder until Phase 5 details the joint, one standard hole),
  L/r ≤ 300 advisory. Roof / side-wall X from the bracing system, end-wall X from the end-rafter frame.
- **Wind-column flange braces (user decision 2026-11-09):** L50x5 pairs from the gable girts to each wind column's INNER
  flange, 45° horizontal in plan, as the main columns' (inner flange mid-thickness to 50 mm into the girt); default at
  every SECOND girt row the column carries, counted from its top row (Claude's reading of "every second": the upper
  part, where suction moments are largest, first); editable per end wall (Building form "Wind-column flange braces",
  `BuildingInput.wc_braces_first / _last`, 0 = none); only where a girt piece runs past the brace end (wall ends,
  openings: a corner column gets the inward brace only). They are the inner flange's restraint points in the
  wind-column check: building 1 WF3 0.745 -> 0.226 (with the wall switched off: 0.745 again). Building 1 now 404
  members (+28), the end-rafter variant 402 (+32); the clash filter treats brace-to-wind-column / gable-girt points as
  generated joints. Not counted in the frames' secondary weight (they hang on the wind columns).
- **Eave struts moved to step 6** (Claude's sequencing): their compression check is AISI S100 on a cold-formed C and needs
  the properties-from-geometry and distortional buckling step 6 builds for the purlins.
- Building 1 (end-rafter first wall): max 0.745 (WF3), end rafters 0.04, rods 0.26. Tests: rod and angle capacities by hand
  (r_min against an independent numerical integration), wind-column demand wL²/8 / wL/2 and bracing, shear longhand,
  end-rafter moment signs and bracing, a rod that must fail, the whole building (slow).

**Step 4 — what was built (2026-11-08):** `engine/design/serviceability.py`, on the SERVICE results (nominal stiffness,
no notional loads). `ServiceLimits` (editable: sway H/100, rafter L/180, purlins L/150 for step 6, `crane_sway` hook;
`from_dict` refuses unknown keys and non-positive values).
- Sway: every ASD combination containing a wind case, |dx| of each knee node ≤ H/100, H = that knee's height above its
  base node (centroid line, e.g. 5668 mm on building 1). The TOTAL eave movement is judged, so an ASD combination with
  wind and Lr includes the knees' gravity spread (conservative; a pure-gravity ASD combination is not a sway check).
- Rafter: the Lr case alone, unfactored; the drop of every rafter node (knee ends, splices, ridge) below the chord
  between the two knee-end rafter nodes ≤ L/180, L = span. Model nodes only (a peak between nodes is not seen; for a
  gable under uniform Lr the ridge governs).
- Crane hook: `has_crane=True` adds a crane line with ratio inf, never a pass. No wind combination / no Lr → inf.
- The analysis result now carries `factors` per combination; `analyse_building(limits=…)` attaches `serviceability` to
  each solved frame line. (JSON: an inf ratio would break FastAPI's encoder — only reachable with cranes; handle in step 9.)
- Tests: synthetic ratios by hand (gravity spread ignored, chord at the ridge), H/200 negative control, unevaluated
  never passes, frame line 3 recomputed from the solve's own displacements. Building 1 line 3: sway 0.124, rafter
  0.223 (29.8 mm).

**Phase 3 open questions — ANSWERED by the user (2026-11-08) and built:**
1. Wind columns (and later girts / purlins): **ASCE 7-16 Ch. 30 C&C**, effective wind area = span × max(spacing, span/3),
   wall zones 4 / 5 — `engine/analysis/cc_wind.py`, VERIFIED flags False (new code), hand-check of WF3 in `test_cc_wind.py`.
2. End-rafter frame: **no reliance on sheeting** — X-bracing in the end walls (default one braced bay, bay 1 from line A,
   on an end-rafter wall; none on a main-frame wall — the portal is stable), tension-only diagonals carry the sway
   (`endwall.py endwall_braces`, `end_rafter_frame`; refused without bracing).
3. Longitudinal bracing: **the actual wind-column top reactions**, summed per end wall (`longitudinal_feed`), not a blanket
   half. Claude's reading, to confirm: the feed uses **MWFRS** end-wall pressure (the bracing is part of the MWFRS); C&C is
   for designing the columns. Total = bimsteelauto's net pressure × end-wall area; building 1 eave share 0.53. Strut
   drag gets the larger side's top force (bimsteelauto halves F_eave per end).
4. ECP 201: **keep refusing**; later the combinations come from the user's ecp205-lrfd library with clause references.
5. Ridge-tie strap **PL3x50** and wind-column cap plate **PL10: CONFIRMED** (by the user on 2026-11-05).
Still open: run one `.std` in STAAD.Pro V8i and compare with Manafe3's first-order numbers.

### Phase 3 — what was built (steps and commits)

| # | Step | Commit |
|---|---|---|
| 1 | "Loads…" form, `state.m3loads`, `POST /peb/loads/check` (`engine/peb/loads_input.py`) | efcea4c |
| 2 | Frame line → bimsteelauto `FrameLayout` on centroid lines, rigid knee / ridge links (`engine/analysis/frame_model.py`) | c438f17 |
| 3 | Loads and combinations on each frame (`frame_loads.py`): D (plates + sheeting + secondary), C, Lr (§4.8), 6 wind cases | 4c3bfc4 |
| 4 | Solve a frame line: every case unfactored + LRFD + ASD, P-Delta (`solve.py`); wall-wind direction fix | cf2a688 |
| 5 | anastruct cross-check (`crosscheck.py`), STAAD.Pro `.std` writer (`staad.py`) | 2aa6954 |
| 6 | Longitudinal tension-only bracing (`bracing_system.py`) | 39ce7a4 |
| 7 | End walls: wind columns (simple beams), end-rafter frame (`endwall_analysis.py`) | 39e4402 |
| 8a | Whole building (`building_analysis.py`), secondary steel weighed (`secondary_weight.py`), `POST /peb/analysis` | 812c2e0 |
| 8b | Browser "Analysis…" (`app/manafe3/frame-analysis.js`, `frame-analysis-ui.js`) | 609c615 |
| 9 | ECP 201 hook (pluggable combination sets), `.std` download, this HANDOVER | (end-work) |

**What was learnt / decided while building (2026-11-07):**
- **Wall wind direction defect (found by the statics test, fixed in the adapter):** bimsteelauto applies wall wind NORMAL
  to a column, relying on PyNite's local axes of an EXACTLY vertical member; a Manafe3 column on its tapered centroid line
  is slightly inclined, PyNite turns its local y the other way and the load flipped (the frame swayed against the wind).
  The adapter now applies wall wind as global X (bimsteelauto's sign: + toward +X) × height/length. bimsteelauto itself is
  unchanged; its own layouts have vertical columns and are not affected.
- **The same PyNite rule sets the moment sign the browser draws:** + = tension on the member's local +y face (top of a
  rafter, outside of an inclined column; an exactly vertical member has local y = −X going up). The diagrams use PyNite's
  rule (`localY`), so M is drawn on the tension side for tapered AND constant columns (`test_moment_sign_is_tension_on_local_y`).
- `Envelope.eave_drift` only looks at nodes named "E…" (bimsteelauto's layouts) — it would read 0 on Manafe3 layouts.
  Manafe3 reports **sway** (mean sideways movement of the two eaves — the drift to judge) and the **largest eave movement**
  (which also holds the knees spreading under gravity) separately.
- anastruct keeps ONE distributed load per element — a second `q_load` REPLACES the first (found by the cross-check,
  pinned in `test_crosscheck.py`); its reported reactions and displacements are the negative of the real ones.
- On building 1 the ASCE §28.3.4 minimum governs Load Case A (87.4 kN computed vs 121.3 kN → × 1.3887, stated in each
  load's origin). Under ASD 1.0D + 0.6W the light roof is in net uplift: columns in tension, P-Delta REDUCES the sway
  (the negative control); with columns in compression it amplifies it.
- **Speed:** time grows with slices × combinations (49 per line). Taper step 0.10 is used (within 0.2 % of 0.025 on
  building 1; `test_taper_step_converged` keeps it); identical frame lines are solved once, distinct ones in parallel:
  building 1 (5 lines, 2 distinct) takes ~37 s from the browser.
- **Step 6 differs from the plan:** the plan said a 3D PyNite truss; built instead as bimsteelauto's verified
  `solve_longitudinal` chain on Manafe3's own panel depths, with the wall diagonal checked by a PyNite tension-only truss
  (the slack diagonal is the negative control). Strut forces are bimsteelauto's (0 with the end bays braced).
- Secondary steel in D is weighed from the model (C/Z centre-line area with square corners, rods, angles, cleats): building 1
  roof 0.070 kN/m², walls 0.056 kN/m². End walls (gable girts, wind columns) are not in the frames' D — their own path.
- With an end wall of type "frame" the wind columns take no gravity (vertical slotted holes at the top, Phase 5).

### Phase 3 plan (as agreed, kept for the record)

**Reuse bimsteelauto unchanged:** `loads/wind.py` (Ch. 28 envelope, Load Cases A/B × ±GCpi, end zones, §28.3.4 minimum,
longitudinal end-wall pressure; VERIFIED flags all True — keep them honest: nothing Manafe3 adds may flip one),
`loads/gravity.py` (dead build-up; Lr = Lo·R1·R2 from the tributary area, bounded 0.58–0.96 — never hard-coded),
`loads/combinations.py` (ASCE 7-16 LRFD/ASD; wind = four separate cases, positive factors), `analysis/frame.py`
(`FrameAnalysis`: PyNite 2D, taper discretisation, P-Delta, pinned/fixed bases, envelope, reactions, drift).
`FrameLayout` is generic, so the adapter builds one per frame line with ALL segments (column, haunch, rafter pieces;
rigid knee, splices, ridge) and solves with bimsteelauto's verified solver; wind pressures per surface (wall, windward /
leeward roof) are spread over every sub-member of that surface. bimsteelauto's 2D module has no tension-only bracing or
end-wall frame: Manafe3 adds those (PyNite directly).

| # | Step | Tests (hand values) |
|---|---|---|
| 1 | "Loads…" form stored in the model (`state.m3loads`): sheeting single skin / sandwich, collateral, Lo, wind V / exposure / enclosure / Kzt / risk category, bases pinned / fixed, LRFD + ASD | mapping |
| 2 | Frame model adapter: building frame line → `FrameLayout` on centroid lines with rigid knee / ridge links; taper sub-elements refined until results change < 1 % | prismatic portal vs closed form; one tapered member vs independent integration; convergence |
| 3 | Loads on frames: self-weight (frame plates + purlins / girts / sheeting by tributary width), dead, Lr with its reduction, four wind cases with end zones → line loads per frame | line loads by hand for an interior and an end-zone frame |
| 4 | Solve every frame line, all combinations, P-Delta; reactions, forces at stations, eave drift, apex deflection | statics per case; closed-form portal |
| 5 | Cross-checks: anastruct on one interior frame; STAAD .std export (`MEMBER TAPERED`) for STAAD.Pro V8i on this PC | agreement; .std content by hand |
| 6 | Longitudinal system: 3D PyNite truss of the braced bays — tension-only rods, struts (eave struts / purlins at the nodes), end-wall wind via wind-column top reactions | statics; one diagonal slack |
| 7 | End walls: end-rafter frame on wind columns pinned top and bottom (in-plane); wind columns as simple beams under end-wall wind (out-of-plane) feeding step 6 | closed-form simple beam |
| 8 | Browser "Analysis…": per frame line and case / combination — deflected shape, N / V / M diagrams (SVG), base-reaction table per column per combination (+ CSV for the foundation designer), drift and deflections | mapping + browser check |
| 9 | HANDOVER (ECP 201 hook: combinations as a pluggable factor set), `end-work.ps1` | |

Notes: MySteelApp's STAAD export is on the laptop — a small writer here; comparing it is a laptop task. Results are
re-run by the engine on demand, not stored in the model. No member design (Phase 4).

**Decisions (user, 2026-11-05):** analysis on **centroid lines with rigid knee / ridge links**; sheeting defaults
**single skin 0.07 kN/m², sandwich panel 0.12 kN/m² (50 mm PU, 0.5 / 0.5 mm facings)**, editable; collateral **0.10 kN/m²
per horizontal plan**; combinations **LRFD and ASD** by default; Lr = 0.96 with the ASCE 7-16 §4.8 reduction; bases
pinned by default (fixed as an option); P-Delta on. Start by reading bimsteelauto
`loads/`, `analysis/frame.py` and `pipeline.run_frame`, and the `ProjectSpec` / `DesignResult` contract. **Write the plan
here and show it to the user before coding** (the Phase 2 defaults are confirmed; two new sizes still to confirm: the
ridge-tie strap PL3x50 and the wind-column cap plate PL10). Same rules: hand-checked tests, commit after each green step on `main`, `end-work.ps1` at the end.

**Additions (user, 2026-11-05) — built as stated:**
1. **Collateral is its own load case** and is EXCLUDED from the uplift combinations (LRFD 0.9D + 1.0W, ASD 0.6D + 0.6W);
   it stays in every gravity combination.
2. **The reactions CSV also gives UNFACTORED base reactions per separate load case** — D, collateral, Lr and every wind
   case (A / B with + / − GCpi) — not only the combinations, so the foundation designer can apply their own factors.
3. **Strength results from the LRFD combinations; deflection and drift from the ASD combinations**; every result is
   labelled with the set it comes from.

### Phase 2 — what was built (steps and commits)

| # | Step | Commit |
|---|---|---|
| 1 | Lipped C / Z, rods, metric angles (`app/manafe3/coldformed.js`), job catalogue, starter sizes | a1944b9 |
| 2 | Purlin and girt lines (`engine/peb/secondary.py`) | e0aad5c |
| 3 | Lapped pieces, holes, cleats | dc37dfc |
| 4 | Sag rods, X-bracing, flange braces (`engine/peb/bracing.py`) | a3dff9e |
| 5 | End walls (`engine/peb/endwall.py`) | fae48bc |
| 6 | Framed openings (`engine/peb/openings.py`) | 455e65e |
| 7 | Whole building `POST /peb/building` (`engine/peb/building.py`) + the "Building…" form (`app/manafe3/peb-building*.js`) | 46001d2, ecbdde8 |
| 8 | DSTV for C/Z, punch list CSV, IFC for every new part (+ import fix) | e8e0cf2, 1d0e545 |

**Phase 2 defaults CONFIRMED by the user (2026-11-05)** — every item marked "TO CONFIRM" below stands, with these changes
(done, commit after 7045a4b):
- **Ridge tie**: the two ridge purlins tied across the apex at every sag-rod row so sag forces balance — role `ridge_tie`,
  rod (default, the sag rod) or **strap** (PL3x50, one M12 each end — **CONFIRMED** by the user).
- **Wind column placeholder**: built-up web 300 constant, flanges 150×8, S355 (`endwall.py WIND_COLUMN`). Its top follows
  the rafter slope (cut across the flanges: `cuts.endU`, flanges become trapezoid shaped plates) under a **cap plate** PL10,
  20 mm past the column all round (**CONFIRMED** by the user).
- **Gable-girt cleats** on the wind / corner columns, generated after openings (`building.py gable_cleats`).
- **PHASE 5 MUST: vertical slotted holes at the wind-column top (cap plate / rafter connection) for the rafter's deflection.**

**Known limits / later.** Cleats and cap plates are loose plates (not yet welded into the frame / column assemblies —
Phase 5 connections); the column under the apex has a flat top (no ridge-shaped cap); rods have no NC (cut and threaded); Z goes to DSTV as `SO`
(test one file on the machine); cold-formed default grade S350GD, cleats S275, rods/angles the frame grade — editable,
**to confirm**; members brought back by Import IFC lose their "generated" tag (a re-generation would not replace them);
the upstream Analysis tab now sees purlins/rods as frame members (an aid only — Phase 3 replaces it with the PEB analysis).

### Phase 2 plan (as agreed, kept for the record) Tests per step with hand-checked values, commit on `main` after each green step, everything
`designed: false` until Phase 4, `end-work.ps1` at the end.

### Phase 2 plan

**Findings.** bimsteelauto `design/purlins.py` designs C/Z to AISI S100 from CATALOGUE properties only (A, Ix, Sx,
Se_top/bot — never derived from dimensions), solves purlin lines as continuous beams, and treats the bottom flange as
braced only where a sag rod / brace is fitted. DetailCraft has no lipped C, no Z, no round rod and no metric angle
(its L sizes are AISC inch angles; EN covers IPE/HEA/HEB/UPN only) — Phase 2 adds them.

**Building model.** "PEB building…" stores its inputs in the model (`state.m3building`); the engine lays out every
member (Python, hand-checked) and the app builds parts. "Edit building…" reopens the form and regenerates: generated
members are tagged and replaced (a warning first); members you add yourself stay.

| # | Step | Tests (hand values) |
|---|---|---|
| 1 | App shapes: lipped C and Z (`C200x65x20x2.0`: depth × flange × lip × t, + inside radius), round rods (M12/M20, nuts + washers in the BOM), metric equal angles (L50x5 …); job catalogue (editable, generic starter sizes); outlines → 3D, marks, BOM, bar cut list | areas, kg/m, part weights for 2 C, 2 Z, rods, L50x5 |
| 2 | Engine: purlin and girt lines — spacing 1.25 m default, first position and spacing editable per roof side and per wall; C at eaves (eave strut), Z elsewhere; cleats | line positions for 2 buildings |
| 3 | Engine: laps and holes — lapped Z pieces over interior frames, simple at end frames; cut lengths; frame and lap holes; cleats PL8 | piece lengths, hole positions for 6 m and 7.5 m bays |
| 4 | Engine: sag rods, X-bracing (rods or angles) + eave struts in the chosen bays, flange braces | rod / brace end points and lengths |
| 5 | Engine: end walls — main frame, or end rafter + wind columns | geometry for both |
| 6 | Engine + app: framed openings per wall (girts cut, C jambs + header, + sill for windows) | girt pieces and jamb positions by hand |
| 7 | App: "PEB building…" form (span, length/bays, eave, slope, braced bays, spacings + first positions per side, lap, end walls, openings, sections), stored and regenerated | mapping tests + a browser check |
| 8 | Outputs: DSTV NC with holes for C/Z (best effort; test one file on the machine), rods, angles, cleats; CSV punch list for C/Z; IFC export AND import of every new part; cut list | contours/holes by hand; IFC round trip |
| 9 | HANDOVER, `end-work.ps1` | |

**Decisions (user, 2026-11-05).**
- Catalogue: **generic starter sizes** (Z/C 150–300 deep, t 1.5–3.0), geometry only; design properties blank, marked
  "from supplier", until a manufacturer's table is loaded (needed before Phase 4). Editable per job.
- Holes and cleats, **shop pattern "M12, 2+2, PL8 cleat"**: M12 bolts in 14 mm holes; at each frame 2 holes in the web,
  vertical gauge = depth − 2 × (lip + 25); at each lap end 2 holes, same gauge; cleat PL8 × (depth − 50) × 100 welded
  to the frame flange.
- Z/C NC: **both** DSTV (best effort) and a CSV punch list (mark, length, quantity, holes along the length and across the web).
- Openings: **framed openings** per wall (position, width, height): girts cut, C jambs + header (+ sill for windows).
- Flange braces (L50x5) default: **knee + haunch zone** — every purlin over the haunch length plus the next one, both
  sides of every interior frame; the top two girts of every column. Add / remove per position. (True hogging zones: Phase 3.)
- End wall with rafter + wind columns: **built-up**, wind columns equally spaced at most 6 m; end rafter and wind
  columns constant built-up sections from the span rules; editable.
- Lap length: **10 % of the bay each side of the frame** (6 m → 600, 7.5 m → 750); per-job override.
- From the scope: Z lapped over frames by default, C at eaves / openings / where chosen; spacing 1.25 m; sag rods 1 row
  at mid-bay for bays ≤ 7.5 m, 2 rows above, M12; rod X-bracing M20 in chosen roof and wall bays with eave struts,
  angle option (default L75x6, editable).
- Additions (user, 2026-11-05, defaults approved): **bolt size per job**, M12 default (14 mm holes) or M16 (18 mm
  holes). **Ridge purlins**: one each side of the ridge at 150–300 mm from the apex (default 200 mm, measured along the
  roof from the apex to the purlin's web line; editable); the first purlin at the eave strut; the rest evenly spaced
  between them, never more than the set spacing.
- Step 3 details (user, 2026-11-05): the shop pattern's cleat was too short for its gauge (200 deep: holes at 45 / 155,
  cleat 150) → **cleat = depth − 20** (180), top hole 25 below its top edge; **lap-end holes 40 mm** from the piece end;
  purlins/girts run out to the **end-wall girt line** (end column flange/2 + end-wall girt depth, 125 + 200 = 325 by
  default); **eave strut C: butt joints, 10 mm gap, 2 holes 25 mm each side of the frame line (4-hole cleat)**.
- Step 4 (user, 2026-11-05): sag rods through the webs at **one third of the depth below the top flange**; roof
  X-bracing nodes **near 45°** (panels ≈ bay long up the roof, snapped to purlin lines; eave strut and ridge purlin always
  nodes); wall bracing **one X if eave ≤ 1.5 × bay**, else two panels (node at the girt nearest mid-height); flange braces
  **45°, a pair** (one each side of the frame web).
- Step 4 detailing defaults by Claude — **TO CONFIRM with the user** (editable constants in `engine/peb/bracing.py`):
  sag-rod pieces end in their own holes, adjacent pieces 80 mm apart along the purlin; 50 mm thread each rod end; sag-rod
  fasteners 4 nuts + 4 washers per rod; roof brace rods through the rafter web 75 mm below the top flange; wall braces in
  the column web plane at mid-height, base to 100 mm below the eave; flange braces 50 mm into the purlin/girt; column
  flange braces horizontal in plan; at END columns only the inward brace of a pair (the outward one would leave the
  building); default braced bays = first and last bay.
- Step 5 end-wall set-out by Claude — **TO CONFIRM with the user** (`engine/peb/endwall.py`): BOTH end-wall types get
  wind columns (gable girts cannot span between the main columns): "main frame" = portal + interior wind columns under
  its rafter; "rafter" = end rafter on corner columns (at y = bf/2, span − bf/2) + interior wind columns. Wind columns:
  web = the span rules' rafter depth, constant, depth along X, outer flange on the end-wall plane (x = −bf/2 / L + bf/2,
  the same girt line as the main columns), top cut square under the rafter at the column centre. End rafter: constant
  rafter section, eave point to apex, plumb ends, 12 m split. Gable girts lapped over the wind columns; above the eave a
  row runs where it stays 300 mm under the roof.
- Step 6 openings set-out by Claude — **TO CONFIRM with the user** (`engine/peb/openings.py`): an opening = { wall A/B/
  first/last, at, width, sill (0 = door), height }; girt rows with sill < z < head cut between the jambs (2 new holes 40 mm
  from each cut end); C jambs (eave-strut section) from the floor (doors) or the girt at/under the sill (windows) to the
  first girt at/above the head (else the eave); C header at the head and C sill for windows unless a girt row is already
  there; all in the girt plane, depth out of the building.
- Planned defaults (Claude, approved): purlins on the rafters with the Z top flange up-slope; girts on the outer
  column faces; sag rods purlin to purlin, eave to ridge; bracing node to node; nested laps are marked as intended
  overlaps for the clash check.

### Phase 1 — what was built (steps and commits)

| # | Step | Commit |
|---|---|---|
| 1 | Engine: `engine/sections/builtup.py` (segments, splice/minimum checks, properties at any x via bimsteelauto `WeldedI`), `POST /section/builtup` | 988d821 |
| 2 | `app/manafe3/builtup.js` (cleanBuiltUp, segmentPlates, plateWeights, buMark) + `model.js` keeps `member.bu` | eea4d4c |
| 3 | `app/manafe3/builtup-parts.js` (web = shaped plate `SPL`, flanges = PL), marks/BOM, `app/manafe3/platelist.js` | 2777998 |
| 4 | 3D true taper (`view3d.js`), Properties segment editor + "Make built-up…" (`builtup-ui.js`), Output › Plate list | 6cbacec |
| 5 | DSTV NC: web as a sheet with its outline contour (`nc1.js`) | a958b83 |
| 6 | IFC4: web IfcPlate + IfcArbitraryClosedProfileDef, assembly per segment with `Manafe3_BuiltUp`; import rebuilds | 208c8f8 |
| 7 | PEB frame: `engine/peb/builtup_frame.py` (span rules, plumb/roof-line end cuts, 12 m transport split), form sizes | f45b063 |
| — | Drawings made safe: built-up assembly sheets left out and named (Phase 6) | 8920164 |

**Design facts to know.**
- `member.bu = { segments: [{ length, hwStart, hwEnd, tw, top:{b,t}, bot:{b,t}, grade, straight }], cuts?: { start, end } }`.
  The last segment's length is always the rest of the member line. `straight: 'top'` = the +v flange's outer face on the
  member line (rafter: roof line; column turned so −v points into the building: its outer face).
- End cuts: the member's end face is x = end + k·v (k = 0 square). PEB frame: rafter both ends k = slope (plumb at the
  column face and the ridge); column top k = −slope (follows the roof). Splices are always square.
- Parts per segment: web `<member>.s<n>.web` (type = the member's, assembly main part, profile kind `SPL` with an
  `outline`), flanges `.top` / `.bot` (type plate, `PL t×b` on their mid-thickness line, `look` = member colour).
  Weights gross = outline area × t × 7850. A web part starts at its outline's smallest x (DSTV needs x ≥ 0).
- Engine ↔ app names: engine snake_case (`hw_start`, `bf_top`, `cut_start`), app camelCase — converted only in
  `app/manafe3/peb-frame.js` `buOf`.
- Built-up PEB frames: column lines A/B are the columns' OUTER faces; eave height = roof line at the outer column face.

**Known limits (on purpose, later phases).** Holes/copes/connections on built-up members are reported, not built
(Phase 5); splices, knee and ridge are points only (Phase 5); flange-to-web welds not sized (Phase 5); a sloping flange's
end skew through its thickness is not cut in NC; built-up shop and assembly drawings: refused / left out with a message,
GA sheets draw built-up members approximately (Phase 6); the Analysis tab skips built-up members as "profile" (Phase 3);
Manafe3's own UI words are English only (not in `app/lang/*.json` yet).

### Phase 1 plan (as agreed, kept for the record)

**Findings.** Every DetailCraft part is one constant profile along a straight line (build.js → view3d, nc1, marks,
BOM, ifc, shop). A tapered web is a plate with a trapezoid outline, so the core addition is a **shaped-plate part**
(polygon outline × thickness) that each consumer learns. bimsteelauto `sections.py` already has `WeldedI` (A, Ix, Iy,
Sx_top/bot, Zx, …) and `TaperedMember` (only the depth varies; a flange change = a new member) — **reuse it**, with the
`sectionproperties` library (MIT, FE section solver, dev dependency) as the independent cross-check.

**Data model.** A member keeps its role (`column` / `beam`) and gets a built-up section: `segments[]`, each
`{ length, hwStart, hwEnd, tw, top: {b, t}, bot: {b, t}, grade, straight }`. Each segment = one shipping assembly of
3 plates (trapezoid web + 2 flange strips); segments meet at splice points. Minimums: web ≥ 6 mm, flange ≥ 8 mm.
**Splice check (user, 2026-11-05):** at every splice the adjoining segments must have equal web depth (hwEnd of the
one = hwStart of the next) and the same top and bottom flange widths; otherwise the member is refused with a message
naming the splice. (Flange and web thicknesses may change at a splice.)
Grades offered: S275, S355, A572 Gr 50, St 37, St 44, St 52.

| # | Step | Tests |
|---|---|---|
| 1 | Engine: properties at any x (A, Ix, Iy, Zx, Sx_top/bot) via bimsteelauto; `POST /section/builtup` | 2 tapered sections by hand at start/mid/end; `sectionproperties` within 1 % at 5 stations |
| 2 | Model + DOM-free geometry: store/validate/save/undo; segments → web outline + flange lines | outlines, areas, weights by hand (2 sections); minimums refused |
| 3 | Parts: shaped-plate part, assemblies per segment, marks, BOM, gross weight per plate (outline area × t × 7850, holes not deducted), a plate cut list | marks group identical plates; totals = hand totals |
| 4 | 3D true taper; Properties panel segment editor; convert a member to built-up | Node mapping tests + one browser check |
| 5 | NC: one DSTV file per plate, web with its trapezoid AK contour | contour points by hand |
| 6 | IFC4: assembly of 3 IfcPlate per segment (web = IfcArbitraryClosedProfileDef) + Pset `Manafe3_BuiltUp`; Import IFC rebuilds the member; other imports unchanged | export → import round trip; upstream suite green |
| 7 | "PEB frame…": built-up columns and rafters, haunch at the knee, splices at haunch end and ridge | geometry by hand for 2 frames |
| 8 | HANDOVER, `end-work.ps1` | |

Made safe, not built: shop/assembly drawings of built-up parts (Phase 6: buttons say "not yet"), Analysis tab marks
them "not checked" (Phase 3), flange-to-web welds not sized (Phase 5).

**Decisions (user, 2026-11-05).**
- Depth typed = **web plate depth hw**; overall d = hw + tf_top + tf_bot shown beside it (bimsteelauto uses d).
- Taper side = **PEB standard**, per segment: column outer flange plumb on the column line, inner flange sloping;
  rafter top flange straight along the roof line, bottom flange sloping.
- Splices in Phase 1 = **splice points only**: each segment its own assembly, cut square to the member at the splice;
  end plates and bolts come in Phase 5 (nothing invented).
- "PEB frame…" sizes = **span rules, editable in the form, `designed: false`**:
  - knee web depth hw_knee = span / 30, rounded up to 50 mm (24 m → 800)
  - column: hw from 300 at the base to hw_knee at the eave (one tapered segment)
  - rafter: hw_rafter = max(300, 0.5 · hw_knee) constant to the ridge; split again if a segment exceeds 12 m (transport)
  - haunch: length = span / 10 from the column face, hw from hw_knee to **hw_rafter** (24 m: 800 → 400), so the
    splice joins equal webs (user fix, 2026-11-05)
  - flanges: span ≤ 20 m 200×10, ≤ 30 m 250×12, else 300×16; web t = 6 if hw ≤ 600, else 8; grade S355
  - knee: the rafter starts at the column's inner flange face; ridge: the two rafters cut plumb at the apex.

## How to run

```powershell
.\start-work.ps1                    # git pull, uv sync, tests, prints this "Next task"
python manafe3.py                   # engine http://127.0.0.1:8765 + web app http://localhost:8000 (opens it)
python manafe3.py --check           # start, check /health and the page, stop
.\end-work.ps1 -Message "..."       # tests, "Last session" below, commit, push (refuses when a test fails)
```
(If scripts are blocked: `powershell -ExecutionPolicy Bypass -File .\start-work.ps1`.)

In the app: **Place › PEB** opens Manafe3's menu (Building…, Loads…; Analysis… in Phase 3) — one button so the
toolbar stays on one row; **Output › Lists** has the plate list and the C/Z punch list. **PEB › Building…** → the whole building (span, bays, eave, slope, frame sizes, purlin/girt spacing and
first positions, end walls, braced bays, lap, bolts, sections, openings) → **Make building**; the same button edits it
(generated members replaced, your own kept). **Output › Plates** / **Punch** download the plate list / C-Z punch list. Click a member: its segments are edited in
the Properties panel; any catalog beam/column has **Make built-up…**. **Output › Plate list** downloads the plate cut list.
After pulling new engine code, restart `python manafe3.py` (the engine does not reload itself).

## Architecture (decided)

```
browser (JS, port 8000)                                      engine (Python, port 8765)
DetailCraft fork: app/ + devshell/serve.mjs   --fetch-->     FastAPI engine/api.py
  app/manafe3/peb-frame-ui.js  (button, form)                  GET  /health
  app/manafe3/peb-frame.js     (DOM-free mapping)              POST /peb/frame (+ /defaults) -> engine/peb/frame.py,
  app/manafe3/builtup*.js      (built-up members)                                               builtup_frame.py
  app/manafe3/platelist.js, output-ui.js                       POST /section/builtup -> engine/sections/builtup.py
manafe3.py starts both (stdlib only; runs `uv sync` on first use)
```

- Engine units SI (mm, kN, MPa). Model axes: **X along the building (frame lines 1…n+1, DetailCraft's numbered
  grids), Y across the span (column lines A, B, lettered grids), Z up.** BIMSteelAuto uses X across / Y along: one
  conversion function when we hand frames to it (Phase 3).
- CORS: the engine accepts only http://localhost:8000 and http://127.0.0.1:8000 (port from `.env.local`).
- Per-machine settings: `.env.local` (git-ignored) — `MANAFE3_PROJECTS_DIR`, `BIMSTEELAUTO_PEB_PATH`,
  `MYSTEELAPP_PATH`, ports. Template: `.env.local.example`. Read by `engine/settings.py` and `manafe3.py`.
- Python: uv, Python 3.12, `uv.lock` committed → `uv sync` gives identical packages on both PCs. `[tool.uv] package =
  false`: the engine runs from the repo root.
- Later phases may port DetailCraft engine parts (nc1.js, nest.js, marks.js, IFC writer) to Python, each with a test
  proving equal output on the fixtures.

## DetailCraft source (v0.8.1) — what is where

- **No build step.** Plain ES modules + CSS + one page. `node devshell/serve.mjs` serves it at :8000; libraries
  (three.js 0.186.1, noble-*) are downloaded once by exact version into `devshell/vendor/` (git-ignored, sha256-checked
  against `devshell/vendor.json`) — from getcadcraft.com, the first time only.
- **Page:** `app/ui.inc` (+ `app/settings.inc`) rendered by `devshell/render.php` **with PHP**; without PHP (our PCs)
  the server uses the pre-rendered `devshell/index.html`. So UI changes go in JS, or in both `ui.inc` and `index.html`.
- **The app:** `app/detailcraft.js` (the page: toolbar, panels, 3D, reports, exports; ~2500 lines),
  `app/model.js` (the model state and its ONE edit path: `model.change(label, tx => …)` = one undo step; `Tx.addMember`,
  `setGrids`, `setLevels`…), `app/build.js` (model → parts), `app/view3d.js` (three.js), `app/profiles.js` +
  `app/shapes/sections.js` (profile tables: W, C, L, HSS, IPE/HEA/HEB…), `app/connections.js` (end plate, base plate,
  shear tab, splice, gusset, mitre — geometry only, no strength), `app/marks.js` (numbering), `app/nc1.js` (DSTV NC),
  `app/nest.js` (cut list), `app/ifc.js` / `app/ifc-import.js` (IFC4 out / IFC2X3+4 in), `app/drawings.js` +
  `app/shop.js` + `app/pdf.js` + `app/dwgout.js` (GA/assembly/shop sheets as PDF/DWG/DXF), `app/clash.js`,
  `app/analysis*.js` + `app/frame/` (first-order frame analysis, AISC/EN I-shape checks — an aid), `app/rebar.js`,
  `app/stair.js`, `app/agents.js` (tools for AI assistants), `app/lang/*.json` (words), `app/help/*.md` (help;
  compiled to `help.js` by PHP).
- **Model state** (`model.js` header): `{grids:{x:[{label,at}],y:[…]}, levels:[{name,z}], members:[{id,type:
  beam|column|brace|plate, profile, material, start:[x,y,z], end, rotation, position, cuts, holes, phase}],
  connections, footings, stairs, bolts, profiles, phases, issues, …}`, mm, Z up. Saved as `.detailcraft.json`.
- **Tests:** `npm test` = `devshell/test.mjs`: builds a mirror in `.cc-test/` (layout of their website repo), runs
  every `tests/bin/test-*.mjs`. Main suite `test-detailcraft.mjs` (7714 checks). Optional readers (Python venvs,
  poppler, LibreOffice, `--oracles` copyleft readers) are skipped when absent — that is normal here.
- **Not built yet upstream** (`app/help/not-built-yet.md`, summary): no haunches, no tapered members, no connection
  strength checks, first-order analysis only (no P-Δ), no wind/snow load generation, round holes only (no slots),
  shop drawings of I-shapes and plates only, no imperial input. That is exactly what Manafe3 adds.

## Rename (Phase 0) — what was renamed and what deliberately was not

- `tools/manafe3-rebrand.mjs` (re-run after every upstream merge; `--check` lists leftovers): visible
  "DetailCraft"/"CadCraft" → "Manafe3" ("CadCraft Studio" → "Manafe3 Desktop") in `app/lang/*`, shell lang files,
  help (`.md` + compiled `help.js`), `devshell/index.html`, `app.json` name, window title, file-type labels.
- By hand: Manafe3 logo (`devshell/site/favicon.*`, concept B M-frame from `branding/` — see `branding/README.md`), app-bar logo, "About" link to getcadcraft.com hidden.
- **Kept on purpose (not visible / needed by tests):** internal slug `detailcraft` (test mirror paths), module and
  file names, the `.detailcraft.json` / `detailcraft-clip` formats, code comments, and the **producer strings inside
  exported files** (NC header `** DetailCraft`, IFC FILE_NAME / Pset 'DetailCraft', PDF Producer, KISS id line, USD
  app). Those are asserted by upstream tests; rename them with their tests in Phase 6 (drawings/exports).
- Every changed upstream file is listed in `MANAFE3-CHANGES.md`.

## Decisions made

| Decision | By | When |
|---|---|---|
| Architecture (JS fork + Python FastAPI engine, one launcher, SI) | user | prompt |
| Fork base: DetailCraft tag `detailcraft-v0.8.1` (latest), remote `upstream`; `main` is ours | user/Claude | 2026-11-04 |
| GitHub CLI installed with winget on ENG04-PC | user | 2026-11-04 |
| BIMSteelAuto as a git dependency: `pyproject.toml` added on branch `packaging` of the public repo (only files already public) | user | 2026-11-05 |
| Upstream CI workflow removed (no Actions minutes); tests run locally via start-work/end-work | user | 2026-11-05 |
| Manafe3's own code stays "All rights reserved – Ahmed Ali" (final) — SUPERSEDED 2026-11-10 | user | 2026-11-05 |
| The repository is public; Manafe3's own code is Apache-2.0 too (NOTICE, TRADEMARKS for the name and logo) | user | 2026-11-10 |
| The 5 private peb files that differ from the public repo stay PRIVATE (used through `BIMSTEELAUTO_PEB_PATH`) | user | 2026-11-05 |
| bimsteelauto `packaging` merged into its `main` (fast-forward; `main` = c0b2318, the commit Manafe3 pins) | user | 2026-11-05 |
| Upstream bug fixed: `app/dwg/objects-write.js` synced from `tests/lib/dwg` (upstream's own test failed on v0.8.1) | Claude | 2026-11-04 |
| UI added from JS (`app/manafe3/`), not `ui.inc`, because no PHP on the PCs and to keep merges easy | Claude | 2026-11-05 |
| Logo: concept B "M-Frame" (M as a two-span tapered frame; navy + primer orange, wordmark with the 3 in orange); replaced concept A the same day; all concepts kept in `branding/` | user | 2026-11-05 |
| Phase 0 profiles: placeholders by span (≤15 m HEA300/IPE400, ≤24 m HEA400/IPE500, else HEA500/IPE600), `designed: false` | Claude | 2026-11-05 |
| Phase 1: web plate depth input; PEB-standard straight flange; splice points only; span-rule sizes; haunch ends at the rafter depth; splice check (equal webs, same flange widths) | user | 2026-11-05 |
| Phase 1: section properties = bimsteelauto `WeldedI` (reused, not rewritten); `sectionproperties` (MIT) as the independent check, dev dependency only | Claude | 2026-11-05 |
| Phase 1: member end cuts (k·v) to make the agreed plumb ridge / column-face cuts; column top along the roof line | Claude | 2026-11-05 |
| Phase 1: built-up frame column lines = outer column faces; `section: "hot_rolled"` keeps the Phase 0 frame | Claude | 2026-11-05 |
| Phase 1: grades S275, S355, A572 Gr 50, St 37, St 44, St 52; web part = assembly main (marks C…/B…) | Claude | 2026-11-05 |

## Reusing existing work

- **BIMSteelAuto (public, MIT)** — `bimsteelauto` in `pyproject.toml` from git, pinned to commit c0b2318 of
  `main` (`uv.lock`; it was branch `packaging`, merged 2026-11-05). Installs `bimsteelauto`, `bimsteelauto_connections`, and the vendored cfs modules
  `aisi_s100`, `direct_strength`. Optional extra `[fabdraw]` (ifcopenshell 0.8.5, ifcclash, ifctester, ezdxf, shapely,
  pymupdf) — not installed yet. Pins: PyNiteFEA 3.0.0, numpy 2.5.1, scipy 1.18.0, pyaisc360 @ 007a3f6.
- **Private PEB pipeline (office PC)** — a private local folder (`BIMSTEELAUTO_PEB_PATH` in `.env.local`); never in this repo
  (`BIMSTEELAUTO_PEB_PATH`). Its HANDOVER_PROMPT.md was read. Facts:
  - Layer 1 engine `bimsteelauto\` (spec.py ProjectSpec/DesignResult = THE CONTRACT; pipeline.run_frame; sections.py
    tapered built-up I; loads\wind.py = ASCE 7-16 wind — **there is no file called `peb_wind.py`**; analysis\frame.py
    plane frame (verified), space.py 3D; design\; report\calcsheet.py; fabdraw\ gates G1/G2). Layer 2 = FreeCAD adapter
    (not for Manafe3), Layer 3 = workbench.
  - Its baseline: `pytest` 1083 passed, 1 skipped, 3 xfailed (2026-10-26).
  - Compared with the public repo (line endings ignored): **only 5 files differ** — `bimsteelauto/connections.py`,
    `bimsteelauto/spec.py`, `bimsteelauto/design/members.py`, `bimsteelauto_connections/core.py`,
    `bimsteelauto_connections/__init__.py`. Everything else is identical.
  - **Import plan:** the engine uses the public package by default. Where the private version is needed, an opt-in
    module `engine/integrations/bsa_private.py` (Phase 3) will put `BIMSTEELAUTO_PEB_PATH` (and its `vendor\cfs`) at the
    FRONT of `sys.path` only when the setting is present, and `/health` will report which copy is in use. **Decided
    2026-11-05: the 5 files stay private**, so this opt-in override is the way to use them (a private package may
    replace the path setting later). Never copy them into Manafe3 or into the public repo.
  - Its working agreements carry over (CLAUDE.md): VERIFIED flags, negative controls, no circular verification, never
    invent a value, NOT FOR ISSUE until verified, do not modify `bimsteelauto_connections`.
- **MySteelApp Studio** (`C:\MyStructureApp`, laptop): **LAPTOP TASK** — on DESKTOP-VBCSCS0 inventory `main.py` and its
  modules (FEA, 3D model, DXF/STAAD export, MTO) and list which are worth reusing (STAAD export and MTO especially). Set
  `MYSTEELAPP_PATH` in the laptop's `.env.local`.
- **PyNite** (`PyNiteFEA`) production solver; **anastruct** independent cross-check (both installed).

## Open items

1. Laptop: choose its projects folder and fill `.env.local`; do the MySteelApp inventory.
2. Upstream checks skipped on Windows (python venv for oracle readers, poppler, unzip, DSTV runners): optional.

3. Optional: rewrite the git history to drop the old private-folder path (a force push — the user's call).
4. bimsteelauto suite, two failures that are not from Manafe3's changes (seen 2026-11-12, run with the Manafe3 venv):
   `tests/test_bsa_dxf.py` cannot import `ezdxf` (not installed in that venv); `tests/test_fc_adapter.py::
   test_the_engine_writes_the_json_the_adapter_reads` needs `design_result.json`, written by `run_frame_example.py`
   (not present in the clone). Both fail the same way without the 0.15.3 change.
5. **CLOSED (2026-11-15)** — bimsteelauto 0.15.4 (main `358c2fb`, pushed with the user's approval; Manafe3 pinned to it):
   the double-fillet base metal (user decisions 2026-11-15: 1a 2a 3a 4a 5a, 6 yes): `size_fillet_weld(t_shared=, base_mode=)` opt-in (default unchanged: the
   thinner part's full t to each line, J2-2 shear), `base_mode="tension"` = J4.1 (still unverified), `fillet_line_strength`
   per mm; Manafe3 step 3 passes the flange / web as the shared plate, step 4's `size_line` calls `fillet_line_strength`
   (its own pyaisc360 weld / base-metal code removed). Step 3 "full strength" now means the DESIGN strength 0.9 Fy (flange
   0.9 Fy bf tf, web tension zone 0.9 Fy tw Lt; the end-plate stiffener already used it): the base-metal row of such a
   weld reads "develops plate (by definition)", U is the weld metal's. Building 1 weld sizes unchanged (end plates 8 / 5
   mm, stiffener welds as before, flange-to-web 5 mm, base 5 mm).
6. **CLOSED (2026-11-15, user review: hand values match, every U ≤ 1.0)** — longitudinal wind. Finding: the frame lines already carry ASCE 7-16
   Load Case B (WB+ / WB−, Fig. 28.3-1's longitudinal case); the bracing is Case B zones 5 / 6 scaled to the §28.3.4
   minimum when that governs. What was missing was the PAIRING. User decisions (1a–7a + additions):
   - `engine/connections/longitudinal.py`: every LRFD combination with WB± pairs the frame reaction (Ry, Rx) with the
     Case B brace force alone × its wind factor (1.0 / 0.5); the minimum family 0.9D / 1.2D + 1.0 W_min pairs the minimum
     brace force with the DEAD-LOAD reaction only (never a WB uplift). The bracing result now carries `minimum_scale` and
     `minimum_ratio` (endwall_analysis.longitudinal_feed) to split them.
   - Printed per base / building: the Ch. 28 limits (h ≤ 18 m and h ≤ the least plan dimension — else the pairing is NOT
     EVALUATED) and the torsional-case exception (one-story h ≤ 30 ft / 9.1 m, or a stated flexible diaphragm — else
     torsion NOT EVALUATED and the base stays PARTIAL).
   - Base plates / anchors (`building_bases(..., analysis=)`, the anchors take √(Vs² + Vw²)) and the base welds take the
     pairs; a braced-bay base is DESIGNED only when every pair is evaluated and passes.
   - Building 1 (h 6600 mm, limits met, torsion exempt; brace T 21.075 = 1.11743 × Case B 18.861): worst uplift frame line
     1 / 5 base A 0.9D + 1.0WB+: 22.302 + 13.224 = 35.526 kN (base B 27.925); frame line 2 / 4 base A 44.341 (B 35.307);
     minimum family at 0.9D: 1.197 kN. Old → new at the 8 braced-bay bases: plate 12 mm 370 × 250 → unchanged, rods M20
     → unchanged (anchor concrete still NOT EVALUATED: no pedestal input), weld 5 mm → unchanged; base weld status
     "PARTIAL - brace case NOT EVALUATED" → "DESIGNED"; base plate status unchanged ("PLATE DESIGNED - ANCHORS NOT
     EVALUATED").
   - Tests: `engine/tests/test_longitudinal.py` (hand values, negative controls: the minimum never paired with a WB
     uplift; h > 18 m → NOT EVALUATED; h above the least plan dimension; torsion not exempt); `test_welds.py` building 1.
   - Review table (building 1, old → new, governing over every case; anchor U = rod STEEL only — φ 0.65 tension, 0.60 ×
     0.80 grout shear, 4 × M20 4.6; combined = ACI 17.8 on the steel U; plate = (t_req / 12)²; weld = the larger of web /
     flanges):
     | Bases | Uplift kN (governing) | V strong / V weak max | rod T | rod V | combined | plate | weld |
     |---|---|---|---|---|---|---|---|
     | F1-BA, F5-BA | 24.48 → 35.53 (0.9D+1.0WB+) | 31.62 / 0 → 31.62 / 15.03 | 0.096 → 0.139 | 0.280 → 0.280 | 0.280 → 0.280 | 0.287 → 0.417 | 0.080 → 0.080 |
     | F1-BB, F5-BB | 24.48 → 27.93 (0.9D+1.0WB+) | 31.62 / 0 → 31.62 / 15.03 | 0.096 → 0.110 | 0.280 → 0.280 | 0.280 → 0.280 | 0.287 → 0.328 | 0.080 → 0.080 |
     | F2-BA/BB, F4-BA/BB | 54.87 → 54.87 (0.9D+1.0WA±: transverse still governs; the Case B pair 44.34 / 35.31) | 59.74 / 0 → 59.74 / 15.03 | 0.215 → 0.215 | 0.529 → 0.529 | 0.529 → 0.529 | 0.644 → 0.644 | 0.151 → 0.151 |
     Sizes set by the minimums: plate 12 mm = the palette minimum (t_req at most 9.63); rods M20 = `rod_min_frame` (steel U
     at most 0.53); the 300 mm embedment minimum is NOT applied (no pedestal → no embedment chosen; the concrete modes
     are not evaluated).
7. **Phase 4 member-check gap** (user 2026-11-15) — fix BEFORE step 7: the braced-bay columns (axial force from the wall
   bracing) and the eave struts (strut forces) are not checked under the brace axial forces. Shown as NOT EVALUATED on the
   connection results (`longitudinal.members_not_evaluated`) and in the design run summary (`brace_axial_not_evaluated`).
8. **Pedestal / footing input** (user 2026-11-15) — fix BEFORE step 7, the user's decisions first: with no pedestal input
   EVERY base of a building (building 1: all 16 — 10 frame bases and 6 wind-column bases) reads "PLATE DESIGNED - ANCHORS
   NOT EVALUATED": only the rod steel is checked, the ACI 318-19 Ch. 17 concrete modes (breakout, pullout, side-face
   blowout, pryout) and the embedment are not. Input needed per building (or per base type): pedestal / footing size,
   edge distances, f'c, cracked or uncracked, and the hairpin / anchor-reinforcement option (step 2b).

(Settled 2026-11-05: private peb files stay private; `packaging` merged into bimsteelauto `main`. 2026-11-10: the repo is
public and all of it Apache-2.0.)

## Roadmap (do NOT build ahead of the current phase)
- Wind-column deflection limit and end-wall serviceability in Design… (not checked today; the web is held ≥ 300).
- Sizing loop: different flange plates per segment (column / haunch / rafter) for lighter frames (user, 2026-11-09 —
  roadmap, not now; the generator's splice rule keeps one flange plate today).

- **Phase 1** tapered built-up member type (web taper, flange plates, 3D, BOM, NC per plate) — **DONE 2026-11-05**
- **Phase 2** secondary steel (Z/C purlins and girts with laps, sag rods, flange braces, rod/angle bracing, end-wall frames) — **DONE 2026-11-05**
- **Phase 3** loads (dead, live, ASCE 7-16 Ch. 28 wind from bimsteelauto `loads/wind.py`) + PyNite analysis with taper
  discretisation and P-Delta — **DONE 2026-11-07**
- **Phase 4** member design ECP 205 / AISC 360 + cold-formed AISI S100
- **Phase 5** connections from bimsteelauto_connections (eave/apex end plates 4E/4ES/8ES, base plates + anchors, cleats,
  gussets) with HTML calc sheets — **including vertical slotted holes at every wind-column top (rafter deflection)**,
  and welding the generated cleats / cap plates into their frame and column assemblies
- **Phase 6** drawings: anchor bolt plan, frame elevations, built-up member shop drawings, erection drawings; NC/DSTV,
  IFC4 with Psets, MTO Excel (rename the producer strings in exports here, with their tests)
- **Phase 7** packaging: Windows installer, then optional online hosting
- **Later (user, 2026-11-08 — roadmap only, do not build now):**
  - a **concrete / reference member type**: drawn and clash-checked, never counted in steel weight (MTO, BOM);
  - **crane support**: runway girders, brackets, crane loads in the analysis (the Phase 4 serviceability "crane hook").

## Tests (after the Phase 3 answers, 2026-11-08)

- Engine **111 passed**: + C&C (`test_cc_wind.py`: WF3 longhand, bounds, θ reduction, minimum, zone 5 vs 4), the
  longitudinal feed (areas longhand, total = bimsteelauto p × area, eave share ≠ 0.5), strut drag from the larger side,
  end-wall bracing (geometry by hand, T·cos θ = load at rafter level, slack diagonal, refusal).
- App **13 of 13**. Browser: an end-rafter building → Analysis… 48 s, end-wall X-brace 10.22 kN (LRFD), no console errors.

## Tests (baseline after Phase 3, 2026-11-07)

- Engine `uv run pytest -q`: **104 passed** (~5 min; the frame solves dominate) — Phase 2 (71) + loads input; the frame
  model (closed-form portal H = 15 kN, tapered cantilever vs Simpson within 1 %); loads by hand; statics of every load
  case; P-Delta amplifies the sway with columns in compression and reduces it in tension (negative control); the moment
  sign; PyNite vs anastruct (independent code) within 1–2 % for D and WA+L; the `.std` text by hand; the bracing chain
  longhand + a PyNite tension-only truss (slack diagonal); wind columns as closed-form simple beams; the end-rafter frame
  by longhand statics and anastruct; taper-step convergence; secondary weights by hand; de-duplicated lines re-solved;
  the ECP 201 slot refuses; the API refuses a missing wind speed.
- App `npm test`: **13 of 13 test files passed** — + `test-manafe3-analysis.mjs` (21: diagram points by hand, PyNite's
  local-y rule incl. vertical members, reactions CSV, summary ratios, refusals).
- Browser (headless Edge, fresh engine): the default building (24 m span, 4 × 6 m bays, main frames at
  both ends) → Analysis… in 29–38 s, 5 lines / 2 distinct, 49 cases and combinations, symmetric M on the tension side, sway under
  wind downwind, `.std` download 206 lines; no console errors.

## Tests (baseline after Phase 2, 2026-11-05)

- Engine `uv run pytest -q`: **71 passed** — Phase 1 (39) + purlin/girt lines, laps/holes/cleats, sag rods/bracing/flange
  braces, end walls, openings, the whole building (hand values in each test header).
- App `npm test`: **11 of 11 test files passed** — upstream 7714 + 13 unchanged; Manafe3 tests incl. cold-formed shapes,
  the building fixture (`fixtures/manafe3/building1.json`, made by the engine) into a real model (596 parts by hand), NC /
  punch list / IFC round trip of the whole building.
- Browser: "Building…" 24 m × 4 bays + door → 364 members, 150 cleats, 1 996 holes, 596 parts, 47 marks, 39 assemblies,
  22 463 kg, no console errors; toolbar on one row at 1600 px (before the ridge-tie / wind-column / gable-cleat changes;
  after them the fixture gives 370 members, 196 cleats, 648 parts — checked by hand in `test-manafe3-building.mjs`).

## Tests (baseline after Phase 1, 2026-11-05)

- Engine `uv run pytest -q`: **39 passed** — health, CORS, hot-rolled frames by hand (Phase 0), built-up sections S1/T1/T2
  by hand (A, Ix, Iy, Zx, Sx top/bottom), `sectionproperties` within 1 % at 5 stations (agrees to < 0.0001 %), a negative
  control (web depth taken as overall depth is 7.5 % off and must fail), splice/minimum refusals, built-up frames 24 m and
  36 m by hand (36 m rafter split for transport).
- App `npm test`: **8 of 8 test files passed** — upstream 7714 + 13 (unchanged), Manafe3: built-up model 26, parts 28,
  editor 16, NC 10, IFC 14, PEB frame 30.
- Browser (headless Edge): built-up members in 3D with true tapers; panel edit 800 → 900 gives 509.4 kg (hand 509.38);
  tw 4 refused; PEB frame 24 m × 4 bays → 20 members, 90 parts, 9 part marks, 3 assemblies, 12 812.4 kg, no console errors.
- Independent hand values are written out in each test's header; none is recomputed by the code under test.

## Last session

<!-- LAST-SESSION:START (written by end-work.ps1) -->
- When: 2026-11-15 09:20 on ENG04-PC
- Did: Phase 5 step 4: welds (approved)
- Tests: engine engine: 239 passed (34 files, largest peak 323 MiB in test_building_analysis.py, 1152 s) | app 16 of 16 test files passed
<!-- LAST-SESSION:END -->
