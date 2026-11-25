# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""On-disk cache of whole-building analyses, FOR THE TEST RUNNER ONLY (user decision 2026-11-25, branch test-speedup).

OFF unless the environment variable MANAFE3_ANALYSIS_CACHE names a folder; only tools/run-tests-by-file.py sets it
(.cache/analysis, git-ignored). The app and the API never set it, so production always solves.

    key          sha256 of (code fingerprint, the call's inputs as canonical JSON). An input that cannot be written as
                 canonical JSON (an unknown type) is NEVER cached: the call just solves.
    fingerprint  the content of every engine/**/*.py except engine/tests, uv.lock (the pinned bimsteelauto, ecp205-lrfd and
                 PyNite), the Python version and the installed versions of the numeric libraries. engine.__version__ is
                 NOT used (it has not changed since Phase 0). Any engine code change → every key changes → no stale result.
    store        one pickle per key; written to a temp file then os.replace (never half a file); one lock file per key so
                 two test files running in parallel do not solve the same building twice (a stale lock — its process
                 gone, or older than LOCK_STALE_S — is removed); a corrupt or unreadable file is deleted and re-solved.
    load         every hit is a fresh copy from disk (no shared in-memory object a test could change for another).
What it cannot close: run-time changes that are not in the key (a monkeypatched constant or function). The tests'
conftest.py turns the cache off for every test that uses monkeypatch or carries the no_analysis_cache marker.
"""

from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
import os
import pickle
import sys
import time
from importlib import metadata
from pathlib import Path

ENV = "MANAFE3_ANALYSIS_CACHE"
ENGINE = Path(__file__).resolve().parents[1]
ROOT = ENGINE.parent
LIBS = ("numpy", "scipy", "PyNiteFEA", "bimsteelauto", "bimsteelauto-connections", "ecp205-lrfd")
LOCK_WAIT_S = 3600.0          # wait at most this long for another process solving the same key, then solve here
LOCK_STALE_S = 3 * 3600.0     # a lock older than this is left over from a killed run
_FINGERPRINT: str | None = None


class NotCanonical(TypeError):
    """An input the key cannot represent exactly: the call is not cached."""


def cache_dir() -> Path | None:
    v = os.environ.get(ENV, "").strip()
    return Path(v) if v else None


def _canon(o):
    if o is None or isinstance(o, (bool, int, str)):
        return o
    if isinstance(o, float):
        return {"f": repr(o)}                          # exact; 1 and 1.0 stay different
    if isinstance(o, enum.Enum):
        return {"enum": f"{type(o).__qualname__}.{o.name}"}
    if dataclasses.is_dataclass(o) and not isinstance(o, type):
        return {"dc": f"{type(o).__module__}.{type(o).__qualname__}",
                "fields": {f.name: _canon(getattr(o, f.name)) for f in dataclasses.fields(o)}}
    if isinstance(o, (list, tuple)):
        return {type(o).__name__: [_canon(x) for x in o]}
    if isinstance(o, dict):
        if not all(isinstance(k, str) for k in o):
            raise NotCanonical("dict with non-string keys")
        return {"dict": {k: _canon(o[k]) for k in sorted(o)}}
    raise NotCanonical(f"cannot key a {type(o).__name__}")


def input_hash(inputs: dict) -> str:
    return hashlib.sha256(json.dumps(_canon(inputs), sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def code_fingerprint() -> str:
    global _FINGERPRINT
    if _FINGERPRINT is None:
        h = hashlib.sha256()
        for p in sorted(ENGINE.rglob("*.py")):
            rel = p.relative_to(ENGINE).as_posix()
            if rel.startswith("tests/") or "__pycache__" in rel:
                continue
            h.update(rel.encode() + b"\0" + p.read_bytes() + b"\0")
        lock = ROOT / "uv.lock"
        h.update(b"uv.lock\0" + (lock.read_bytes() if lock.exists() else b"(none)") + b"\0")
        h.update(sys.version.encode() + b"\0")
        for lib in LIBS:
            try:
                v = metadata.version(lib)
            except metadata.PackageNotFoundError:
                v = "(not installed)"
            h.update(f"{lib}={v}\0".encode())
        _FINGERPRINT = h.hexdigest()
    return _FINGERPRINT


def cache_key(inputs: dict) -> str:
    return hashlib.sha256((code_fingerprint() + ":" + input_hash(inputs)).encode()).hexdigest()


def _pid_alive(pid: int) -> bool:
    try:
        import psutil
        return psutil.pid_exists(pid)
    except Exception:                                  # no psutil: rely on the age rule
        return True


def _acquire(lock: Path) -> bool:
    """True when this process holds the lock; False after LOCK_WAIT_S (then the caller solves without it)."""
    t0 = time.time()
    while True:
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            return True
        except FileExistsError:
            try:
                age = time.time() - lock.stat().st_mtime
                pid = int(lock.read_text() or "0")
                if age > LOCK_STALE_S or (pid and not _pid_alive(pid)):
                    lock.unlink(missing_ok=True)
                    continue
            except (OSError, ValueError):
                pass                                   # being written or removed right now: try again
            if time.time() - t0 > LOCK_WAIT_S:
                return False
            time.sleep(0.5)


def _load(path: Path):
    try:
        with open(path, "rb") as f:
            return True, pickle.load(f)
    except FileNotFoundError:
        return False, None
    except Exception:                                  # corrupt / truncated / unreadable: never a result
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
        return False, None


def _store(path: Path, value) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with open(tmp, "wb") as f:
        pickle.dump(value, f, protocol=pickle.HIGHEST_PROTOCOL)
    os.replace(tmp, path)


def cached(kind: str, inputs: dict, compute):
    """compute() through the cache when it is on; compute() directly when it is off or the inputs cannot be keyed."""
    d = cache_dir()
    if d is None:
        return compute()
    try:
        key = cache_key(inputs)
    except NotCanonical:
        return compute()
    d.mkdir(parents=True, exist_ok=True)
    path = d / f"{kind}-{key}.pkl"
    hit, value = _load(path)
    if hit:
        return value
    lock = path.with_name(path.name + ".lock")
    held = _acquire(lock)
    try:
        if held:
            hit, value = _load(path)                   # another process may have written it while we waited
            if hit:
                return value
        value = compute()
        _store(path, value)
        hit, fresh = _load(path)                       # hand back the disk copy, as every later hit gets
        return fresh if hit else value
    finally:
        if held:
            lock.unlink(missing_ok=True)
