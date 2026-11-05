# HANDOVER — Manafe3 (منافع)

Read this and `CLAUDE.md` first, on either PC. Then `.\start-work.ps1`.

## Where we are

**Phase 0 done (2026-11-05):** the DetailCraft fork runs as Manafe3, the Python engine answers, two PCs work from git.
**Phase 1 done (2026-11-05, ENG04-PC):** welded built-up members — tapered or constant, in segments joined at splice
points — in the model, 3D, Properties panel, parts/marks/BOM, plate cut list, DSTV NC per plate, IFC4 out and back in,
engine section properties along the length, and "PEB frame…" now builds built-up frames with a haunch at the knee.

## Next task

**Phase 2 — secondary steel** (Z/C purlins and girts with laps, sag rods, flange braces, rod/angle bracing, end-wall
frames). Start by reading `bimsteelauto/design/purlins.py`, `aisi_s100` / `direct_strength` (cold-formed) and
`bimsteelauto/loads/cladding.py`; how DetailCraft holds C/Z profiles (`app/shapes/sections.js`, `profiles.js`,
`CUSTOM_KINDS`) and the brace gusset (`app/connections.js`). **Write the plan here and show it to the user before
coding**; ask about every engineering decision (lap lengths, purlin spacing rules, sag-rod rows, flange-brace spacing,
bracing type). Same rules: tests per step with hand-checked values, commit on `main` after each green step.

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

In the app: **Place › PEB frame…** → span, eave height, roof slope (rise/run), bay spacing, bays, section (built-up,
default) and the built-up sizes (filled from the span rules) → **Add frame**. Click a member: its segments are edited in
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
- **Phase 2** secondary steel (Z/C purlins and girts with laps, sag rods, flange braces, rod/angle bracing, end-wall frames)
- **Phase 3** loads (dead, live, ASCE 7-16 Ch. 28 wind from bimsteelauto `loads/wind.py`) + PyNite analysis with taper
  discretisation and P-Delta
- **Phase 4** member design ECP 205 / AISC 360 + cold-formed AISI S100
- **Phase 5** connections from bimsteelauto_connections (eave/apex end plates 4E/4ES/8ES, base plates + anchors, cleats,
  gussets) with HTML calc sheets
- **Phase 6** drawings: anchor bolt plan, frame elevations, built-up member shop drawings, erection drawings; NC/DSTV,
  IFC4 with Psets, MTO Excel (rename the producer strings in exports here, with their tests)
- **Phase 7** packaging: Windows installer, then optional online hosting

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
- When: 2026-11-05 11:19 on ENG04-PC
- Did: Phase 1 done: tapered built-up members (model, 3D, editor, parts, plate list, NC, IFC, engine section properties, built-up PEB frames)
- Tests: engine 39 passed, 1 warning in 3.19s | app 8 of 8 test files passed
- Next: Phase 2 secondary steel: plan first, show the user, then build
<!-- LAST-SESSION:END -->
