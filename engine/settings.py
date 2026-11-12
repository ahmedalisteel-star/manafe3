# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Per-machine settings from `.env.local` at the repo root (git-ignored; see `.env.local.example`).

No path or user name is written in the code: the office PC and the laptop each keep their own `.env.local`.
Environment variables of the same name win over the file.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / ".env.local"

#: The keys Manafe3 reads, and what each is for.
KEYS = {
    "MANAFE3_PROJECTS_DIR": "folder for client drawings, real-project IFC and vendor PDFs (never in git)",
    "BIMSTEELAUTO_PEB_PATH": "the private BIMSteelAuto peb folder (office PC only, for now)",
    "MYSTEELAPP_PATH": "MySteelApp Studio folder (laptop only)",
    "MANAFE3_ENGINE_PORT": "engine port, default 8765",
    "MANAFE3_WEB_PORT": "web app port, default 8000",
    "MANAFE3_WORKERS": "analysis processes at once (frame lines / sizing); default: one per job up to CPUs - 1, at most 3; "
                       "the per-file test runner sets 1",
}


def read_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """KEY=value lines; blank lines and # comments skipped; surrounding quotes removed."""
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key.strip()] = value
    return out


def get(key: str, default: str | None = None) -> str | None:
    return os.environ.get(key) or read_env_file().get(key) or default


#: The default ceiling on analysis processes (user decision 2026-11-12: memory) — MANAFE3_WORKERS or workers= override it.
DEFAULT_WORKER_CAP = 3


def analysis_workers(requested: int | None, n_jobs: int, cap: int | None = None) -> int:
    """How many analysis processes to start (user decision 2026-11-12, memory): an explicit `requested` wins; else
    MANAFE3_WORKERS (environment or .env.local; the per-file test runner sets 1); else one per job up to CPUs − 1, at most
    DEFAULT_WORKER_CAP (3), and `cap`. Never more than the jobs, never fewer than 1. A malformed MANAFE3_WORKERS is refused (no silent default)."""
    if requested is not None:
        n = int(requested)
    else:
        v = get("MANAFE3_WORKERS")
        if v is not None:
            try:
                n = int(v)
            except ValueError:
                raise ValueError(f"MANAFE3_WORKERS must be a whole number, got {v!r}") from None
            if n < 1:
                raise ValueError(f"MANAFE3_WORKERS must be >= 1, got {n}")
        else:
            n = min(max(1, (os.cpu_count() or 2) - 1), DEFAULT_WORKER_CAP)
            if cap is not None:
                n = min(n, cap)
    return max(1, min(n, max(1, n_jobs)))


def get_path(key: str) -> Path | None:
    """A configured folder, or None when it is not set (a path that does not exist is returned as is)."""
    v = get(key)
    return Path(v).expanduser() if v else None
