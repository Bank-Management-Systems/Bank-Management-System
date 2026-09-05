"""Shared helpers for the Bank Management System integration test suite.

Run target : the compiled C++ API (default http://localhost:8080)
Override   : export API_BASE_URL=http://host:port before running pytest

Skip semantics: a 501 response means the endpoint exists but the owning
candidate has not implemented it yet, so the test SKIPS instead of failing.
This keeps CI green on the fresh template and turns each test strict the
moment the endpoint is implemented.
"""
import os
import time

import pytest
import requests

BASE_URL = os.environ.get("API_BASE_URL", "http://localhost:8080")
TIMEOUT = 10  # seconds

# Seed credentials (database/seed.sql). Candidate 4 keeps these in sync.
STAFF_USER = os.environ.get("TEST_STAFF_USER", "admin")
STAFF_PASS = os.environ.get("TEST_STAFF_PASS", "admin123")
SEED_ACCOUNT_A = int(os.environ.get("TEST_ACC_A", "1001"))
SEED_ACCOUNT_B = int(os.environ.get("TEST_ACC_B", "1002"))
SEED_PIN = os.environ.get("TEST_CUSTOMER_PIN", "1234")


def call(method, path, body=None, **kw):
    """One API call against the backend under test."""
    return requests.request(method, BASE_URL + path, json=body, timeout=TIMEOUT, **kw)


def skip_if_unimplemented(response, owner):
    """Convert 501 into a pytest skip with a pointer to the owner."""
    if response.status_code == 501:
        pytest.skip(f"not implemented yet - {owner}")


def make_account(**overrides):
    """Create a fresh account via FR-01; fall back to the seeded account.

    Returns (account_number, created_via_api: bool). Falls back to the seeded
    account 1001 while FR-01 is still unimplemented, so Candidates 2 and 3 are
    not blocked by Candidate 1's progress.
    """
    payload = {
        "name": f"IT User {int(time.time() * 1000)}",
        "address": "1 Test Lane",
        "contact": "9000000000",
        "type": "Savings",
        "opening_deposit": 5000,
    }
    payload.update(overrides)
    r = call("POST", "/api/accounts", payload)
    if r.status_code in (200, 201):
        body = r.json()
        acc = body.get("account_number") or body.get("accountNumber")
        if acc is not None:
            return int(acc), True
    return SEED_ACCOUNT_A, False
