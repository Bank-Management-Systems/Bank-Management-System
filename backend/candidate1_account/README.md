# Candidate 1 - Account Management (backend)

**You own this folder.** Nobody else commits here.

| Item | Value |
|---|---|
| Requirements | FR-01 Create account, FR-04 Modify customer details, FR-05 Close account |
| Test plan | `docs/Bank_Management_System_Test_Plan_V2.docx` - Chapter 4 (sections 4.1 - 4.3) |
| File to code | `account_module.hpp` (replace the three 501 stubs) |
| Route mounting | Already done in `backend/main.cpp` - do not edit it |
| Acceptance tests | `tests/integration/test_candidate1_account.py` |

## Endpoints you implement

| Method | Path | FR | Success | Typical failure |
|---|---|---|---|---|
| POST | `/api/accounts` | FR-01 | `201` + account number | `400` blank name / deposit < 500 |
| PUT | `/api/accounts/{id}` | FR-04 | `200` updated fields | `404` unknown account |
| POST | `/api/accounts/{id}/close` | FR-05 | `200` status=closed | `400` balance not zero |

## How to work
1. `git checkout -b candidate1/create-account` (branch naming: `candidate1/<feature>`)
2. Implement one endpoint, run `bash scripts/run_integration_tests.sh`
3. Commit `candidate1: implement FR-01 create account` and push - CI runs on every push.
