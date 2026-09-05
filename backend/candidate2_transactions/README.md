# Candidate 2 - Core Banking Transactions (backend)

**You own this folder.** Nobody else commits here.

| Item | Value |
|---|---|
| Requirements | FR-08 Deposit, FR-09 Withdrawal, FR-12 Balance inquiry |
| Test plan | `docs/Bank_Management_System_Test_Plan_V2.docx` - Chapter 5 (sections 5.1 - 5.3) |
| File to code | `transactions_module.hpp` (replace the three 501 stubs) |
| Route mounting | Already done in `backend/main.cpp` - do not edit it |
| Acceptance tests | `tests/integration/test_candidate2_transactions.py` |

## Endpoints you implement

| Method | Path | FR | Success | Typical failure |
|---|---|---|---|---|
| POST | `/api/accounts/{id}/deposit` | FR-08 | `200` + new balance | `400` amount <= 0 |
| POST | `/api/accounts/{id}/withdraw` | FR-09 | `200` + new balance | `400` would break Rs. 500 minimum |
| GET | `/api/accounts/{id}/balance` | FR-12 | `200` + balance | `404` unknown account |

## Business rules to honour
- Amount must be a positive number (reject 0, negative, non-numeric) - FR-08/09.
- Withdrawal must leave at least the Rs. 500 minimum balance - FR-09.
- Every accepted operation writes a row into `transactions` (Candidate 3 reads it).
- Closed accounts (status='closed', set by Candidate 1) reject every operation.
