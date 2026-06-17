"""Shared pytest fixtures for ClawJob API tests."""
import os

# Enterprise routers (KYC, workspace, billing) must load before app.main is imported by tests.
os.environ.setdefault("CLAWJOB_ENTERPRISE", "1")
# Tests generate many local requests quickly; keep rate limiting from flaking.
os.environ.setdefault("RATE_LIMIT_DEFAULT", "1000000/minute")

import pytest


@pytest.fixture(autouse=True)
def _reset_runtime_circuit_breakers():
    """Avoid cross-test pollution when circuit-breaker tests open hosts like example.com."""
    from app.core.systems import runtime_guard

    runtime_guard._state.clear()
    yield
    runtime_guard._state.clear()
