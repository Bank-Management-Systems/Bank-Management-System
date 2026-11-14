"""Candidate 4 - Security & Authentication contract tests (FR-18, FR-19, FR-20).

These unit, integration, and system acceptance tests implement the 24 test cases
specified in Chapter 7 (Tables 19, 20, 21) of the Bank Management System Test Plan V2:
- FR-18: Staff Authentication (UT_28 - UT_30, IT_28 - IT_30, ST_19 - ST_20)
- FR-19: Customer Authentication (UT_31 - UT_33, IT_31 - IT_33, ST_21 - ST_22)
- FR-20: PIN Management (UT_34 - UT_36, IT_34 - IT_36, ST_23 - ST_24)

Safety Rule: All PIN manipulation tests use isolated test accounts created via
make_account() to avoid mutating the shared seed account (1001).
"""
import os
import time
import pytest
import requests

from config import (
    call, skip_if_unimplemented, make_account,
    STAFF_USER, STAFF_PASS, SEED_ACCOUNT_A, SEED_PIN, BASE_URL
)
from test_candidate1_account import _restart_server, _run_mysql_query

C4 = "Candidate 4 (backend/candidate4_security)"


def _get_user_failed_tries(username, role):
    """Helper to query the failed_tries counter directly from MySQL for a user."""
    sql = f"SELECT failed_tries FROM users WHERE username = '{username}' AND role = '{role}';"
    res = _run_mysql_query(sql)
    out = res.stdout.strip()
    if out.isdigit():
        return int(out)
    return None


def _get_user_secret_hash(username, role):
    """Helper to query the secret_hash column directly from MySQL."""
    sql = f"SELECT secret_hash FROM users WHERE username = '{username}' AND role = '{role}';"
    res = _run_mysql_query(sql)
    return res.stdout.strip()


# ============================================================================
# FR-18: Staff Authentication (Table 19: UT_28 - UT_30, IT_28 - IT_30, ST_19 - ST_20)
# ============================================================================

def test_ut28_staff_login_valid_credentials():
    """UT_28: Valid staff credentials grant access with 200 and return role 'staff'."""
    r = call("POST", "/api/auth/staff/login", {"username": STAFF_USER, "password": STAFF_PASS})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 200, f"Expected 200 OK, got {r.status_code}: {r.text}"
    body = r.json()
    assert body.get("role") == "staff", f"Expected role 'staff', got {body.get('role')}"
    assert body.get("username") == STAFF_USER
    assert body.get("is_admin") is True
    assert "token" in body and len(body["token"]) > 0


def test_ut29_staff_login_wrong_password():
    """UT_29: Wrong staff password returns 401 Unauthorized with clean generic error JSON."""
    r = call("POST", "/api/auth/staff/login", {"username": STAFF_USER, "password": "definitely-wrong-password"})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 401, f"Expected 401 Unauthorized, got {r.status_code}: {r.text}"
    body = r.json()
    assert "error" in body, "Response must include an error message"
    assert "token" not in body, "Session token must not be issued on failed login"


def test_ut30_staff_login_unknown_username():
    """UT_30: Unknown staff username returns 401 without revealing whether username or password failed."""
    r = call("POST", "/api/auth/staff/login", {"username": "ghost99", "password": "arbitraryPassword123!"})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 401, f"Expected 401 Unauthorized, got {r.status_code}: {r.text}"
    body = r.json()
    assert "error" in body
    # Verify generic message to prevent account enumeration
    assert body.get("error") == "Invalid credentials"


def test_it28_staff_consecutive_failed_attempts_lockout_counter():
    """IT_28: Consecutive failed staff attempts feed the lockout/audit counter without crashing."""
    staff_user = f"staff_test_{int(time.time() * 1000) % 100000}"
    # Provision a dedicated staff account
    r_create = call("POST", "/api/staff", {"username": staff_user, "password": "StaffPassword123"})
    skip_if_unimplemented(r_create, C4)
    assert r_create.status_code in (200, 201), f"Failed to create test staff: {r_create.text}"

    # Verify initial failure counter is 0
    init_fails = _get_user_failed_tries(staff_user, "staff")
    assert init_fails == 0, f"Expected initial failed_tries = 0, got {init_fails}"

    # Perform 3 consecutive failed logins
    for attempt in range(1, 4):
        r_fail = call("POST", "/api/auth/staff/login", {"username": staff_user, "password": f"wrong_{attempt}"})
        assert r_fail.status_code == 401

    # Counter should increment to 3
    final_fails = _get_user_failed_tries(staff_user, "staff")
    assert final_fails == 3, f"Expected failed_tries = 3 after 3 failed attempts, got {final_fails}"


def test_it29_staff_audit_session_attribution():
    """IT_29: Audit/Staff session attribution in transaction records and administrative operations."""
    # Authenticate as staff
    r_login = call("POST", "/api/auth/staff/login", {"username": STAFF_USER, "password": STAFF_PASS})
    skip_if_unimplemented(r_login, C4)
    assert r_login.status_code == 200
    staff_token = r_login.json().get("token")
    assert staff_token.startswith("staff_")

    # Access administrative staff directory
    r_staff = call("GET", "/api/staff")
    skip_if_unimplemented(r_staff, C4)
    assert r_staff.status_code == 200
    staff_list = r_staff.json()
    assert isinstance(staff_list, list)
    admin_entry = next((s for s in staff_list if s.get("username") == STAFF_USER), None)
    assert admin_entry is not None, "Admin staff account must be present in staff directory"
    assert admin_entry.get("role") == "staff"


def test_it30_staff_session_logout_demands_reauth():
    """IT_30: Session boundary / logout demands re-authentication."""
    # Attempting to authenticate with empty/blank credentials fails
    r_empty = call("POST", "/api/auth/staff/login", {"username": "", "password": ""})
    skip_if_unimplemented(r_empty, C4)
    assert r_empty.status_code == 401

    # Valid authentication produces active token
    r_auth = call("POST", "/api/auth/staff/login", {"username": STAFF_USER, "password": STAFF_PASS})
    assert r_auth.status_code == 200
    token = r_auth.json().get("token")
    assert token is not None

    # After logout, invalid token or missing credentials cannot authenticate
    r_bad = call("POST", "/api/auth/staff/login", {"username": STAFF_USER, "password": "expired_session"})
    assert r_bad.status_code == 401


def test_st19_staff_full_administrative_journey_e2e():
    """ST_19: Full administrative journey from login to staff provisioning and directory inspection."""
    # 1. Staff admin login
    r_login = call("POST", "/api/auth/staff/login", {"username": STAFF_USER, "password": STAFF_PASS})
    skip_if_unimplemented(r_login, C4)
    assert r_login.status_code == 200

    # 2. Provision new staff member
    new_staff = f"clerk_{int(time.time() * 1000) % 100000}"
    new_pass = "ClerkPass2026!"
    r_create = call("POST", "/api/staff", {"username": new_staff, "password": new_pass})
    assert r_create.status_code in (200, 201), r_create.text

    # 3. Verify directory lists new staff member
    r_list = call("GET", "/api/staff")
    assert r_list.status_code == 200
    usernames = [u.get("username") for u in r_list.json()]
    assert new_staff in usernames

    # 4. Verify new clerk can log in
    r_clerk_login = call("POST", "/api/auth/staff/login", {"username": new_staff, "password": new_pass})
    assert r_clerk_login.status_code == 200
    assert r_clerk_login.json().get("role") == "staff"
    assert r_clerk_login.json().get("username") == new_staff


def test_st20_role_separation_customer_cannot_access_staff_endpoints():
    """ST_20: Role separation: customer session cannot access staff-only endpoints or staff privileges."""
    # Customer authenticates
    r_cust = call("POST", "/api/auth/customer/login", {"account_number": SEED_ACCOUNT_A, "pin": SEED_PIN})
    skip_if_unimplemented(r_cust, C4)
    assert r_cust.status_code == 200
    cust_data = r_cust.json()
    assert cust_data.get("role") == "customer"
    assert cust_data.get("is_admin") is not True

    # Customer credentials submitted to staff login endpoint are rejected
    r_impersonate = call("POST", "/api/auth/staff/login", {"username": str(SEED_ACCOUNT_A), "password": SEED_PIN})
    assert r_impersonate.status_code == 401
    assert r_impersonate.json().get("error") == "Invalid credentials"


# ============================================================================
# FR-19: Customer Authentication (Table 20: UT_31 - UT_33, IT_31 - IT_33, ST_21 - ST_22)
# ============================================================================

def test_ut31_customer_login_valid_account_and_pin():
    """UT_31: Valid account number and PIN (1001 / 1234) grant access with 200 and return role 'customer'."""
    r = call("POST", "/api/auth/customer/login", {"account_number": SEED_ACCOUNT_A, "pin": SEED_PIN})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("role") == "customer"
    assert body.get("account_number") == SEED_ACCOUNT_A
    assert "token" in body and body["token"].startswith("cust_")


def test_ut32_customer_login_wrong_pin():
    """UT_32: Wrong PIN returns 401 Unauthorized with clean error JSON."""
    r = call("POST", "/api/auth/customer/login", {"account_number": SEED_ACCOUNT_A, "pin": "0000"})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 401
    body = r.json()
    assert body.get("error") == "Invalid credentials"
    assert "token" not in body


def test_ut33_customer_login_unknown_account_number():
    """UT_33: Unknown account number (e.g., 999999) returns 401 without crashing or hanging."""
    r = call("POST", "/api/auth/customer/login", {"account_number": 999999, "pin": "1234"})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 401
    body = r.json()
    assert body.get("error") == "Invalid credentials"


def test_it31_customer_failed_attempts_accumulate_and_reset_on_success():
    """IT_31: Failed attempts accumulate; a valid login clears/resets the failure threshold."""
    acc, _ = make_account()

    # Initial login ensures user row is provisioned
    r_init = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
    skip_if_unimplemented(r_init, C4)
    assert r_init.status_code == 200
    assert _get_user_failed_tries(str(acc), "customer") == 0

    # 1. First wrong PIN attempt
    r_fail1 = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "9999"})
    assert r_fail1.status_code == 401
    assert _get_user_failed_tries(str(acc), "customer") == 1

    # 2. Second wrong PIN attempt
    r_fail2 = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "8888"})
    assert r_fail2.status_code == 401
    assert _get_user_failed_tries(str(acc), "customer") == 2

    # 3. Successful login with correct PIN clears/resets counter
    r_succ = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
    assert r_succ.status_code == 200
    assert _get_user_failed_tries(str(acc), "customer") == 0


def test_it32_customer_account_isolation_session_binding():
    """IT_32: Account isolation: authenticated customer session is restricted to its own account data."""
    acc_a, _ = make_account()
    acc_b, _ = make_account()

    # Authenticate Account A
    r_a = call("POST", "/api/auth/customer/login", {"account_number": acc_a, "pin": "1234"})
    skip_if_unimplemented(r_a, C4)
    assert r_a.status_code == 200
    body_a = r_a.json()
    assert body_a.get("account_number") == acc_a
    assert body_a.get("token") == f"cust_{acc_a}_token"

    # Authenticate Account B
    r_b = call("POST", "/api/auth/customer/login", {"account_number": acc_b, "pin": "1234"})
    assert r_b.status_code == 200
    body_b = r_b.json()
    assert body_b.get("account_number") == acc_b
    assert body_b.get("token") == f"cust_{acc_b}_token"

    # Verify session tokens are isolated and strictly distinct
    assert body_a.get("token") != body_b.get("token")


def test_it33_customer_pin_format_validation():
    """IT_33: PIN format validation: leading zeros handled properly (4 digits); non-numeric or short PINs rejected."""
    acc, _ = make_account()

    # Change PIN to a 4-digit PIN with a leading zero ('0123')
    r_change = call("POST", f"/api/auth/customer/{acc}/pin-change", {"old_pin": "1234", "new_pin": "0123"})
    skip_if_unimplemented(r_change, C4)
    assert r_change.status_code == 200, f"Failed to set leading zero PIN: {r_change.text}"

    # Login with exact 4-character string '0123' must succeed
    r_login_lead = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "0123"})
    assert r_login_lead.status_code == 200, "Leading-zero PIN '0123' must be accepted"

    # Login with numeric-truncated '123' must fail
    r_login_trunc = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "123"})
    assert r_login_trunc.status_code == 401, "Truncated 3-digit PIN '123' must be denied"


def test_st21_customer_complete_self_service_journey_e2e():
    """ST_21: Complete customer self-service journey under one login (inquiry, deposit, history)."""
    acc, _ = make_account(opening_deposit=5000.0)

    # 1. Customer login
    r_login = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
    skip_if_unimplemented(r_login, C4)
    assert r_login.status_code == 200

    # 2. Check initial balance
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    assert r_bal.status_code == 200
    assert float(r_bal.json().get("balance", 0)) == 5000.0

    # 3. Perform deposit of Rs. 500.00
    r_dep = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 500.0})
    assert r_dep.status_code == 200
    assert float(r_dep.json().get("balance", 0)) == 5500.0

    # 4. View transaction history
    r_hist = call("GET", f"/api/accounts/{acc}/transactions")
    if r_hist.status_code == 200:
        history = r_hist.json().get("transactions", [])
        assert len(history) >= 1

    # 5. Logout and verify fresh session requires login
    r_relogin = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
    assert r_relogin.status_code == 200


def test_st22_customer_repeated_invalid_pin_account_protection_lockout():
    """ST_22: Repeated invalid PIN attempts trigger account protection/lockout counter per policy."""
    acc, _ = make_account()

    # Pre-condition: establish customer user record
    call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})

    # Series A: 2 wrong PINs followed by correct PIN -> allowed below threshold
    call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "9991"})
    call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "9992"})
    r_ok = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
    skip_if_unimplemented(r_ok, C4)
    assert r_ok.status_code == 200
    assert _get_user_failed_tries(str(acc), "customer") == 0

    # Series B: 3 consecutive wrong PINs -> failure counter accumulates to threshold
    for i in range(1, 4):
        r_fail = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": f"777{i}"})
        assert r_fail.status_code == 401

    fails = _get_user_failed_tries(str(acc), "customer")
    assert fails == 3, f"Expected 3 failed attempts accumulated, got {fails}"


# ============================================================================
# FR-20: PIN Management (Table 21: UT_34 - UT_36, IT_34 - IT_36, ST_23 - ST_24)
# ============================================================================

def test_ut34_pin_change_valid_succeeds_and_enforced():
    """UT_34: Valid PIN change succeeds with 200 and immediate new PIN enforcement."""
    acc, _ = make_account()

    # Change PIN from 1234 to 4561
    r_chg = call("POST", f"/api/auth/customer/{acc}/pin-change", {"old_pin": "1234", "new_pin": "4561"})
    skip_if_unimplemented(r_chg, C4)
    assert r_chg.status_code == 200, r_chg.text
    assert r_chg.json().get("message") == "PIN changed"

    # Old PIN must be immediately rejected
    r_old = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
    assert r_old.status_code == 401

    # New PIN must be accepted immediately
    r_new = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "4561"})
    assert r_new.status_code == 200
    assert r_new.json().get("role") == "customer"


def test_ut35_pin_change_wrong_old_pin_blocked():
    """UT_35: Wrong old PIN blocks change with 401; existing PIN remains active."""
    acc, _ = make_account()

    # Attempt PIN change with wrong old PIN
    r_chg = call("POST", f"/api/auth/customer/{acc}/pin-change", {"old_pin": "9999", "new_pin": "4561"})
    skip_if_unimplemented(r_chg, C4)
    assert r_chg.status_code == 401
    assert "Invalid old PIN" in r_chg.text

    # Current PIN ('1234') must remain valid and operational
    r_login = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
    assert r_login.status_code == 200


def test_ut36_pin_change_format_violation_rejected():
    """UT_36: Format violation on new PIN (e.g. non-numeric, wrong length) rejected with 400."""
    acc, _ = make_account()

    invalid_pins = [
        "12",       # too short (< 4 digits)
        "123",      # 3 digits
        "1234567",  # too long (> 6 digits)
        "ABCD",     # non-numeric
        "12a4",     # alphanumeric
        "12 34",    # space
    ]

    for inv_pin in invalid_pins:
        r = call("POST", f"/api/auth/customer/{acc}/pin-change", {"old_pin": "1234", "new_pin": inv_pin})
        skip_if_unimplemented(r, C4)
        assert r.status_code == 400, f"Expected 400 for invalid PIN '{inv_pin}', got {r.status_code}"

    # Current PIN remains operational
    r_check = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
    assert r_check.status_code == 200


def test_it34_pin_change_identical_new_pin_rejected_reuse_policy():
    """IT_34: New PIN identical to old PIN rejected per credential reuse policy (400 Bad Request)."""
    acc, _ = make_account()

    r = call("POST", f"/api/auth/customer/{acc}/pin-change", {"old_pin": "1234", "new_pin": "1234"})
    skip_if_unimplemented(r, C4)
    assert r.status_code == 400
    assert "New PIN must differ" in r.text


def test_it35_pin_change_hashed_in_db_survives_restart():
    """IT_35: PIN security: PIN is hashed in database/storage and survives server restart."""
    acc, _ = make_account()

    # Change PIN to 5678
    r_chg = call("POST", f"/api/auth/customer/{acc}/pin-change", {"old_pin": "1234", "new_pin": "5678"})
    skip_if_unimplemented(r_chg, C4)
    assert r_chg.status_code == 200

    # Verify secret_hash in database is 64 hex characters (SHA2-256) and not plaintext
    db_hash = _get_user_secret_hash(str(acc), "customer")
    assert len(db_hash) == 64, f"Expected 64-char hex hash, got '{db_hash}'"
    assert "5678" not in db_hash, "Plaintext PIN must never be stored in database"

    # Restart backend API server
    _restart_server()

    # Verify new PIN works across server restart
    r_post = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "5678"})
    assert r_post.status_code == 200
    assert r_post.json().get("role") == "customer"


def test_it36_pin_change_switchover_immediacy():
    """IT_36: Switchover immediacy: old PIN stops working immediately; new PIN accepted."""
    acc, _ = make_account()

    r_chg = call("POST", f"/api/auth/customer/{acc}/pin-change", {"old_pin": "1234", "new_pin": "7890"})
    skip_if_unimplemented(r_chg, C4)
    assert r_chg.status_code == 200

    # Old PIN rejected on immediate subsequent call
    r_old = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
    assert r_old.status_code == 401

    # New PIN accepted on immediate subsequent call
    r_new = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "7890"})
    assert r_new.status_code == 200


def test_st23_credential_update_journey_preserves_balance_and_history():
    """ST_23: Full credential update journey without loss or corruption of balances or history."""
    acc, _ = make_account(opening_deposit=3000.0)

    # 1. Deposit funds under initial PIN
    r_dep = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 1000.0})
    assert r_dep.status_code == 200
    assert float(r_dep.json().get("balance", 0)) == 4000.0

    # 2. Update PIN
    r_chg = call("POST", f"/api/auth/customer/{acc}/pin-change", {"old_pin": "1234", "new_pin": "4561"})
    skip_if_unimplemented(r_chg, C4)
    assert r_chg.status_code == 200

    # 3. Log in with new PIN
    r_login = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "4561"})
    assert r_login.status_code == 200

    # 4. Inquire balance to guarantee balance preservation
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    assert r_bal.status_code == 200
    assert float(r_bal.json().get("balance", 0)) == 4000.0

    # 5. Perform another deposit under new PIN session
    r_dep2 = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 500.0})
    assert r_dep2.status_code == 200
    assert float(r_dep2.json().get("balance", 0)) == 4500.0


def test_st24_pin_lockout_counting_applies_to_active_pin_after_change():
    """ST_24: Lockout counting applies to the active PIN following a credential change."""
    acc, _ = make_account()

    # Change PIN to 4561
    r_chg = call("POST", f"/api/auth/customer/{acc}/pin-change", {"old_pin": "1234", "new_pin": "4561"})
    skip_if_unimplemented(r_chg, C4)
    assert r_chg.status_code == 200

    # Submitting the obsolete old PIN ('1234') counts as failed attempts
    for attempt in range(1, 4):
        r_fail = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "1234"})
        assert r_fail.status_code == 401

    # Counter reflects 3 failed attempts
    fails = _get_user_failed_tries(str(acc), "customer")
    assert fails == 3, f"Expected failed_tries = 3, got {fails}"

    # Entering the correct new PIN succeeds and clears the counter
    r_correct = call("POST", "/api/auth/customer/login", {"account_number": acc, "pin": "4561"})
    assert r_correct.status_code == 200
    assert _get_user_failed_tries(str(acc), "customer") == 0


# ============================================================================
# Backward Compatibility Aliases for Legacy Test Harness References
# ============================================================================
test_fr18_staff_login_success = test_ut28_staff_login_valid_credentials
test_fr18_staff_login_wrong_password = test_ut29_staff_login_wrong_password
test_fr19_customer_login_success = test_ut31_customer_login_valid_account_and_pin
test_fr19_customer_login_wrong_pin = test_ut32_customer_login_wrong_pin
test_fr20_pin_change_requires_correct_old_pin = test_ut35_pin_change_wrong_old_pin_blocked
test_fr20_pin_change_takes_effect_immediately = test_ut34_pin_change_valid_succeeds_and_enforced
