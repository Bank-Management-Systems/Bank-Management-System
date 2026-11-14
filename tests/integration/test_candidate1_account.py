"""Candidate 1 - Account Management contract tests (FR-01, FR-02, FR-03, FR-04, FR-05, NFR-02).

These are the unit, integration, and system acceptance cases corresponding to
Chapter 4 in the Bank Management System Test Plan V2 document and sprint deliverables.
"""
import os
import signal
import subprocess
import time
import urllib.parse
import pytest
import requests

from config import call, skip_if_unimplemented, make_account, SEED_ACCOUNT_A, BASE_URL

C1 = "Candidate 1 (backend/candidate1_account)"


def _get_db_env():
    """Extract database connection credentials from environment or root .env file."""
    env_vars = {}
    env_path = os.path.join(os.path.dirname(__file__), "../../.env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env_vars[k.strip()] = v.strip().strip("'").strip('"')

    host = os.environ.get("DB_HOST", env_vars.get("DB_HOST", "127.0.0.1"))
    port = os.environ.get("DB_PORT", env_vars.get("DB_PORT", "3306"))
    user = os.environ.get("DB_USER", env_vars.get("DB_USER", "root"))
    password = os.environ.get("DB_PASS", env_vars.get("DB_PASS", "root"))
    dbname = os.environ.get("DB_NAME", env_vars.get("DB_NAME", "bank_db"))
    return host, port, user, password, dbname


def _run_mysql_query(sql):
    """Execute a raw SQL query or command via the mysql CLI."""
    host, port, user, password, dbname = _get_db_env()
    cmd = ["mysql", f"-h{host}", f"-P{port}", f"-u{user}", f"-p{password}", "-sN", "-e", sql, dbname]
    return subprocess.run(cmd, capture_output=True, text=True)


def _pid_is_running(pid):
    """Check whether a process with given PID is currently active."""
    try:
        os.kill(pid, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def _restart_server():
    """Restart the local backend/bank_server API server and wait for health check."""
    root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    server_bin = os.path.join(root_dir, "backend", "bank_server")
    if not os.path.exists(server_bin):
        pytest.skip("backend/bank_server binary not found for restart test")

    parsed = urllib.parse.urlparse(BASE_URL)
    if parsed.hostname not in ("localhost", "127.0.0.1", "0.0.0.0"):
        pytest.skip("Skipping restart test for non-local BASE_URL")

    # Locate current running PID
    target_pid = None
    for pid_path in ["/tmp/server.pid", "/tmp/bms_server.pid"]:
        if os.path.exists(pid_path):
            try:
                with open(pid_path) as f:
                    p = int(f.read().strip())
                    if _pid_is_running(p):
                        target_pid = p
                        break
            except Exception:
                pass

    if target_pid:
        try:
            os.kill(target_pid, signal.SIGTERM)
        except OSError:
            pass
    else:
        res = subprocess.run(["pgrep", "-f", "bank_server"], capture_output=True, text=True)
        for line in res.stdout.strip().split():
            if line.isdigit():
                p = int(line)
                if p != os.getpid():
                    try:
                        os.kill(p, signal.SIGTERM)
                    except OSError:
                        pass

    time.sleep(0.5)

    env = os.environ.copy()
    host, port, user, password, dbname = _get_db_env()
    env["DB_HOST"] = host
    env["DB_PORT"] = str(port)
    env["DB_USER"] = user
    env["DB_PASS"] = password
    env["DB_NAME"] = dbname
    if parsed.port:
        env["PORT"] = str(parsed.port)

    new_proc = subprocess.Popen(
        [server_bin],
        cwd=root_dir,
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    for pid_path in ["/tmp/server.pid", "/tmp/bms_server.pid"]:
        if os.path.exists(pid_path):
            try:
                with open(pid_path, "w") as f:
                    f.write(str(new_proc.pid))
            except Exception:
                pass

    healthy = False
    for _ in range(30):
        try:
            r = requests.get(f"{BASE_URL}/api/health", timeout=1)
            if r.status_code == 200:
                healthy = True
                break
        except Exception:
            pass
        time.sleep(0.2)

    assert healthy, "API server did not recover after restart"


# ============================================================================
# FR-01: Create New Bank Account (UT_01 - UT_03, IT_01 - IT_03, ST_01 - ST_02)
# ============================================================================

def test_fr01_create_account_success():
    """UT_01: Create a new account with all valid customer details and qualifying opening deposit."""
    r = call("POST", "/api/accounts", {
        "name": "Rahul Sharma", "address": "12 MG Road", "contact": "9876543210",
        "type": "Savings", "opening_deposit": 5000,
    })
    skip_if_unimplemented(r, C1)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    acc = int(body.get("account_number", 0))
    assert acc >= 1001, "account numbers start at 1001"
    assert float(body.get("balance", 0)) == 5000.0

    # Verify status through lookup
    chk = call("GET", f"/api/accounts/{acc}")
    assert chk.status_code == 200
    assert chk.json().get("status") == "active"


def test_fr01_rejects_blank_name():
    """UT_02: Reject account creation when mandatory name field is blank."""
    r = call("POST", "/api/accounts", {
        "name": "", "address": "12 MG Road", "contact": "9876543210",
        "type": "Savings", "opening_deposit": 5000,
    })
    skip_if_unimplemented(r, C1)
    assert r.status_code == 400, "blank mandatory name must be rejected"


def test_fr01_rejects_opening_deposit_below_minimum():
    """UT_03: Reject opening deposit below minimum required balance (Rs. 499)."""
    r = call("POST", "/api/accounts", {
        "name": "Low Deposit", "address": "2 MG Road", "contact": "9876500002",
        "type": "Savings", "opening_deposit": 499,   # boundary: one below 500
    })
    skip_if_unimplemented(r, C1)
    assert r.status_code == 400, "deposit below Rs. 500 must be rejected"


def test_it01_create_account_search_lookup():
    """IT_01: Newly created account is immediately retrievable through account search / lookup."""
    acc, ok = make_account(name="Search Retrieval User", address="77 Residency Way", contact="9876543211", opening_deposit=5200)
    assert ok, "Account creation failed"
    r = call("GET", f"/api/accounts/{acc}")
    assert r.status_code == 200
    body = r.json()
    assert body.get("name") == "Search Retrieval User"
    assert body.get("address") == "77 Residency Way"
    assert float(body.get("balance", 0)) == 5200.0


def test_it02_create_account_usable_for_deposit():
    """IT_02: Newly created account is immediately usable for a deposit transaction."""
    acc, ok = make_account(name="Deposit Trans User", opening_deposit=500)
    assert ok
    r_dep = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 1000})
    if r_dep.status_code != 501:
        assert r_dep.status_code == 200
        r_get = call("GET", f"/api/accounts/{acc}")
        assert r_get.status_code == 200
        assert float(r_get.json().get("balance", 0)) == 1500.0


def test_it03_create_account_persisted_to_db():
    """IT_03: Complete account record is written to the database after creation."""
    acc, ok = make_account(name="Priya Nair", address="5 Koramangala", contact="9876501234", type="Savings", opening_deposit=5000)
    assert ok
    sql = f"SELECT name, address, contact, type, balance, status FROM accounts WHERE account_number = {acc};"
    res = _run_mysql_query(sql)
    assert res.returncode == 0
    row = res.stdout.strip().split("\t")
    assert row[0] == "Priya Nair"
    assert row[1] == "5 Koramangala"
    assert row[2] == "9876501234"
    assert row[3] == "Savings"
    assert float(row[4]) == 5000.0
    assert row[5] == "active"


def test_st01_open_two_accounts_end_to_end():
    """ST_01: Staff opens two accounts end-to-end in one session; both are retrievable with correct balances."""
    acc_a, ok_a = make_account(name="Amit Verma", opening_deposit=6000)
    acc_b, ok_b = make_account(name="Sneha Iyer", opening_deposit=5000)
    assert ok_a and ok_b
    assert acc_b > acc_a

    r_a = call("GET", f"/api/accounts/{acc_a}")
    r_b = call("GET", f"/api/accounts/{acc_b}")
    assert r_a.status_code == 200 and r_b.status_code == 200
    assert r_a.json().get("name") == "Amit Verma" and float(r_a.json().get("balance", 0)) == 6000.0
    assert r_b.json().get("name") == "Sneha Iyer" and float(r_b.json().get("balance", 0)) == 5000.0


def test_st02_rejected_creations_leave_no_partial_records():
    """ST_02: Rejected creation attempts leave no partial or orphan records in the database."""
    res_before = _run_mysql_query("SELECT COUNT(*) FROM accounts;")
    count_before = int(res_before.stdout.strip()) if res_before.returncode == 0 and res_before.stdout.strip().isdigit() else 0

    # Attempt 1: blank name
    r1 = call("POST", "/api/accounts", {"name": "", "address": "12 MG Road", "contact": "9876543210", "type": "Savings", "opening_deposit": 5000})
    assert r1.status_code == 400

    # Attempt 2: deposit below minimum
    r2 = call("POST", "/api/accounts", {"name": "Test User", "address": "12 MG Road", "contact": "9876543210", "type": "Savings", "opening_deposit": 100})
    assert r2.status_code == 400

    # Attempt 3: valid account
    acc3, ok3 = make_account(name="Valid E2E User", opening_deposit=5000)
    assert ok3

    res_after = _run_mysql_query("SELECT COUNT(*) FROM accounts;")
    count_after = int(res_after.stdout.strip())
    assert count_after == count_before + 1, "Only the single valid account should exist in the database"


# ============================================================================
# FR-04: Modify Customer Details (UT_04 - UT_06, IT_04 - IT_06, ST_03 - ST_04)
# ============================================================================

def test_fr04_modify_customer_details():
    """UT_04 / UT_06: Update address and contact of an existing account."""
    acc, _ = make_account()
    r = call("PUT", f"/api/accounts/{acc}", {
        "address": "45 Brigade Towers", "contact": "9876599999",
    })
    skip_if_unimplemented(r, C1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("address") == "45 Brigade Towers"
    assert body.get("contact") == "9876599999"


def test_fr04_unknown_account_returns_404():
    """UT_05: Modify non-existent account returns 404."""
    r = call("PUT", "/api/accounts/999999", {"address": "nowhere", "contact": "9876543210"})
    skip_if_unimplemented(r, C1)
    assert r.status_code == 404


def test_it04_modify_persisted_to_db():
    """IT_04: Modified address and contact are persisted to the database."""
    acc, ok = make_account()
    assert ok
    r = call("PUT", f"/api/accounts/{acc}", {"address": "10 Downing Road", "contact": "9876543219"})
    assert r.status_code == 200
    res = _run_mysql_query(f"SELECT address, contact FROM accounts WHERE account_number = {acc};")
    assert res.returncode == 0
    parts = res.stdout.strip().split("\t")
    assert parts[0] == "10 Downing Road"
    assert parts[1] == "9876543219"


def test_it05_modify_leaves_balance_and_type_unchanged():
    """IT_05: Modification of contact/address leaves account balance and type unchanged."""
    acc, ok = make_account(opening_deposit=7500, type="Savings")
    assert ok
    r = call("PUT", f"/api/accounts/{acc}", {"address": "New House", "contact": "9123456780"})
    assert r.status_code == 200
    check = call("GET", f"/api/accounts/{acc}")
    assert check.status_code == 200
    assert float(check.json().get("balance", 0)) == 7500.0
    assert check.json().get("type") == "Savings"


def test_it06_modify_reflected_in_subsequent_lookup():
    """IT_06: Subsequent account lookup reflects the modified values."""
    acc, ok = make_account()
    assert ok
    call("PUT", f"/api/accounts/{acc}", {"address": "Fresh Lookup St", "contact": "9876543215"})
    r = call("GET", f"/api/accounts/{acc}")
    assert r.status_code == 200
    assert r.json().get("address") == "Fresh Lookup St"
    assert r.json().get("contact") == "9876543215"


def test_st03_modify_address_and_contact_end_to_end():
    """ST_03: End-to-end modify: staff updates address & contact, verifies search reflects new data."""
    acc, ok = make_account(name="Modify E2E User", address="Initial Address", contact="9876500000")
    assert ok
    r_put = call("PUT", f"/api/accounts/{acc}", {"address": "Updated Suite 300", "contact": "9876599999"})
    assert r_put.status_code == 200

    r_get = call("GET", f"/api/accounts/{acc}")
    assert r_get.status_code == 200
    assert r_get.json().get("address") == "Updated Suite 300"
    assert r_get.json().get("contact") == "9876599999"


def test_st04_invalid_modify_leaves_original_data_intact():
    """ST_04: Invalid modify attempts fail with 400 and leave the original record intact."""
    acc, ok = make_account(address="Safe Haven 1", contact="9876543210")
    assert ok

    # Attempt invalid contact with letters
    r_bad = call("PUT", f"/api/accounts/{acc}", {"address": "Invalid Place", "contact": "98765ABCDE"})
    assert r_bad.status_code == 400

    # Verify original details preserved
    r_check = call("GET", f"/api/accounts/{acc}")
    assert r_check.status_code == 200
    assert r_check.json().get("address") == "Safe Haven 1"
    assert r_check.json().get("contact") == "9876543210"


# ============================================================================
# FR-05: Close an Account (UT_07 - UT_09, IT_07 - IT_09, ST_05 - ST_06)
# ============================================================================

def test_fr05_close_rejected_while_balance_above_zero():
    """UT_08: Closure is blocked when the account still holds funds (> 0)."""
    acc, ok = make_account(opening_deposit=6000)
    assert ok
    r = call("POST", f"/api/accounts/{acc}/close")
    skip_if_unimplemented(r, C1)
    assert r.status_code == 400, "close must be refused while balance > 0"


def test_fr05_close_unknown_account_returns_404():
    """UT_09: Closure on unknown non-existent account returns 404."""
    r = call("POST", "/api/accounts/999999/close")
    skip_if_unimplemented(r, C1)
    assert r.status_code == 404


def test_ut07_close_zero_balance_account_success():
    """UT_07: Close zero-balance account successfully."""
    acc, ok = make_account(name="Zero Bal User", opening_deposit=500)
    assert ok
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00 WHERE account_number = {acc};")
    r = call("POST", f"/api/accounts/{acc}/close")
    skip_if_unimplemented(r, C1)
    assert r.status_code == 200
    assert r.json().get("status") == "closed"


def test_it07_closed_account_rejects_deposit():
    """IT_07: Closed account no longer accepts deposit transactions."""
    acc, ok = make_account()
    assert ok
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00 WHERE account_number = {acc};")
    r_close = call("POST", f"/api/accounts/{acc}/close")
    assert r_close.status_code == 200

    r_dep = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 500})
    if r_dep.status_code != 501:
        assert r_dep.status_code in (400, 403, 404), "Deposit into closed account must be rejected"


def test_it08_closure_recorded_in_db_no_row_deletion():
    """IT_08: Closure is recorded in the database and row is never deleted."""
    acc, ok = make_account()
    assert ok
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00 WHERE account_number = {acc};")
    r_close = call("POST", f"/api/accounts/{acc}/close")
    assert r_close.status_code == 200

    res = _run_mysql_query(f"SELECT status FROM accounts WHERE account_number = {acc};")
    assert res.returncode == 0
    assert res.stdout.strip() == "closed"


def test_it09_settle_balance_then_close_success():
    """IT_09: Settle balance to zero then close successfully."""
    acc, ok = make_account(opening_deposit=700)
    assert ok
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00 WHERE account_number = {acc};")
    r_close = call("POST", f"/api/accounts/{acc}/close")
    assert r_close.status_code == 200
    assert r_close.json().get("status") == "closed"


def test_st05_closed_account_enforced_in_search_and_lookup():
    """ST_05: End-to-end closure enforced: account shows status 'closed' in search and lookup."""
    acc, ok = make_account()
    assert ok
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00 WHERE account_number = {acc};")
    r_close = call("POST", f"/api/accounts/{acc}/close")
    assert r_close.status_code == 200

    r_lookup = call("GET", f"/api/accounts/{acc}")
    assert r_lookup.status_code == 200
    assert r_lookup.json().get("status") == "closed"


def test_st06_mixed_closure_attempts_maintain_consistency():
    """ST_06: Mixed closure attempts leave data fully consistent (active stays active, closed stays closed)."""
    acc_active, ok_a = make_account(opening_deposit=6000)
    acc_zero, ok_z = make_account(opening_deposit=500)
    assert ok_a and ok_z

    _run_mysql_query(f"UPDATE accounts SET balance = 0.00 WHERE account_number = {acc_zero};")

    # Attempt close on active (must fail)
    r_bad = call("POST", f"/api/accounts/{acc_active}/close")
    assert r_bad.status_code == 400

    # Close zero balance (must succeed)
    r_good = call("POST", f"/api/accounts/{acc_zero}/close")
    assert r_good.status_code == 200

    # Check both
    r1 = call("GET", f"/api/accounts/{acc_active}")
    assert r1.status_code == 200
    assert r1.json().get("status") == "active"
    assert float(r1.json().get("balance", 0)) == 6000.0

    r2 = call("GET", f"/api/accounts/{acc_zero}")
    assert r2.status_code == 200
    assert r2.json().get("status") == "closed"


# ============================================================================
# FR-02: Account Numbering & Continuity (Sprint Enhancement)
# ============================================================================

def test_fr02_account_numbers_strictly_increase():
    """FR-02: Account numbers are system-assigned and strictly increase."""
    acc1, ok1 = make_account(name="Strict Sequence 1")
    assert ok1, "First account creation must succeed"
    assert acc1 >= 1001, "Account numbers start at >= 1001"

    acc2, ok2 = make_account(name="Strict Sequence 2")
    assert ok2, "Second account creation must succeed"
    assert acc2 > acc1, "Subsequent account number must be strictly greater"
    assert acc2 == acc1 + 1, "Consecutive accounts must increment sequence by +1"


def test_fr02_client_supplied_account_number_ignored():
    """FR-02: A manually supplied account_number in the request body is ignored/overridden."""
    bogus_number = 99999
    r = call("POST", "/api/accounts", {
        "account_number": bogus_number,
        "name": "Client Override Ignored",
        "address": "42 Security Road",
        "contact": "9876500042",
        "type": "Savings",
        "opening_deposit": 5000,
    })
    skip_if_unimplemented(r, C1)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assigned = int(body.get("account_number", 0))
    assert assigned != bogus_number, "Client-supplied account_number must be ignored"
    assert assigned >= 1001, "System-assigned account number must follow sequence"

    # Confirm the bogus account number was never created
    check_bogus = call("GET", f"/api/accounts/{bogus_number}")
    assert check_bogus.status_code == 404, "Manually supplied account number must not exist"

    # Confirm the assigned account exists with correct details
    check_assigned = call("GET", f"/api/accounts/{assigned}")
    assert check_assigned.status_code == 200
    assert check_assigned.json().get("name") == "Client Override Ignored"


def test_fr02_create_close_create_no_reuse():
    """FR-02: Closed account numbers are never reissued; no row deletion occurs."""
    acc_a, ok_a = make_account(name="To Be Closed")
    assert ok_a, "Account A creation must succeed"

    _run_mysql_query(f"UPDATE accounts SET balance = 0.00 WHERE account_number = {acc_a};")

    close_res = call("POST", f"/api/accounts/{acc_a}/close")
    skip_if_unimplemented(close_res, C1)
    assert close_res.status_code == 200, close_res.text
    assert close_res.json().get("status") == "closed"

    # Create account B after account A has been closed
    acc_b, ok_b = make_account(name="Created After Close")
    assert ok_b, "Account B creation must succeed"

    assert acc_b > acc_a, "Account number must strictly increase; closed number must not be reused"
    assert acc_b != acc_a, f"Closed account number {acc_a} must never be reissued"

    acc_a_check = call("GET", f"/api/accounts/{acc_a}")
    assert acc_a_check.status_code == 200
    assert acc_a_check.json().get("status") == "closed"


def test_fr02_restart_continuity():
    """FR-02: Server restart does not reset or reuse the sequence."""
    acc_pre, ok_pre = make_account(name="Pre-Restart Continuity")
    assert ok_pre, "Pre-restart account creation must succeed"

    # Restart the server
    _restart_server()

    # Create account post-restart
    acc_post, ok_post = make_account(name="Post-Restart Continuity")
    assert ok_post, "Post-restart account creation must succeed"

    assert acc_post > acc_pre, "Post-restart account number must be strictly greater than pre-restart"
    assert acc_post == acc_pre + 1, "Post-restart account number must continue the consecutive sequence without gap"


# ============================================================================
# FR-03: Account Lookup Details & Freshness (Sprint Enhancement)
# ============================================================================

def test_fr03_get_account_details_success():
    """FR-03: Retrieve correct details for a known account (all expected fields present)."""
    acc, created = make_account(
        name="Lookup Target User",
        address="100 Inspection Boulevard",
        contact="9876500123",
        type="Savings",
        opening_deposit=5500,
    )
    assert created, "Account creation must succeed"

    r = call("GET", f"/api/accounts/{acc}")
    skip_if_unimplemented(r, C1)
    assert r.status_code == 200, r.text

    body = r.json()
    assert int(body.get("account_number", 0)) == acc
    assert body.get("name") == "Lookup Target User"
    assert body.get("address") == "100 Inspection Boulevard"
    assert body.get("contact") == "9876500123"
    assert body.get("type") == "Savings"
    assert body.get("status") == "active"
    assert float(body.get("balance", 0)) == 5500.0
    assert "created_at" in body or "opened_at" in body, "created_at/opened_at timestamp must be present"


def test_fr03_get_account_unknown_and_malformed_returns_404():
    """FR-03: Unknown account numbers and malformed account IDs return 404."""
    # Unknown non-existent account ID
    r_unknown = call("GET", "/api/accounts/999999")
    skip_if_unimplemented(r_unknown, C1)
    assert r_unknown.status_code == 404, f"Expected 404 for unknown account, got {r_unknown.status_code}"

    # Zero or invalid account ID
    r_zero = call("GET", "/api/accounts/0")
    skip_if_unimplemented(r_zero, C1)
    assert r_zero.status_code == 404, f"Expected 404 for zero account, got {r_zero.status_code}"

    # Malformed non-numeric account path
    r_malformed = call("GET", "/api/accounts/not_a_valid_number")
    skip_if_unimplemented(r_malformed, C1)
    assert r_malformed.status_code == 404, f"Expected 404 for malformed ID, got {r_malformed.status_code}"


def test_fr03_account_details_freshness_after_modify_deposit_close():
    """FR-03: Details change immediately after modify (FR-04), deposit (FR-08), and close (FR-05)."""
    acc, created = make_account(
        name="Freshness Tracking User",
        address="10 Old St",
        contact="9876543210",
        opening_deposit=5000,
    )
    assert created

    # Baseline check
    r0 = call("GET", f"/api/accounts/{acc}")
    assert r0.status_code == 200
    assert r0.json().get("address") == "10 Old St"
    assert float(r0.json().get("balance", 0)) == 5000.0
    assert r0.json().get("status") == "active"

    # 1. Freshness after Modify (FR-04): Address and contact updated
    r_mod = call("PUT", f"/api/accounts/{acc}", {
        "address": "20 New Fresh Ave",
        "contact": "9998887776",
    })
    assert r_mod.status_code == 200

    r1 = call("GET", f"/api/accounts/{acc}")
    assert r1.status_code == 200
    assert r1.json().get("address") == "20 New Fresh Ave", "Address must immediately reflect modified value"
    assert r1.json().get("contact") == "9998887776", "Contact must immediately reflect modified value"

    # 2. Freshness after Deposit (FR-08): Balance updated
    r_dep = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 2500})
    if r_dep.status_code != 501:
        assert r_dep.status_code == 200
        r2 = call("GET", f"/api/accounts/{acc}")
        assert r2.status_code == 200
        assert float(r2.json().get("balance", 0)) == 7500.0, "Balance must immediately reflect deposit"

    # 3. Freshness after Close (FR-05): Status updated to 'closed'
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00 WHERE account_number = {acc};")
    r_close = call("POST", f"/api/accounts/{acc}/close")
    assert r_close.status_code == 200
    assert r_close.json().get("status") == "closed"

    r3 = call("GET", f"/api/accounts/{acc}")
    assert r3.status_code == 200
    assert r3.json().get("status") == "closed", "Status must immediately reflect 'closed'"


# ============================================================================
# NFR-02: Input Validation & Server Robustness Sweep (NT_01 - NT_04)
# ============================================================================

def test_nfr02_malformed_json_and_empty_body():
    """NT_01: Malformed JSON, non-JSON text, and empty bodies return 400 (never 500/hang)."""
    headers = {"Content-Type": "application/json"}

    # 1. Empty body
    r1 = call("POST", "/api/accounts", body=None, data="", headers=headers)
    skip_if_unimplemented(r1, C1)
    assert r1.status_code == 400, f"Expected 400 for empty body, got {r1.status_code}"

    # 2. Plain text / non-JSON
    r2 = call("POST", "/api/accounts", body=None, data="not a json payload", headers=headers)
    skip_if_unimplemented(r2, C1)
    assert r2.status_code == 400, f"Expected 400 for plain text, got {r2.status_code}"

    # 3. Truncated / malformed JSON
    r3 = call("POST", "/api/accounts", body=None, data='{"name": "Broken', headers=headers)
    skip_if_unimplemented(r3, C1)
    assert r3.status_code == 400, f"Expected 400 for truncated JSON, got {r3.status_code}"


def test_nfr02_oversized_payload_and_string_fields():
    """NT_02: Oversized strings (> 100/200 chars, 10k chars) and control chars are rejected (clean 400)."""
    # 10,000-character name
    huge_name = "A" * 10000
    r1 = call("POST", "/api/accounts", {
        "name": huge_name,
        "address": "1 Valid St",
        "contact": "9876543210",
        "type": "Savings",
        "opening_deposit": 5000,
    })
    skip_if_unimplemented(r1, C1)
    assert r1.status_code == 400, f"Oversized name must be rejected with 400, got {r1.status_code}"

    # 10,000-character address
    huge_addr = "B" * 10000
    r2 = call("POST", "/api/accounts", {
        "name": "Normal Name",
        "address": huge_addr,
        "contact": "9876543210",
        "type": "Savings",
        "opening_deposit": 5000,
    })
    skip_if_unimplemented(r2, C1)
    assert r2.status_code == 400, f"Oversized address must be rejected with 400, got {r2.status_code}"

    # String with ASCII control characters
    bad_name = "Bad\x00Name\x07Alert"
    r3 = call("POST", "/api/accounts", {
        "name": bad_name,
        "address": "1 Valid St",
        "contact": "9876543210",
        "type": "Savings",
        "opening_deposit": 5000,
    })
    skip_if_unimplemented(r3, C1)
    assert r3.status_code == 400, f"Control characters must be rejected with 400, got {r3.status_code}"


def test_nfr02_alphabetic_and_unicode_in_numeric_fields():
    """NT_03: Alphabetic, special, or unicode characters in numeric fields are rejected."""
    # Alphabetic opening deposit
    r1 = call("POST", "/api/accounts", {
        "name": "Alpha Deposit",
        "address": "1 MG Road",
        "contact": "9876543210",
        "type": "Savings",
        "opening_deposit": "five-thousand",
    })
    skip_if_unimplemented(r1, C1)
    assert r1.status_code == 400, f"Alphabetic deposit must return 400, got {r1.status_code}"

    # Unicode currency symbol in deposit
    r2 = call("POST", "/api/accounts", {
        "name": "Unicode Deposit",
        "address": "1 MG Road",
        "contact": "9876543210",
        "type": "Savings",
        "opening_deposit": "₹5000",
    })
    skip_if_unimplemented(r2, C1)
    assert r2.status_code == 400, f"Unicode deposit must return 400, got {r2.status_code}"

    # Alphabetic characters in contact number
    r3 = call("POST", "/api/accounts", {
        "name": "Alpha Contact",
        "address": "1 MG Road",
        "contact": "98765ABCDE",
        "type": "Savings",
        "opening_deposit": 5000,
    })
    skip_if_unimplemented(r3, C1)
    assert r3.status_code == 400, f"Alphabetic contact must return 400, got {r3.status_code}"

    # Negative deposit
    r4 = call("POST", "/api/accounts", {
        "name": "Negative Deposit",
        "address": "1 MG Road",
        "contact": "9876543210",
        "type": "Savings",
        "opening_deposit": -500,
    })
    skip_if_unimplemented(r4, C1)
    assert r4.status_code == 400, f"Negative deposit must return 400, got {r4.status_code}"


def test_nfr02_robustness_sweep_and_recovery_integrity():
    """NT_04: Rapid mixed sequence of invalid requests does not crash server; valid request succeeds afterwards with intact DB."""
    # Capture initial database count
    res_before = _run_mysql_query("SELECT COUNT(*) FROM accounts;")
    count_before = int(res_before.stdout.strip()) if res_before.returncode == 0 and res_before.stdout.strip().isdigit() else None

    hostile_payloads = [
        {"name": "", "address": "foo", "contact": "1234567890", "opening_deposit": 5000},
        {"name": "X" * 500, "address": "foo", "contact": "1234567890", "opening_deposit": 5000},
        {"name": "Normal", "address": "X" * 500, "contact": "1234567890", "opening_deposit": 5000},
        {"name": "Normal", "address": "foo", "contact": "short", "opening_deposit": 5000},
        {"name": "Normal", "address": "foo", "contact": "1234567890", "type": "InvalidType", "opening_deposit": 5000},
        {"name": "Normal", "address": "foo", "contact": "1234567890", "opening_deposit": "abc"},
        {"name": "Normal", "address": "foo", "contact": "1234567890", "opening_deposit": 100},
        {"name": "Normal\x00Bad", "address": "foo", "contact": "1234567890", "opening_deposit": 5000},
    ]

    for p in hostile_payloads:
        r = call("POST", "/api/accounts", p)
        assert r.status_code == 400, f"Hostile payload {p} should return 400, got {r.status_code}"

    # Verify server is still alive and responsive: a valid create must succeed
    valid_acc, created = make_account(name="Recovery After Fuzz")
    assert created, "Server must remain responsive and valid creation must succeed after hostile burst"
    assert valid_acc >= 1001

    # Verify database was not corrupted: only exactly 1 new account was added
    if count_before is not None:
        res_after = _run_mysql_query("SELECT COUNT(*) FROM accounts;")
        count_after = int(res_after.stdout.strip())
        assert count_after == count_before + 1, "Database must not contain partial or corrupted rows from rejected requests"
