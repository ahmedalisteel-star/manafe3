# Manafe3 tool. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Run the engine tests ONE FILE AT A TIME, each in a fresh Python process (user decision 2026-11-12: the PC runs short of
memory; a single pytest process keeps every file's imports, caches and results alive).

    uv run python tools/run-tests-by-file.py                 # every file, slow tests included (end-work.ps1)
    uv run python tools/run-tests-by-file.py -m "not slow"   # the fast set (start-work.ps1)
    options: --min-free-gib 3   warn when less memory than this is free before the run (default 3)

Every file runs with MANAFE3_WORKERS=1 (analyses serial; a test that passes workers= explicitly still gets its pool —
test_building_analysis.py keeps the parallel path tested with 2). Per file: pytest's summary, the time and the PEAK
memory of the whole process tree (pytest + its analysis subprocesses), sampled every 0.2 s. Nothing is skipped: a file
that fails or runs out of memory is reported by name with its peak, and the exit code is 1. In the full run (no -m) a
file that collects no test is a failure; with -m a file whose tests are all deselected is fine.
The last line is the summary end-work.ps1 records:  engine: <n> passed, <n> failed, ... (<files> files, largest peak ...)
"""

from __future__ import annotations

import argparse
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


def run_file(f: Path, marker: str | None) -> dict:
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider"] + (["-m", marker] if marker else []) + [str(f.relative_to(ROOT))]
    env = {**os.environ, "MANAFE3_WORKERS": "1"}
    t0 = time.time()
    p = subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                         encoding="utf-8", errors="replace")
    chunks: list[str] = []
    reader = threading.Thread(target=lambda: chunks.append(p.stdout.read()))
    reader.start()
    root = psutil.Process(p.pid)
    peak, procs_at_peak = 0, 1
    while p.poll() is None:
        try:
            tree = [root] + root.children(recursive=True)
            rss = 0
            for q in tree:
                try:
                    rss += q.memory_info().rss
                except psutil.Error:
                    pass
            if rss > peak:
                peak, procs_at_peak = rss, len(tree)
        except psutil.Error:
            pass
        time.sleep(0.2)
    reader.join()
    out = "".join(chunks)
    lines = out.splitlines()
    summary = next((ln.strip(" =") for ln in reversed(lines) if re.search(r"\d+ (passed|failed|errors?|skipped|deselected)", ln)), "")
    counts = {}
    for k in KINDS:
        m = re.search(rf"(\d+) {k}\b", summary)
        if m:
            key = "errors" if k in ("error", "errors") else k
            counts[key] = counts.get(key, 0) + int(m.group(1))
    # 5 = nothing collected: fine when -m deselected every test of the file (the fast set), a FAILURE in the full run
    # (user decision 2026-11-12: a file that collects no test is a broken file)
    ok = p.returncode == 0 or (p.returncode == 5 and marker is not None)
    return {"file": f.name, "rc": p.returncode, "ok": ok, "seconds": time.time() - t0, "peak_mib": peak / 2**20,
            "procs": procs_at_peak, "summary": summary or "(no pytest summary - killed?)", "counts": counts,
            "tail": "" if ok else "\n".join(lines[-40:])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("-m", dest="marker", default=None, help='pytest marker expression, e.g. "not slow"')
    ap.add_argument("--min-free-gib", type=float, default=3.0)
    a = ap.parse_args()
    vm = psutil.virtual_memory()
    free = vm.available / 2**30
    print(f"memory: {free:.1f} GiB free of {vm.total / 2**30:.1f} GiB")
    if free < a.min_free_gib:
        print(f"WARNING: less than {a.min_free_gib:g} GiB free - the run may be stopped for memory. Largest users now:")
        for name, n, gib in top_memory():
            print(f"    {name:28s} {n:3d} processes {gib:5.2f} GiB")
        print("  Close browser tabs / other programs if you can. The run continues.")
    files = sorted((ROOT / "engine" / "tests").glob("test_*.py"))
    tot: dict[str, int] = {}
    bad, rows, t0 = [], [], time.time()
    for f in files:
        r = run_file(f, a.marker)
        rows.append(r)
        for k, v in r["counts"].items():
            tot[k] = tot.get(k, 0) + v
        flag = "" if r["ok"] else "   <-- FAILED"
        print(f"{r['file']:36s} {r['seconds']:7.1f} s  peak {r['peak_mib']:6.0f} MiB ({r['procs']} proc)  {r['summary']}{flag}", flush=True)
        if not r["ok"]:
            bad.append(r)
    for r in bad:
        print(f"\n---- {r['file']} (exit {r['rc']}, peak {r['peak_mib']:.0f} MiB) ----\n{r['tail']}")
    big = max(rows, key=lambda r: r["peak_mib"]) if rows else None
    parts = ", ".join(f"{tot[k]} {k}" for k in ("passed", "failed", "errors", "skipped", "deselected", "xfailed", "xpassed") if tot.get(k))
    tail = f" ({len(files)} files, largest peak {big['peak_mib']:.0f} MiB in {big['file']}, {time.time() - t0:.0f} s)" if big else ""
    print(f"\nengine: {parts or 'no tests'}{tail}" + (f"  FAILED FILES: {', '.join(r['file'] for r in bad)}" if bad else ""))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
