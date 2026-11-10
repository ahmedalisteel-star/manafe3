# Files Manafe3 changed in DetailCraft

Manafe3 is based on DetailCraft by The Data Design Group, Inc. (Apache-2.0, tag `detailcraft-v0.8.1`). As section 4(b)
of the Apache License asks, this list names every upstream file Manafe3 changed and why. Files Manafe3 added are not
listed here: they are `engine/`, `manafe3.py`, `tools/manafe3-*`, `app/manafe3/`, `tests/manafe3/`, the `*.ps1`
scripts, `pyproject.toml`, `uv.lock`, `.env.local.example`, `tests/bin/test-manafe3-*.mjs` and the Manafe3 docs (CLAUDE.md, HANDOVER.md, README.md, this file).

| File(s) | Change | Why |
|---|---|---|
| `app/lang/*.json`, `devshell/site/assets/lang/shell/*.json` | "DetailCraft"/"CadCraft" → "Manafe3" ("CadCraft Studio" → "Manafe3 Desktop") | TRADEMARKS.md: a fork uses its own name. Done by `tools/manafe3-rebrand.mjs` |
| `app/help/**` (`.md` and compiled `help*.js`), `devshell/site/assets/help/**/*.md` | same renaming | same |
| `devshell/index.html` | same renaming; app-bar logo → the Manafe3 placeholder; "About" link to getcadcraft.com hidden | same |
| `devshell/render.php` | app-bar logo, "About" link, generator meta | same (keeps the PHP-rendered page equal to `index.html`) |
| `devshell/app.json` | name, role, tagline, short description | same |
| `devshell/site/favicon.svg`, `favicon.ico`, `favicon-32.png` | the CadCraft logo replaced by the Manafe3 logo (concept B, M-frame; drawn by `branding/build-logos.mjs`) | TRADEMARKS.md: take out the CadCraft logo |
| `app/detailcraft.js` | window title and file-type labels say Manafe3; loads the Manafe3 module `app/manafe3/peb-frame-ui.js` | renaming; Phase 0 feature |
| `app/model.js` | a member may carry `bu` (built-up segments): checked by `app/manafe3/builtup.js` instead of the profile table, kept on save/open and undo; Phase 2: a member's `gen` tag and `state.m3building` (the PEB building's inputs) are kept | Phase 1, Phase 2 |
| `app/build.js` | a built-up member becomes its plates (`app/manafe3/builtup-parts.js`); a part's own `plateWeight` wins over profile mass × length | Phase 1 built-up members |
| `app/marks.js` | a shaped plate (kind `SPL`, built-up web) is marked as it lies, its outline part of its signature; lipped C turns like a channel, a Z only about its axis | Phase 1, Phase 2 |
| `app/profiles.js` | lipped C / Z (`C200x65x20x2.0`, custom kinds CFC / CFZ), rods (`RD20`) and metric equal angles (`L50x5`) from `app/manafe3/coldformed.js`: names, outlines, exact areas, hole faces | Phase 2 secondary steel |
| `app/view3d.js` | a shaped plate (built-up web) is drawn from its true outline; a part's `look` sets its colour (built-up flanges as their member) | Phase 1 |
| `app/detailcraft.js` (Phase 1) | Properties panel: the built-up section editor / "Make built-up…" (`app/manafe3/builtup-ui.js`); "Plate list" output (`app/manafe3/output-ui.js`) | Phase 1 |
| `app/detailcraft.js` (Phase 2, 3) | the PEB menu: "Building…" (`app/manafe3/peb-building-ui.js`), "Loads…" (`loads-ui.js`), "Analysis…" (`frame-analysis-ui.js`), chained after the toolbar is built | Phase 2, Phase 3 |
| `app/nc1.js` | a shaped plate (built-up web) is written as a sheet (code B) with its outline as the AK contour | Phase 1 |
| `app/ifc.js` | a built-up web as IfcPlate with an IfcArbitraryClosedProfileDef; each built-up segment's assembly carries a `Manafe3_BuiltUp` property set (the member as JSON, mm); property-set name may vary | Phase 1 |
| `app/ifc-import.js` | assemblies with `Manafe3_BuiltUp` come back as one built-up member each; their plates are not imported again | Phase 1 |
| `app/drawings.js` | assembly sheets of built-up members are left out and listed (`builtUpLeftOut`) until Phase 6; `app/detailcraft.js` says so in the status bar | Phase 1 (made safe) |
| `app/nc1.js` (Phase 2) | lipped C as code C, Z as SO (best effort), web/flange contours and holes; rods refused (cut and threaded) | Phase 2 |
| `app/ifc.js`, `app/ifc-import.js` (Phase 2) | lipped C as IfcCShapeProfileDef, Z as an outline, rods as circles; web-hole openings on C/Z; import recognises them by profile name | Phase 2 |
| `app/nest.js` | built-up webs (`BUW…`) are left out of the bar cut list (they are plates) | Phase 1 |
| `README.md` | moved to `docs/DETAILCRAFT-README.md`; a Manafe3 README took its place | the fork's own install guide |
| `app/dwg/objects-write.js` | synced byte for byte from `tests/lib/dwg/objects-write.js` (R2004+ class header: version fields as BL) | upstream v0.8.1 shipped the two out of step and its own test `writer-sync --check` failed |
| `tests/bin/test-detailcraft.mjs` | five error-message patterns say Manafe3 | the messages were renamed |
| `.github/workflows/test.yml` | removed | user decision 2026-11-05: no GitHub Actions minutes on the private repo; tests run on both PCs via start-work/end-work |
| `NOTICE`, `.gitignore` | Manafe3 notice line; per-machine and private files kept out of git | licence; two-PC workflow |
| `app/build.js`, `app/detailcraft.js`, `app/clash.js` (field fixes 2, 15) | a member with a concrete material (`app/manafe3/materials.js`) weighs 0 kg as steel, carries its concrete volume and a warning; the status bar and model summary show concrete m³ separately; `clash.js` leaves such parts out of the steel clash check | R1 field fixes: concrete never weighed at 7850 kg/m³ |
| `app/detailcraft.js` (field fix 3) | on the model's 'load' event (and a new Model): selection reset, the Name field rewritten even when focused, every Manafe3 panel told (`app/manafe3/panels.js`) | R1 field fixes: panels showed the previous model |
| `app/transform.js` (field fix 4) | a mirror turns a lipped C (CFC) over like a channel | R1 field fixes: a mirrored eave strut / jamb faced the wrong way |
| `app/model.js`, `app/detailcraft.js` (field fix 8) | `state.m3buildings` (several PEB buildings) kept on save / open; the Building form gets the selection to open on the selected member's building | R1 field fixes: several buildings per model |
| `app/build.js`, `app/drawings.js` (field fix 10) | a base plate on a built-up column is built against its base section (`builtUpEndSection`), welded to the bottom segment's web; the anchor bolt sheet finds a built-up column through its plate | R1 field fixes: base plates and anchor bolt plan for PEB columns |
| `app/clash.js`, `app/detailcraft.js`, `app/model.js` (field fix 16) | plates of one built-up segment are not checked against each other; the Clashes panel groups by type and can hide generated connection points (`app/manafe3/clash-groups.js`); a generated member keeps its role (`m3role`) | R1 field fixes: hundreds of clashes at points Phase 5 will detail |
| `app/view3d.js`, `app/detailcraft.js`, `app/workspace-detailcraft.js` (field fix 17) | the Elevation view works on x grid lines too (clipping, camera, picking, dragging by the grid's axis); the picker and the view tabs list both axes (`app/manafe3/views.js`) | R1 field fixes: elevations on lettered grids running along x |
| `app/model.js`, `app/detailcraft.js` (field fixes 23, 26, 27) | `Model.replace(label, text)`: a new model as one undoable step; Manafe3's assistant tools registered on `window.detailcraftControl` (`app/manafe3/agent-tools.js`); `exportSheets` (chosen sheets as one PDF or a DXF zip) | R1 field fixes: the assistant side panel drives Manafe3 |
| `app/clash.js`, `app/build.js`, `app/model.js`, `app/detailcraft.js` (field fixes 11-13) | a shaped plate (tapered web, cut flange) is clash-checked on its true strip at each station, not its bounding box; the crane warning in build problems; a building's crane inputs kept on save / open; PEB > "Crane runway..." mounted (`app/manafe3/crane.js`, `crane-ui.js`) | R1 field fixes: crane runway geometry; false clashes at tapered webs |
| `app/rebar.js`, `app/model.js`, `app/detailcraft.js` (field fix 14) | bar names T / Y / Ø / H for the BS 4449 bars; the job's units kept in the model (`m3units`, `app/manafe3/units.js`); labels and the bending schedule follow the job's metric bar mark; PEB > "Job units..." mounted | R1 field fixes: metric rebar and concrete grades |
| `app/drawings.js`, `app/detailcraft.js`, `app/model.js` (field fixes 18, 19, 23, 24) | optional drawing settings (`opts.m3`): text / dimension text / line scales, marks hidden on GA plans, paper and scale per sheet (GA default A1), drawing number, a title block with client / project / job / status / revision; the Drawings dialog's settings and tick-box export panels (`app/manafe3/drawings-ui.js`); issue note from the status | R1 field fixes: drawings the customer can read |
| `app/view3d.js`, `app/model.js`, `app/detailcraft.js` (Phase 4 step 9) | `view.setColors(map)`: members drawn in a colour by member id (Design… utilisation colours; each colour a material key so selection restores it); the project's design settings kept in the model (`m3design`); PEB > "Design..." mounted (`app/manafe3/design.js`, `design-ui.js`) with select and colour hooks | Phase 4: member design in the browser |
