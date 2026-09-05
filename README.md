# Bank Management System

Team project template for 4 candidates · **12 functional requirements (3 per candidate)** ·
Backend **C++17 + cpp-httplib** · Frontend **HTML/CSS/JS** · Database **MySQL** ·
**Integration tests run automatically on every push and pull request.**

## Documentation (docs/)

| File | Purpose |
|---|---|
| `docs/Bank_Management_System_Test_Plan_V2.docx` | The 12 FRS, the 96 test cases and the candidate allocation - your working contract |
| `docs/Bank_Management_System_srs_V2.docx` | Software Requirements Specification *(team lead adds this file)* |
| `contribution.docx` | Step-by-step contribution workflow (clone → branch → switch → code → push → PR) |

## Who codes where

| Candidate | Module | Backend folder | Frontend file | FRs |
|---|---|---|---|---|
| Candidate 1 | Account Management | `backend/candidate1_account/` | `frontend/js/candidate1_accounts.js` | FR-01, FR-04, FR-05 |
| Candidate 2 | Core Transactions | `backend/candidate2_transactions/` | `frontend/js/candidate2_transactions.js` | FR-08, FR-09, FR-12 |
| Candidate 3 | Transfer & Records | `backend/candidate3_records/` | `frontend/js/candidate3_records.js` | FR-13, FR-15, FR-17 |
| Candidate 4 | Security | `backend/candidate4_security/` | `frontend/js/candidate4_security.js` | FR-18, FR-19, FR-20 |

Shared files (`backend/main.cpp`, `database/schema.sql`, `frontend/js/app.js`,
`frontend/css/style.css`) carry ownership comments - add only your own lines.

## Repository layout

```
bank_management_system/
├── docs/                        test plan + SRS uploads
├── backend/                     C++ API (cpp-httplib, single header in third_party/)
│   ├── main.cpp                 server entry - mounts all four modules
│   ├── common/                  shared db.hpp + http_utils.hpp
│   ├── candidate1_account/      ← Candidate 1 codes here
│   ├── candidate2_transactions/ ← Candidate 2 codes here
│   ├── candidate3_records/      ← Candidate 3 codes here
│   └── candidate4_security/     ← Candidate 4 codes here
├── frontend/                    basic HTML/CSS/JS (no framework)
├── database/                    MySQL schema.sql + seed.sql + ownership map
├── tests/integration/           pytest contract tests (skip until implemented)
├── scripts/run_integration_tests.sh
└── .github/workflows/ci.yml     build + tests on push / PR
```

## Quickstart (local)

```bash
# 1. database (needs a local MySQL; adjust DB_* env vars if needed)
mysql -u root -p < database/schema.sql
mysql -u root -p < database/seed.sql

# 2. backend (needs g++ and libmysqlclient-dev)
cd backend && make && ./bank_server        # serves API + frontend on :8080

# 3. open the app
#    http://localhost:8080  (health: /api/health)

# 4. integration tests
cd .. && bash scripts/run_integration_tests.sh
```

Until an endpoint is implemented it answers **501** and its tests report
**skipped** - they turn strict automatically as each candidate delivers.

## Continuous integration

`.github/workflows/ci.yml` triggers on **every push and pull request**:
spins up a MySQL 8 service, imports `schema.sql` + `seed.sql`, compiles the
backend, boots the API and runs `pytest -q tests/integration`. A pull request
is mergeable when the build is green and no implemented test fails.
