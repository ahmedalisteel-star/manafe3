# Manafe3 (منافع)

A browser-based PEB / steel detailing app that runs on your own PC (localhost), with PEB design inside it.

- **Front end:** JavaScript in the browser, based on [DetailCraft](https://github.com/getcadcraft/detailcraft) by
  The Data Design Group, Inc. (Apache-2.0): 3D view, panels, drawings, NC, IFC, numbering, BOM, clash.
- **Engine:** Python (FastAPI) at http://127.0.0.1:8765: all PEB engineering. Uses
  [BIMSteelAuto](https://github.com/ahmedalisteel-star/bimsteelauto) and PyNite.
- Status: **Phase 0** (skeleton). See `HANDOVER.md`.

## Install and run on a new Windows PC (PowerShell)

Needs: Git, Python 3.12, Node.js 20.19+, uv, GitHub CLI. Install any that are missing with
`winget install Git.Git Python.Python.3.12 OpenJS.NodeJS.LTS astral-sh.uv GitHub.cli`.

```powershell
gh auth login                                   # once per PC (the repo is private)
cd D:\                                          # or any folder you like; paths with spaces are fine
gh repo clone ahmedalisteel-star/manafe3 Manafe3
cd .\Manafe3
Copy-Item .env.local.example .env.local         # then edit .env.local: this PC's folders
uv sync                                         # identical Python packages on every PC (uv.lock)
python manafe3.py                               # engine + web app, opens http://localhost:8000
```

Click **PEB frame…** in the toolbar (Place group), keep or change the numbers, **Add frame**: the frame appears in 3D.

## Every day, on either PC

```powershell
powershell -ExecutionPolicy Bypass -File .\start-work.ps1                  # pull, uv sync, tests, prints the task
python manafe3.py
powershell -ExecutionPolicy Bypass -File .\end-work.ps1 -Message "What I did"   # tests, HANDOVER, commit, push
```

## Tests

```powershell
uv run pytest -q        # engine
npm test                # the app (DetailCraft's suite + Manafe3's tests in tests/bin/test-manafe3-*.mjs)
python manafe3.py --check   # starts both servers, checks them, stops
```

## Licences

- DetailCraft code: Apache-2.0 (`LICENSE`, `NOTICE`; changed files in `MANAFE3-CHANGES.md`). Manafe3 is based on
  DetailCraft by The Data Design Group, Inc. and is not made or endorsed by it (`TRADEMARKS.md`).
- Manafe3's own code (`engine/`, `manafe3.py`, `app/manafe3/`, the `*.ps1` scripts, `tests/bin/test-manafe3-*`):
  All rights reserved – Ahmed Ali (licence to be decided). `tools/manafe3-rebrand.mjs` is Apache-2.0 like the code it edits.
- Upstream's README: `docs/DETAILCRAFT-README.md`.
