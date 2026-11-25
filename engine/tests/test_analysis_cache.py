# Manafe3 engine tests. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""The test runner's analysis cache (engine/analysis/analysis_cache.py; branch test-speedup, user decision 2026-11-25).

Negative controls (each must MISS or re-solve, never hand back a stale result):
    (a) a changed input (bay spacing + 1 mm, a loads value) → another key, compute runs again
    (b) a changed code fingerprint (an engine .py edited, uv.lock edited) → another key, compute runs again; a change
        under engine/tests does NOT change it (the tests are not the engine)
    (c) a corrupt cache file → deleted and re-solved, no crash
    (d) cache off (no MANAFE3_ANALYSIS_CACHE) → the solver runs every time; an input the key cannot represent → solved,
        nothing stored
    (e) SLOW: the cached result of sized building 1 equals a fresh solve, value for value. The fresh side always solves
        (it calls _analyse_building, never the cache), whatever the runner's setting.
Also: workers is not in the key (one solve for workers 1 and 2); a hit is a fresh copy (changing it does not change the
next hit); a stale lock of a dead process is removed; a lock held too long → the caller solves without it.
"""

import dataclasses
import json
import math
import os
import pathlib

import pytest

from engine.analysis import analysis_cache as AC
from engine.analysis import building_analysis as BA
from engine.peb.building import BuildingInput, resolve
from engine.peb.builtup_frame import BuiltUpSizes
from engine.peb.loads_input import LoadsInput

B1 = dict(span=24000, eave_height=6000, roof_slope=0.1, bay_spacing=6000, n_bays=4)
FIX = pathlib.Path(__file__).resolve().parents[2] / "fixtures" / "manafe3"


@pytest.fixture
def on(tmp_path, monkeypatch):
    monkeypatch.setenv(AC.ENV, str(tmp_path / "cache"))
    return tmp_path / "cache"


class Counter:
    def __init__(self, value=None):
        self.n, self.value = 0, value

    def __call__(self):
        self.n += 1
        return {"n": self.n, "value": self.value, "list": [1.0, 2.0]}


def _inputs(**kw):
    return {"b": BuildingInput(**{**B1, **kw}), "li": LoadsInput(V=45, exposure="C"), "p_delta": True, "step": 0.10, "limits": None}


def test_hit_returns_the_stored_result_as_a_fresh_copy(on):
    c = Counter("x")
    r1 = AC.cached("t", _inputs(), c)
    r2 = AC.cached("t", _inputs(), c)
    assert c.n == 1 and r1 == r2 == {"n": 1, "value": "x", "list": [1.0, 2.0]}
    r2["list"].append(99.0)                                    # a test changing its copy ...
    assert AC.cached("t", _inputs(), c)["list"] == [1.0, 2.0] and c.n == 1      # ... does not change the next hit
    assert len(list(on.glob("t-*.pkl"))) == 1 and not list(on.glob("*.lock")) and not list(on.glob("*.tmp"))


def test_a_changed_input_misses(on):
    # NEGATIVE CONTROL (a): bay spacing + 1 mm, and a loads value, each → another key and a new solve
    c = Counter()
    AC.cached("t", _inputs(), c)
    AC.cached("t", _inputs(bay_spacing=6001), c)
    i = _inputs()
    i["li"] = LoadsInput(V=46, exposure="C")
    AC.cached("t", i, c)
    assert c.n == 3 and len(list(on.glob("t-*.pkl"))) == 3
    assert AC.input_hash(_inputs()) != AC.input_hash(_inputs(bay_spacing=6001))
    assert AC.input_hash({"x": 1}) != AC.input_hash({"x": 1.0})                  # int and float stay different
    sized = dataclasses.replace(BuildingInput(**B1), sizes=BuiltUpSizes(hw_knee=475, hw_base=300, hw_rafter=300, haunch_length=2400,
                                                                          bf=200, tf=10, grade="S355", tw_column=6, tw_haunch=6, tw_rafter=6))
    assert AC.input_hash({"b": sized}) != AC.input_hash({"b": dataclasses.replace(sized, sizes=dataclasses.replace(sized.sizes, tf=12))})


def test_a_changed_code_fingerprint_misses(on, tmp_path, monkeypatch):
    # NEGATIVE CONTROL (b), the key: another fingerprint → another key → a new solve
    c = Counter()
    AC.cached("t", _inputs(), c)
    monkeypatch.setattr(AC, "_FINGERPRINT", "0" * 64)
    AC.cached("t", _inputs(), c)
    assert c.n == 2
    # (b), the fingerprint itself, on a scratch "engine": an edited .py or uv.lock changes it; a test file does not
    eng, root = tmp_path / "repo" / "engine", tmp_path / "repo"
    (eng / "analysis").mkdir(parents=True)
    (eng / "tests").mkdir()
    (eng / "analysis" / "solve.py").write_text("X = 1\n")
    (eng / "tests" / "test_x.py").write_text("T = 1\n")
    (root / "uv.lock").write_text("rev = a\n")
    monkeypatch.setattr(AC, "ENGINE", eng)
    monkeypatch.setattr(AC, "ROOT", root)

    def fp():
        monkeypatch.setattr(AC, "_FINGERPRINT", None)
        return AC.code_fingerprint()
    f0 = fp()
    (eng / "tests" / "test_x.py").write_text("T = 2\n")
    assert fp() == f0
    (eng / "analysis" / "solve.py").write_text("X = 2\n")
    f1 = fp()
    assert f1 != f0
    (root / "uv.lock").write_text("rev = b\n")
    assert fp() != f1


def test_the_real_fingerprint_covers_the_engine_not_the_tests():
    files = [p.relative_to(AC.ENGINE).as_posix() for p in AC.ENGINE.rglob("*.py")]
    assert "analysis/building_analysis.py" in files and "analysis/solve.py" in files      # what the key must cover
    assert len(AC.code_fingerprint()) == 64 and AC.code_fingerprint() == AC.code_fingerprint()


def test_a_corrupt_file_is_resolved(on):
    # NEGATIVE CONTROL (c)
    c = Counter()
    AC.cached("t", _inputs(), c)
    (p,) = on.glob("t-*.pkl")
    p.write_bytes(b"not a pickle")
    assert AC.cached("t", _inputs(), c)["n"] == 2 and c.n == 2
    assert AC.cached("t", _inputs(), c)["n"] == 2 and c.n == 2                  # the re-solved result is stored again


def test_off_solves_every_time_and_unknown_inputs_are_not_cached(tmp_path, monkeypatch):
    # NEGATIVE CONTROL (d): no MANAFE3_ANALYSIS_CACHE → compute every time, nothing written
    monkeypatch.delenv(AC.ENV, raising=False)
    c = Counter()
    AC.cached("t", _inputs(), c)
    AC.cached("t", _inputs(), c)
    assert c.n == 2
    monkeypatch.setenv(AC.ENV, str(tmp_path / "c2"))
    odd = {"x": object()}                                      # not canonical → solved, never stored
    AC.cached("t", odd, c)
    AC.cached("t", odd, c)
    assert c.n == 4 and not list((tmp_path / "c2").glob("*.pkl"))


def test_analyse_building_goes_through_the_cache_and_workers_is_not_in_the_key(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(BA, "_analyse_building", lambda b, li, **kw: calls.append(kw["workers"]) or {"workers": kw["workers"]})
    b, li = BuildingInput(**B1), LoadsInput(V=45, exposure="C")
    monkeypatch.delenv(AC.ENV, raising=False)
    BA.analyse_building(b, li, workers=1)
    BA.analyse_building(b, li, workers=1)
    assert calls == [1, 1]                                     # (d) off → the solver runs each time
    monkeypatch.setenv(AC.ENV, str(tmp_path / "c3"))
    BA.analyse_building(b, li, workers=1)
    BA.analyse_building(b, li, workers=2)                      # the result does not depend on workers
    BA.analyse_building(b, li, p_delta=False, workers=1)       # p_delta is in the key
    assert calls == [1, 1, 1, 1]


def test_locks(on, monkeypatch):
    on.mkdir(parents=True)
    key = AC.cache_key(_inputs())
    lock = on / f"t-{key}.pkl.lock"
    lock.write_text("999999999")                               # a dead process's lock: removed, the call goes on
    monkeypatch.setattr(AC, "_pid_alive", lambda pid: False)
    c = Counter()
    AC.cached("t", _inputs(), c)
    assert c.n == 1 and not lock.exists()
    # a live holder that never finishes: after LOCK_WAIT_S the caller solves without the lock (and leaves it alone)
    monkeypatch.setattr(AC, "_pid_alive", lambda pid: True)
    monkeypatch.setattr(AC, "LOCK_WAIT_S", 0.3)
    i = _inputs(bay_spacing=6001)
    lock2 = on / f"t-{AC.cache_key(i)}.pkl.lock"
    lock2.write_text(str(os.getpid()))
    AC.cached("t", i, c)
    assert c.n == 2 and lock2.exists()


def test_monkeypatch_tests_run_uncached(monkeypatch):
    # conftest.py: a test using monkeypatch starts with the cache OFF (a patch is not in the key)
    assert AC.ENV not in os.environ


def _first_difference(a, b, path="result"):
    if type(a) is not type(b):
        return f"{path}: type {type(a).__name__} != {type(b).__name__}"
    if isinstance(a, dict):
        if a.keys() != b.keys():
            return f"{path}: keys differ {sorted(set(a) ^ set(b))[:5]}"
        return next((d for k in a if (d := _first_difference(a[k], b[k], f"{path}[{k!r}]"))), None)
    if isinstance(a, (list, tuple)):
        if len(a) != len(b):
            return f"{path}: length {len(a)} != {len(b)}"
        return next((d for i, (x, y) in enumerate(zip(a, b)) if (d := _first_difference(x, y, f"{path}[{i}]"))), None)
    if isinstance(a, float) and math.isnan(a) and math.isnan(b):
        return None
    if hasattr(a, "shape"):                                    # numpy arrays, if any
        import numpy as np
        return None if np.array_equal(a, b, equal_nan=True) else f"{path}: arrays differ"
    return None if a == b else f"{path}: {a!r} != {b!r}"


@pytest.mark.slow
def test_cached_equals_a_fresh_solve(tmp_path):
    # CONTROL (e): the result the cache hands out for sized building 1 equals a solve made now, value for value. The cached
    # side uses the runner's cache when it is on (a hit from an earlier run is exactly what this checks), else a scratch
    # one; the fresh side calls _analyse_building directly, so it always solves.
    fx = json.loads((FIX / "building1-sized.json").read_text(encoding="utf-8"))
    b, _ = resolve(BuildingInput(**fx["building"], sizes=BuiltUpSizes(**fx["sizes"])))
    li = LoadsInput(**fx["loads"])
    if not os.environ.get(AC.ENV):
        os.environ[AC.ENV] = str(tmp_path / "cache")
        try:
            cached = BA.analyse_building(b, li, workers=1)
        finally:
            os.environ.pop(AC.ENV, None)
    else:
        cached = BA.analyse_building(b, li, workers=1)
    fresh = BA._analyse_building(b, li, workers=1)
    assert _first_difference(cached, fresh) is None, _first_difference(cached, fresh)
    assert len(cached["frames"]) == 5 and cached["banner"].startswith("NOT FOR ISSUE")
