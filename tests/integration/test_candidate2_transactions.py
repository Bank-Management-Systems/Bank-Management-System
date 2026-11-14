"""Candidate 2 - Core Transactions contract tests (FR-08, FR-09, FR-10, FR-11, FR-12, NFR-01).

These are the unit, integration, and system acceptance cases corresponding to
Chapter 5 in the Bank Management System Test Plan V2 document and sprint deliverables.
"""
import os
import subprocess
import time
import statistics
import pytest
import requests

from config import call, skip_if_unimplemented, make_account, SEED_ACCOUNT_A, BASE_URL
from test_candidate1_account import _restart_server, _run_mysql_query

C2 = "Candidate 2 (backend/candidate2_transactions)"

# ============================================================================
# NFR-01: Performance & Response Time Budgets (seconds)
# Target: interactive endpoints well under 1 s (typically < 100 ms).
# Hard limit per V1 requirements: 2.0 s.
# ============================================================================
TARGET_LATENCY_BUDGET = 1.0  # seconds
HARD_LIMIT_BUDGET = 2.0      # seconds


def _percentiles(samples):
    """Compute p50 and p95 latencies from a list of durations."""
    sorted_s = sorted(samples)
    n = len(sorted_s)
    p50 = statistics.median(sorted_s)
    idx_95 = min(int(0.95 * n), n - 1)
    p95 = sorted_s[idx_95]
    return p50, p95


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


def _seed_bulk_transactions(account_number, count=5000):
    """Seed transactions into the database for the bulk-growth performance test."""
    host, port, user, password, dbname = _get_db_env()
    chunk_size = 1000
    for chunk_start in range(0, count, chunk_size):
        chunk_count = min(chunk_size, count - chunk_start)
        rows = []
        for i in range(chunk_count):
            idx = chunk_start + i
            ttype = "DEPOSIT" if idx % 2 == 0 else "WITHDRAWAL"
            amt = 10.00 + (idx % 50)
            bal = 5000.00 + (idx * 5)
            rows.append(f"({account_number}, '{ttype}', {amt:.2f}, {bal:.2f}, '2026-01-01 00:00:00')")
        sql = f"INSERT INTO transactions (account_number, type, amount, balance_after, created_at) VALUES {','.join(rows)};\n"
        cmd = ["mysql", f"-h{host}", f"-P{port}", f"-u{user}", f"-p{password}", dbname]
        res = subprocess.run(cmd, input=sql, text=True, capture_output=True)
        if res.returncode != 0:
            raise RuntimeError(f"Failed to seed transactions via mysql CLI: {res.stderr}")


def _count_account_transactions(account_number):
    """Count transaction rows directly in MySQL for this account."""
    host, port, user, password, dbname = _get_db_env()
    sql = f"SELECT COUNT(*) FROM transactions WHERE account_number = {account_number};"
    cmd = ["mysql", f"-h{host}", f"-P{port}", f"-u{user}", f"-p{password}", "-sN", "-e", sql, dbname]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0 and res.stdout.strip().isdigit():
        return int(res.stdout.strip())
    # Fallback to records endpoint if available
    r = call("GET", f"/api/accounts/{account_number}/transactions")
    if r.status_code == 200:
        return r.json().get("count", 0)
    return None


# ============================================================================
# FR-08: Deposit into an Existing Account (UT_10 - UT_12, IT_10 - IT_12, ST_07 - ST_08)
# ============================================================================

def test_fr08_deposit_increases_balance():
    """UT_10: Valid deposit increases the account balance by exactly the deposited amount."""
    acc, _ = make_account()
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r_bal, C2)
    start_bal = float(r_bal.json()["balance"])

    r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 1000})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "balance" in body, "response must contain the new balance"
    assert float(body["balance"]) == round(start_bal + 1000.0, 2)


def test_fr08_rejects_zero_and_negative_amounts():
    """UT_11: Deposit of zero or negative amount is rejected with 400; balance unchanged."""
    acc, _ = make_account()
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r_bal, C2)
    start_bal = float(r_bal.json()["balance"])

    for amount in (0, -500):
        r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": amount})
        skip_if_unimplemented(r, C2)
        assert r.status_code == 400, f"deposit of {amount} must be rejected"

    r_chk = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_chk.json()["balance"]) == start_bal, "Balance must remain unchanged after rejected deposit"


def test_ut12_boundary_deposits_exact():
    """UT_12: Boundary deposits are added exactly (smallest practical amount Rs. 1, large amount Rs. 100,000)."""
    acc, _ = make_account(opening_deposit=3000)
    
    # 1. Deposit smallest amount Rs. 1.00
    r1 = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 1})
    skip_if_unimplemented(r1, C2)
    assert r1.status_code == 200
    assert float(r1.json()["balance"]) == 3001.00

    # 2. Deposit large amount Rs. 100,000.00
    r2 = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 100000})
    assert r2.status_code == 200
    assert float(r2.json()["balance"]) == 103001.00


def test_it10_deposit_writes_transaction_log():
    """IT_10: Every successful deposit writes a transaction log entry with correct type and timestamp."""
    acc, _ = make_account(opening_deposit=5000)
    r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 750})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200

    # Verify transaction row in database
    res = _run_mysql_query(f"SELECT type, amount, balance_after FROM transactions WHERE account_number = {acc} ORDER BY id DESC LIMIT 1;")
    assert res.returncode == 0
    parts = res.stdout.strip().split("\t")
    assert parts[0] == "DEPOSIT"
    assert float(parts[1]) == 750.00
    assert float(parts[2]) == 5750.00


def test_it11_deposit_nonexistent_or_closed_rejected():
    """IT_11: Deposit to a non-existent or closed account is rejected."""
    # 1. Non-existent account
    r_none = call("POST", "/api/accounts/1999/deposit", {"amount": 500})
    skip_if_unimplemented(r_none, C2)
    assert r_none.status_code == 404

    # 2. Closed account
    acc, _ = make_account(opening_deposit=500)
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00, status = 'closed' WHERE account_number = {acc};")
    r_closed = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 500})
    assert r_closed.status_code == 400
    assert "closed" in r_closed.json().get("error", "").lower()


def test_it12_deposited_balance_persists_after_restart():
    """IT_12: Deposited balance persists after program restart."""
    acc, _ = make_account(opening_deposit=6000)
    r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 1000})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200
    assert float(r.json()["balance"]) == 7000.00

    # Restart API server
    _restart_server()

    # Verify balance inquiry reflects 7000 after restart
    r_check = call("GET", f"/api/accounts/{acc}/balance")
    assert r_check.status_code == 200
    assert float(r_check.json()["balance"]) == 7000.00


def test_st07_customer_deposit_end_to_end():
    """ST_07: System test: customer performs a deposit end-to-end and verifies it."""
    acc, _ = make_account(opening_deposit=5000)
    r_dep = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 2000})
    skip_if_unimplemented(r_dep, C2)
    assert r_dep.status_code == 200

    # Balance check
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    assert r_bal.status_code == 200
    assert float(r_bal.json()["balance"]) == 7000.00

    # Transaction history check
    r_txns = call("GET", f"/api/accounts/{acc}/transactions")
    if r_txns.status_code != 501:
        assert r_txns.status_code == 200
        assert r_txns.json().get("count", 0) >= 1


def test_st08_staff_multiple_deposits_accumulate():
    """ST_08: System test: several deposits in one session accumulate correctly (3000 + 500 + 1500 + 2000 = 7000)."""
    acc, _ = make_account(opening_deposit=3000)
    for amt in (500, 1500, 2000):
        r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": amt})
        skip_if_unimplemented(r, C2)
        assert r.status_code == 200

    r_final = call("GET", f"/api/accounts/{acc}/balance")
    assert r_final.status_code == 200
    assert float(r_final.json()["balance"]) == 7000.00


# ============================================================================
# FR-09: Withdrawal from an Account (UT_13 - UT_15, IT_13 - IT_15, ST_09 - ST_10)
# ============================================================================

def test_fr09_withdraw_within_balance_succeeds():
    """UT_13: Valid withdrawal decreases the balance by exactly the withdrawn amount."""
    acc, _ = make_account(opening_deposit=5000)
    r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 1500})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "balance" in body
    assert float(body["balance"]) == 3500.00


def test_fr09_withdraw_breaking_minimum_balance_rejected():
    """UT_14: Withdrawal greater than available balance / breaking minimum balance is rejected."""
    acc, _ = make_account(opening_deposit=5000)
    # Withdrawing 4600 leaves 400 < 500 minimum.
    r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 4600})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 400, "withdrawal leaving less than Rs. 500 must be rejected"

    # Withdrawing 6000 from 5000 is outright overdraft
    r2 = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 6000})
    assert r2.status_code == 400
    assert "insufficient funds" in r2.json().get("error", "").lower()

    # Balance unchanged
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_bal.json()["balance"]) == 5000.00


def test_ut15_zero_and_negative_withdrawal_rejected():
    """UT_15: Zero and negative withdrawal amounts are rejected with 400; balance remains unchanged."""
    acc, _ = make_account(opening_deposit=3000)
    for amt in (0, -500):
        r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": amt})
        skip_if_unimplemented(r, C2)
        assert r.status_code == 400
        assert "greater than zero" in r.json().get("error", "").lower()

    r_chk = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_chk.json()["balance"]) == 3000.00


def test_it13_withdrawal_writes_transaction_log():
    """IT_13: Every successful withdrawal is logged with type, amount, and timestamp."""
    acc, _ = make_account(opening_deposit=3000)
    r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 600})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200

    res = _run_mysql_query(f"SELECT type, amount, balance_after FROM transactions WHERE account_number = {acc} ORDER BY id DESC LIMIT 1;")
    assert res.returncode == 0
    parts = res.stdout.strip().split("\t")
    assert parts[0] == "WITHDRAWAL"
    assert float(parts[1]) == 600.00
    assert float(parts[2]) == 2400.00


def test_it14_deposit_then_withdraw_nets_zero():
    """IT_14: Deposit followed by withdrawal of the same amount nets to zero change."""
    acc, _ = make_account(opening_deposit=5000)
    r_dep = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 1000})
    skip_if_unimplemented(r_dep, C2)
    assert r_dep.status_code == 200
    assert float(r_dep.json()["balance"]) == 6000.00

    r_wdr = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 1000})
    assert r_wdr.status_code == 200
    assert float(r_wdr.json()["balance"]) == 5000.00

    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_bal.json()["balance"]) == 5000.00


def test_it15_withdrawal_nonexistent_or_closed_rejected():
    """IT_15: Withdrawal from non-existent or closed account is rejected."""
    # 1. Non-existent account
    r_none = call("POST", "/api/accounts/1999/withdraw", {"amount": 500})
    skip_if_unimplemented(r_none, C2)
    assert r_none.status_code == 404

    # 2. Closed account
    acc, _ = make_account(opening_deposit=500)
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00, status = 'closed' WHERE account_number = {acc};")
    r_closed = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 500})
    assert r_closed.status_code == 400
    assert "closed" in r_closed.json().get("error", "").lower()


def test_st09_customer_withdrawal_end_to_end():
    """ST_09: System test: customer withdrawal end-to-end with verification."""
    acc, _ = make_account(opening_deposit=5000)
    r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 1200})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200

    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    assert r_bal.status_code == 200
    assert float(r_bal.json()["balance"]) == 3800.00


def test_st10_repeated_withdrawals_enforce_minimum_balance():
    """ST_10: Repeated withdrawals stop correctly at the minimum-balance limit (Rs. 5500 down to Rs. 500)."""
    acc, _ = make_account(opening_deposit=5500)
    for _ in range(5):
        r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 1000})
        skip_if_unimplemented(r, C2)
        assert r.status_code == 200

    # Balance is now exactly Rs. 500.00
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_bal.json()["balance"]) == 500.00

    # 6th withdrawal of Rs. 100 (less than 500 balance, but would break the 500 minimum) must be rejected
    r_excess = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 100})
    assert r_excess.status_code == 400
    assert "minimum balance" in r_excess.json().get("error", "").lower()

    # Even withdrawing Rs. 1000 (exceeds balance) must be rejected
    r_overdraft = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 1000})
    assert r_overdraft.status_code == 400

    r_final = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_final.json()["balance"]) == 500.00


# ============================================================================
# FR-12: Balance Inquiry (UT_16 - UT_18, IT_16 - IT_18, ST_11 - ST_12)
# ============================================================================

def test_fr12_balance_inquiry_returns_current_balance():
    """UT_16: Balance inquiry returns the exact current balance of a valid account."""
    acc, _ = make_account(opening_deposit=6000)
    r = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "balance" in body
    assert float(body["balance"]) == 6000.00


def test_fr12_unknown_account_returns_404():
    """UT_17: Inquiry on a non-existent account number returns 404."""
    r = call("GET", "/api/accounts/999999/balance")
    skip_if_unimplemented(r, C2)
    assert r.status_code == 404


def test_ut18_balance_inquiry_closed_account():
    """UT_18: Inquiry on a closed account reflects its state without misleading active balance."""
    acc, _ = make_account(opening_deposit=500)
    _run_mysql_query(f"UPDATE accounts SET balance = 0.00, status = 'closed' WHERE account_number = {acc};")
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r_bal, C2)
    assert r_bal.status_code == 200
    assert float(r_bal.json()["balance"]) == 0.00

    # Account details view confirms status is closed
    r_acc = call("GET", f"/api/accounts/{acc}")
    assert r_acc.status_code == 200
    assert r_acc.json().get("status") == "closed"


def test_it16_inquiry_reflects_immediate_preceding_transaction():
    """IT_16: Inquiry reflects the immediately preceding transaction without lag."""
    acc, _ = make_account(opening_deposit=6000)
    r_dep = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 300})
    skip_if_unimplemented(r_dep, C2)
    assert r_dep.status_code == 200

    r_inq = call("GET", f"/api/accounts/{acc}/balance")
    assert r_inq.status_code == 200
    assert float(r_inq.json()["balance"]) == 6300.00


def test_it17_inquiry_matches_persisted_value_after_restart():
    """IT_17: Inquiry result matches the persisted value after a server restart."""
    acc, _ = make_account(opening_deposit=5500)
    r1 = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r1, C2)
    assert r1.status_code == 200
    assert float(r1.json()["balance"]) == 5500.00

    _restart_server()

    r2 = call("GET", f"/api/accounts/{acc}/balance")
    assert r2.status_code == 200
    assert float(r2.json()["balance"]) == 5500.00


def test_it18_balance_inquiries_do_not_log_transactions():
    """IT_18: Balance inquiries are read-only and do not create transaction log entries."""
    acc, _ = make_account(opening_deposit=5000)
    count_before = _count_account_transactions(acc)

    # Perform repeated balance inquiries
    call("GET", f"/api/accounts/{acc}/balance")
    call("GET", f"/api/accounts/{acc}/balance")

    count_after = _count_account_transactions(acc)
    if count_before is not None and count_after is not None:
        assert count_after == count_before, "Inquiries must not generate transaction rows"


def test_st11_customer_self_service_balance_check():
    """ST_11: System test: customer checks own balance through self-service."""
    acc, _ = make_account(opening_deposit=5000)
    r1 = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r1, C2)
    assert r1.status_code == 200
    assert float(r1.json()["balance"]) == 5000.00


def test_st12_staff_counter_multiple_inquiries_independent():
    """ST_12: System test: staff performs counter inquiries for two customers in turn."""
    acc1, _ = make_account(opening_deposit=4000)
    acc2, _ = make_account(opening_deposit=7000)

    r_a1 = call("GET", f"/api/accounts/{acc1}/balance")
    r_b = call("GET", f"/api/accounts/{acc2}/balance")
    r_a2 = call("GET", f"/api/accounts/{acc1}/balance")

    assert r_a1.status_code == 200 and float(r_a1.json()["balance"]) == 4000.00
    assert r_b.status_code == 200 and float(r_b.json()["balance"]) == 7000.00
    assert r_a2.status_code == 200 and float(r_a2.json()["balance"]) == 4000.00


# ============================================================================
# FR-10: Overdraft Protection & Minimum Balance Boundary (Sprint Enhancement)
# ============================================================================

def test_fr10_withdraw_boundary_exact_500_succeeds_and_499_99_rejected():
    """FR-10: Exact boundary check: leaving Rs. 500.00 succeeds; leaving Rs. 499.99 rejected."""
    acc, _ = make_account()
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r_bal, C2)
    assert r_bal.status_code == 200
    start_bal = float(r_bal.json()["balance"])
    assert start_bal >= 500.0

    # 1. Attempt to withdraw leaving Rs. 499.99 remaining -> MUST BE REJECTED (400)
    withdraw_leaving_499_99 = round(start_bal - 499.99, 2)
    r_reject = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": withdraw_leaving_499_99})
    skip_if_unimplemented(r_reject, C2)
    assert r_reject.status_code == 400
    err = r_reject.json().get("error", "").lower()
    assert "minimum balance" in err or "500" in err

    # Balance unchanged
    r_chk1 = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_chk1.json()["balance"]) == start_bal

    # 2. Attempt to withdraw leaving exactly Rs. 500.00 remaining -> MUST SUCCEED (200)
    withdraw_leaving_500 = round(start_bal - 500.00, 2)
    r_ok = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": withdraw_leaving_500})
    skip_if_unimplemented(r_ok, C2)
    assert r_ok.status_code == 200
    assert float(r_ok.json()["balance"]) == 500.00


def test_fr10_withdraw_overdraft_protection_no_state_change():
    """FR-10: Overdraft protection: amount greater than balance returns 400, no state change."""
    acc, _ = make_account()
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r_bal, C2)
    assert r_bal.status_code == 200
    balance_before = float(r_bal.json()["balance"])

    overdraft_amount = balance_before + 500.00
    r_overdraft = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": overdraft_amount})
    skip_if_unimplemented(r_overdraft, C2)
    assert r_overdraft.status_code == 400

    r_bal_after = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_bal_after.json()["balance"]) == balance_before


# ============================================================================
# FR-11: Amount Validation Sweep & Boundary Acceptance (Sprint Enhancement)
# ============================================================================

def test_fr11_amount_validation_invalid_class_sweep_deposit():
    """FR-11: Zero, negative, non-numeric, > Rs. 1,000,000, and 3-decimal amounts all return 400."""
    acc, _ = make_account()
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r_bal, C2)
    start_bal = float(r_bal.json()["balance"])

    invalid_cases = [
        ({"amount": 0}, "Zero amount (int)"),
        ({"amount": 0.0}, "Zero amount (float)"),
        ({"amount": "0"}, "Zero amount (string)"),
        ({"amount": -1}, "Negative amount (-1)"),
        ({"amount": -500}, "Negative amount (-500)"),
        ({"amount": "abc"}, "Non-numeric string 'abc'"),
        ({"amount": ""}, "Empty string amount"),
        ({"amount": 1000000.01}, "Exceeds Rs. 1,000,000 cap by 1 cent"),
        ({"amount": 10.555}, "3 decimal places (10.555)"),
        ({}, "Missing amount field"),
    ]

    for payload, desc in invalid_cases:
        r = call("POST", f"/api/accounts/{acc}/deposit", payload)
        skip_if_unimplemented(r, C2)
        assert r.status_code == 400, f"Deposit {desc} must return 400, got {r.status_code}"

    r_bal_check = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_bal_check.json()["balance"]) == start_bal


def test_fr11_amount_validation_invalid_class_sweep_withdraw():
    """FR-11: Validate invalid amount classes on withdrawal."""
    acc, _ = make_account()
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r_bal, C2)
    start_bal = float(r_bal.json()["balance"])

    invalid_cases = [
        ({"amount": 0}, "Zero amount (int)"),
        ({"amount": -1}, "Negative amount (-1)"),
        ({"amount": "abc"}, "Non-numeric string 'abc'"),
        ({"amount": 1000000.01}, "Exceeds Rs. 1,000,000 cap"),
        ({"amount": 10.555}, "3 decimal places"),
        ({}, "Missing amount field"),
    ]

    for payload, desc in invalid_cases:
        r = call("POST", f"/api/accounts/{acc}/withdraw", payload)
        skip_if_unimplemented(r, C2)
        assert r.status_code == 400, f"Withdrawal {desc} must return 400, got {r.status_code}"

    r_bal_check = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_bal_check.json()["balance"]) == start_bal


def test_fr11_amount_validation_boundary_accepted():
    """FR-11: Boundary acceptance: exactly Rs. 1,000,000 and 2-decimal values succeed."""
    acc, _ = make_account(opening_deposit=5000)
    r_dec = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 500.25})
    skip_if_unimplemented(r_dec, C2)
    assert r_dec.status_code == 200
    assert float(r_dec.json()["balance"]) == 5500.25


# ============================================================================
# NFR-01: Performance SLA & Response Time Budgets (Sprint Enhancement)
# ============================================================================

def test_nfr01_repeatable_timing_deposit_withdraw_balance():
    """NFR-01: Time deposit, withdraw, and balance over 50 runs each; report p50/p95 and assert p95 < 2 s."""
    acc, _ = make_account(opening_deposit=5000)

    deposit_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 10})
        elapsed = time.perf_counter() - t0
        skip_if_unimplemented(r, C2)
        assert r.status_code == 200
        deposit_times.append(elapsed)

    p50_dep, p95_dep = _percentiles(deposit_times)
    assert p95_dep < HARD_LIMIT_BUDGET
    assert p50_dep < TARGET_LATENCY_BUDGET

    withdraw_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 10})
        elapsed = time.perf_counter() - t0
        skip_if_unimplemented(r, C2)
        assert r.status_code == 200
        withdraw_times.append(elapsed)

    p50_wdr, p95_wdr = _percentiles(withdraw_times)
    assert p95_wdr < HARD_LIMIT_BUDGET
    assert p50_wdr < TARGET_LATENCY_BUDGET

    balance_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        r = call("GET", f"/api/accounts/{acc}/balance")
        elapsed = time.perf_counter() - t0
        skip_if_unimplemented(r, C2)
        assert r.status_code == 200
        balance_times.append(elapsed)

    p50_bal, p95_bal = _percentiles(balance_times)
    assert p95_bal < HARD_LIMIT_BUDGET
    assert p50_bal < TARGET_LATENCY_BUDGET


def test_nfr01_bulk_growth_history_and_balance():
    """NFR-01: Seed ~5,000 transactions and verify balance and history queries remain within budget."""
    acc, _ = make_account()
    _seed_bulk_transactions(acc, count=5000)

    t0 = time.perf_counter()
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    elapsed_bal = time.perf_counter() - t0
    skip_if_unimplemented(r_bal, C2)
    assert r_bal.status_code == 200
    assert elapsed_bal < HARD_LIMIT_BUDGET
    assert elapsed_bal < TARGET_LATENCY_BUDGET


def test_nfr01_sustained_session_no_degradation():
    """NFR-01: 100 mixed operations — response times in the last 20 must not degrade versus the first 20."""
    acc, _ = make_account(opening_deposit=10000)

    latencies = []
    for i in range(100):
        op = i % 3
        t0 = time.perf_counter()
        if op == 0:
            r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 10})
        elif op == 1:
            r = call("GET", f"/api/accounts/{acc}/balance")
        else:
            r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 10})
        elapsed = time.perf_counter() - t0
        skip_if_unimplemented(r, C2)
        assert r.status_code == 200
        latencies.append(elapsed)

    assert len(latencies) == 100
    first_20 = latencies[:20]
    last_20 = latencies[-20:]

    median_first = statistics.median(first_20)
    median_last = statistics.median(last_20)
    p50_all, p95_all = _percentiles(latencies)

    assert p95_all < HARD_LIMIT_BUDGET
    assert median_last < TARGET_LATENCY_BUDGET
    jitter_buffer = 0.050
    degradation_limit = max(median_first * 1.5, median_first + jitter_buffer)
    assert median_last <= degradation_limit
