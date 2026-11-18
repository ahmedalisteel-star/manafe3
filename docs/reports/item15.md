# Open item 15: cold-formed purlin / eave-strut failures (report, no code)

**NOT FOR ISSUE.** The R table (I6.2.1-1) and the I6.2.3 coefficients were written down from memory and are VERIFIED False.
Building 1 is the sized fixture `fixtures/manafe3/building1-sized.json` with V 45, exposure C, bays 4 × 6000, braced bays
1 and 4, and `brace_axial` on. Report date 2026-11-18, on main at `730b475`. Engine code was not changed. The runs used a
scratch script that patched the functions in memory.

Line names: RA = roof side A. The RB lines mirror RA; this was checked on the placeholder run, and the sized run printed
RA only. Strut lines are RA1 / RA5 / RA10, the purlins at the roof-X nodes, which carry the strut force in bays 1 and 4.
The eave struts are RA0-1 … RA0-4, one simple span per bay.

## Summary of findings

1. **The sizing step does NOT see the strut axial force, either item 7's or the eave-strut force.** `size_cold_formed`
   (`engine/design/sizing.py`) calls `building_lines` + `check_line` directly. The forces `P` / `P_zones` / `P_by_combo`
   are attached only inside `cfs_checks`. Sizing therefore checks every line in bending only: it picked Z250x65x20x1.5
   with "RA1: Flexure (DSM)" at 0.8905. Item 7's "6a: sizing loop sees it" holds for the main frames only.
2. **Z250x65x20x1.5 has no axial distortional buckling value.** The finite strip finds no second minimum, so `Pcrd`
   is None. With today's code the three strut purlin lines of the sized building read **NOT EVALUATED (inf)**. Decision
   (b) as written ("min with the DSM strong-axis value") still needs Pnd, so they would stay NOT EVALUATED. The I6.2.3
   values for Z250x1.5 below are informative only: the strong-axis value uses Pnl, with the distortional mode left out.
3. **The current 0.9D+1.0W pairing is not per direction.** Purlin uplift comes from **C&C** (Fig. 30.3-2A, an envelope
   over all wind directions). The strut force is the **governing (minimum-scaled) 15.027 kN** at the combination's wind
   factor. Item 6/7's rule pairs the Case B share (13.448) with Case B wind and the minimum (15.027) with dead load only.
   Both versions are shown in section 3.
4. With (a) + (b) and the current pairing, the sized building still fails: RA1 1.335, RA5 1.214, eave struts bays 1/4
   1.058. With the same-direction pairing, every line passes (max 0.893, which is C&C alone on RA1/RA2). **The pairing
   rule decides the result more than x does.**

## 1. Item 15 tables, sized profiles vs placeholders (current pairing)

U by method. "DSM" is today's φPn: bare section, Pcre at the 6 m bay. "I6.2.3" is the weak-axis value, taking the
minimum with the DSM strong-axis value. Every governing row is 0.9D+1.0W except where a note says otherwise.

**Sized** (purlin Z250x65x20x1.5, eave strut C200x65x20x1.8):

| Line | Strict, DSM | R-factor, DSM | Strict, I6.2.3 x 0.33 | R-factor, I6.2.3 x 0.33 | R-factor, I6.2.3 x 0.50 |
|---|---|---|---|---|---|
| RA1 / RB1 (strut) | NOT EVALUATED (Pcrd) | NOT EVALUATED | 2.311* | **1.335*** | 1.278* |
| RA5 / RB5 (strut) | NOT EVALUATED | NOT EVALUATED | 2.151* | **1.214*** | 1.157* |
| RA10 / RB10 (strut) | NOT EVALUATED | NOT EVALUATED | 1.559* | 0.938* | 0.881* |
| RA2 / RB2 | 1.821 | 0.893 | 1.821 | 0.893 | 0.893 |
| RA3–4, RA6–9 (and RB) | 1.669 | 0.778 | 1.669 | 0.778 | 0.778 |
| Eave struts, bays 1 / 4 (strut) | 3.592 | 1.755 | 2.894 | **1.058** | 1.015 |
| Eave struts, bays 2 / 3 | 2.060 | 0.603 (gravity) | 2.060 | 0.602 | 0.602 |

\* Informative only: Pcrd of Z250x1.5 is not identified (finding 2).

**Placeholders** (Z200x65x20x2.0, C200x65x20x2.0), for comparison with the first report:

| Line | Strict, DSM | R-factor, DSM | Strict, I6.2.3 x 0.33 | R-factor, I6.2.3 x 0.33 | R-factor, I6.2.3 x 0.50 |
|---|---|---|---|---|---|
| RA1 / RB1 | 3.264 | 2.073 | 2.171 | 0.980 | 0.942 |
| RA5 / RB5 | 3.105 | 1.981 | 2.012 | 0.888 | 0.850 |
| RA10 / RB10 | 2.515 | 1.771 | 1.422 | 0.678 | 0.640 |
| RA2 / RB2 | 1.783 | 0.667 | 1.783 | 0.667 | 0.667 |
| RA3–4, RA6–9 | 1.633 | 0.581 | 1.633 | 0.581 | 0.581 |
| Eave struts, bays 1 / 4 | 3.182 | 1.544 | 2.542 | 0.904 | 0.866 |
| Eave struts, bays 2 / 3 | 1.817 | 0.528 | 1.817 | 0.509 | 0.508 |

**Sizing re-run today:** `size_cold_formed` (R-factor) gives purlin Z200x2.0 → Z250x65x20x1.5 at 0.8905 (RA1,
flexure), eave strut → C200x65x20x1.8 at 0.7027 (RA0-1, flexure), girt → Z225x65x20x1.5 at 0.8484. None of these
governing rows includes an axial term (finding 1).

## 2. Which Table I6.2.1-1 row gave R = 0.70

- **Purlins: the continuous-span row, Z section: R = 0.70.** This row has no depth band in our transcription.
  `r_factor()` calls a line continuous when it has more than one span AND laps. The purlins are **modelled as lapped
  continuous lines** over 4 spans (supports 0 / 6000 / 12000 / 18000 / 24000). The laps are at 5400–6600, 11400–12600
  and 17400–18600, so 600 mm each side of every interior support, against the limit 1.5 d = 300 mm for Z200 and
  375 mm for Z250. Lap stiffness is 2 EI and lap strength 2 × flexure and shear. The condition passes.
- **Eave struts: the simple-span row, C section, 6.5 < d ≤ 8.5 in: R = 0.65** (C200 = 7.87 in). They are butt-jointed,
  one simple span per bay.
- Your memory (simple-span Z, 6.5 < d ≤ 8.5 in, = 0.65) matches our `R_TABLE["simple"]`. That row does not apply to the
  purlins because they are modelled continuous. Our full transcription, also unverified: simple span C/Z 0.70 for
  d ≤ 6.5 in, 0.65 for ≤ 8.5 in, then C 0.40 / Z 0.50 for ≤ 11.5 in; continuous span C 0.60, Z 0.70.
- For information only, nothing changed: if the purlins were taken as simple span, Z200 (7.87 in) would take 0.65, with
  RA2 0.667 → 0.718. Z250 (9.84 in) would take 0.50, with RA2 0.893 → 1.250 (φMn = 0.9 × 0.50 × 11.094 = 4.992 kN·m,
  still above the brace-point 3.427).

## 3. Pairing in 0.9D+1.0W: current vs same direction

**Current pairing (code as it stands):** each roof combination's line load uses the C&C pressures (Win / Wout, zone by
position, an envelope over all directions). The strut force is the **governing** value 15.027 kN × max(Win, Wout
factor), so it is 1.0 in 0.9D+1.0W. Transverse-type uplift is therefore paired with the longitudinal strut force, and
the §28.3.4 minimum-scaled force is paired with a wind uplift. Item 6's rule never pairs the minimum with a wind uplift.

**Same-direction version (item 6 / 7 rule applied to the purlins):** the governing U is the largest of three checks:
1. C&C alone (every roof combination, no strut force).
2. **Case B MWFRS roof uplift + the Case B strut share** 13.448 kN = 15.027 / 1.11743 at the combination's wind factor.
   Case B roof pressure has no inward value, so the inward-wind combinations take gravity + P only (conservative).
3. **The minimum 15.027 kN with dead load only:** 0.9D + 1.0 BRmin and 1.2D + 1.0 BRmin.

Case B roof pressure: **Claude's zoning, to confirm.** 2E within 2a = 4800 mm of either end and zone 2 elsewhere, on
both slopes, with +GCpi. This is conservative: bimsteelauto's frame loading puts 2 on side A and 3 on side B.

Sized profiles with I6.2.3 at x = 0.33:

| Line | Method | Current U | Same dir: C&C alone | Same dir: Case B + P | Same dir: min + D | Same-dir U |
|---|---|---|---|---|---|---|
| RA1 / RB1 | R-factor | 1.335* | 0.893 | 0.881 | 0.438 | **0.893*** |
| RA5 / RB5 | R-factor | 1.214* | 0.778 | 0.881 | 0.438 | **0.881*** |
| RA10 / RB10 | R-factor | 0.938* | 0.515 | 0.701 | 0.429 | **0.701*** |
| Eave struts, bays 1 / 4 | R-factor | 1.058 | 0.706 | 0.672 | 0.351 | **0.706** |
| RA1 / RB1 | strict | 2.311* | 1.821 | 1.522 | 0.438 | 1.821 |
| RA5 / RB5 | strict | 2.151* | 1.669 | 1.522 | 0.438 | 1.669 |
| RA10 / RB10 | strict | 1.559* | 1.106 | 1.125 | 0.429 | 1.125 |
| Eave struts, bays 1 / 4 | strict | 2.894 | 2.414 | 1.651 | 0.351 | 2.414 |

At x = 0.50 (R-factor, same direction): RA1 0.893, RA5 0.830, RA10 0.650, eave 0.706.

With today's DSM φPn (R-factor): sized eave struts bays 1/4 1.755 → 1.296 (Case B + P), and the purlin strut lines
stay NOT EVALUATED. Placeholders: RA1 / RA5 2.073 / 1.981 → 1.616, RA10 1.771 → 1.480, eave 1.544 → 1.151.

\* Z250x1.5: informative (finding 2).

## 4. Longhand (independent arithmetic of the engine's terms)

**Case B pressures:** qh = 0.9484 kPa, GCpi +0.18. For 2E: 0.9484 × (−1.07 − 0.18) = −1.1855 kPa. For 2:
0.9484 × (−0.69 − 0.18) = −0.8251 kPa. Both match bimsteelauto.

**Strut forces:** 15.027 = 1.11743 × 13.448 (item 6/7 split; per slope = per braced bay / 2).

**R-factor capacity** φMn = 0.9 R Mnlo, with Mnlo from the DSM local curve at Mne = My
(Mnl = (1 − 0.15 (1/λ)^0.8)(1/λ)^0.8 My for λ > 0.776):
- Z250x1.5: My 15.477, Mcrl 9.336 → λ 1.2876, (1/λ)^0.8 = 0.8169, Mnl = 0.8169 × 0.8775 × 15.477 = 11.094 kN·m, so
  φMn = 0.9 × 0.70 × 11.094 = **6.989** (engine 6.989).
- C200x1.8: My 13.549, Mcrl 17.665 → λ 0.8758, (1/λ)^0.8 = 1.1119, Mnl = 0.8332 × 1.1119 × 13.549 = 12.552, so
  φMn = 0.9 × 0.65 × 12.552 = **7.343** (engine 7.343).
- Z200x2.0: My 14.946, Mcrl 24.118 → λ 0.7872, (1/λ)^0.8 = 1.2110, Mnl = 0.8184 × 1.2110 × 14.946 = 14.812, so
  φMn = 0.9 × 0.70 × 14.812 = **9.331** (engine 9.331).

**I6.2.3 (from memory, VERIFIED False):** Pn = C1 C2 C3 A E / 29500 (in, kips), with C1 = 0.79x + 0.54,
C2 = 1.17t + 0.93, C3 = 2.5b − 1.63d + 22.8, and φc 0.85:

| Profile | A in² | C1 (x 0.33 / 0.50) | C2 | C3 | Pn kN (x 0.33) | φPn kN (x 0.33 / 0.50) | DSM strong axis Pn kN | Bare DSM φPn today |
|---|---|---|---|---|---|---|---|---|
| Z200x65x20x2.0 | 1.1059 | 0.8007 / 0.935 | 1.0221 | 16.363 | 65.88 | **55.99 / 65.39** | 106.15 (Pnl) | 11.04 |
| Z250x65x20x1.5 | 0.9534 | 0.8007 / 0.935 | 0.9991 | 13.154 | 44.63 | **37.93 / 44.30** | 69.79 (Pnl; Pnd not identified) | 0 (NOT EVALUATED) |
| C200x65x20x1.8 | 0.9990 | 0.8007 / 0.935 | 1.0129 | 16.363 | 58.97 | **50.13 / 58.53** | 89.08 (Pnl) | 15.07 |

The weak axis governs in every case. Checkable limits, all met: t ≤ 0.125 in; 6 ≤ d ≤ 12 in; 70 ≤ d/t ≤ 170
(Z250x1.5: 166.7, close to the limit); 2.8 ≤ d/b < 5; 16 ≤ flange flat w/t < 50; span ≤ 33 ft; Fy ≥ 33 ksi.

**Interaction (H1.2 as coded: P/φPn + B1 M/φMn, B1 = 1/(1 − P/Pex), Pex = π² E Ix / L², L = 6000):**
- Sized RA1, R-factor, x 0.33, current pairing: 15.027/37.93 = 0.3962; Pex 308.2, so B1 1.0513; 6.242/6.989 = 0.8931;
  U = 0.3962 + 1.0513 × 0.8931 = **1.335** (engine 1.3349).
- Sized RA5, R-factor, x 0.33, Case B + P: 13.448/37.93 = 0.3546; B1 = 1/(1 − 13.448/308.2) = 1.0456;
  M 3.52/6.989 = 0.5036; U = 0.3546 + 1.0456 × 0.5036 = **0.881** (engine 0.8812).
- Sized eave RA0-1, R-factor, x 0.33, current: 15.027/50.13 = 0.2998; Pex 215.9, so B1 1.0748; 5.182/7.343 = 0.7057;
  U = 0.2998 + 1.0748 × 0.7057 = **1.058** (engine 1.0582).
- Placeholder RA1, R-factor, DSM today: 15.027/11.04 = 1.361 + 1.067 × 0.667 = **2.073** (engine 2.0732).

**What this record cannot close:**
- The moments come from the engine's beam solver, which `test_cfs` tests against closed forms; they were not redone
  here.
- R, the I6.2.3 coefficients and the limits are from memory.
- The Case B purlin zoning is Claude's reading.
- The I6.2.3 conditions the model cannot know: fasteners ≤ 12 in on centres, rotational lateral stiffness
  ≥ 0.0015 k/in/in, and both flanges restrained at the supports.
- Z250x1.5 Pcrd.

**Negative control in the runs:** the lines with no strut force (RA2, RA3, eave bays 2/3) give the same U in every
pairing and every axial method. The axial change touches only the strut lines.

## 5. Questions before code

1. **Pairing:** adopt the same-direction rule (C&C alone; Case B uplift + Case B share; minimum + dead load only) for
   the purlin and eave struts, as in item 6/7? Claude recommends yes.
2. **Case B purlin zoning:** 2E within 2a of either end and 2 elsewhere, both slopes (conservative), or bimsteelauto's
   2 / 3 by side?
3. **Pcrd not identified (Z250x1.5):** keep NOT EVALUATED, which is the rule, so sizing moves to a profile where it
   evaluates. The alternatives are a supplier Pcrd, or I6.2.3 alone with the strong axis checked by Pnl only. Claude
   recommends keeping NOT EVALUATED.
4. **Sizing sees the strut force:** extend decision (a)'s "same method" so that `size_cold_formed` uses the same lines
   and forces as `cfs_checks`, P included. Claude recommends yes. Expect the purlin size to change.

---
Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
