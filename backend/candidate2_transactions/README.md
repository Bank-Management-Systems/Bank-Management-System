# Candidate 2 - Core Banking Transactions (backend)

**You own this folder.** Nobody else commits here.

| Item | Value |
|---|---|
| Requirements | FR-08 Deposit, FR-09 / FR-10 Withdrawal, FR-12 Balance inquiry |
| Test plan | `docs/Bank_Management_System_Test_Plan_V2.docx` - Chapter 5 (sections 5.1 - 5.3) |
| File to code | `transactions_module.hpp` (replace the three 501 stubs) |
| Route mounting | Already done in `backend/main.cpp` - do not edit it |
| Acceptance tests | `tests/integration/test_candidate2_transactions.py` |

## Endpoints you implement

| Method | Path | FR | Success | Typical failure |
|---|---|---|---|---|
| POST | `/api/accounts/{id}/deposit` | FR-08 | `200` + new balance | `400` amount <= 0 |
| POST | `/api/accounts/{id}/withdraw` | FR-09, FR-10 | `200` + new balance | `400` would break Rs. 500 minimum / overdraft |
| GET | `/api/accounts/{id}/balance` | FR-12 | `200` + balance | `404` unknown account |

## Business rules to honour
- Amount must be a positive number (reject 0, negative, non-numeric via `validate_amount`) - FR-08/09.
- Withdrawal boundary rule (FR-10): a withdrawal is permitted only when `(balance - amount) >= Rs. 500`. Leaving exactly Rs. 500 succeeds; leaving Rs. 499.99 is rejected (400 naming minimum balance).
- Overdraft protection (FR-10): an amount greater than available balance returns 400 with no state change and no ledger row.
- Every accepted operation writes a row into `transactions` (Candidate 3 reads it). Rejected operations write zero rows.
- Closed accounts (status='closed', set by Candidate 1) reject every operation.

## Performance & Latency Budget (NFR-01)
- **Target latency**: Well under 1.0 s per interactive request under normal load (typically < 100 ms).
- **Hard latency limit**: 2.0 s maximum per V1 requirements.
- **Hot-path efficiency**:
  - Deposit, withdrawal, and balance inquiry perform indexed primary-key lookups on `accounts(account_number)` (`O(1)`).
  - Transaction rows append directly without full-table scans.
  - History and statement queries are accelerated by the additive index `idx_txn_account_created ON transactions(account_number, created_at)`.

