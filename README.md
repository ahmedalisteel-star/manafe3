<h1 align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="branding/concepts/bilingual-mframe-dark.svg">
    <img src="branding/concepts/bilingual-mframe-light.svg" alt="Manafe3 (منافع)" width="520">
  </picture>
</h1>

<p align="center" dir="rtl">
لَقَدْ أَرْسَلْنَا رُسُلَنَا بِالْبَيِّنَاتِ وَأَنزَلْنَا مَعَهُمُ الْكِتَابَ وَالْمِيزَانَ لِيَقُومَ النَّاسُ بِالْقِسْطِ ۖ وَأَنزَلْنَا الْحَدِيدَ فِيهِ بَأْسٌ شَدِيدٌ وَمَنَافِعُ لِلنَّاسِ وَلِيَعْلَمَ اللَّهُ مَن يَنصُرُهُ وَرُسُلَهُ بِالْغَيْبِ ۚ إِنَّ اللَّهَ قَوِيٌّ عَزِيزٌ
<br>
[سورة الحديد: 25]
</p>

## What is Manafe3

Manafe3 (منافع) is a free, browser-based app for **pre-engineered steel buildings (PEB)** that runs on your own PC
(localhost — nothing leaves your machine). You describe a building — span, bays, eave, slope, end walls, openings — and
it makes the whole steel model: tapered built-up frames, purlins and girts with their laps and holes, sag rods, bracing,
end walls, cleats. It then loads and analyses it and checks and sizes every member:

- **Model and output** (based on [DetailCraft](https://github.com/getcadcraft/detailcraft), Apache-2.0): 3D, plans and
  elevations, part marks, BOM, plate and cut lists, DSTV NC, IFC4 in / out, drawings, clash check.
- **Engine** (Python, FastAPI at http://127.0.0.1:8765): ASCE 7-16 loads (wind, Lr, C&C), second-order frame analysis
  (PyNite; AISC Direct Analysis Method), member checks to **AISC 360-16 LRFD** (tapered members by Design Guide 25),
  **ECP 205-LRFD** side by side, cold-formed purlins and girts to **AISI S100-16** (DSM, properties and buckling computed
  from the profile geometry), serviceability, and a sizing loop. Uses [BIMSteelAuto](https://github.com/ahmedalisteel-star/bimsteelauto)
  and [ecp205-lrfd](https://github.com/ahmedalisteel-star/ecp205-lrfd).
- **PEB › Design…**: check or size a building, 3D utilisation colours, a results table and printable calc sheets.

> **Not for issue.** Every design result carries a NOT FOR ISSUE banner until the items it rests on have been verified
> against the printed codes (they are listed in the app). Manafe3 does not replace a licensed engineer's own check.

## Install and run (Windows, PowerShell)

Needs Git, Python 3.12, Node.js 20.19+ and [uv](https://docs.astral.sh/uv/). Install any that are missing:
`winget install Git.Git Python.Python.3.12 OpenJS.NodeJS.LTS astral-sh.uv`. No GitHub account is needed.

```powershell
git clone https://github.com/ahmedalisteel-star/manafe3.git Manafe3
cd .\Manafe3
uv sync                                          # the exact Python packages (uv.lock)
python manafe3.py                                # engine + web app, opens http://localhost:8000
```

Then **PEB › Building…** makes a building, **PEB › Loads…** takes the site's wind, **PEB › Analysis…** and
**PEB › Design…** analyse, check and size it. On macOS / Linux the same commands work in a shell.

## Tests

```powershell
uv run pytest -q -m "not slow"   # engine, fast (uv run pytest -q: everything, several minutes)
npm test                         # the app (DetailCraft's suite + Manafe3's tests in tests/bin/test-manafe3-*.mjs)
python manafe3.py --check        # starts both servers, checks them, stops
```

GitHub Actions runs the fast tests on every push and the full suite on `main` (`.github/workflows/tests.yml`).

## Licences and names

- **Everything in this repository is Apache-2.0** (`LICENSE`).
  - The DetailCraft code: Copyright 2026 The Data Design Group, Inc. (`NOTICE`); the files Manafe3 changed are listed in
    `MANAFE3-CHANGES.md`.
  - Manafe3's own code (`engine/`, `manafe3.py`, `app/manafe3/`, `tools/manafe3-*`, the `*.ps1` scripts,
    `tests/bin/test-manafe3-*`): Copyright 2026 Ahmed Ali, Apache-2.0.
- **Names:** Manafe3 is based on DetailCraft and is not made or endorsed by The Data Design Group, Inc. The Manafe3 name
  and logo are the author's; the licence covers the code, not the names (`TRADEMARKS.md`).
- Upstream's README: `docs/DETAILCRAFT-README.md`.

## Maintainer only — the two-PC workflow

The author works on two PCs through git; contributors do not need any of this.

```powershell
Copy-Item .env.local.example .env.local          # this PC's own folders (never committed)
powershell -ExecutionPolicy Bypass -File .\start-work.ps1                    # pull, uv sync, tests, prints the task
python manafe3.py
powershell -ExecutionPolicy Bypass -File .\end-work.ps1 -Message "What I did"   # tests, HANDOVER, commit, push
```

`HANDOVER.md` holds the architecture, the decisions and the current task; `CLAUDE.md` the working rules.
