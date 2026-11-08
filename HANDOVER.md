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

**Phase 4 — member design. Plan APPROVED by the user (2026-11-08) with additions A and B; in progress — step 1 done,
the bimsteelauto sign fix and end-frame braces done; next step 2 (Direct Analysis Method).**

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
| 2 | Direct Analysis Method in the analysis: 0.8 τb EI, notional loads 0.002 Yi in the gravity combinations | notional-load statics; a portal by hand |
| 3 | Main frames AISC 360-16: station checks incl. **DG 25** for tapered segments (A) and **E7 / F5 / G2 without TFA** (B), Lb from step 1 along the whole design member | longhand per limit state; a section that must fail |
| 4 | Serviceability (ASD): sway H/100, rafter L/180 under Lr; editable; crane hook | ratios by hand |
| 5 | Wind columns (C&C), end rafter, side- and end-wall bracing, eave struts | longhand per type |
| 6 | Purlins / girts AISI S100: properties from geometry (DSM / EWM, vendored engine), supplier-table override; C&C zones; L/150 | one line by hand |
| 7 | ECP 205-LRFD from the ecp205-lrfd dependency (ton / cm inside, one boundary), side by side; the governing code from the project setting | one member longhand ECP, equations confirmed with the user |
| 8 | Sizing loop: target 0.90, ≤ 1.00, the plate / width / depth lists above, re-analyse until stable | converges on building 1, minimums kept |
| 9 | Browser "Design…" + project design settings (governing code, limits, target); utilisation colours, tables, HTML calc sheets (NOT FOR ISSUE until verified) | mapping + browser check |
| 10 | HANDOVER, `end-work.ps1` | |

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
- **St 37 Fu: STILL OPEN** — the user's reply held the placeholder "<3.6 or 3.7>", not a value. The table keeps 3.7
  (skill transcription) marked TO CONFIRM; the skill engine is not changed until the value is given.
- All plate strengths VERIFIED False with their sources until the user confirms them.

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
| Manafe3's own code stays "All rights reserved – Ahmed Ali" (final) | user | 2026-11-05 |
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
- **Private PEB pipeline (ENG04-PC)** `D:\Download\AI estimation\bimsteelauto_connections_v0.7.0\peb\`
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

(Settled 2026-11-05: private peb files stay private; `packaging` merged into bimsteelauto `main`; own code All rights reserved.)

## Roadmap (do NOT build ahead of the current phase)

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
- When: 2026-11-08 08:44 on ENG04-PC
- Did: Phase 3 answers: C&C wind columns, end-wall X-bracing, longitudinal feed from actual top reactions; ECP 201 refusal names the source; Phase 4 plan drafted
- Tests: engine 111 passed, 1 warning in 300.10s (0:05:00) | app 13 of 13 test files passed
- Next: User: review the Phase 4 plan DRAFT in HANDOVER and answer its 6 questions; no Phase 4 code before approval
<!-- LAST-SESSION:END -->
