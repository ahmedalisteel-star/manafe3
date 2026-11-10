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


def get_path(key: str) -> Path | None:
    """A configured folder, or None when it is not set (a path that does not exist is returned as is)."""
    v = get(key)
    return Path(v).expanduser() if v else None
