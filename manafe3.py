# Manafe3 launcher. Copyright (c) 2026 Ahmed Ali. All rights reserved.
"""Start Manafe3 with one command:   python manafe3.py

  1. makes sure the Python environment exists (runs `uv sync` the first time),
  2. starts the engine   http://127.0.0.1:8765   (FastAPI, engine/api.py, from .venv)
  3. starts the web app  http://localhost:8000   (node devshell/serve.mjs)
  4. opens the browser, and stops both on Ctrl+C.

Options:  --no-browser   do not open a browser
          --check        start both, check /health and the page, print the result, stop (exit 1 on failure)

Only the standard library is used here, so plain `python` works before the venv exists. Ports come from
.env.local (MANAFE3_ENGINE_PORT, MANAFE3_WEB_PORT) or default to 8765 and 8000.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def env_local() -> dict[str, str]:
    p = ROOT / ".env.local"
    out: dict[str, str] = {}
    if p.is_file():
        for line in p.read_text(encoding="utf-8-sig").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("\"'")
    return out


def venv_python() -> Path:
    win = ROOT / ".venv" / "Scripts" / "python.exe"
    return win if os.name == "nt" else ROOT / ".venv" / "bin" / "python"


def ensure_env() -> Path:
    py = venv_python()
    if py.is_file():
        return py
    uv = shutil.which("uv")
    if not uv:
        sys.exit("Manafe3: no .venv and no uv. Install uv (https://docs.astral.sh/uv/), then run:  uv sync")
    print("Manafe3: first run, creating the Python environment (uv sync)...")
    subprocess.run([uv, "sync"], cwd=ROOT, check=True)
    return py


def wait_for(url: str, seconds: float) -> bytes | None:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        try:
            with urllib.request.urlopen(url, timeout=2) as r:
                return r.read()
        except OSError:
            time.sleep(0.3)
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description="Start the Manafe3 engine and web app.")
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--check", action="store_true", help="start, check, stop")
    a = ap.parse_args()

    cfg = {**env_local(), **{k: v for k, v in os.environ.items() if k.startswith("MANAFE3_")}}
    eport = int(cfg.get("MANAFE3_ENGINE_PORT", "8765"))
    wport = int(cfg.get("MANAFE3_WEB_PORT", "8000"))
    node = shutil.which("node")
    if not node:
        sys.exit("Manafe3: Node.js 20.19+ is needed for the web app (https://nodejs.org).")
    py = ensure_env()

    child_env = {**os.environ, "MANAFE3_WEB_PORT": str(wport)}
    procs = [
        subprocess.Popen([str(py), "-m", "uvicorn", "engine.api:app", "--host", "127.0.0.1", "--port", str(eport)],
                         cwd=ROOT, env=child_env),
        subprocess.Popen([node, str(ROOT / "devshell" / "serve.mjs"), "--port", str(wport)], cwd=ROOT, env=child_env),
    ]
    try:
        health = wait_for(f"http://127.0.0.1:{eport}/health", 60)
        page = wait_for(f"http://127.0.0.1:{wport}/", 30)
        if health is None or page is None or any(p.poll() is not None for p in procs):
            print("Manafe3: did not start (engine up: %s, web app up: %s). Is a port already in use?" % (health is not None, page is not None))
            return 1
        h = json.loads(health)
        print(f"Manafe3 engine {h['engine']}  (PyNite {h['pynite']}, bimsteelauto {h['bimsteelauto']})  http://127.0.0.1:{eport}")
        print(f"Manafe3 web app  http://localhost:{wport}/")
        if a.check:
            ok = b"<title>Manafe3" in page and h.get("status") == "ok"
            print("check:", "OK" if ok else "FAILED")
            return 0 if ok else 1
        if not a.no_browser:
            webbrowser.open(f"http://localhost:{wport}/")
        print("Press Ctrl+C to stop.")
        while all(p.poll() is None for p in procs):
            time.sleep(0.5)
        return 1
    except KeyboardInterrupt:
        return 0
    finally:
        for p in procs:
            if p.poll() is None:
                p.terminate()
        for p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()
        print("Manafe3 stopped.")


if __name__ == "__main__":
    sys.exit(main())
