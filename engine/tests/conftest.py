# Manafe3 engine tests. Copyright 2026 Ahmed Ali. Licensed under the Apache License, Version 2.0 (see LICENSE).
"""Test isolation for the analysis cache (engine/analysis/analysis_cache.py; branch test-speedup, user 2026-11-25).

The runner (tools/run-tests-by-file.py) turns the cache on with MANAFE3_ANALYSIS_CACHE. It is turned OFF for a test that
    - uses monkeypatch (a patched function or constant is not in the cache key), or
    - carries @pytest.mark.no_analysis_cache (e.g. the parallel-path test, which must really run the process pool).
This runs before the test's fixtures are set up (tryfirst), so a module fixture built by such a test is solved too.
"""

import os

import pytest

from engine.analysis.analysis_cache import ENV

_RUNNER_VALUE = os.environ.get(ENV)


@pytest.hookimpl(tryfirst=True)
def pytest_runtest_setup(item):
    off = item.get_closest_marker("no_analysis_cache") is not None or "monkeypatch" in item.fixturenames
    if off or not _RUNNER_VALUE:
        os.environ.pop(ENV, None)
    else:
        os.environ[ENV] = _RUNNER_VALUE
