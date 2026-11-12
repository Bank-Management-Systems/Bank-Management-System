"""Candidate 1 - Account Management contract tests (FR-01, FR-02, FR-04, FR-05).

These are the integration-level acceptance cases corresponding to the unit /
integration / system cases of Chapter 4 in the Test Plan V2 document.
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


def test_fr01_create_account_success():
    r = call("POST", "/api/accounts", {
        "name": "Create Success", "address": "1 MG Road", "contact": "9876500001",
        "type": "Savings", "opening_deposit": 5000,
    })
    skip_if_unimplemented(r, C1)
    assert r.status_code in (200, 201), r.text
    body = r.json()
    assert int(body.get("account_number", 0)) >= 1001, "account numbers start at 1001"


def test_fr01_rejects_opening_deposit_below_minimum():
    r = call("POST", "/api/accounts", {
        "name": "Low Deposit", "address": "2 MG Road", "contact": "9876500002",
        "type": "Savings", "opening_deposit": 499,   # boundary: one below 500
    })
    skip_if_unimplemented(r, C1)
    assert r.status_code == 400, "deposit below Rs. 500 must be rejected"


def test_fr01_rejects_blank_name():
    r = call("POST", "/api/accounts", {
        "name": "", "address": "3 MG Road", "contact": "9876500003",
        "type": "Savings", "opening_deposit": 5000,
    })
    skip_if_unimplemented(r, C1)
    assert r.status_code == 400, "blank mandatory name must be rejected"


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

    # To close an account under FR-05, balance must be zero.
    # Set balance to 0 in DB to simulate full withdrawal/reconciliation.
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00 WHERE account_number = {acc_a};")

    close_res = call("POST", f"/api/accounts/{acc_a}/close")
    skip_if_unimplemented(close_res, C1)
    assert close_res.status_code == 200, close_res.text
    assert close_res.json().get("status") == "closed"

    # Create account B after account A has been closed
    acc_b, ok_b = make_account(name="Created After Close")
    assert ok_b, "Account B creation must succeed"

    # Assert account A's number is not reused and sequence increases monotonically
    assert acc_b > acc_a, "Account number must strictly increase; closed number must not be reused"
    assert acc_b != acc_a, f"Closed account number {acc_a} must never be reissued"

    # Confirm account A row was NOT deleted (no row deletion anywhere)
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


def test_fr04_modify_customer_details():
    acc, _ = make_account()
    r = call("PUT", f"/api/accounts/{acc}", {
        "address": "99 Updated Street", "contact": "9999900000",
    })
    skip_if_unimplemented(r, C1)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body.get("address") == "99 Updated Street"
    assert body.get("contact") == "9999900000"


def test_fr04_unknown_account_returns_404():
    r = call("PUT", "/api/accounts/999999", {"address": "nowhere", "contact": "0"})
    skip_if_unimplemented(r, C1)
    assert r.status_code == 404


def test_fr05_close_rejected_while_balance_above_zero():
    # Seeded account 1001 holds Rs. 5000 - closing must be refused.
    r = call("POST", f"/api/accounts/{SEED_ACCOUNT_A}/close")
    skip_if_unimplemented(r, C1)
    assert r.status_code == 400, "close must be refused while balance > 0"


def test_fr05_close_unknown_account_returns_404():
    r = call("POST", "/api/accounts/999999/close")
    skip_if_unimplemented(r, C1)
    assert r.status_code == 404


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
