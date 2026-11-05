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
| `README.md` | moved to `docs/DETAILCRAFT-README.md`; a Manafe3 README took its place | the fork's own install guide |
| `app/dwg/objects-write.js` | synced byte for byte from `tests/lib/dwg/objects-write.js` (R2004+ class header: version fields as BL) | upstream v0.8.1 shipped the two out of step and its own test `writer-sync --check` failed |
| `tests/bin/test-detailcraft.mjs` | five error-message patterns say Manafe3 | the messages were renamed |
| `.github/workflows/test.yml` | removed | user decision 2026-11-05: no GitHub Actions minutes on the private repo; tests run on both PCs via start-work/end-work |
| `NOTICE`, `.gitignore` | Manafe3 notice line; per-machine and private files kept out of git | licence; two-PC workflow |
