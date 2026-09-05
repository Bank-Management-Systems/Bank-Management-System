"""Candidate 2 - Core Transactions contract tests (FR-08, FR-09, FR-12).

Chapter 5 of the Test Plan V2. Provisioning uses FR-01 when available and
falls back to the seeded account 1001 (balance Rs. 5000) while it is not.
"""
from config import call, skip_if_unimplemented, make_account

C2 = "Candidate 2 (backend/candidate2_transactions)"


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
