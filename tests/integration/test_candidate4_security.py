"""Candidate 4 - Security contract tests (FR-18, FR-19, FR-20).

Chapter 7 of the Test Plan V2. Credentials come from database/seed.sql
(admin/admin123 staff, account 1001 with PIN 1234) and can be overridden via
TEST_STAFF_USER / TEST_STAFF_PASS / TEST_CUSTOMER_PIN environment variables.
"""
import os

from config import (call, skip_if_unimplemented,
                    STAFF_USER, STAFF_PASS, SEED_ACCOUNT_A, SEED_PIN)

C4 = "Candidate 4 (backend/candidate4_security)"


def test_fr18_staff_login_success():
    r = call("POST", "/api/auth/staff/login", {"username": STAFF_USER, "password": STAFF_PASS})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 200, r.text
    assert r.json().get("role") == "staff"


def test_fr18_staff_login_wrong_password():
    r = call("POST", "/api/auth/staff/login", {"username": STAFF_USER, "password": "definitely-wrong"})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 401


def test_fr19_customer_login_success():
    r = call("POST", "/api/auth/customer/login",
             {"account_number": SEED_ACCOUNT_A, "pin": SEED_PIN})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 200, r.text
    assert r.json().get("role") == "customer"


def test_fr19_customer_login_wrong_pin():
    r = call("POST", "/api/auth/customer/login",
             {"account_number": SEED_ACCOUNT_A, "pin": "0000"})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 401


def test_fr20_pin_change_requires_correct_old_pin():
    r = call("POST", f"/api/auth/customer/{SEED_ACCOUNT_A}/pin-change",
             {"old_pin": "9999", "new_pin": "5678"})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 401, "wrong old PIN must not allow a change"


def test_fr20_pin_change_takes_effect_immediately():
    new_pin = "99" + SEED_PIN          # e.g. 991234 - deterministic per run
    r = call("POST", f"/api/auth/customer/{SEED_ACCOUNT_A}/pin-change",
             {"old_pin": SEED_PIN, "new_pin": new_pin})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 200, r.text

    login_new = call("POST", "/api/auth/customer/login",
                     {"account_number": SEED_ACCOUNT_A, "pin": new_pin})
    skip_if_unimplemented(login_new, C4)
    assert login_new.status_code == 200, "new PIN must work immediately"

    # restore the default PIN so the rest of the suite is not affected
    call("POST", f"/api/auth/customer/{SEED_ACCOUNT_A}/pin-change",
         {"old_pin": new_pin, "new_pin": SEED_PIN})
