# HANDOVER — Manafe3 (منافع)

Read this and `CLAUDE.md` first, on either PC. Then `.\start-work.ps1`.

## Where we are

**Phase 0 done (2026-11-05, ENG04-PC):** the DetailCraft fork runs as Manafe3, the Python engine answers, the
"PEB frame…" button puts a portal frame on every grid line, and both PCs can continue from git.

## Next task

**Phase 1 — tapered built-up member type** (web taper, flange plates, 3D, BOM, NC per plate). Start by reading
`app/profiles.js`, `app/shapes/sections.js`, `app/build.js`, `app/nc1.js` and `app/marks.js` (how a member becomes
parts, marks and NC), and `bimsteelauto/sections.py` (welded tapered I-sections, `parse_mark`). Write the plan into this
file before coding. Two open decisions to settle first are in "Open items" below.

## How to run

```powershell
.\start-work.ps1                    # git pull, uv sync, tests, prints this "Next task"
python manafe3.py                   # engine http://127.0.0.1:8765 + web app http://localhost:8000 (opens it)
python manafe3.py --check           # start, check /health and the page, stop
.\end-work.ps1 -Message "..."       # tests, "Last session" below, commit, push (refuses when a test fails)
```
(If scripts are blocked: `powershell -ExecutionPolicy Bypass -File .\start-work.ps1`.)

In the app: **Place › PEB frame…** → span, eave height, roof slope (rise/run), bay spacing, bays → **Add frame**.

## Architecture (decided)

```
browser (JS, port 8000)                                      engine (Python, port 8765)
DetailCraft fork: app/ + devshell/serve.mjs   --fetch-->     FastAPI engine/api.py
  app/manafe3/peb-frame-ui.js  (button, form)                  GET  /health
  app/manafe3/peb-frame.js     (DOM-free mapping)              POST /peb/frame  -> engine/peb/frame.py
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
- By hand: placeholder "M3" logo (`devshell/site/favicon.*`), app-bar logo, "About" link to getcadcraft.com hidden.
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
| Our code: "All rights reserved – Ahmed Ali" until the user decides | user | prompt |
| Upstream bug fixed: `app/dwg/objects-write.js` synced from `tests/lib/dwg` (upstream's own test failed on v0.8.1) | Claude | 2026-11-04 |
| UI added from JS (`app/manafe3/`), not `ui.inc`, because no PHP on the PCs and to keep merges easy | Claude | 2026-11-05 |
| Phase 0 profiles: placeholders by span (≤15 m HEA300/IPE400, ≤24 m HEA400/IPE500, else HEA500/IPE600), `designed: false` | Claude | 2026-11-05 |

## Reusing existing work

- **BIMSteelAuto (public, MIT)** — `bimsteelauto` in `pyproject.toml` from git, pinned to a commit of branch
  `packaging` (`uv.lock`). Installs `bimsteelauto`, `bimsteelauto_connections`, and the vendored cfs modules
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
    FRONT of `sys.path` only when the setting is present, and `/health` will report which copy is in use. Long-term:
    publish the 5 changes (user decides) or make a private package — then the path setting goes away.
  - Its working agreements carry over (CLAUDE.md): VERIFIED flags, negative controls, no circular verification, never
    invent a value, NOT FOR ISSUE until verified, do not modify `bimsteelauto_connections`.
- **MySteelApp Studio** (`C:\MyStructureApp`, laptop): **LAPTOP TASK** — on DESKTOP-VBCSCS0 inventory `main.py` and its
  modules (FEA, 3D model, DXF/STAAD export, MTO) and list which are worth reusing (STAAD export and MTO especially). Set
  `MYSTEELAPP_PATH` in the laptop's `.env.local`.
- **PyNite** (`PyNiteFEA`) production solver; **anastruct** independent cross-check (both installed).

## Open items

1. The 5 private-vs-public differences above: push them to the public repo, or keep a private override? (user)
2. Merge the `packaging` branch of bimsteelauto into its `main`? Manafe3 pins the commit, so it works either way. (user)
3. Laptop: choose its projects folder and fill `.env.local`; do the MySteelApp inventory.
4. Upstream checks skipped on Windows (python venv for oracle readers, poppler, unzip, DSTV runners): optional.
5. Licence of Manafe3's own code. (user)

## Roadmap (do NOT build ahead of the current phase)

- **Phase 1** tapered built-up member type (web taper, flange plates, 3D, BOM, NC per plate)
- **Phase 2** secondary steel (Z/C purlins and girts with laps, sag rods, flange braces, rod/angle bracing, end-wall frames)
- **Phase 3** loads (dead, live, ASCE 7-16 Ch. 28 wind from bimsteelauto `loads/wind.py`) + PyNite analysis with taper
  discretisation and P-Delta
- **Phase 4** member design ECP 205 / AISC 360 + cold-formed AISI S100
- **Phase 5** connections from bimsteelauto_connections (eave/apex end plates 4E/4ES/8ES, base plates + anchors, cleats,
  gussets) with HTML calc sheets
- **Phase 6** drawings: anchor bolt plan, frame elevations, built-up member shop drawings, erection drawings; NC/DSTV,
  IFC4 with Psets, MTO Excel (rename the producer strings in exports here, with their tests)
- **Phase 7** packaging: Windows installer, then optional online hosting

## Tests (Phase 0 baseline)

- Engine `uv run pytest -q`: **10 passed** (health versions; frame geometry for 2 hand-calculated cases; bad input
  refused; HTTP endpoint; CORS).
- App `npm test`: **3 of 3 test files passed** — upstream 7714 + 13 checks, Manafe3 `test-manafe3-pebframe.mjs` 18.
- Browser end-to-end (headless Edge, 2026-11-05): button present, dialog opens, 24 m × 5 bays → 24 members on 6 frame
  lines, apex 8200 mm, 23 609 kg, no console errors.

## Last session

<!-- LAST-SESSION:START (written by end-work.ps1) -->
- When: 2026-11-05 on ENG04-PC
- Did: Phase 0 — fork, rename, engine skeleton, PEB frame button, two-PC scripts, docs.
<!-- LAST-SESSION:END -->
