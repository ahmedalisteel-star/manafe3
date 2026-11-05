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
