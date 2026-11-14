# Bank Management System - Unit Test Report
**Module:** Candidate 4 - Security & Authentication (FR-18, FR-19, FR-20)  
**Author:** Ajay T Naik (`aajaytnaik705@gmail.com`)  
**Testing Period:** 2nd November 2026 – 6th November 2026  
**Document Version:** 1.0 (Final)  
**Status:** Completed - 100% Pass Rate  

---

## 1. Executive Summary

This report documents the unit-level testing activities conducted for the **Security & Authentication** subsystem of the Bank Management System. All unit test cases defined in Chapter 7 (Tables 19, 20, 21) of the Test Plan V2 were executed against the compiled C++17 backend API server connected to MySQL 8.0.

- **Total Unit Test Cases:** 9 (UT_28 through UT_36)
- **Passed:** 9 (100.0%)
- **Failed:** 0 (0.0%)
- **Blocked / Skipped:** 0
- **Overall Result:** **PASSED**

---

## 2. Test Environment & Configuration

| Item | Specification / Value |
|---|---|
| **Operating System** | Linux (Ubuntu x86_64, Kernel 6.8.0 / WSL2) |
| **Compiler** | GCC 11.4.0 (`g++ -std=c++17 -Wall -O0 --coverage`) |
| **HTTP Engine** | cpp-httplib (single-header multi-threaded server) |
| **Database** | MySQL Server 8.0.40 on `127.0.0.1:3306` (Database: `bank_db`) |
| **Server Endpoint** | `http://localhost:8080` |
| **Test Automation** | Python 3.10.12 / pytest 9.2.0 / requests 2.25.1 / coverage.py 7.16.2 |
| **Execution Mode** | Automated contract tests with transactional database state verification |

---

## 3. Scope of Unit Testing

Candidate 4 owns all core authentication, role management, and credential lifecycle operations:
1. **FR-18 (Staff Authentication):** Verification of administrative credentials, bearer token generation, clean generic failure responses, and masking against credential enumeration attacks.
2. **FR-19 (Customer Authentication):** Validating customer account number and PIN pairs, issuing account-scoped tokens, rejecting unauthorized attempts, and graceful handling of unknown accounts.
3. **FR-20 (Customer PIN Management):** Enforcing current PIN verification, validating new PIN length (4–6 digits) and numeric composition, ensuring credential non-reuse, and enforcing immediate switchover.

---

## 4. Detailed Unit Test Execution Results

| Test Case ID | Requirement | Test Case Description | Test Input Data | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|:---:|
| **UT_28** | FR-18 | Valid staff credentials grant access to administrative operations | `username`: "admin"<br>`password`: "admin123" | HTTP 200 OK; payload returns `role: "staff"`, `is_admin: true`, and bearer token | HTTP 200 OK; returned `{"role": "staff", "username": "admin", "is_admin": true, "token": "staff_1_token"}` | **PASS** |
| **UT_29** | FR-18 | Wrong staff password is denied with generic error message | `username`: "admin"<br>`password`: "definitely-wrong-password" | HTTP 401 Unauthorized; clean error JSON; zero tokens issued | HTTP 401 Unauthorized; returned `{"error": "Invalid credentials"}`; no token leaked | **PASS** |
| **UT_30** | FR-18 | Unknown staff username is denied without revealing user existence | `username`: "ghost99"<br>`password`: "arbitraryPassword123!" | HTTP 401 Unauthorized; generic error message identical to wrong password | HTTP 401 Unauthorized; returned `{"error": "Invalid credentials"}`; user enumeration prevented | **PASS** |
| **UT_31** | FR-19 | Valid customer account number and PIN grant customer access | `account_number`: 1001<br>`pin`: "1234" | HTTP 200 OK; payload returns `role: "customer"`, account number, and customer token | HTTP 200 OK; returned `{"role": "customer", "account_number": 1001, "token": "cust_1001_token"}` | **PASS** |
| **UT_32** | FR-19 | Wrong PIN is denied and failed attempt is registered | `account_number`: 1001<br>`pin`: "0000" | HTTP 401 Unauthorized; generic error message; failed attempt incremented | HTTP 401 Unauthorized; returned `{"error": "Invalid credentials"}`; failed attempt logged | **PASS** |
| **UT_33** | FR-19 | Unknown account number is denied without crashing or leaking details | `account_number`: 999999<br>`pin`: "1234" | HTTP 401 Unauthorized; generic error message; server remains stable | HTTP 401 Unauthorized; returned `{"error": "Invalid credentials"}`; server responsive | **PASS** |
| **UT_34** | FR-20 | Valid PIN change succeeds and new PIN is immediately enforced | `account_number`: valid ID<br>`old_pin`: "1234"<br>`new_pin`: "4561" | HTTP 200 OK; confirmation message; old PIN fails (401), new PIN succeeds (200) | HTTP 200 OK; returned `{"account_number": 1005, "message": "PIN changed"}`; new PIN enforced | **PASS** |
| **UT_35** | FR-20 | Wrong old PIN blocks change and keeps existing PIN active | `old_pin`: "9999"<br>`new_pin`: "4561" | HTTP 401 Unauthorized; error naming invalid old PIN; current PIN remains valid | HTTP 401 Unauthorized; returned `{"error": "Invalid old PIN"}`; existing PIN 1234 valid | **PASS** |
| **UT_36** | FR-20 | New PIN violating format rules is rejected | `new_pin`: "12", "123", "1234567", "ABCD", "12a4", "12 34" | HTTP 400 Bad Request; format validation error; existing PIN remains intact | HTTP 400 Bad Request across all invalid formats; existing PIN operational | **PASS** |

---

## 5. Defect Retest & Verification Summary

During the execution of the unit test suite, one critical defect was identified and successfully resolved:

1. **DEF-07 (Default PIN 1234 Fallback Overwriting Active Changed PIN):**
   - *Requirement:* FR-20 (Customer PIN Management) & FR-19 (Customer Authentication).
   - *Discovered by:* `UT_34` (Valid PIN change enforcement).
   - *Issue Description:* In `backend/candidate4_security/security_module.hpp`, when customer authentication failed for any attempted credentials, the handler checked if `pin == "1234"`. If true, an upsert query (`INSERT INTO users ... ON DUPLICATE KEY UPDATE secret_hash = VALUES(secret_hash)`) was executed to auto-seed default credentials for new accounts. However, this query executed even when the user record already existed, inadvertently overwriting the user's updated PIN back to `"1234"`.
   - *Root Cause:* Absence of a pre-check verifying whether a `users` record already existed for that account number before executing the auto-provisioning logic.
   - *Fix Applied:* Modified `security_module.hpp` to query `users` first. The fallback auto-provisioning of `"1234"` is strictly restricted to accounts that do not have an existing row in `users`. For existing users, invalid PINs immediately route to failure handling (`failed_tries + 1` and HTTP 401).
   - *Retest Result:* **PASS** (Verified by `test_ut34_pin_change_valid_succeeds_and_enforced`, `test_it36_pin_change_switchover_immediacy`, and `test_st24_pin_lockout_counting_applies_to_active_pin_after_change`).

---

## 6. Unit Testing Conclusion & Sign-off

All 9 unit test cases for Candidate 4 have executed successfully with a 100% pass rate. The authentication mechanisms, generic error handling, and PIN format validation strictly fulfill the security requirements of FR-18, FR-19, and FR-20.

**Signed off by:**  
**Ajay T Naik** (`aajaytnaik705@gmail.com`)  
Candidate 4 - Security & Authentication Subsystem Owner  
Date: 6th November 2026  
