# Bank Management System - Candidate Issues & Technical Q&A Guide

This document catalogs all functional and non-functional requirements (issues) assigned across Candidate 1 through Candidate 4, their test specifications, and 25 comprehensive technical Q&A pairs covering branching, CI/CD, project automation, testing methodologies, and system architecture.

---

## Candidate 1: Account Management

### Assigned Issues

#### 1. Issue #1: [FR-01] Create New Bank Account

Implements POST /api/accounts to register new customers with initial deposit, name, address, contact, and account type. Enforces minimum opening balance (Rs. 500), generates unique sequential account numbers, and validates input formatting. Returns HTTP 201 with created record; rejects missing/invalid payload with 400.

#### 2. Issue #2: [FR-04] Modify Customer Details

Implements PUT /api/accounts/{id} to update address, phone, and profile details for existing active accounts. Verifies account existence, prevents altering immutable fields (account number, balance), and sanitizes strings against control characters. Returns 200 on success; rejects closed or non-existent accounts with 400/404.

#### 3. Issue #3: [FR-05] Close Account

Implements POST /api/accounts/{id}/close to transition active accounts to closed state. Enforces strict zero-balance precondition (balance must be zero before closure). Once closed, accounts reject all further deposits, withdrawals, or transfers. Returns 200 on success; returns 400 if funds remain or account is already closed.

#### 4. Issue #22: [FR-03] Account Search / View Account Details API

Implements GET /api/accounts/{id} returning real-time stored details (name, contact, status, balance, created_at). Reflects state changes immediately following deposits, modifications, or closure. Returns 200 with structured JSON for valid accounts; returns 404 for unknown or malformed IDs with clean error structure.

#### 5. Issue #25: [FR-02] Account Number Generator Hardening

Hardens account ID generation against race conditions and duplicates using atomic database auto-increment/transactions. Guarantees gapless or monotonically increasing sequence starting from 1001, preventing collisions under concurrent account creation. Returns 400 cleanly on constraint violations.

#### 6. Issue #29: [NFR-02] Robustness: Hostile Input Validation Sweep

Hardens route handlers against hostile payloads: malformed JSON, 10,000-char strings, unicode, and control characters return clean 400s rather than 500 crashes or server hangs. Wraps handlers with exception safety and ensures DB state remains uncorrupted before, during, and after hostile fuzzing sweeps.

### Candidate 1 Test Details

Candidate 1 test suite in tests/integration/test_candidate1_account.py comprises 24 core test cases (UT_01-UT_09, IT_01-IT_09, ST_01-ST_06) plus robustness fuzzing sweeps (NFR-02). Tests validate account creation, field updates, closure zero-balance gating, real-time detail lookup freshness, and 400 error handling across malformed JSON, boundary strings, and invalid data types. All pass in CI with zero 500s or hangs.

---

## Candidate 2: Core Banking Transactions

### Assigned Issues

#### 1. Issue #4: [FR-08] Cash Deposit

Implements POST /api/accounts/{id}/deposit to credit positive amounts to active accounts. Updates balance atomically in cents, appends a DEPOSIT entry to the transaction audit ledger, and returns the updated balance. Rejects non-positive amounts, invalid formatting, and closed/missing accounts with HTTP 400/404.

#### 2. Issue #5: [FR-09] Cash Withdrawal

Implements POST /api/accounts/{id}/withdraw allowing cash withdrawal when funds permit. Enforces the bank minimum balance floor of Rs. 500, updates account balance, and writes a WITHDRAWAL audit row in transactions. Rejects attempts breaching minimum balance, overdrafts, and operations on closed accounts with clean 400 errors.

#### 3. Issue #6: [FR-12] Balance Inquiry

Implements GET /api/accounts/{id}/balance returning current balance and status. Provides immediate freshness following deposits or withdrawals and operates as a non-mutating idempotent read. Returns 200 with balance figure for valid accounts; returns 404 for unknown IDs and handles closed account balance lookups cleanly.

#### 4. Issue #20: [FR-11] Transaction Amount Validation (Shared Validator)

Introduces shared validate_amount helper in backend/common/http_utils.hpp. Enforces positive numeric amounts, maximum per-transaction cap of Rs. 1,000,000, and max 2 decimal places. Applied across deposit and withdrawal endpoints to reject invalid, negative, zero, or overflow amounts prior to database access.

#### 5. Issue #21: [FR-10] Withdrawal Rules: Minimum Balance & Overdraft

Hardens withdrawal logic with exact boundary enforcement: (balance - amount) >= Rs. 500. Exactly Rs. 500 remaining succeeds; Rs. 499.99 is rejected. Overdraft attempts exceeding total balance are blocked atomically with no partial debits or corrupt ledger writes, shared across staff and customer interfaces.

#### 6. Issue #30: [NFR-01] Performance: Transaction Response Time SLA

Optimizes transaction hot-paths by adding composite indexes in database/schema.sql (idx_txn_account_created). Enforces p95 latency under 2.0s across 50 repeated deposit/withdraw/balance calls, maintains <1.0s response under 5,000 seeded historical ledger rows, and guarantees zero degradation over 100 sustained operations.

### Candidate 2 Test Details

Candidate 2 test suite in tests/integration/test_candidate2_transactions.py contains 32 test cases covering UT_10-UT_18, IT_10-IT_18, ST_07-ST_12, boundary cases for FR-10 (exact Rs. 500 vs Rs. 499.99), invalid-class fuzz sweeps for FR-11, and NFR-01 latency benchmarks (p95 < 2s, 5000-row volume test, 100-op sustained load). Achieves 84.1% line coverage and 84.8% branch coverage on backend/candidate2_transactions/transactions_module.hpp.

---

## Candidate 3: Transfer, Records and Statements

### Assigned Issues

#### 1. Issue #7: [FR-13] Atomic Funds Transfer

Implements POST /api/transfers executing atomic multi-account transfers within a single database transaction. Debits source, credits destination, and writes paired TRANSFER_OUT and TRANSFER_IN audit records. Rejects insufficient balance, minimum balance violations, closed accounts, or missing beneficiaries with zero partial debit.

#### 2. Issue #8: [FR-15] Transaction History

Implements GET /api/accounts/{id}/transactions returning chronological lists of debits, credits, transfers, and timestamps. Provides strict account data isolation, clean empty-state messaging for new accounts without errors, and immediate visibility of newly completed transactions without cross-account leakage.

#### 3. Issue #9: [FR-17] Account Statement

Implements GET /api/accounts/{id}/statement generating comprehensive account summaries with opening balance, all chronological transactions, and closing balance reconciliation. Validates active accounts, returns structured error on non-existent accounts, and ensures figures match live balance and history exactly.

#### 4. Issue #23: [FR-16] Filter Transaction History by Date Range

Extends history endpoint with optional from_date and to_date query parameters. Validates ISO-8601 timestamps, enforces from <= to constraints, and filters records accordingly. Supports open-ended ranges, boundary inclusive filtering, and graceful error handling on malformed date formats.

#### 5. Issue #24: [FR-14] Transaction Logging Audit & Reconciliation

Formalizes ledger audit reconciliation: asserts that computed sum of opening balance plus credits minus debits equals live balance down to exact cents. Ensures every balance-mutating operation logs complete audit attributes (timestamps, amounts, transaction types) without omitted or orphaned records.

#### 6. Issue #27: [NFR-03] Data Integrity & Transaction Atomicity

Hardens database ACID guarantees using explicit START TRANSACTION, COMMIT, and ROLLBACK blocks with FOR UPDATE row-level locking. Eliminates race conditions during concurrent transfers or simultaneous deposit/withdraw ops, preventing negative balances, partial commits, or phantom balance inflation.

### Candidate 3 Test Details

Candidate 3 test suite in tests/integration/test_candidate3_records.py covers 24 core test cases (UT_19-UT_27, IT_19-IT_27, ST_13-ST_18) and atomicity checks. Tests verify atomic transfer debit/credit balance conservation, rollback on partial failures, chronological history ordering, account isolation, date filtering, statement closing balance reconciliation, and persistence across server restarts.

---

## Candidate 4: Security & Authentication

### Assigned Issues

#### 1. Issue #10: [FR-18] Staff Login

Implements POST /api/auth/staff/login for administrative authentication. Verifies employee username and password, returns role staff and session tokens, and audits access. Rejects invalid passwords and non-existent usernames with 401 Unauthorized without exposing whether the user or credential failed.

#### 2. Issue #11: [FR-19] Customer Authentication (Login)

Implements POST /api/auth/customer/login for self-service customer access using account number and 4-digit PIN. Validates active account status, verifies secure credential matching, and grants customer session role. Blocks closed or locked accounts and denies invalid PIN attempts with HTTP 401.

#### 3. Issue #12: [FR-20] Change PIN

Implements POST /api/auth/customer/{id}/pin-change requiring verified old PIN before applying new 4-digit numeric PIN. Rejects mismatched current PIN, non-numeric or malformed PINs, and identical new-to-old PINs. Applies new PIN immediately for subsequent logins with zero plain-text leaks.

#### 4. Issue #19: [FR-21] Security: Account Lockout After Failed Attempts

Tracks consecutive failed login attempts on staff and customer accounts. Locks identity after 3 consecutive failures, blocking further attempts with 401 Account Locked even on valid credentials. Resets counter on successful login. Adds staff-only POST /api/auth/staff/unlock endpoint to restore locked accounts.

#### 5. Issue #26: [FR-24] Security & Persistence Across Restarts

Ensures credentials, lock states, audit logs, and account balances survive server restarts intact. Validates schema migrations, state hydration on server startup, and verifies that session termination and password security policies persist seamlessly without state loss or corruption.

#### 6. Issue #28: [NFR-04] PIN Protection & Sensitive Data Redaction

Eliminates plain-text credential leaks across the entire system. Enforces cryptographic hashing (bcrypt/SHA-256 with salt) in DB storage, masks password/PIN fields in UI, strips secrets from HTTP responses and error messages, and adds redaction filters to prevent dumping credentials in server logs.

### Candidate 4 Test Details

Candidate 4 test suite in tests/integration/test_candidate4_security.py covers 24 core test cases (UT_28-UT_36, IT_28-IT_36, ST_19-ST_24) plus lockout, hashing, and leak-sweep tests (FR-21, FR-24, NFR-04). Tests validate staff/customer login, 3-attempt lockout threshold, staff unlock recovery, PIN change enforcement, hash verification in DB rows, and log/response leak sweeps with zero plain-text credentials exposed.

---

## Technical Q&A Guide (25 Project Defense & Viva Questions)

This section prepares the team to explain the project architecture, pull requests, branching strategy, CI/CD pipelines, automation, testing tiers, and security models.

### Q1: What branching model was followed in this project and why?

**Answer:**
The project adopted a feature-branch workflow (GitHub Flow). Developers create short-lived isolated branches prefixed by candidate and feature name (e.g., `candidate2/amount-validation`). Branches are rebased onto `main`, verified against CI test suites, and merged via Pull Requests after review. This prevents trunk pollution and keeps the `main` branch always production-ready.

### Q2: How were pull requests reviewed and merged in the team?

**Answer:**
Every Pull Request required at least one peer approval and a passing GitHub Actions CI status check before merging. Reviewers inspected code adherence to modular architecture, absence of raw pointer leaks, exception safety, and verified that corresponding pytest integration test cases and docx test plans were updated.

### Q3: Why was git rebase used instead of git merge when updating feature branches?

**Answer:**
Rebase replays local candidate commits sequentially on top of the latest upstream `main` branch. This avoids unnecessary non-fast-forward merge commit noise (merge bubbles), maintains a clean, linear commit history, and ensures that any merge conflicts are identified and resolved commit-by-commit locally prior to pushing.

### Q4: How did the team resolve merge conflicts on shared files like schema.sql or http_utils.hpp?

**Answer:**
Shared headers (`http_utils.hpp`) and SQL migrations were coordinated through additive changes only. Database alterations used idempotent scripts or `IF NOT EXISTS` clauses. For code conflicts, candidates communicated ownership boundaries, rebased frequently against `main`, and verified combined suites using pytest across all 4 candidate test files.

### Q5: What branch protection rules were configured on the GitHub repository?

**Answer:**
The `main` branch was protected requiring: (1) Mandatory pull request reviews before merging, (2) Required status checks passing for the GitHub Actions CI pipeline (build, test, and restart persistence), (3) Linear commit history enforcement, and (4) Direct force-push (`git push --force`) prevention.

### Q6: What jobs and steps are executed in the GitHub Actions CI pipeline?

**Answer:**
The CI workflow (`.github/workflows/ci.yml`) triggers on every push and PR to `main`. It runs: (1) Environment provisioning with GCC/G++ and MySQL service container, (2) Database schema creation and seed injection, (3) CMake build compilation of `bank_server`, (4) Unit and pytest integration suites across all 4 candidate modules, and (5) A service restart verification job.

### Q7: How does the CI pipeline automate testing on pull requests before merging?

**Answer:**
When a PR is opened or updated, GitHub Actions spins up an ephemeral Ubuntu runner with a live MySQL service container. It compiles the C++ codebase using `g++ -Wall -Werror`, launches the backend daemon, and executes `pytest tests/integration/`. If any assertion fails or status code mismatches, the check turns red, blocking PR merge.

### Q8: What is the CI restart persistence job and why is it critical?

**Answer:**
Financial applications cannot lose state on process crash or reboot. The CI restart test initializes state (creates accounts, deposits funds, changes PINs), terminates the `bank_server` process, restarts it against the persistent MySQL volume, and verifies that balances, transaction logs, and credentials remain 100% intact and uncorrupted.

### Q9: How are environment variables and database secrets managed in CI and local environments?

**Answer:**
Local development uses `.env` files (copied from `.env.example`) containing `DB_HOST`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`, and `SERVER_PORT`, which are strictly git-ignored. In CI, secrets are supplied via GitHub Repository Secrets or container environment mappings, preventing hardcoded credentials in source control.

### Q10: What happens if a build fails or tests break in the CI pipeline?

**Answer:**
The CI pipeline terminates with an exit code non-zero, flagging the PR as failed with an orange/red status check. Pull request merges are automatically blocked. GitHub Actions logs the exact compiler error or pytest traceback, allowing the candidate to fix the issue on their feature branch and push a new commit to re-trigger CI.

### Q11: How is the C++ backend compiled and what build system is utilized?

**Answer:**
The project uses CMake / Makefile build automation. Running `make` or `cmake --build build` compiles the C++17 modular codebase into the `bank_server` binary. Header-only libraries (`cpp-httplib` for HTTP REST networking, `nlohmann/json` for serialization) eliminate heavy dynamic link dependencies, speeding up clean builds to under 5 seconds.

### Q12: How are database migrations and test seed data automated?

**Answer:**
Database management is automated via `database/schema.sql` (table definitions with constraints and indexes) and `database/seed.sql` (initial admin credentials and test accounts 1001/1002). Scripts in the repository allow one-command database reset (`mysql -u... -p... < database/schema.sql`) before test runs.

### Q13: How does the Python test suite automatically interact with the C++ backend?

**Answer:**
`tests/integration/config.py` defines a unified `call()` helper using `requests` communicating over HTTP REST with the local running server on `localhost:8080`. It wraps headers, JSON serialization, response parsing, and error decoding, allowing test suites to simulate live staff/customer web traffic programmatically.

### Q14: How does the test suite achieve test isolation across multiple test runs?

**Answer:**
Shared test fixtures utilize `make_account(opening_deposit=...)` in `tests/integration/config.py` to generate fresh, isolated accounts with distinct IDs for destructive operations (such as multiple withdrawals or closures). This avoids depleting the fixed seeded accounts (1001/1002) and prevents cross-test state leakage.

### Q15: How were code coverage and branch coverage reports generated automatically?

**Answer:**
GCC compiler flags `--coverage` (`-fprofile-arcs -ftest-coverage`) were enabled during test build compilation. Running the pytest suite exercised backend execution paths, generating `.gcda` and `.gcno` runtime traces. `gcov` and `gcov -b` were executed against candidate modules to compute precise line and branch coverage percentages.

### Q16: What is the distinction between Unit, Integration, and System tests in this project?

**Answer:**
Unit Tests (UT) validate individual function and route logic with focused payloads (e.g. valid deposit credits balance). Integration Tests (IT) verify multi-component interactions like database writing, ledger reconciliation, and restart durability. System Tests (ST) validate full end-to-end customer/staff operational journeys across sequential HTTP calls.

### Q17: What is Boundary Value Analysis and where was it applied in this system?

**Answer:**
Boundary Value Analysis evaluates system behavior at the edges of permissible input equivalence partitions. In FR-10 withdrawal rules, tests verified: (1) Withdrawing to exactly Rs. 500 remaining balance succeeds (valid boundary), (2) Withdrawing to Rs. 499.99 remaining is rejected with HTTP 400 (invalid boundary), and (3) Maximum deposit cap of Rs. 1,000,000.

### Q18: What is Fuzz / Robustness Testing and how was NFR-02 implemented?

**Answer:**
Robustness testing (NFR-02) subjected endpoints to malformed inputs: empty bodies, invalid JSON types, non-numeric strings in numeric fields, SQL special characters, and 10,000-character payload sweeps. The server must reject all hostile inputs with structured 400 Bad Request responses without crashing (500) or corrupting database records.

### Q19: What coverage thresholds were achieved for candidate modules and why does branch coverage matter?

**Answer:**
Candidate 2 achieved 84.13% line coverage and 84.77% branch coverage on `transactions_module.hpp`. Branch coverage measures whether every if/else branch decision path (e.g., balance check passing vs failing, account found vs not found) was executed. High branch coverage ensures error-handling and boundary-checking branches are genuinely verified.

### Q20: How was transaction atomicity tested during simultaneous funds transfers?

**Answer:**
Transfer tests (FR-13, NFR-03) verified that funds transfer is strictly atomic: if a debit occurs, the credit must occur. Simulated error cases (transferring more than balance, non-existent destination account, or closed account) proved that transactions roll back completely, ensuring the sender is never debited and no partial ledger rows are written.

### Q21: How does the system architecture ensure modular separation between candidate domains?

**Answer:**
The backend is structured into domain-specific modules: `candidate1_account` (lifecycle), `candidate2_transactions` (deposits/withdrawals), `candidate3_records` (transfers/statements), and `candidate4_security` (authentication/RBAC). Each module registers its routes onto a shared `httplib::Server`, decoupling implementations while sharing core database utilities.

### Q22: Why is monetary balance stored in integer cents (fixed-point) instead of double or float?

**Answer:**
Standard IEEE 754 floating-point representations introduce binary rounding imprecision (e.g., 0.1 + 0.2 = 0.30000000000000004), which can cause fraction-of-a-cent discrepancies in financial balance calculations. The system stores balances in cents (integer BIGINT / `int64_t`) and performs fixed-point math, preventing rounding errors entirely.

### Q23: How are passwords and customer PINs secured against database compromise and log leaks?

**Answer:**
Passwords and PINs are cryptographically hashed using salted hashing algorithms prior to storage; plain-text credentials never touch persistent tables. In addition, logging middleware scrubs sensitive keywords (`pin`, `password`) to prevent credential leakage into `server.log`, and API responses never echo back entered secrets.

### Q24: How does the account lockout mechanism protect against brute-force attacks (FR-21)?

**Answer:**
The security module tracks consecutive failed login attempts in the database. Upon 3 consecutive failed attempts, the identity is flagged `is_locked = TRUE`. Any subsequent login attempts return 401 Account Locked, even if the correct credential is provided. Only an authenticated staff member can unlock the account via `POST /api/auth/staff/unlock`.

### Q25: How was the transaction response time performance SLA (NFR-01) benchmarked?

**Answer:**
NFR-01 specifies that routine operations complete within 2 seconds. Pytest automated benchmarks measured 50 repeated deposit, withdraw, and balance calls, asserting p95 latency under 2.0s (measured <10ms locally). Furthermore, bulk scalability was proven by seeding 5,000 transaction rows and confirming query responses remained well under 1.0s.
