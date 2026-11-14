# Bank Management System - Branch Coverage Report
**Subsystem:** Candidate 2 - Core Banking Transactions (`backend/candidate2_transactions`) & Validation Infrastructure  
**Author:** BharathPESU (`cdbharath234@gmail.com`)  
**Assessment Date:** 6th November 2026  
**Document Version:** 1.0 (Final)  
**Quality Gate Status:** PASSED (All Decision Logic Paths Exercised)  

---

## 1. Executive Summary

This report presents the branch and decision coverage analysis for Candidate 2 (Core Banking Transactions) and shared validation logic of the Bank Management System. Branch coverage metrics were captured using GCC's native `-fprofile-arcs -ftest-coverage` tooling with the `gcov -b` (branch analysis) flag.

- **Candidate 2 Module (`transactions_module.hpp`):** **84.77% Branch Execution** (334 / 394 branches executed)
- **Shared Validation Utilities (`http_utils.hpp`):** **54.61% Branch Execution** (166 / 304 branches executed)
- **Database Wrapper (`db.hpp`):** **79.41% Branch Execution** (54 / 68 branches executed)
- **Explicit Logical Decision Branches (Programmer `if/else`):** **100% Tested** (Both True and False branches evaluated)

---

## 2. Methodology & Compiler Mechanics

GCC evaluates branch coverage at the intermediate representation (GIMPLE/RTL) level:
1. **Explicit Control Flow Branches:** Explicit programmer decisions including `if`, `else`, ternary operators, and loop exit conditions.
2. **Implicit Exception Unwind Branches:** In C++17, every standard library operation (such as `std::string` allocation, concatenation, stream formatting, and JSON parsing) generates compiler-generated exception landing-pad branches (`__cxa_throw` / unwind paths).
3. **Taken-Branch Mechanics:** In standard operating conditions without memory exhaustion, unwind branches are evaluated by the CPU but not taken, which explains why total taken percentages settle around 47% while executable branch coverage reaches $\sim$85%.

---

## 3. Subsystem Branch Coverage Summary

| File / Component | Primary Responsibility | Total Branches | Branches Executed | Taken at Least Once | Branch Exec Rate (%) | Logical Coverage |
|---|---|:---:|:---:|:---:|:---:|:---:|
| `backend/candidate2_transactions/transactions_module.hpp` | Deposit, withdrawal, overdraft protection, balance inquiry | 394 | 334 | 186 | **84.77%** | **100%** |
| `backend/common/http_utils.hpp` | Amount validation, JSON parsing, error handlers | 304 | 166 | 91 | **54.61%** | **100%** |
| `backend/common/db.hpp` | MySQL connection pool and transactional queries | 68 | 54 | 29 | **79.41%** | **100%** |
| `backend/main.cpp` | Bootstrap, candidate routes, signal handling | 70 | 56 | 28 | **80.00%** | **100%** |
| **Candidate 2 Combined Path** | **Combined Execution Path** | **836** | **610** | **334** | **72.97%** | **100%** |

---

## 4. Detailed Decision Logic & Branch Truth Table

The table below catalogs every critical decision branch in Candidate 2, demonstrating that both the positive (True) and negative (False) paths are systematically tested.

| Decision Point | Location | Condition Tested | True Path (Condition Met) | False Path (Condition Not Met) | Test Case Verifying |
|---|---|---|---|---|---|
| **D-01** | `transactions_module.hpp`<br>L63 | `!validate_amount(req.body, ...)` | Returns HTTP 400 Bad Request ("Invalid amount format") | Continues to begin database transaction | `test_fr11_amount_validation_invalid_class_sweep_deposit`<br>`test_fr08_deposit_increases_balance` |
| **D-02** | `transactions_module.hpp`<br>L74 | `!result` (SELECT in Deposit) | Rollback; returns HTTP 500 Database Error | Proceeds to fetch account row | Covered via DB error simulation |
| **D-03** | `transactions_module.hpp`<br>L81 | `!row` (Deposit account lookup) | Rollback; returns HTTP 404 Unknown Account | Proceeds to check account status | `test_it11_deposit_nonexistent_or_closed_rejected`<br>`test_fr08_deposit_increases_balance` |
| **D-04** | `transactions_module.hpp`<br>L89 | `status == "closed"` (Deposit) | Rollback; returns HTTP 400 ("Account is closed") | Proceeds to calculate new balance | `test_it11_deposit_nonexistent_or_closed_rejected`<br>`test_fr08_deposit_increases_balance` |
| **D-05** | `transactions_module.hpp`<br>L140 | `!validate_amount(req.body, ...)` | Returns HTTP 400 Bad Request | Continues to begin database transaction | `test_fr11_amount_validation_invalid_class_sweep_withdraw`<br>`test_fr09_withdraw_within_balance_succeeds` |
| **D-06** | `transactions_module.hpp`<br>L158 | `!row` (Withdrawal account lookup) | Rollback; returns HTTP 404 Unknown Account | Proceeds to check account status | `test_it15_withdrawal_nonexistent_or_closed_rejected`<br>`test_fr09_withdraw_within_balance_succeeds` |
| **D-07** | `transactions_module.hpp`<br>L166 | `status == "closed"` (Withdrawal) | Rollback; returns HTTP 400 ("Account is closed") | Proceeds to overdraft evaluation | `test_it15_withdrawal_nonexistent_or_closed_rejected`<br>`test_fr09_withdraw_within_balance_succeeds` |
| **D-08** | `transactions_module.hpp`<br>L180 | `amount_cents > balance_cents` | Rollback; returns HTTP 400 ("Insufficient funds: exceeds balance") | Proceeds to minimum balance check | `test_fr10_withdraw_overdraft_protection_no_state_change`<br>`test_fr09_withdraw_within_balance_succeeds` |
| **D-09** | `transactions_module.hpp`<br>L189 | `remaining_cents < 50000LL` | Rollback; returns HTTP 400 ("Minimum balance of Rs. 500 must be maintained") | Proceeds to execute debit and record ledger | `test_fr10_withdraw_boundary_exact_500_succeeds_and_499_99_rejected`<br>`test_fr09_withdraw_within_balance_succeeds` |
| **D-10** | `transactions_module.hpp`<br>L238 | `!row` (Balance inquiry) | Returns HTTP 404 Not Found ("Unknown account") | Returns HTTP 200 with current balance JSON | `test_fr12_unknown_account_returns_404`<br>`test_fr12_balance_inquiry_returns_current_balance` |

---

## 5. Boundary Value & Robustness Analysis

1. **Minimum Balance Boundary (Threshold: Rs. 500.00 Remaining):**
   - Remaining = Rs. 499.99 ($N-1$): Tested via `test_fr10_withdraw_boundary_exact_500_succeeds_and_499_99_rejected` $\rightarrow$ Evaluated to True $\rightarrow$ 400 Bad Request.
   - Remaining = Rs. 500.00 ($N$): Tested via `test_fr10_withdraw_boundary_exact_500_succeeds_and_499_99_rejected` $\rightarrow$ Evaluated to False $\rightarrow$ 200 OK.
   - Remaining = Rs. 500.01 ($N+1$): Allowed with 200 OK.
2. **Transaction Amount Cap (Threshold: Rs. 1,000,000.00):**
   - $N$ (Rs. 1,000,000.00): Tested via `test_fr11_amount_validation_boundary_accepted` $\rightarrow$ Accepted with 200 OK.
   - $N+1$ cent (Rs. 1,000,000.01): Tested via `test_fr11_amount_validation_invalid_class_sweep_deposit` $\rightarrow$ Rejected with 400 Bad Request.
3. **Decimal Precision Limits (Threshold: 2 Decimal Places):**
   - 2 decimals ("500.25"): Accepted with 200 OK.
   - 3 decimals ("10.555"): Rejected with 400 Bad Request.
4. **Zero & Negative Value Boundaries:**
   - Amount = Rs. 0.00: Rejected with 400 Bad Request.
   - Amount = -Rs. 500.00: Rejected with 400 Bad Request.
   - Amount = Rs. 0.01: Accepted with 200 OK (if balance allows).

---

## 6. Branch Coverage Verification & Sign-off

The Core Banking Transactions subsystem has attained **84.77%** branch execution in `transactions_module.hpp`. Every programmer decision condition and financial threshold has been thoroughly exercised in both directions, confirming robust protection against overdrafts, precision loss, and invalid inputs.

**Approved by:**  
**BharathPESU** (`cdbharath234@gmail.com`)  
Candidate 2 Subsystem Owner  
Date: 6th November 2026  
