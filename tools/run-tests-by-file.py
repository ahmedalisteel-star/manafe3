# Manafe3 tool. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Run the engine tests ONE FILE PER PROCESS, each in a fresh Python process (user decision 2026-11-12: the PC runs short
of memory; a single pytest process keeps every file's imports, caches and results alive), up to --jobs files at once.

    uv run python tools/run-tests-by-file.py                 # every file, slow tests included (end-work.ps1)
    uv run python tools/run-tests-by-file.py -m "not slow"   # the fast set (start-work.ps1)
    options: --min-free-gib 3   keep at least this much memory free (default 3): warn before the run when less is free,
                                and start another file next to running ones only when free >= this + 0.5 GiB
             --jobs 3           files at once (default 3; 1 = one after the other, as before 2026-11-25)
             --no-cache         solve every building analysis (no analysis cache)
             --only "test_x*.py" only the files matching this glob (negative controls / quick checks; end-work -OnlyTests)

Speed-up (user decision 2026-11-25, branch test-speedup):
  parallel files  up to --jobs files run at once; a file is started next to running ones only while enough memory is free
                  (the gate above), so a PC short of memory falls back to one file at a time. Longest files start first,
                  from the times of the last run (.cache/test-times.json, git-ignored; a file with no time yet goes first).
  analysis cache  MANAFE3_ANALYSIS_CACHE=.cache/analysis for every file (engine/analysis/analysis_cache.py: key = the
                  engine code fingerprint + the full input, so changed code or input never reuses a result). --no-cache
                  turns it off; a fully uncached run is required before any upstream merge into main and once a week.
Every file runs with MANAFE3_WORKERS=1 (analyses serial; a test that passes workers= explicitly still gets its pool —
test_building_analysis.py keeps the parallel path tested with 2). Per file: pytest's summary, the time and the PEAK
memory of the whole process tree (pytest + its analysis subprocesses), sampled every 0.2 s; with --jobs > 1 also the peak
of all running files together. Nothing is skipped: a file that fails or runs out of memory is reported by name with its
peak, and the exit code is 1. In the full run (no -m) a file that collects no test is a failure; with -m a file whose
tests are all deselected is fine. Files are listed as they finish.
The last line is the summary end-work.ps1 records:  engine: <n> passed, <n> failed, ... (<files> files, largest peak ...)
Exit code (2026-11-23, user): 0 only when every file passed with a pytest summary; 1 when any file failed, ran out of
memory or gave no summary line (or no test file matched); 2 when the runner itself crashed (then NO "engine:" line is
printed, so end-work.ps1 refuses too). Output is UTF-8 whatever the console or pipe (a non-ASCII test name or message
crashed the cp1252 print before).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

ROOT = Path(__file__).resolve().parent.parent
KINDS = ("passed", "failed", "errors", "error", "skipped", "deselected", "xfailed", "xpassed")
CACHE = ROOT / ".cache"
TIMES = CACHE / "test-times.json"
GATE_MARGIN_GIB = 0.5          # free memory needed above --min-free-gib before a file starts next to running ones


def top_memory(n: int = 5) -> list[tuple[str, int, float]]:
    agg: dict[str, list] = {}
    for p in psutil.process_iter(["name", "memory_info"]):
        try:
            a = agg.setdefault(p.info["name"] or "?", [0, 0])
            a[0] += 1
            a[1] += p.info["memory_info"].rss
        except (psutil.Error, TypeError):
            pass
    return sorted(((k, v[0], v[1] / 2**30) for k, v in agg.items()), key=lambda t: -t[2])[:n]


def free_gib() -> float:
    return psutil.virtual_memory().available / 2**30


class Running:
    """One test file in its own pytest process; its output read on a thread, its tree's memory sampled by poll()."""

    def __init__(self, f: Path, marker: str | None, cache: Path | None):
        self.f, self.marker = f, marker
        cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + (["-m", marker] if marker else []) + [str(f.relative_to(ROOT))]
        env = {**os.environ, "MANAFE3_WORKERS": "1"}
        env.pop("MANAFE3_ANALYSIS_CACHE", None)
        if cache is not None:
            env["MANAFE3_ANALYSIS_CACHE"] = str(cache)
        self.t0 = time.time()
        self.p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                  encoding="utf-8", errors="replace")
        self.chunks: list[str] = []
        self.reader = threading.Thread(target=lambda: self.chunks.append(self.p.stdout.read()))
        self.reader.start()
        self.root = psutil.Process(self.p.pid)
        self.peak, self.procs_at_peak, self.rss = 0, 1, 0

    def poll(self) -> bool:
        """Sample the memory; True while the process runs."""
        if self.p.poll() is not None:
            self.rss = 0
            return False
        try:
            tree = [self.root] + self.root.children(recursive=True)
            rss = 0
            for q in tree:
                try:
                    rss += q.memory_info().rss
                except psutil.Error:
                    pass
            self.rss = rss
            if rss > self.peak:
                self.peak, self.procs_at_peak = rss, len(tree)
        except psutil.Error:
            pass
        return True

    def result(self) -> dict:
        self.reader.join()
        out = "".join(self.chunks)
        lines = out.splitlines()
        summary = next((ln.strip(" =") for ln in reversed(lines) if re.search(r"\d+ (passed|failed|errors?|skipped|deselected)", ln)), "")
        counts = {}
        for k in KINDS:
            m = re.search(rf"(\d+) {k}\b", summary)
            if m:
                key = "errors" if k in ("error", "errors") else k
                counts[key] = counts.get(key, 0) + int(m.group(1))
        rc = self.p.returncode
        # 5 = nothing collected: fine when -m deselected every test of the file (the fast set), a FAILURE in the full run
        # (user decision 2026-11-12: a file that collects no test is a broken file)
        ok = rc == 0 or (rc == 5 and self.marker is not None)
        if ok and not summary:                   # no summary line: killed, or pytest did not finish — never a pass
            ok = False
        return {"file": self.f.name, "rc": rc, "ok": ok, "seconds": time.time() - self.t0, "peak_mib": self.peak / 2**20,
                "procs": self.procs_at_peak, "summary": summary or "(no pytest summary - killed?)", "counts": counts,
                "tail": "" if ok else "\n".join(lines[-40:])}


def load_times() -> dict:
    try:
        return json.loads(TIMES.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def save_times(times: dict) -> None:
    try:
        CACHE.mkdir(parents=True, exist_ok=True)
        tmp = TIMES.with_name(TIMES.name + ".tmp")
        tmp.write_text(json.dumps(times, indent=1, sort_keys=True), encoding="utf-8")
        os.replace(tmp, TIMES)
    except OSError:
        pass                                     # the order is only an optimisation


def order(files: list[Path], times: dict) -> list[Path]:
    """Longest first; a file with no recorded time first of all (it may be a new slow one)."""
    return sorted(files, key=lambda f: (f.name in times, -times.get(f.name, 0.0), f.name))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-m", dest="marker", default=None, help='pytest marker expression, e.g. "not slow"')
    ap.add_argument("--min-free-gib", type=float, default=3.0)
    ap.add_argument("--jobs", type=int, default=3, help="test files at once (default 3)")
    ap.add_argument("--no-cache", action="store_true", help="no analysis cache: solve every building analysis")
    ap.add_argument("--only", default=None, help='only the test files matching this glob, e.g. "test_cleats*.py"')
    a = ap.parse_args()
    if a.jobs < 1:
        ap.error("--jobs must be 1 or more")
    vm = psutil.virtual_memory()
    free = vm.available / 2**30
    cache = None if a.no_cache else CACHE / "analysis"
    print(f"memory: {free:.1f} GiB free of {vm.total / 2**30:.1f} GiB; jobs {a.jobs}; analysis cache "
          + ("OFF (--no-cache)" if cache is None else f"ON ({cache.relative_to(ROOT).as_posix()})"))
    if free < a.min_free_gib:
        print(f"WARNING: less than {a.min_free_gib:g} GiB free - the run may be stopped for memory"
              + (", and it runs one file at a time" if a.jobs > 1 else "") + ". Largest users now:")
        for name, n, gib in top_memory():
            print(f"    {name:28s} {n:3d} processes {gib:5.2f} GiB")
        print("  Close browser tabs / other programs if you can. The run continues.")
    files = sorted((ROOT / "engine" / "tests").glob(a.only or "test_*.py"))
    if not files:
        print(f"no test file matches {a.only or 'test_*.py'}")
        return 1
    tkey = "fast" if a.marker else "full"
    all_times = load_times()
    times = all_times.get(tkey, {})
    queue = order(files, times)
    tot: dict[str, int] = {}
    bad, rows, running, t0 = [], [], [], time.time()
    peak_all, most = 0, 0
    while queue or running:
        # start: always when nothing runs; next to running files only up to --jobs and while the memory gate allows
        while queue and (not running or (len(running) < a.jobs and free_gib() >= a.min_free_gib + GATE_MARGIN_GIB)):
            running.append(Running(queue.pop(0), a.marker, cache))
            most = max(most, len(running))
        time.sleep(0.2)
        still = []
        for r in running:
            if r.poll():
                still.append(r)
                continue
            res = r.result()
            rows.append(res)
            for k, v in res["counts"].items():
                tot[k] = tot.get(k, 0) + v
            if res["ok"]:
                times[res["file"]] = round(res["seconds"], 1)
            flag = "" if res["ok"] else "   <-- FAILED"
            print(f"{res['file']:36s} {res['seconds']:7.1f} s  peak {res['peak_mib']:6.0f} MiB ({res['procs']} proc)  {res['summary']}{flag}", flush=True)
            if not res["ok"]:
                bad.append(res)
        running = still
        peak_all = max(peak_all, sum(r.rss for r in running))
    all_times[tkey] = times
    save_times(all_times)
    for r in bad:
        print(f"\n---- {r['file']} (exit {r['rc']}, peak {r['peak_mib']:.0f} MiB) ----\n{r['tail']}")
    big = max(rows, key=lambda r: r["peak_mib"]) if rows else None
    parts = ", ".join(f"{tot[k]} {k}" for k in ("passed", "failed", "errors", "skipped", "deselected", "xfailed", "xpassed") if tot.get(k))
    extra = (f", jobs {a.jobs} (at most {most} at once, together peak {peak_all / 2**20:.0f} MiB)" if a.jobs > 1 else ", jobs 1") \
        + (", cache off" if cache is None else ", cache on")
    tail = f" ({len(files)} files, largest peak {big['peak_mib']:.0f} MiB in {big['file']}, {time.time() - t0:.0f} s{extra})" if big else ""
    print(f"\nengine: {parts or 'no tests'}{tail}" + (f"  FAILED FILES: {', '.join(r['file'] for r in bad)}" if bad else ""))
    return 1 if bad else 0


def _utf8() -> None:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass


if __name__ == "__main__":
    _utf8()
    try:
        rc = main()
    except SystemExit:                           # argparse (--help, a bad option) keeps its own exit code
        raise
    except BaseException as e:                   # a crash of the runner itself is never a pass (no "engine:" line)
        import traceback
        traceback.print_exc()
        print(f"\nRUNNER CRASHED ({type(e).__name__}): the test result is unknown - treated as FAILED")
        rc = 2
    sys.exit(rc)
