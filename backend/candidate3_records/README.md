# Candidate 3 - Transfer, Records and Statements (backend)

**You own this folder.** Nobody else commits here.

| Item | Value |
|---|---|
| Requirements | FR-13 Transfer, FR-15 Transaction history, FR-17 Statement |
| Test plan | `docs/Bank_Management_System_Test_Plan_V2.docx` - Chapter 6 (sections 6.1 - 6.3) |
| File to code | `records_module.hpp` (replace the three 501 stubs) |
| Route mounting | Already done in `backend/main.cpp` - do not edit it |
| Acceptance tests | `tests/integration/test_candidate3_records.py` |

## Endpoints you implement

| Method | Path | FR | Success | Typical failure |
|---|---|---|---|---|
| POST | `/api/transfers` | FR-13 | `200` + both balances | `400` insufficient funds / closed account |
| GET | `/api/accounts/{id}/transactions` | FR-15 | `200` + ordered list | `404` unknown account |
| GET | `/api/accounts/{id}/statement` | FR-17 | `200` + reconciling statement | `404` unknown account |

## Key rule
FR-13 is **atomic**: wrap debit + credit in `START TRANSACTION` ... `COMMIT`, and
`ROLLBACK` on any failure. The integration tests deliberately try to break this.
