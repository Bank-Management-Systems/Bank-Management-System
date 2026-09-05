"""Candidate 1 - Account Management contract tests (FR-01, FR-04, FR-05).

These are the integration-level acceptance cases corresponding to the unit /
integration / system cases of Chapter 4 in the Test Plan V2 document.
"""
from config import call, skip_if_unimplemented, make_account, SEED_ACCOUNT_A

C1 = "Candidate 1 (backend/candidate1_account)"


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
