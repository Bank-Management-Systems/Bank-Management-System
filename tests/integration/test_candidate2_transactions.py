"""Candidate 2 - Core Transactions contract tests (FR-08, FR-09, FR-12).

Chapter 5 of the Test Plan V2. Provisioning uses FR-01 when available and
falls back to the seeded account 1001 (balance Rs. 5000) while it is not.
"""
import os
import subprocess
import time
import statistics
from config import call, skip_if_unimplemented, make_account

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



def test_fr08_deposit_increases_balance():
    acc, _ = make_account()
    r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 1000})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "balance" in body, "response must contain the new balance"


def test_fr08_rejects_zero_and_negative_amounts():
    acc, _ = make_account()
    for amount in (0, -500):
        r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": amount})
        skip_if_unimplemented(r, C2)
        assert r.status_code == 400, f"deposit of {amount} must be rejected"


def test_fr09_withdraw_within_balance_succeeds():
    acc, _ = make_account()
    r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 500})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200, r.text
    assert "balance" in r.json()


def test_fr09_withdraw_breaking_minimum_balance_rejected():
    acc, _ = make_account()
    # Seeded fallback balance is 5000: withdrawing 4600 leaves 400 < 500 minimum.
    r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 4600})
    skip_if_unimplemented(r, C2)
    assert r.status_code == 400, "withdrawal leaving less than Rs. 500 must be rejected"


def test_fr10_withdraw_boundary_exact_500_succeeds_and_499_99_rejected():
    """FR-10: Exact boundary check.
    
    Leaving Rs. 499.99 remaining must be rejected with 400 (naming minimum balance).
    Leaving exactly Rs. 500.00 remaining must succeed with 200.
    """
    acc, _ = make_account()

    # Get current balance
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r_bal, C2)
    assert r_bal.status_code == 200
    start_bal = float(r_bal.json()["balance"])
    assert start_bal >= 500.0

    # 1. Attempt to withdraw leaving Rs. 499.99 remaining -> MUST BE REJECTED (400)
    withdraw_leaving_499_99 = round(start_bal - 499.99, 2)
    r_reject = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": withdraw_leaving_499_99})
    skip_if_unimplemented(r_reject, C2)
    assert r_reject.status_code == 400, (
        f"Withdrawal leaving Rs. 499.99 must return 400, got {r_reject.status_code}: {r_reject.text}"
    )
    err = r_reject.json().get("error", "").lower()
    assert "minimum balance" in err or "500" in err, f"Error message must name minimum balance, got: {err}"

    # Balance must remain completely unchanged
    r_chk1 = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_chk1.json()["balance"]) == start_bal, "Balance changed after rejected boundary withdrawal"

    # 2. Attempt to withdraw leaving exactly Rs. 500.00 remaining -> MUST SUCCEED (200)
    withdraw_leaving_500 = round(start_bal - 500.00, 2)
    r_ok = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": withdraw_leaving_500})
    skip_if_unimplemented(r_ok, C2)
    assert r_ok.status_code == 200, (
        f"Withdrawal leaving exactly Rs. 500 must return 200, got {r_ok.status_code}: {r_ok.text}"
    )
    assert float(r_ok.json()["balance"]) == 500.00, f"Expected new balance 500.00, got {r_ok.json()['balance']}"

    # Confirm via balance inquiry
    r_chk2 = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_chk2.json()["balance"]) == 500.00

    # 3. From exactly Rs. 500.00 balance, even Rs. 0.01 withdrawal leaves 499.99 -> REJECTED (400)
    r_sub_cent = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 0.01})
    assert r_sub_cent.status_code == 400
    r_chk3 = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_chk3.json()["balance"]) == 500.00


def test_fr10_withdraw_overdraft_protection_no_state_change():
    """FR-10: Overdraft protection.
    
    An amount greater than available balance must return 400,
    cause no state change, and write no transaction row to the ledger.
    """
    acc, _ = make_account()

    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r_bal, C2)
    assert r_bal.status_code == 200
    balance_before = float(r_bal.json()["balance"])

    # Query transaction history before attempted overdraft
    r_hist_before = call("GET", f"/api/accounts/{acc}/transactions")
    count_before = r_hist_before.json().get("count", 0) if r_hist_before.status_code == 200 else None

    # Attempt to withdraw more than available balance (overdraft)
    overdraft_amount = balance_before + 500.00
    r_overdraft = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": overdraft_amount})
    skip_if_unimplemented(r_overdraft, C2)
    assert r_overdraft.status_code == 400, (
        f"Overdraft withdrawal must return 400, got {r_overdraft.status_code}: {r_overdraft.text}"
    )

    # Verify balance did NOT change
    r_bal_after = call("GET", f"/api/accounts/{acc}/balance")
    assert float(r_bal_after.json()["balance"]) == balance_before, (
        f"Balance changed after rejected overdraft: before={balance_before}, after={r_bal_after.json()['balance']}"
    )

    # Verify no transaction row was written to the ledger
    if count_before is not None:
        r_hist_after = call("GET", f"/api/accounts/{acc}/transactions")
        assert r_hist_after.status_code == 200
        count_after = r_hist_after.json().get("count", 0)
        assert count_after == count_before, (
            f"Transaction row was written despite overdraft rejection: count_before={count_before}, count_after={count_after}"
        )



def test_fr12_balance_inquiry_returns_current_balance():
    acc, _ = make_account()
    r = call("GET", f"/api/accounts/{acc}/balance")
    skip_if_unimplemented(r, C2)
    assert r.status_code == 200, r.text
    assert isinstance(r.json().get("balance"), (int, float))


def test_fr12_unknown_account_returns_404():
    r = call("GET", "/api/accounts/999999/balance")
    skip_if_unimplemented(r, C2)
    assert r.status_code == 404


def test_nfr01_repeatable_timing_deposit_withdraw_balance():
    """NFR-01: Time deposit, withdraw, and balance over 50 runs each; report p50/p95 and assert p95 < 2 s."""
    acc, _ = make_account()

    # 1. 50 Deposit calls
    deposit_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        r = call("POST", f"/api/accounts/{acc}/deposit", {"amount": 10})
        elapsed = time.perf_counter() - t0
        skip_if_unimplemented(r, C2)
        assert r.status_code == 200, f"Deposit failed: {r.text}"
        deposit_times.append(elapsed)

    p50_dep, p95_dep = _percentiles(deposit_times)
    print(f"\n[NFR-01] Deposit (50 calls): p50 = {p50_dep*1000:.2f} ms, p95 = {p95_dep*1000:.2f} ms")
    assert p95_dep < HARD_LIMIT_BUDGET, f"Deposit p95 {p95_dep:.4f}s exceeds hard limit {HARD_LIMIT_BUDGET}s"
    assert p50_dep < TARGET_LATENCY_BUDGET, f"Deposit p50 {p50_dep:.4f}s exceeds target {TARGET_LATENCY_BUDGET}s"

    # 2. 50 Withdraw calls
    withdraw_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        r = call("POST", f"/api/accounts/{acc}/withdraw", {"amount": 10})
        elapsed = time.perf_counter() - t0
        skip_if_unimplemented(r, C2)
        assert r.status_code == 200, f"Withdraw failed: {r.text}"
        withdraw_times.append(elapsed)

    p50_wdr, p95_wdr = _percentiles(withdraw_times)
    print(f"[NFR-01] Withdraw (50 calls): p50 = {p50_wdr*1000:.2f} ms, p95 = {p95_wdr*1000:.2f} ms")
    assert p95_wdr < HARD_LIMIT_BUDGET, f"Withdraw p95 {p95_wdr:.4f}s exceeds hard limit {HARD_LIMIT_BUDGET}s"
    assert p50_wdr < TARGET_LATENCY_BUDGET, f"Withdraw p50 {p50_wdr:.4f}s exceeds target {TARGET_LATENCY_BUDGET}s"

    # 3. 50 Balance inquiry calls
    balance_times = []
    for _ in range(50):
        t0 = time.perf_counter()
        r = call("GET", f"/api/accounts/{acc}/balance")
        elapsed = time.perf_counter() - t0
        skip_if_unimplemented(r, C2)
        assert r.status_code == 200, f"Balance inquiry failed: {r.text}"
        balance_times.append(elapsed)

    p50_bal, p95_bal = _percentiles(balance_times)
    print(f"[NFR-01] Balance (50 calls): p50 = {p50_bal*1000:.2f} ms, p95 = {p95_bal*1000:.2f} ms")
    assert p95_bal < HARD_LIMIT_BUDGET, f"Balance p95 {p95_bal:.4f}s exceeds hard limit {HARD_LIMIT_BUDGET}s"
    assert p50_bal < TARGET_LATENCY_BUDGET, f"Balance p50 {p50_bal:.4f}s exceeds target {TARGET_LATENCY_BUDGET}s"


def test_nfr01_bulk_growth_history_and_balance():
    """NFR-01: Seed ~5,000 transactions and verify balance and history queries remain within budget."""
    acc, _ = make_account()

    # Seed ~5,000 transactions for this account
    _seed_bulk_transactions(acc, count=5000)

    # 1. Balance inquiry after 5,000 transactions
    t0 = time.perf_counter()
    r_bal = call("GET", f"/api/accounts/{acc}/balance")
    elapsed_bal = time.perf_counter() - t0
    skip_if_unimplemented(r_bal, C2)
    assert r_bal.status_code == 200, f"Balance inquiry failed: {r_bal.text}"
    print(f"\n[NFR-01] Bulk Growth (5,000 txns) Balance query: {elapsed_bal*1000:.2f} ms")
    assert elapsed_bal < HARD_LIMIT_BUDGET, f"Balance query {elapsed_bal:.4f}s exceeds hard limit {HARD_LIMIT_BUDGET}s"
    assert elapsed_bal < TARGET_LATENCY_BUDGET, f"Balance query {elapsed_bal:.4f}s exceeds target {TARGET_LATENCY_BUDGET}s"

    # 2. History query after 5,000 transactions
    t0 = time.perf_counter()
    r_hist = call("GET", f"/api/accounts/{acc}/transactions")
    elapsed_hist = time.perf_counter() - t0
    skip_if_unimplemented(r_hist, "Candidate 3 (backend/candidate3_records)")
    assert r_hist.status_code == 200, f"History query failed: {r_hist.text}"
    body = r_hist.json()
    assert body.get("count", 0) >= 5000, f"Expected >= 5000 transactions, got {body.get('count')}"
    print(f"[NFR-01] Bulk Growth (5,000 txns) History query: {elapsed_hist*1000:.2f} ms (count = {body.get('count')})")
    assert elapsed_hist < HARD_LIMIT_BUDGET, f"History query {elapsed_hist:.4f}s exceeds hard limit {HARD_LIMIT_BUDGET}s"
    assert elapsed_hist < TARGET_LATENCY_BUDGET, f"History query {elapsed_hist:.4f}s exceeds target {TARGET_LATENCY_BUDGET}s"


def test_nfr01_sustained_session_no_degradation():
    """NFR-01: 100 mixed operations — response times in the last 20 must not degrade versus the first 20."""
    acc, _ = make_account()

    latencies = []
    # 100 mixed operations (deposit, balance, withdraw)
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
        assert r.status_code == 200, f"Op {i} failed: {r.text}"
        latencies.append(elapsed)

    assert len(latencies) == 100
    first_20 = latencies[:20]
    last_20 = latencies[-20:]

    mean_first = statistics.mean(first_20)
    median_first = statistics.median(first_20)
    mean_last = statistics.mean(last_20)
    median_last = statistics.median(last_20)
    p50_all, p95_all = _percentiles(latencies)

    print(f"\n[NFR-01] Sustained Session (100 ops):")
    print(f"  First 20 ops: mean = {mean_first*1000:.2f} ms, median = {median_first*1000:.2f} ms")
    print(f"  Last 20 ops:  mean = {mean_last*1000:.2f} ms, median = {median_last*1000:.2f} ms")
    print(f"  Overall:      p50 = {p50_all*1000:.2f} ms, p95 = {p95_all*1000:.2f} ms")

    # Hard budget assertion
    assert p95_all < HARD_LIMIT_BUDGET, f"Session p95 {p95_all:.4f}s exceeds hard limit {HARD_LIMIT_BUDGET}s"
    assert median_last < TARGET_LATENCY_BUDGET, f"Last 20 median {median_last:.4f}s exceeds target {TARGET_LATENCY_BUDGET}s"

    # Degradation check: last 20 median must not degrade compared to first 20
    # Include a generous buffer (50 ms) to absorb typical OS/network scheduling jitter
    jitter_buffer = 0.050  # 50 ms
    degradation_limit = max(median_first * 1.5, median_first + jitter_buffer)
    assert median_last <= degradation_limit, (
        f"Response times degraded: last 20 median ({median_last*1000:.2f} ms) "
        f"exceeded threshold ({degradation_limit*1000:.2f} ms, first 20 median = {median_first*1000:.2f} ms)"
    )

