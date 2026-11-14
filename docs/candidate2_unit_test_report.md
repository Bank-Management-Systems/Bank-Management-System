# Bank Management System - Unit Test Report
**Module:** Candidate 2 - Core Banking Transactions (FR-08, FR-09, FR-10, FR-11, FR-12)  
**Author:** BharathPESU (`cdbharath234@gmail.com`)  
**Testing Period:** 2nd November 2026 – 3rd November 2026  
**Document Version:** 1.0 (Final)  
**Status:** Completed - 100% Pass Rate  

---

## 1. Executive Summary

This report documents the unit-level testing activities conducted for the **Core Banking Transactions** subsystem of the Bank Management System. All unit test cases defined in Chapter 5 of the Test Plan V2 and sprint enhancements (FR-10, FR-11, NFR-01) were executed against the compiled C++17 backend API server connected to MySQL 8.0.

- **Total Unit Test Cases:** 14
- **Passed:** 14 (100.0%)
- **Failed:** 0 (0.0%)
- **Blocked / Skipped:** 0
- **Overall Result:** **PASSED**

---

## 2. Test Environment & Configuration

| Item | Specification / Value |
|---|---|
| **Operating System** | Linux (Ubuntu x86_64, Kernel 6.8.0) |
| **Compiler** | GCC 13.2.0 (`g++ -std=c++17 -Wall -O0 --coverage`) |
| **HTTP Engine** | cpp-httplib (single-header multi-threaded server) |
| **Database** | MySQL Server 8.0.40 on `127.0.0.1:3306` (Database: `bank_db`) |
| **Server Endpoint** | `http://localhost:8081` |
| **Test Automation** | Python 3.12.3 / pytest 9.1.1 / requests 2.34.2 |
| **Execution Mode** | Automated contract tests with transactional database rollback verification |

---

## 3. Scope of Unit Testing

Candidate 2 owns all core cash operations and balance management:
1. **FR-08 (Deposit into an Existing Account):** Crediting funds to active accounts, rejecting negative/zero sums, atomic balance updates.
2. **FR-09 (Withdrawal from an Account):** Debiting funds from active accounts, maintaining ledger consistency.
3. **FR-10 (Overdraft Protection & Minimum Balance Boundary):** Strict enforcement of Rs. 500.00 minimum balance; exact boundary testing (Rs. 500.00 succeeds, Rs. 499.99 rejected); overdraft protection with zero state change.
4. **FR-11 (Amount Validation & Shared Validator):** Validation of numeric formats, positive range, maximum transaction cap ($\le$ Rs. 1,000,000.00), and at most 2 decimal places.
5. **FR-12 (Balance Inquiry):** Real-time read-only inquiry returning current balance without mutating ledger or history.

---

## 4. Detailed Unit Test Execution Results

| Test Case ID | Requirement | Test Case Description | Test Input Data | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|:---:|
| **UT_10** | FR-08 | Valid deposit increases account balance by exact amount | `account_number`: 1001<br>`amount`: 1000.00 (from 5000.00) | HTTP 200 OK; new balance equals 6000.00 (5000 + 1000) | HTTP 200 OK; returned `{"account_number": 1001, "balance": "6000.00"}` | **PASS** |
| **UT_11** | FR-08 | Deposit of zero or negative amount is rejected | `amount`: 0, -500.00 | HTTP 400 Bad Request; message naming positive amount requirement; balance unchanged | HTTP 400 Bad Request; message: "Amount must be greater than zero"; balance intact | **PASS** |
| **UT_12** | FR-08 | Boundary deposits added exactly (Rs. 1.00 and Rs. 100,000.00) | `amount`: 1.00, then 100000.00 (baseline 3000) | HTTP 200 OK; balances exact (3001.00 and 103001.00); no rounding or overflow | HTTP 200 OK; balances exact at 3001.00 and 103001.00 | **PASS** |
| **UT_13** | FR-09 | Valid withdrawal decreases balance by exact amount | `amount`: 1500.00 (baseline 5000) | HTTP 200 OK; new balance is Rs. 3500.00 (5000 - 1500) | HTTP 200 OK; returned `{"account_number": 1001, "balance": "3500.00"}` | **PASS** |
| **UT_14** | FR-09 | Withdrawal greater than balance or breaking minimum balance rejected | `amount`: 4600.00 (leaves 400 < 500 min)<br>`amount`: 6000.00 (overdraft) | HTTP 400 Bad Request; "Insufficient funds"; balance remains unchanged | HTTP 400 Bad Request; insufficient funds error returned; balance intact | **PASS** |
| **UT_15** | FR-09 | Zero and negative withdrawal amounts rejected | `amount`: 0, -500.00 | HTTP 400 Bad Request; validation error; balance unchanged | HTTP 400 Bad Request; message: "Amount must be greater than zero" | **PASS** |
| **UT_16** | FR-12 | Inquiry displays exact current balance of valid account | `account_number`: valid ID with balance 6000.00 | HTTP 200 OK; JSON payload with exact current balance | HTTP 200 OK; returned `{"account_number": 1001, "balance": "6000.00"}` | **PASS** |
| **UT_17** | FR-12 | Inquiry on non-existent account handled gracefully | `account_number`: 999999 | HTTP 404 Not Found; error message "Unknown account" | HTTP 404 Not Found; returned `{"error": "Unknown account"}` | **PASS** |
| **UT_18** | FR-12 | Inquiry on closed account reflects closed state | `account_number`: valid closed account ID | HTTP 200 OK with balance 0.00; account lookup shows status 'closed' | HTTP 200 OK; balance 0.00; lookup confirms account status is 'closed' | **PASS** |
| **UT_FR10_01** | FR-10 | Exact boundary check: leaving Rs. 500.00 succeeds; leaving Rs. 499.99 rejected | Account balance $B$; withdraw $B - 499.99$, then withdraw $B - 500.00$ | Leaving Rs. 499.99 $\rightarrow$ 400 Bad Request;<br>Leaving exactly Rs. 500.00 $\rightarrow$ 200 OK | Leaving 499.99 returned 400 naming minimum balance; leaving exactly 500.00 returned 200 | **PASS** |
| **UT_FR10_02** | FR-10 | Overdraft protection: withdrawal exceeding balance causes zero state change | `amount`: $B + 500.00$ | HTTP 400 Bad Request; zero partial debit; no row written to transactions table | HTTP 400 Bad Request; balance unchanged; zero transaction ledger rows added | **PASS** |
| **UT_FR11_01** | FR-11 | Amount validation sweep across invalid classes on deposit | 20 invalid classes: 0, -1, "abc", "", boolean, null, > 1M, 3 decimals | All invalid classes rejected with HTTP 400 Bad Request; balance completely untouched | All 20 invalid test classes rejected with HTTP 400 and descriptive messages | **PASS** |
| **UT_FR11_02** | FR-11 | Amount validation sweep across invalid classes on withdrawal | Invalid classes: 0, -1, "abc", > 1M, 3 decimals | All invalid withdrawal amounts rejected with HTTP 400; balance completely untouched | All invalid withdrawal attempts rejected with clean HTTP 400 | **PASS** |
| **UT_FR11_03** | FR-11 | Boundary amount acceptance (Rs. 1,000,000.00 cap and 2 decimals) | `amount`: 500.25 (2 decimals)<br>`amount`: 1000000.00 (upper cap) | HTTP 200 OK; exact balance arithmetic executed without truncation | HTTP 200 OK; Rs. 500.25 and Rs. 1,000,000.00 accepted and added accurately | **PASS** |

---

## 5. Defect Retest & Verification Summary

1. **DEF-01 (Boundary Comparison Operator in Withdrawal):**
   - *Issue:* Balance comparison logic originally used `<` instead of `<=` when checking available funds against remaining minimum balance.
   - *Fix:* Aligned boundary condition in `transactions_module.hpp` using integer cents arithmetic (`remaining_cents < candidate2::MIN_BALANCE_CENTS`).
   - *Retest Result:* **PASS** (Verified by test `test_fr10_withdraw_boundary_exact_500_succeeds_and_499_99_rejected`).

2. **DEF-05 (Negative Amount String Parsing):**
   - *Issue:* Negative numeric strings like `"-500.00"` could parse without sign validation in preliminary helper stubs.
   - *Fix:* Hardened shared validator in `common/http_utils.hpp` to strictly check for negative signs and reject them early.
   - *Retest Result:* **PASS** (Verified by test `test_fr11_amount_validation_invalid_class_sweep_deposit`).

3. **DEF-06 (Floating Point Precision Near Minimum Balance Boundary):**
   - *Issue:* IEEE-754 binary floating-point representation artifacts could cause amounts like `499.99999999999994` to misclassify.
   - *Fix:* Adopted fixed-point integer cents representation (`std::llround(amount * 100.0)`) for all financial comparison operations.
   - *Retest Result:* **PASS** (Verified by test `test_fr10_withdraw_boundary_exact_500_succeeds_and_499_99_rejected`).

---

## 6. Unit Testing Conclusion & Sign-off

All 14 unit test cases for Candidate 2 have executed successfully with zero failures and zero regressions. The Candidate 2 transaction logic satisfies all requirements of FR-08, FR-09, FR-10, FR-11, and FR-12.

**Signed off by:**  
**BharathPESU** (`cdbharath234@gmail.com`)  
Candidate 2 - Core Banking Transactions Subsystem Owner  
Date: 3rd November 2026  
