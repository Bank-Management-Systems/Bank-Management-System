# Integration Tests

API-level acceptance tests. Each candidate owns ONE test file and may extend it:

| Test file | Validates | Endpoint owner |
|---|---|---|
| `test_health.py` | API is up (already implemented) | shared |
| `test_candidate1_account.py` | FR-01, FR-04, FR-05 | Candidate 1 |
| `test_candidate2_transactions.py` | FR-08, FR-09, FR-12 | Candidate 2 |
| `test_candidate3_records.py` | FR-13, FR-15, FR-17 | Candidate 3 |
| `test_candidate4_security.py` | FR-18, FR-19, FR-20 | Candidate 4 |

## Run locally

```bash
bash scripts/run_integration_tests.sh        # db import + build + boot + pytest
# or, against an already-running server:
python3 -m pip install -r tests/requirements.txt
python3 -m pytest -q tests/integration
```

## Skip vs fail

- `501 Not Implemented`  ->  **skipped** (endpoint exists, owner has not finished it).
- Anything else that breaks the contract  ->  **failed** (must be fixed before merge).

In short: the pipeline cannot go red because a teammate has not started yet,
but it goes red the moment a implemented behaviour regresses.

## Configuration

| Env var | Default | Meaning |
|---|---|---|
| `API_BASE_URL` | http://localhost:8080 | server under test |
| `TEST_STAFF_USER` / `TEST_STAFF_PASS` | admin / admin123 | seed staff credentials |
| `TEST_CUSTOMER_PIN` | 1234 | seed PIN for account 1001 |
