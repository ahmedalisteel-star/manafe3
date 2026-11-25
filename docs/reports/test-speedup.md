# Engine test speed-up: parallel files + analysis cache (branch `test-speedup`, 2026-11-25)

Built on the laptop (DESKTOP-VBCSCS0) from `main` at `aad723da`. User decisions 2026-11-25: (a) `--jobs 3` with the
free-memory gate and longest-first order; (b) the analysis cache, off by default, on only in the test runner; (c)
end-work uses the cache, but control (e) "cached = fresh solve" always solves; `-NoCache` on start-work / end-work; (d)
one slow apex-building test. **HANDOVER.md is NOT edited here** (the office branch changes it): the user moves these
notes into HANDOVER on Sunday.

## For HANDOVER (to move on Sunday)

- **Rule (user 2026-11-25): a fully uncached run is REQUIRED before any upstream merge into main and once a week:**
  `powershell -ExecutionPolicy Bypass -File .\end-work.ps1 -NoCache -Message "..."` (or `-NoCache -DryRun`).
- **Correction to the roadmap line "speed up the full engine suite (~2 h)":** the last recorded full run took
  **2480 s (41 min)** on ENG04-PC (2026-11-24, "Last session": 310 passed, 43 files). The ~2 h figure is not in any
  recorded run; read it as "about 40 min at the office, much longer on the laptop when it is short of memory".
- **New test counts:** fast set **274 passed, 47 deselected (44 files)** (was 265 passed, 45 deselected, 43 files);
  full suite expected **321** (310 + 10 in `test_analysis_cache.py` + 1 apex test) — to be confirmed by the office run.
- **Workflow:** `tools/run-tests-by-file.py` now runs up to 3 files at once (`--jobs`), longest first, with the analysis
  cache on (`.cache/analysis`, git-ignored); `--no-cache` / `-NoCache` turn it off. On the laptop (< 3.5 GB free) the
  memory gate keeps it to one file at a time by itself.

## What was built

| File | Change |
|---|---|
| `engine/analysis/analysis_cache.py` (new) | the cache: key, code fingerprint, lock, load / store |
| `engine/analysis/building_analysis.py` | `analyse_building` → `analysis_cache.cached(...)` around the old body (`_analyse_building`); off unless `MANAFE3_ANALYSIS_CACHE` is set |
| `engine/tests/conftest.py` (new) | cache OFF for any test using `monkeypatch` or marked `no_analysis_cache` (before fixtures are built) |
| `engine/tests/test_analysis_cache.py` (new) | negative controls (a)–(d), locks, copies; control (e) slow |
| `engine/tests/test_apex_haunch.py` | + slow `test_apex_building_analysis_collateral_statics_by_hand` |
| `engine/tests/test_building_analysis.py`, `test_workers.py` | `pytestmark = no_analysis_cache` (the parallel-path test must really run the pool; the worker setting is the subject) |
| `tools/run-tests-by-file.py` | `--jobs` (default 3), memory gate, longest-first order (`.cache/test-times.json`), `--no-cache`, concurrent peak in the summary; the `engine:` line format kept (end-work parses it) |
| `start-work.ps1`, `end-work.ps1` | `-NoCache` switch; the uncached-run rule in the header |
| `pyproject.toml`, `.gitignore` | `no_analysis_cache` marker; `.cache/` |

**Cache key** = sha256(code fingerprint, canonical JSON of every input: BuildingInput with its sizes, LoadsInput,
`p_delta`, `step`, `limits`). `workers` is not in the key (the result does not depend on it; control (e) and the dedup test
check results). An input the key cannot represent (an unknown type) is never cached — the call solves.
**Code fingerprint** = the content of every `engine/**/*.py` except `engine/tests`, `uv.lock` (pins bimsteelauto,
ecp205-lrfd, PyNite 3.0.0), the Python version and the installed numpy / scipy / PyNiteFEA / bimsteelauto / ecp205-lrfd
versions. `engine.__version__` is not used (0.1.0 since Phase 0).
**Store**: one pickle per key (2.6 MiB for sized building 1), temp file + `os.replace`; a lock file per key so parallel
files do not solve the same building twice (a dead process's lock or one older than 3 h is removed; after 1 h of waiting
the caller solves without it); a corrupt file is deleted and re-solved; every hit is a fresh copy from disk.

## Controls (VERIFIED by the tests, run on the laptop)

- (a) changed input (bay spacing + 1 mm; V 45 → 46; tf 10 → 12 in the sizes) → another key, compute runs again.
- (b) another fingerprint → miss; on a scratch engine: an edited `.py` or `uv.lock` changes the fingerprint, an edited
  file under `engine/tests` does not.
- (c) corrupt cache file → re-solved and stored again, no crash.
- (d) cache off → the solver runs every time (`analyse_building` with a counting stand-in); an un-keyable input → solved,
  nothing stored; `workers` 1 and 2 → one solve; `p_delta` changed → a second solve.
- Locks: a dead process's lock removed; a live lock held past the wait → the caller solves and leaves the lock.
- conftest guard: a test using `monkeypatch` starts with the cache off.
- **(e) cached = fresh solve, sized building 1, value for value** (every key, every number, exact): PASSED with a cold
  cache (157 s: two solves) and with a warm cache (53 s: the fresh solve only — the cached side was the hit stored by the
  run before).
- **Mutation check of the negative controls** (scratch plugin, not committed): `input_hash` forced constant → 4 tests
  fail; `code_fingerprint` forced constant → 2 tests fail. So the controls catch a broken key.
- **Apex test (d)** — slow, NOT run on the laptop (user: the slow suite runs at the office on Sunday). Its hand values were
  checked here against a single frame-line solve of the apex building, line 3, case C, without P-Δ: ΣV 13.806 kN,
  VA = VB = 6.903 kN, ΣH 0.000, tributary 6.0 m — equal to the hand values 0.10 × 6.0 × 2 × (12 000 − 495) / 1000 = 13.806.
  The test itself runs the whole building with P-Δ through `analyse_building`; P-Δ does not change vertical statics or
  symmetry, but the test's first full run is the office's.

What the cache cannot close: a run-time change that is not in the key (a monkeypatched function or constant) — handled
by the conftest guard, not by the key; a dependency changed inside `.venv` without a version change — covered only by the
weekly uncached run.

## Numbers, old → new

| | Old | New |
|---|---|---|
| Fast set, tests | 265 passed, 45 deselected (43 files) | **274 passed, 47 deselected (44 files)** |
| Full suite, tests | 310 passed (43 files) | 321 expected (office run Sunday) |
| Fast set, laptop, `--jobs 1` | 1100 s (start-work, 2026-11-25 morning, laptop stalling) | **218 s** (cache on, jobs 1) |
| Control (e) | — | 157 s cold, 53 s warm |

**The 1100 s → 218 s fast-set drop is NOT from this change**: the fast set has no repeated building analysis (the cache
does nothing there) and it ran with `--jobs 1`. The machine was less starved (1.9 GiB free vs about 1 GiB; the morning
run had stalls of ~10 min in single tests: `test_ecp_checks.py` 690 s then, 54 s now; `test_frame_model.py` 5 s / 633 s /
2 s across runs). Laptop timings are not a benchmark.

**Expected at the office (estimates, not measured):** the slow set analyses sized building 1 **10 times** (brace_axial ×2,
brace_ends, eave_transfer, endplates, joints, ridge_knee ×2, stability_braces, welds), 5 braces-off variants (4 distinct)
and unsized building 1 twice (1 distinct): 11 of 17 building analyses become cache hits on a cold cache (more on a warm
one). With 3 files at once the full suite is estimated at **~8–14 min** (was 41 min); the fast set ~2–4 min. A run right
after an engine code change starts cold (every key changes) — that is by design.

## Laptop notes

- Free memory on the laptop is about 1–2 GiB of 7.8 GiB, so `--jobs 3` falls back to one file at a time (seen: `--jobs 2`
  ran "at most 1 at once" at 1.9 GiB free). Run `--jobs 1` here, as the user asked.
- Runs here: `test_analysis_cache.py` (10 passed, incl. (e), twice) and the fast set (`--jobs 1`); the parallel path ran
  only on 4 small files (gate-limited to 1); `--no-cache` on the same 4 files. Not run here: the slow suite, `npm test`
  (no app file changed), end-work.
