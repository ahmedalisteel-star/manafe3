# Manafe3 engine. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""MANAFE3_WORKERS (engine/settings.analysis_workers, user decision 2026-11-12): how many analysis processes start.

By hand: an explicit request wins over the environment; MANAFE3_WORKERS=1 makes every analysis serial (the per-file test
runner sets it); unset → one per job up to CPUs − 1, at most 3, and the cap; never more than the jobs, never fewer than 1.
Negative controls: "two" and 0 are refused, not replaced by a default. The PARALLEL path itself stays tested by
test_building_analysis.py's `whole` fixture (workers=2 explicitly, 2 distinct frame lines, one line checked against a
serial solve)."""

import os

import pytest

from engine.settings import analysis_workers


def test_explicit_beats_environment(monkeypatch):
    monkeypatch.setenv("MANAFE3_WORKERS", "1")
    assert analysis_workers(2, 3) == 2
    assert analysis_workers(None, 3) == 1


def test_default_and_caps(monkeypatch):
    monkeypatch.delenv("MANAFE3_WORKERS", raising=False)
    monkeypatch.setattr("engine.settings.read_env_file", lambda *a, **k: {})      # .env.local must not decide this test
    cpu = max(1, (os.cpu_count() or 2) - 1)
    assert analysis_workers(None, 100) == min(cpu, 3)                               # the default ceiling 3 (2026-11-12)
    assert analysis_workers(None, 100, cap=2) == min(cpu, 2)
    assert analysis_workers(5, 100) == 5 and analysis_workers(None, 2) == min(cpu, 2)  # an explicit request is not capped
    assert analysis_workers(None, 1) == 1 and analysis_workers(None, 0) == 1
    assert analysis_workers(8, 2) == 2                                               # never more than the jobs


def test_malformed_environment_refused(monkeypatch):
    for bad in ("two", "0"):
        monkeypatch.setenv("MANAFE3_WORKERS", bad)
        with pytest.raises(ValueError):
            analysis_workers(None, 3)
