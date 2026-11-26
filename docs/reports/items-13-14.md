# Open items 13 and 14: eave transfer and wind-column tops, options compared (report, 2026-11-26)

NOT FOR ISSUE. Report only: no engine code, test or HANDOVER change goes with this file. Run on the laptop
(DESKTOP-VBCSCS0) at `main` `aad723da`, one engine run at a time. The option runs used throw-away scripts outside the
repository. They patched the bracing generator (`engine/peb/bracing.roof_nodes`) or the end-frame rafter segments **in
memory only**, then ran the normal engine chain: `analyse_building`, `building_joints`, `building_endplates`,
`building_eave_transfer` (5d), `building_brace_ends` (5b), `sizing.evaluate` (Phase 4, AISC, DG 25) and `cfs_checks`
(step 6). Option 14(c) also ran `secondary_checks` (end rafters, posts, bracing). The fixtures are
`fixtures/manafe3/building1-sized.json` (building 1) and `building1-apex.json` (building 1 + apex haunch).

## User decisions 2026-11-26 (recorded)
- **Item 13 = option (a):** the lowest roof-brace node moves from the first purlin past the knee to the eave (the eave strut
  line).
- **Item 14 = a per-end-wall input "expandable" (default NO):**
  - **NO** = post-and-beam end wall (end rafter on posts), with the end rafters and posts **sized properly**, and with the
    **post-top connection** and the **end-rafter eave transfer** wired into 5d and checked.
  - **YES** = rigid end frame with the **sliding bracket** at the wind-column tops.
  - When a ridge-column long slot goes beyond AISC J3, that stays an **open decision, flagged unverified**.
- **Order:** implement item 14 **after the DetailCraft 0.11 merge and the engine test speed-up, BEFORE step 7.**

## Item 13: the eave transfer at the interior braced-bay frames 2 and 4

The option geometry is Claude's what-if choice, not a design value: the rod's lower end goes into the haunch web
**100 mm past the column's inner face** (see note 2). In (a) the first panel's lower node moves there. In (b) every node
is kept and an extra X is added between that point and the first purlin.

### Building 1 (`building1-sized.json`)

| | Base | (a) lowest node moved to the eave | (b) extra brace in the eave panel |
|---|---|---|---|
| Frames 2/4, side A (top flange alone) | **1.066 FAILS** | 0.984 | 0.996 |
| Frames 2/4, side B | **1.008 FAILS** | 0.937 | 0.950 |
| Eave nodes | 4 pass / 4 fail | 8 pass | 8 pass |
| Next checks (column top / knee tension bolts) | 0.822 / 0.794 | 0.822 / 0.795 | 0.828 / 0.797 |
| End frames 1 / 5 (top flange alone) | 0.601 | 0.494 | 0.506 |
| Worst roof-brace end (rafter F2-RA net section at the rod hole, P310-a) | 0.879 | 0.922 | 0.913 |
| Worst brace end overall (wall brace on column F2-CA) | 0.976 | 0.976 | 0.978 |
| Main frames, worst ratio (Phase 4) | 0.8965 | 0.8965 | 0.8982 |
| Purlins / eave struts (step 6, worst) | 0.727 | 0.727 | 0.727 |
| F_x Case B at the node, kN | 14.83 | 14.13 | 18.82 (*) |
| Roof rods, total length | 128.678 m (16 rods) | 131.704 m (16 rods) | 176.908 m (24 rods) |
| Steel added (RD20 at 2.466 kg/m) | — | **+7.5 kg** | **+118.9 kg** |
| Members | 432 | 432 | 440 |
| Parts that change | — | 8 roof rods RD20 (the first panel of bays 1 and 4, both slopes) grow from 7 648.9 to 8 027.1 mm; their lower hole moves from the first purlin (a = 688.5 mm) to the haunch web (a = 100 mm); the first purlin is no longer a roof-X node | + 8 RD20 rods of 6 028.8 mm (very flat: 5.6° to the purlins), + 16 rod ends (brace-end joints 48 → 64), + 8 holes in the haunch web |

(*) The engine takes F_x = T of the deepest panel × the brace's own direction cosine. On the flat eave-panel diagonal
that overstates it: the real panel shear is V ≈ 13.4 kN in Case B. So (b) is a little better than its numbers.

### Building 1 + apex haunch (`building1-apex.json`)

| | Apex base | (a) lowest node moved to the eave | (b) extra brace in the eave panel |
|---|---|---|---|
| Frames 2/4, side A (top flange alone) | **1.042 FAILS** | 0.961 | 0.974 |
| Frames 2/4, side B | 0.985 | 0.916 | 0.929 |
| Eave nodes | 6 pass / 2 fail | 8 pass | 8 pass |
| Next checks (column top / knee tension bolts) | 0.805 / 0.776 | 0.805 / 0.777 | 0.811 / 0.779 |
| End frames 1 / 5 (top flange alone) | 0.590 | 0.484 | 0.495 |
| Worst roof-brace end (rafter F2-RA, P310-a) | 0.855 | 0.901 | 0.892 |
| Worst brace end overall (wall brace on column F2-CA) | 0.957 | 0.957 | 0.959 |
| Main frames, worst ratio (Phase 4) | 0.8783 | 0.8783 | **CRASH** (note 3) |
| Purlins / eave struts (step 6, worst) | 0.727 | 0.727 | 0.727 |
| F_x Case B at the node, kN | 14.91 | 14.21 | 18.92 (*) |
| Steel added | — | +7.5 kg | +118.9 kg |
| Members | 448 | 448 | 456 |
| Parts that change | — | as building 1 (a) | as building 1 (b) |

The apex base reproduces `docs/reports/item17.md` to within 0.0005: side A there is 1.0413, here 1.0418; side B 0.9841
there, 0.9846 here. The difference is probably item 17b's kink flange braces, which were added after that report.
Not checked.

### Why plain building 1 already fails
The failure was recorded on **plain** building 1, before the apex haunch existed. Step 5d (2026-11-17, review 1) gave
1.047. Open item 7 (2026-11-17), which added the bracing's axial forces, raised it to 1.066. The apex haunch (item 17,
2026-11-24) **lowers** it to 1.042, and side B passes, because the knee forces drop.

### What the pass rests on
- At a = 100 mm the top flange is already at about **0.94 from the frame moment alone**; F_x × a adds only about 0.04.
  The pass margin is small and grows with a (note 2).
- The clean detail for (a) is the rod into the **column top** (a gusset at the cap or knee stiffener), which takes the
  rafter flange out of the load path. Then the column top (0.82 / 0.81) would govern. The engine cannot check that path
  today: 5d looks only for rafter hosts.

## Item 14: wind-column top slots (building 1)

The required movement after bolting is from the ASD combinations without D (the 5d rule):
- quarter-span columns: δ down 28.70, up 24.23 mm (third column up 22.82) → slot 77 / 76 mm with M16;
- ridge column: δ down 62.38, up 49.36 mm → slot 136 mm with M16.

The AISC long slot is 2.5 d: 40 mm for M16.

### (a) Sliding bracket
With a slot in each of two plates, each slot = d0 + (δ_down + δ_up + 6) / 2. Hole sizes and slot limits are from AISC
Table J3.3M, **from memory, VERIFIED False**.

| Bolt (hole / long-slot limit) | Quarter-span columns | Ridge column |
|---|---|---|
| M16 (18 / 40 mm) | 48 mm, too long | 77 mm, too long |
| M20 (22 / 50 mm) | 52 mm, too long | 81 mm, too long |
| M24 (27 / 60 mm) | **57 mm, fits** | 86 mm, too long |
| M30 (33 / 75 mm) | — | 92 mm, too long |

- No AISC long slot fits the ridge column.
- AISC J3.2 (from memory, VERIFIED False) allows a long slot in only ONE part at a contact surface. A bracket with two
  slots must therefore be a **three-plate slider**: an intermediate plate and two bolt groups, with one slotted part at
  each contact surface.
- Strength: the M16 checks are already 0.451 / 0.495 (eccentric bolt shear); bigger bolts only lower them.
- Steel: roughly +4 kg per top, about +25 kg for 6 tops. This is an estimate: the plate is not designed.

### (b) Stiffer end-frame rafter
Frame line 1 was solved alone with the rafter segments replaced in memory: the haunch runs from the knee depth to H,
then H is constant to the ridge; flanges bf × tf; tw = max(6, `web_t`); the columns unchanged. The slot uses the 5d
rule. The base row reproduces the engine's 77 / 136 / 76 mm.

| End rafter (web H × flanges) | Slot, quarter columns / ridge / quarter (M16) | Rafter steel per end frame |
|---|---|---|
| 300 × 200×10 (now) | 77 / 136 / 76 | 1 072.7 kg |
| 600 × 200×10 | 53 / 79 / 53 | 1 365.5 kg |
| 750 × 250×12 | 43 / 58 / 43 | 2 136.9 kg |
| 900 × 250×12 | 39 / 51 / 39 | 2 332.1 kg |
| 1000 × 250×15 | 36 / 44 / 36 | 2 734.6 kg |
| 1000 × 300×15 | 35 / 43 / 35 | 3 006.9 kg |
| 1100 × 250×15 | 34 / 42 / 34 | 2 864.7 kg |
| **1200 × 300×15** | **32 / 38 / 32 (fits 40)** | **3 267.2 kg** |
| 1500 × 300×15 | 30 / 33 / 30 | 3 657.6 kg |

- **Needed: about a 1200 mm web with 300×15 flanges, +2 194.5 kg per end frame, +4 389 kg for both end frames.**
- Not checked: the knee and its end plate (a 1200 mm rafter against a 475 mm column top), the columns, member strength.
- A mix also works on paper: a 750 × 250×12 rafter (+1 064 kg per frame) with the M16 slider gives slots of
  18 + (18.6 + 6) / 2 = 31 mm and 18 + (33.7 + 6) / 2 = 38 mm.

### (c) Post-and-beam end walls (`end_first` = `end_last` = "rafter")

End-wall steel was weighed from the generated members at frame lines 1 and 5:
- built-up members from their plate segments;
- rods by area;
- the other parts by length × weight per metre: PL10x190 = 14.9 kg/m, L50x5 = 3.77 kg/m (table value from memory).

| | Rigid end frame (now) | Post-and-beam |
|---|---|---|
| Built-up members + rods, both end walls | 4 616.5 kg | **4 306.9 kg (−309.6 kg)** |
| — in that | columns 1 191.6, rafters 2 145.3, wind columns (6) 1 279.6 | end rafters 2 196.3, posts (10) 2 028.4, end-wall X RD20 (4) 82.1 |
| Cap plates PL10x190 | 2.14 m (6) | 3.56 m (10), about +21 kg |
| Flange braces L50x5 | 24.62 m (48) | 22.53 m (44), about −8 kg |
| Gable girts | 252.24 m Z200x65x20x2.0 | unchanged |
| **Net** | | **about −296 kg** |
| End rafter | — | 300 web × 6, flanges 200×10 (`end_rafter` None = the main rafter's section) |
| Posts | wind columns 300 web × 6, flanges 150×8 | the same section (placeholder), 5 per wall including the corners, 5 678 / 6 268 / 6 868 mm long |
| End rafter ratio | — | 0.068 |
| Post ratio (worst) | wind columns as before | 0.227 (outward C&C + frame P) |
| End-wall brace rod ratio | — | 0.127 |
| Wind-column / post slot | 76–136 mm, beyond the AISC long slot | **none needed** |
| Members | 432 | 420 |

- The sections are **placeholders, not designed**: at ratios of 0.07–0.23 sizing them would save more. Not run.
- No slot is needed because the posts carry the end rafter, so the rafter and post tops move together and standard
  holes work.
- Not checked by the engine:
  - the post-top connection: it reads NOT EVALUATED, "not wired in 5d";
  - the end-bay eave transfer: dropped without warning (note 4).
- Unchanged by (c): frames 2/4 still fail the eave transfer (1.068 / 1.009), because item 13 is independent of the end
  walls; the main frames' worst ratio is 0.8959; purlins / eave struts 0.727.
- A post-and-beam end wall cannot be extended later without replacing it. This is why the user's "expandable" input
  exists.

## Recommendation (Claude; engineering judgement from GCC / Egypt PEB practice, not verified)
- **Item 13 (a):** starting the roof bracing at the eave strut line is the usual PEB layout, and it costs 7.5 kg.
  Option (b) adds about 119 kg of nearly flat rods that are hard to tension and sag.
- **Item 14:** post-and-beam where an end wall will not be extended. It is the common choice: lighter, and the slot
  problem disappears. Use the rigid frame with the slider only on expandable ends.
- The user's decisions above follow this.

## Notes for the implementation and for review (found 2026-11-26, NOT fixed)
1. **Slot-hint bug, `engine/connections/eave_transfer.py:421`** (at `aad723da`). The item 14 note says a sliding bracket
   needs slots "each about ceil(L/2)" (68 / 39 mm). That is wrong: two slots of L/2 give a travel of L − 2·d0 only (at
   the quarter columns 42 mm against the 59 mm needed). The correct length of each slot is
   d0 + (δ_down + δ_up + tolerance) / 2: 48 mm at the quarter columns and 77 mm at the ridge, with M16. Also, AISC J3.2
   (from memory, VERIFIED False) allows a long slot in only one part at each contact surface, so the bracket must be a
   three-plate slider.
2. **The 100 mm rod-entry assumption.** Options 13(a) and (b) above put the rod's lower end into the haunch web 100 mm
   past the column's inner face. That is Claude's choice, not a design value. The passes (building 1: 0.984 / 0.996;
   apex: 0.961 / 0.974) rest on it, because the top flange is about 0.94 from the frame moment alone. Item 13(a) must
   fix the real detail: the rod into the column top, which bypasses the rafter, needs a column-host path in 5d; a rod in
   the haunch web needs a set, checked distance.
3. **Phase 4 crash: Lc/r = 0.** The apex fixture + 13(b) eave-panel braces → `sizing.evaluate` →
   `frame_checks.check_frame_line` → bimsteelauto DG 25 `compression` → pyaisc360 `GeometryError: slenderness ratio
   Lc/r must be positive, got 0.0; a fully braced member has no flexural buckling limit state`. It is an exception; it
   **must read NOT EVALUATED** (or the limit state must be handled for a fully braced member), never crash.
   - Plain building 1 + 13(b) and apex + 13(a) do not crash.
   - The analysis and the connections had run; the eave / brace-end values in the apex (b) column come from a rerun
     that skipped only the Phase 4 check.
4. **End-rafter eave nodes are dropped without warning.** With `end_first` / `end_last` = "rafter", the end-bay roof-brace
   nodes on the end rafter are not listed at all in 5d: `building_eave_transfer` keeps role "rafter" hosts only. A missing
   check that leaves no NOT EVALUATED row breaks the working agreement. The post tops read NOT EVALUATED ("an end-rafter
   wall: not wired in 5d"). Both must be wired for item 14 "expandable = NO" (user decision above).
5. **"Worst brace end 0.879 → 0.957 with the apex haunch" was Claude's comparison error, not an engine result.** The
   0.879 was the worst ROOF-brace end on building 1; the 0.957 was the worst brace end OVERALL on the apex fixture.
   These are different joints and different checks. Like for like, the apex haunch LOWERS both:
   - roof-brace end (rafter F2-RA at P310-a, member net section at the hole |P|/An + |M| c/In): 0.879 → 0.855;
   - overall (a wall-brace end on column F2-CA, `P313-b` / `P319-b`): 0.976 → 0.957. The 0.976 agrees with HANDOVER
     open item 7 ("brace ends worst 0.9732 → 0.976").

   Still relevant for item 13(a): moving the rod hole next to the knee raises the roof-brace end to 0.922 (building 1) /
   0.901 (apex), because the hole sits in the haunch where the moment is high. It passes, but it belongs in the
   item 13(a) detail check.
6. Machine note: a full option run takes 3–6 min on the laptop with memory free (other applications closed), and 25–80
   min when memory is short (8 GB PC, about 0.9 GB free).
