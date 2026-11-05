# CLAUDE.md — rules for Claude Code on Manafe3 (both PCs)

**Read `HANDOVER.md` first, every session, on either PC.** It has the architecture, the decisions, what is done and
the next task. Then run `.\start-work.ps1` (or tell the user the exact command) and report the test numbers before
changing anything.

## The two PCs
- Office **ENG04-PC** (user `USR`, 16 GB) and laptop **DESKTOP-VBCSCS0** (user `Windows 10` — the name has a SPACE).
- **No hard-coded paths or user names** in code, tests or scripts. Everything is relative to the repo root; per-machine
  folders live in the git-ignored `.env.local` (`engine/settings.py` reads it; keys in `.env.local.example`).
- **Quote every path.** Use `-LiteralPath` in PowerShell. Test paths with spaces in mind.
- Work flows through git: `start-work.ps1` (pull, `uv sync`, tests, current task) and `end-work.ps1 -Message "..."`
  (tests, HANDOVER "Last session", commit, push; it refuses to push when a test fails).

## The user
- Give **PowerShell** commands only (Windows PowerShell 5.1: no `&&`, no `cmd` syntax). Keep answers short; lead with
  the result. Write files yourself; do not hand over code to paste.
- **Ask before:** installing anything system-wide, any paid service, pushing anything public, and any decision that is
  the user's (licence, public/private, naming).

## Architecture (decided — do not change)
- Front end = JavaScript in the browser, forked from DetailCraft v0.8.1 (`app/`, `devshell/`). Engine = Python FastAPI
  at http://127.0.0.1:8765 (`engine/`). `python manafe3.py` starts both and opens http://localhost:8000.
- All PEB engineering lives in the engine. Units inside it: **SI — mm, kN, MPa**; imperial only at a library boundary.
- Model axes: X along the building (frame lines 1, 2, …), Y across the span (column lines A, B), Z up, mm.
  BIMSteelAuto uses X across the frame, Y along: convert in exactly ONE function, never ad hoc.
- BIMSteelAuto is a **dependency** (git, pinned in `pyproject.toml`/`uv.lock`) — never copy-paste its code.
  PyNite = production solver; anastruct = independent cross-check.

## Licence and names (must follow)
- DetailCraft code stays Apache-2.0: keep `LICENSE`, `NOTICE`; every upstream file you change gets a row in
  `MANAFE3-CHANGES.md`, and a `Manafe3 (changed file …)` comment where you change code.
- Visible names are **Manafe3** (TRADEMARKS.md). After merging an upstream release run
  `node tools/manafe3-rebrand.mjs`, then `npm test`. Never show "DetailCraft"/"CadCraft" as our product name.
- No code from proprietary software or GPL/LGPL/MPL projects (CONTRIBUTING.md "Clean room"). Permissive deps only.
- Our own new code: header `Copyright (c) 2026 Ahmed Ali. All rights reserved.`

## Working agreements (from BIMSteelAuto — not optional)
- **VERIFIED flags:** a number is verified only by an independent source (another tool, another implementation or
  longhand arithmetic). A formula taken from a reference is not verified by that reference. No circular verification.
- Find a **negative control**; state what a record cannot close. **Count is not correctness:** check positions,
  lengths, weights against something already known.
- **Never invent a value.** Blanks over assumptions; accepted assumptions are listed and printed.
- An unevaluated check never reads as a pass (ratio = inf with a note).
- Outputs carry a **NOT FOR ISSUE** banner until their checks are verified. Phase 0 profiles are placeholders
  (`designed: false`).
- Do not modify `bimsteelauto_connections` (v0.7.0, all flags closed).

## Code and tests
- Small steps; tests after each step; commit after each green step.
- Engine tests: `uv run pytest -q` (`engine/tests/`). App tests: `npm test` (upstream suite + `tests/bin/test-manafe3-*.mjs`).
- Our browser code goes in `app/manafe3/` (DOM-free logic in its own module so Node can test it), hooked into
  upstream files with as few lines as possible, so upstream merges stay easy.
- No PHP on the PCs: `devshell/index.html` is the pre-rendered page. Prefer adding UI from JS (`app/manafe3/*-ui.js`)
  over editing `app/ui.inc`; if you must edit `ui.inc`, make the same change in `devshell/index.html`.
- Windows PowerShell 5.1 traps: native args with embedded quotes break (`git commit -F file`, not `-m "…"`);
  `Set-Content -Encoding utf8` writes a BOM that breaks TOML/JSON (use `[IO.File]::WriteAllText` with UTF8 no BOM).
- Never commit client data: drawings, real-project IFC, vendor PDFs go to `MANAFE3_PROJECTS_DIR` (see `.env.local`).
