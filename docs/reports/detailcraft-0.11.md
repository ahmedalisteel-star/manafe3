# DetailCraft 0.11.0 vs 0.10.0 — what touches Manafe3 (report only, 2026-11-24)

Tag `detailcraft-v0.11.0` (upstream commit d8a427e6, "CadCraft Studio 0.11.0", 23 Nov 2026), fetched into this
repository; **nothing merged**. 1 369 files changed upstream (+168 786 / −19 944), most of them help / language files
and upstream's own test tools. Method: `git diff detailcraft-v0.10.0 detailcraft-v0.11.0` per file, and a dry-run
merge `git merge-tree --write-tree main detailcraft-v0.11.0` (it writes no files and moves no branch).

## 1. Dry-run merge result

316 conflicted paths: **305 help / language files** (taken from upstream and re-branded, as in 0.10) and **11 others**:

| Path | Conflict | Expected resolution |
|---|---|---|
| `README.md` | both changed | ours (as in 0.10) |
| `android/ linux/ macos/ web/ windows/README.md` (`ios` unchanged upstream) | upstream edited files we deleted | delete again (user decision 2026-11-23) |
| `devshell/index.html` (6 hunks) | upstream's pre-rendered page changed | upstream's page + our app-bar mark / About link, as in 0.10; `render.php` (+5 −1) auto-merged, check by eye |
| `app/build.js` (3 hunks) | 0.11 PERF.36 / PERF.78: an incremental build cache (per-member and per-connection versions, kept results, `fresh` parts only re-weighed) and a `CONN_BUILDERS` table | see 2.1 |
| `app/clash.js` (1 hunk) | 0.11 caches a part's section points (`A._sec`) | our shaped-plate sampling (true strip at each station, field fixes 11-13) moves into the new point routine; the cache must not reuse a rectangle for an SPL plate |
| `app/model.js` (2 hunks) | 0.11 DC.27: ids from a random per-session tag (`history/ids.js`, `takeIdBlock`, `nextId` → `nextNumber`) | keep our `builtup.js` import; `Model.replace` stays one `change()` and must also take an id block (a replaced model is an opened file); see 2.3 |
| `app/detailcraft.js` (11 hunks, +514 −953) | 0.11 splits more of it into modules: `member-props-ui`, `many-props-ui`, `conn-props-ui`, `conn-add-ui`, `report-panel-ui`, `tool-options-ui`, `place-ui` | see 2.2 |

Auto-merged without a conflict but changed upstream where we have edits (to be checked by tests, not trusted):
`app/view3d.js` (+224 −21; our SPL geometry key, `setColors`, x-grid elevations all still present in the merged text),
`app/marks.js` (+14 −3), `app/ifc.js` (+2 −16: `S()` moved to `ifc/step.js` and re-exported — our `Manafe3_BuiltUp` set
uses it), `app/export-ui.js` (+37 −1: the Zeman entry under NC files; our `ctx.bn()` edits kept),
`app/workspace-detailcraft.js` (+18 −4), `app/ui.inc` (+1, we do not edit it), `devshell/app.json`.

Unchanged upstream (our edits carry over as they are): `profiles.js`, `nc1.js`, `ifc-import.js`, `drawings.js`,
`drawings-ui.js`, `nest.js`, `transform.js`, `rebar.js`, `footing-stair-ui.js`, `clash-ui.js`, `analysis.js`,
`analysis-ui.js`, `dwg/objects-write.js`, `tests/bin/test-detailcraft.mjs`, `NOTICE`, `.gitignore`, favicons.

## 2. How our hooks move

### 2.1 `app/build.js` — the incremental build (the biggest semantic risk)
Our hooks: built-up members skip the profile table (`if (m.bu) builtUp.push(m)`); the base plate on a built-up column
(field fix 10, `buBase`, plate attached to the bottom segment's web); `builtUpParts(m)` per built-up member; the part
weight `p.plateWeight ?? …`; concrete members weigh 0 and carry m³ (field fixes 2/15); the crane warning.
In 0.11: (a) the member loop computes a cached `base` per member version → our `m.bu` skip goes before it; (b) the
connection loop calls `CONN_BUILDERS[c.type](c, drafts, conns)` with a cache key from the members' versions → the
built-up base plate must either be a wrapper builder that sees `buBase`, or stay a special case before the table — and
**its cache key must include the built-up column's version** (`membersOf(c)` gives it only if the column is in
`cache.mver`, which our skipped built-up members are not); (c) weights are set only for `fresh` parts → our
`plateWeight` and the concrete rule go inside the same `fresh` block, and built-up parts must be marked fresh when the
member changes. Test to add after the merge: edit a built-up member's web depth → its plates' weight and its base
plate move; edit an unrelated member → the built-up parts are the same objects (the cache works).

### 2.2 `app/detailcraft.js` — more modules
Imports: our `builtup-ui.js` import stays next to upstream's new imports. Our hooks by hunk: field fix 3 (`'load'` →
selection reset, `m3ModelLoaded`) stays in `detailcraft.js`; the status-bar counts with concrete m³ and the window
title stay; field fix 17 grid picker stays; **the Properties panel's built-up editor / "Make built-up…" button moves
to `member-props-ui.js`** (where the profile field now lives: `app.f.profile`); **the model summary's concrete m³
moves to `report-panel-ui.js`**; the open-file types, `bn` (field fix 14), `clashHideGen` (field fix 16) and
`exportSheets` (field fixes 23 / 26) are context lines in the mount calls and stay. New `MANAFE3-CHANGES.md` rows:
`member-props-ui.js`, `report-panel-ui.js`.

### 2.3 Ids (0.11 DC.27)
New member ids become `m<tag × 2^21 + n>` (large numbers, a random tag per session); ids already in a file never
change. Our code takes ids only through `tx.addMember` (`peb-building.js` applyBuilding, crane, frame), so nothing of
ours writes ids by hand. Expected test churn: any app test that compares member ids by value after an Apply (to be
listed when the merge runs). Engine: unaffected (it never sees app ids).

### 2.4 `app/view3d.js` (auto-merged) — check
0.11 PERF.36 `updateParts` keeps unchanged parts' meshes after an edit. Our Design… colours are a material key per
part (`colorKey`) and `setColors` calls a full `setModel`. Risk: an edit after colouring keeps a part's old batch
(material key not in the "same part" test). Test to add: colour, edit one member, the others keep their colour and the
edited one is redrawn; two built-up webs of different taper still never share a geometry (the existing merge test).

## 3. New in 0.11 that may be useful to us

- **Weld checks** (`app/frame/frame-weld.js`, help `weld-checks.md`): the Analysis tab's design checks gain a weld group
  all round each member end — AISC 360-16 J2.4 (with the load angle), J4.2 base metal, Table J2.5 CJP; EN 1993-1-8
  4.5.3.3 / 4.7.1; elastic vector method. Upstream says some constants are not compared with a printed copy. Our
  Analysis tab skips PEB members (user 2026-11-18), so it will not run on PEB frames. **Use: cross-check only** — an
  independent implementation of J2.4 to compare, in a Node test, with one of our step 4 weld results on the same
  numbers (a verification source for a VERIFIED flag, never the production check).
- **Zeman export add-on** (`app/addons/zeman`, Apache-2.0, off by default): one folder per assembly mark with an XML and
  the DSTV files, for a Zeman assembly / welding machine. Upstream: built from one sample, I-shape main parts with plates,
  no weld information, "check the first export on the machine". Our built-up members are a web plate + flange plates
  (no I-shape main part) → probably not usable for PEB members without a mapping; worth a try on a hot-rolled
  assembly after the merge. Shows "Zeman" in the add-on list — not a trademark of ours or of upstream; fine.
- **Big-model speed**: incremental build and 3D update (PERF.36 / PERF.78: only changed parts rebuilt / redrawn,
  alike parts share one geometry), IFC geometry in a Web Worker while the page stays responsive (PERF.8,
  `ifc/mesh-stream.js`, `mesh-worker.js`), one STEP string helper (PERF.73). Building 1 (620 members) should
  re-draw faster after Building… Apply / Design… Apply; measure by hand as for 0.10.
- Also new upstream: per-session ids (2.3), `history/ifc-journal.js`, connection add / properties panels.

## 4. What this report cannot close

- Only a real merge with the full test suites shows the real conflicts in behaviour; the dry run shows text conflicts.
- No 0.11 "What's new" page in English was found in the tag (`whats-new.md` still describes 0.10); the feature list
  above is read from the code and the help pages.
- The speed gain on our models is not measured.
