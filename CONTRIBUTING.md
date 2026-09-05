# Contributing

**Read `contribution.docx` (repo root) for the full illustrated walkthrough.**

Short version:

1. Clone: `git clone https://github.com/<your-team>/bank_management_system.git`
2. Branch: `git checkout -b candidate1/create-account`  *(pattern: `candidate<n>/<feature>`)*
3. Verify: `git branch --show-current`
4. Code **only in your folders** (see the table below or README).
5. Test locally: `bash scripts/run_integration_tests.sh`
6. Commit: `git add <your folders> && git commit -m "candidate1: implement FR-01 create account"`
7. Push: `git push -u origin candidate1/create-account`
8. Open a Pull Request on GitHub - CI runs automatically; merge needs green CI + 1 review.

| Candidate | Backend folder | Frontend file | FRs |
|---|---|---|---|
| 1 | `backend/candidate1_account/` | `frontend/js/candidate1_accounts.js` | FR-01, FR-04, FR-05 |
| 2 | `backend/candidate2_transactions/` | `frontend/js/candidate2_transactions.js` | FR-08, FR-09, FR-12 |
| 3 | `backend/candidate3_records/` | `frontend/js/candidate3_records.js` | FR-13, FR-15, FR-17 |
| 4 | `backend/candidate4_security/` | `frontend/js/candidate4_security.js` | FR-18, FR-19, FR-20 |

Never push directly to `main`. Never commit credentials - the backend reads
`DB_*` environment variables.
