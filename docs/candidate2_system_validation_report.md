# Bank Management System - System Validation Report
**Subsystem:** Candidate 2 - Core Banking Transactions (FR-08, FR-09, FR-10, FR-11, FR-12, NFR-01)  
**Lead Author:** BharathPESU (`cdbharath234@gmail.com`)  
**Validation Period:** 4th November 2026 – 6th November 2026  
**Document Version:** 1.0 (Final)  
**Status:** System Validated - Production Ready  

---

## 1. Executive Summary

This report documents the system validation and end-to-end integration results for **Candidate 2 (Core Banking Transactions)** in the Bank Management System. Testing verified end-to-end customer and staff workflows, concurrency and restart persistence, minimum balance boundaries, ledger auditability, and non-functional performance SLAs (NFR-01).

- **Candidate 2 System & Integration Tests:** 18 / 18 Passed (100.0%)
- **Total System Regression Test Suite:** 79 / 79 Passed (100.0%)
- **Performance Budget Compliance (NFR-01):** 100% within SLA (p95 $< 100$ ms, target $< 1.0$ s, hard limit $< 2.0$ s)
- **Critical & High Severity Defects:** 0 Unresolved
- **System Validation Verdict:** **PASSED & APPROVED FOR PRODUCTION**

---

## 2. System Architecture & Money Movement Workflow

```
       [Customer Self-Service / Staff Counter Client]
                             |
                             | HTTP REST (POST /deposit, POST /withdraw, GET /balance)
                             v
           +------------------------------------+
           |  Candidate 2 Transactions Module   |
           |    - Shared Amount Validator       |
           |    - Fixed-Point Cents Arithmetic  |
           |    - Overdraft Protection Logic    |
           +------------------------------------+
                             |
            ACID Transaction (START TRANSACTION)
            SELECT ... FOR UPDATE (Row Locking)
                             v
           +------------------------------------+
           |            MySQL 8.0               |
           |  - accounts (balance update)       |
           |  - transactions (audit ledger)     |
           +------------------------------------+
```

---

## 3. Detailed System Validation Scenarios

| Test Case ID | Test Scenario | Preconditions & Execution Steps | Test Data | Expected System Behavior | Observed Result | Status |
|---|---|---|---|---|---|:---:|
| **ST_07** | Customer deposit end-to-end | 1. Customer logs in.<br>2. Deposits Rs. 2000.<br>3. Inquires balance.<br>4. Checks history. | Account: 1001<br>Deposit: Rs. 2000.00 | Balance increases by Rs. 2000; transaction logged; clean session exit | Balance updated to Rs. 7000.00; ledger row verified; session clean | **PASS** |
| **ST_08** | Staff multiple deposit accumulation | 1. Staff opens counter.<br>2. Deposits Rs. 500, 1500, 2000 in sequence.<br>3. Verifies final balance. | Account: 1002 (base 3000)<br>Deposits: 500, 1500, 2000 | Final balance equals Rs. 7000.00 (3000 + 4000); transactions logged in order | Final balance exact at Rs. 7000.00; 3 rows logged in execution order | **PASS** |
| **ST_09** | Customer withdrawal end-to-end | 1. Customer logs in.<br>2. Withdraws Rs. 1200.<br>3. Inquires balance.<br>4. Checks history. | Account: valid ID (base 5000)<br>Withdrawal: Rs. 1200.00 | Balance decreases to Rs. 3800.00; withdrawal row logged with timestamp | Balance shows Rs. 3800.00; withdrawal entry logged; session completed | **PASS** |
| **ST_10** | Repeated withdrawals enforcing minimum balance | 1. Account balance Rs. 5500.<br>2. Withdraw Rs. 1000 five times.<br>3. Attempt 6th withdrawal of Rs. 100. | Account: base 5500<br>Withdrawals: 5 $\times$ 1000, then 100 | First five succeed down to Rs. 500.00; 6th rejected; balance remains Rs. 500.00 | First 5 withdrawals succeeded; 6th rejected with 400; final balance Rs. 500.00 | **PASS** |
| **ST_11** | Customer self-service balance inquiry | 1. Customer authenticates.<br>2. Queries current balance.<br>3. Re-queries after session restart. | Account: valid ID (base 5000) | Correct balance displayed in both queries; zero cross-account leakage | Exactly Rs. 5000.00 displayed across sessions | **PASS** |
| **ST_12** | Staff counter multiple inquiries | 1. Staff queries Account 1002.<br>2. Queries Account 1003.<br>3. Re-queries Account 1002. | Accounts: 1002 (4000), 1003 (7000) | Inquiries return correct respective balances without crosstalk | 4000.00, 7000.00, 4000.00 returned accurately | **PASS** |
| **IT_10** | Deposit writes transaction log | Deposit Rs. 750 into active account | Deposit: Rs. 750.00 | Database `transactions` table contains row with type `DEPOSIT` and amount 750 | Row verified in database with exact amount, type, and updated balance | **PASS** |
| **IT_11** | Deposit to non-existent / closed account | 1. Deposit into 1999.<br>2. Deposit into closed account. | Targets: 1999, closed ID | Unknown $\rightarrow$ 404; Closed $\rightarrow$ 400; zero transaction rows logged | 404 returned for 1999; 400 returned for closed account; 0 rows added | **PASS** |
| **IT_12** | Deposited balance restart persistence | 1. Deposit Rs. 1000 (base 6000).<br>2. Restart server process.<br>3. Inquire balance. | Deposit: Rs. 1000.00 | Balance shows Rs. 7000.00 after server recovery | Balance shows Rs. 7000.00 after restart; zero data loss | **PASS** |
| **IT_13** | Withdrawal writes transaction log | Withdraw Rs. 600 from active account | Withdrawal: Rs. 600.00 | Row in `transactions` with type `WITHDRAWAL` and balance_after updated | Row verified with type `WITHDRAWAL`, amount 600.00, balance 2400.00 | **PASS** |
| **IT_14** | Deposit + withdrawal nets zero change | 1. Deposit Rs. 1000.<br>2. Withdraw Rs. 1000.<br>3. Check balance and history. | Amounts: +1000, -1000 | Balance returns to Rs. 5000; both entries logged chronologically | Balance exactly Rs. 5000.00; both entries present in ledger | **PASS** |
| **IT_15** | Withdrawal from non-existent / closed account | 1. Withdraw from 1999.<br>2. Withdraw from closed ID. | Targets: 1999, closed ID | Unknown $\rightarrow$ 404; Closed $\rightarrow$ 400; zero balance changes | 404 returned for 1999; 400 returned for closed account | **PASS** |
| **IT_16** | Inquiry reflects immediate transaction | 1. Deposit Rs. 300.<br>2. Immediate balance inquiry. | Deposit: Rs. 300.00 | Balance inquiry reflects Rs. 6300 without lag | Inquiry returned Rs. 6300.00 immediately | **PASS** |
| **IT_17** | Inquiry restart persistence | Query balance before and after restart | Account: valid ID | Both inquiry results identical | Pre- and post-restart balances identical at Rs. 5500.00 | **PASS** |
| **IT_18** | Inquiry does not log transactions | Perform repeated balance inquiries | 2 $\times$ GET `/api/accounts/{id}/balance` | Transaction history row count unchanged | Count before = count after; inquiries are purely read-only | **PASS** |

---

## 4. NFR-01 Performance SLA & Latency Analysis

Candidate 2 executed extensive performance benchmarking to validate compliance with the NFR-01 SLA budgets:
- **Target Latency:** Under 1.0 second (typically $< 100$ ms)
- **Hard Latency Limit:** Under 2.0 seconds

| Performance Benchmark | Sample Size / Volume | Observed Metric | SLA Target | Compliance Status |
|---|---|---|---|:---:|
| **Repeatable Deposit Timing** | 50 consecutive calls | p50 = **1.45 ms**, p95 = **3.20 ms** | p95 $< 2.0$ s | **PASS** (100% within SLA) |
| **Repeatable Withdrawal Timing** | 50 consecutive calls | p50 = **1.52 ms**, p95 = **3.45 ms** | p95 $< 2.0$ s | **PASS** (100% within SLA) |
| **Repeatable Balance Inquiry Timing** | 50 consecutive calls | p50 = **0.85 ms**, p95 = **1.90 ms** | p95 $< 2.0$ s | **PASS** (100% within SLA) |
| **Bulk Growth Balance Query** | Account with 5,000 ledger rows | Elapsed = **1.20 ms** | $< 1.0$ s | **PASS** (Zero degradation) |
| **Bulk Growth History Query** | Account with 5,000 ledger rows | Elapsed = **18.50 ms** (count $\ge 5000$) | $< 1.0$ s | **PASS** (Indexed lookup) |
| **Sustained Session (100 ops)** | 100 mixed ops (deposit/withdraw/balance) | First 20 median = **1.2 ms**<br>Last 20 median = **1.3 ms** | Zero degradation | **PASS** (Stable throughput) |

---

## 5. Cross-Subsystem Integration Regression

Candidate 2 transactions were verified in conjunction with the other subsystem modules:
- **Candidate 1 x Candidate 2:** Newly created accounts are immediately usable for deposits and withdrawals; closed accounts reject transactions cleanly.
- **Candidate 2 x Candidate 3:** Deposits and withdrawals create immutable transaction records correctly consumed by Candidate 3 transfer history and account statements.
- **Candidate 2 x Candidate 4:** Authenticated customer sessions can query balance and initiate withdrawals within authorized limits.
- **Regression Suite:** All **79 tests** passed across Candidates 1, 2, 3, 4, and health probes.

---

## 6. System Validation Sign-off

The Core Banking Transactions subsystem (Candidate 2) has met all functional and non-functional requirements with 100% pass rate. Financial ledger integrity, fixed-point precision, minimum balance boundaries, and sub-second performance budgets are completely validated.

**System Validation Status:** **PASSED & APPROVED FOR PRODUCTION**

**Sign-off:**  
**BharathPESU** (`cdbharath234@gmail.com`)  
Candidate 2 Subsystem Owner  
Date: 6th November 2026  
