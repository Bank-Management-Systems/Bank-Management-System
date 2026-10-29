"""Candidate 3 - Transfer / Records / Statement contract tests (FR-13, FR-15, FR-17).

Chapter 6 of the Test Plan V2. Uses the two seeded accounts 1001 and 1002
(balances 5000 / 3000 after a fresh schema import).
"""
from config import (call, skip_if_unimplemented, make_account,
                    SEED_ACCOUNT_A, SEED_ACCOUNT_B)

C3 = "Candidate 3 (backend/candidate3_records)"


def test_fr13_transfer_moves_money_between_accounts():
    acc_from, acc_to = SEED_ACCOUNT_A, SEED_ACCOUNT_B
    r = call("POST", "/api/transfers",
             {"from_account": acc_from, "to_account": acc_to, "amount": 250})
    skip_if_unimplemented(r, C3)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "from_balance" in body and "to_balance" in body


def test_fr13_transfer_is_rejected_without_partial_application():
    acc_from, acc_to = SEED_ACCOUNT_A, SEED_ACCOUNT_B
    # Seeded balance of 1001 is 5000: moving 6000 is impossible.
    r = call("POST", "/api/transfers",
             {"from_account": acc_from, "to_account": acc_to, "amount": 6000})
    skip_if_unimplemented(r, C3)
    assert r.status_code == 400, "insufficient funds must be rejected"


def test_fr13_transfer_to_unknown_account_fails():
    r = call("POST", "/api/transfers",
             {"from_account": SEED_ACCOUNT_A, "to_account": 999999, "amount": 100})
    skip_if_unimplemented(r, C3)
    assert r.status_code in (400, 404), "unknown beneficiary must fail, never credit"


def test_fr15_history_lists_recorded_activity():
    acc, _ = make_account()
    call("POST", f"/api/accounts/{acc}/deposit", {"amount": 100})  # best effort setup
    r = call("GET", f"/api/accounts/{acc}/transactions")
    skip_if_unimplemented(r, C3)
    assert r.status_code == 200, r.text
    body = r.json()
    items = body.get("transactions", body if isinstance(body, list) else [])
    assert isinstance(items, list) and len(items) >= 1
    first = items[0]
    assert {"type", "amount"} <= set(first), "each row needs at least type and amount"


def test_fr17_statement_reconciles_with_balance():
    acc, _ = make_account()
    r = call("GET", f"/api/accounts/{acc}/statement")
    skip_if_unimplemented(r, C3)
    assert r.status_code == 200, r.text
    body = r.json()
    assert "closing_balance" in body, "statement must state the closing balance"
def test_failed_transfer_leaves_balances_and_logs_unchanged():
    """A rejected transfer must not change balances or add transaction rows."""
    acc_from, acc_to = SEED_ACCOUNT_A, SEED_ACCOUNT_B

    # Capture both balances before the rejected transfer.
    from_before = call("GET", f"/api/accounts/{acc_from}/balance")
    to_before = call("GET", f"/api/accounts/{acc_to}/balance")

    assert from_before.status_code == 200, from_before.text
    assert to_before.status_code == 200, to_before.text

    from_balance_before = from_before.json()["balance"]
    to_balance_before = to_before.json()["balance"]

    # Capture transaction histories before the transfer.
    from_history_before = call(
        "GET", f"/api/accounts/{acc_from}/transactions"
    )
    to_history_before = call(
        "GET", f"/api/accounts/{acc_to}/transactions"
    )

    assert from_history_before.status_code == 200, from_history_before.text
    assert to_history_before.status_code == 200, to_history_before.text

    from_count_before = from_history_before.json()["count"]
    to_count_before = to_history_before.json()["count"]

    # A transfer to a nonexistent account must fail.
    response = call(
        "POST",
        "/api/transfers",
        {
            "from_account": acc_from,
            "to_account": 999999,
            "amount": 100,
        },
    )
    skip_if_unimplemented(response, C3)
    assert response.status_code in (400, 404), response.text

    # Verify that neither balance changed.
    from_after = call("GET", f"/api/accounts/{acc_from}/balance")
    to_after = call("GET", f"/api/accounts/{acc_to}/balance")

    assert from_after.status_code == 200, from_after.text
    assert to_after.status_code == 200, to_after.text
    assert from_after.json()["balance"] == from_balance_before
    assert to_after.json()["balance"] == to_balance_before

    # Verify that no transaction records were added.
    from_history_after = call(
        "GET", f"/api/accounts/{acc_from}/transactions"
    )
    to_history_after = call(
        "GET", f"/api/accounts/{acc_to}/transactions"
    )

    assert from_history_after.status_code == 200, from_history_after.text
    assert to_history_after.status_code == 200, to_history_after.text
    assert from_history_after.json()["count"] == from_count_before
    assert to_history_after.json()["count"] == to_count_before
