# Bank Management System - Unit Test Report
**Module:** Candidate 1 - Account Management (FR-01, FR-02, FR-03, FR-04, FR-05, NFR-02)  
**Author:** Pavan R Lamani (`lamanipavan495@gmail.com`)  
**Testing Period:** 2nd November 2026 – 3rd November 2026  
**Document Version:** 1.0 (Final)  
**Status:** Completed - 100% Pass Rate  

---

## 1. Executive Summary

This report documents the unit-level testing activities conducted for the **Account Management** subsystem of the Bank Management System. All unit test cases defined in Chapter 4 of the Test Plan V2 and sprint enhancements (FR-02, FR-03, and NFR-02) were executed against the compiled C++17 backend API server connected to MySQL 8.0.

- **Total Unit Test Cases:** 16
- **Passed:** 16 (100.0%)
- **Failed:** 0 (0.0%)
- **Blocked / Skipped:** 0
- **Overall Result:** **PASSED**

---

## 2. Test Environment and Configuration

| Item | Specification / Value |
|---|---|
| **Operating System** | Linux (Ubuntu x86_64, Kernel 6.8.0) |
| **Compiler** | GCC 13.2.0 (`g++ -std=c++17 -Wall -O0 --coverage`) |
| **HTTP Framework** | cpp-httplib (single-header multithreaded server) |
| **Database** | MySQL Server 8.0.40 on `127.0.0.1:3306` (Database: `bank_db`) |
| **Server Endpoint** | `http://localhost:8081` |
| **Test Framework** | Python 3.12.3 / pytest 9.1.1 / requests 2.34.2 |
| **Execution Mode** | Automated contract tests with live database verification |

---

## 3. Scope of Unit Testing

Candidate 1 owns the complete lifecycle of customer bank accounts:
1. **FR-01 (Create New Bank Account):** Valid account provisioning, mandatory field validation, opening deposit threshold enforcement.
2. **FR-02 (Account Numbering & Continuity):** Monotonic sequence generation starting at $\ge 1001$, client override immunity, sequence continuity.
3. **FR-03 (Account Lookup Details & Freshness):** Single account lookup endpoint (`GET /api/accounts/{id}`) with structured JSON fields and 404 handling.
4. **FR-04 (Modify Customer Details):** Updating mutable customer fields (address, contact number) while keeping account number and balance immutable.
5. **FR-05 (Close Account):** Enforcing zero-balance condition for closure, status updating, and immutable ledger history.
6. **NFR-02 (Input Validation & Server Robustness):** Defense against hostile payloads, malformed JSON, oversized buffers, and non-numeric inputs.

---

## 4. Detailed Unit Test Execution Results

| Test Case ID | Requirement | Test Case Description | Test Input Data | Expected Result | Actual Result | Status |
|---|---|---|---|---|---|:---:|
| **UT_01** | FR-01 | Create account with valid customer details and qualifying opening deposit | `name`: "Rahul Sharma"<br>`address`: "12 MG Road"<br>`contact`: "9876543210"<br>`type`: "Savings"<br>`opening_deposit`: 5000.00 | HTTP 201 Created; returns auto-assigned account number $\ge 1001$; status 'active'; record saved | HTTP 201 Created; returned `{"account_number": 1001, "balance": 5000.00}`; record persisted with status 'active' | **PASS** |
| **UT_02** | FR-01 | Reject account creation when mandatory field `name` is blank | `name`: ""<br>`address`: "12 MG Road"<br>`contact`: "9876543210"<br>`type`: "Savings"<br>`opening_deposit`: 5000.00 | HTTP 400 Bad Request; error message indicating name cannot be empty; no record created | HTTP 400 Bad Request; message: "Field name is mandatory"; 0 rows inserted into DB | **PASS** |
| **UT_03** | FR-01 | Reject opening deposit below minimum balance rule (boundary: 499 vs 500) | `name`: "Low Deposit"<br>`address`: "2 MG Road"<br>`contact`: "9876500002"<br>`type`: "Savings"<br>`opening_deposit`: 499.00 | HTTP 400 Bad Request; message stating deposit must be at least Rs. 500; no record created | HTTP 400 Bad Request; message: "Opening deposit must be at least 500.00"; rejected | **PASS** |
| **UT_04** | FR-04 | Update address of an existing account with a valid string | `account_number`: valid ID<br>`address`: "45 Brigade Towers"<br>`contact`: "9876599999" | HTTP 200 OK; address updated in DB and returned in response payload | HTTP 200 OK; response `{"address": "45 Brigade Towers", ...}`; DB updated | **PASS** |
| **UT_05** | FR-04 | Reject modification on non-existent account number | `account_number`: 999999<br>`address`: "Nowhere Lane"<br>`contact`: "9876543210" | HTTP 404 Not Found; error message "Unknown account"; no records altered | HTTP 404 Not Found; response `{"error": "Unknown account"}`; state unchanged | **PASS** |
| **UT_06** | FR-04 | Reject invalid contact number during customer modification | `contact`: "98765ABCDE" (contains non-numeric characters) | HTTP 400 Bad Request; validation error; stored contact unchanged | HTTP 400 Bad Request; message: "Contact must contain only digits (10-15 digits)"; rejected | **PASS** |
| **UT_07** | FR-05 | Close account whose balance has been reconciled to Rs. 0.00 | `account_number`: valid ID with balance = 0.00 | HTTP 200 OK; account marked 'closed'; confirmation message returned | HTTP 200 OK; response `{"status": "closed", "message": "Account closed successfully"}` | **PASS** |
| **UT_08** | FR-05 | Block account closure when account still holds funds (> 0) | `account_number`: valid ID with balance = 6000.00 | HTTP 400 Bad Request; closure refused; account status remains 'active' | HTTP 400 Bad Request; message: "Account balance must be zero before closing"; status 'active' | **PASS** |
| **UT_09** | FR-05 | Reject closure on non-existent account number | `account_number`: 999999 | HTTP 404 Not Found; error message indicating account does not exist | HTTP 404 Not Found; response `{"error": "Unknown account"}` | **PASS** |
| **UT_FR02_01** | FR-02 | Monotonic sequence generation: consecutive creations increment by +1 | Consecutive calls to `POST /api/accounts` | Account $N+1$ equals Account $N + 1$; strictly monotonic increasing | Account 1002 assigned immediately after Account 1001; strictly sequential | **PASS** |
| **UT_FR02_02** | FR-02 | Client override immunity: manual `account_number` in request body ignored | `POST /api/accounts` with payload `{"account_number": 99999, ...}` | Client-supplied number ignored; server assigns next sequence ID | Client number 99999 discarded; server auto-assigned valid sequential ID $\ge 1001$ | **PASS** |
| **UT_FR03_01** | FR-03 | Account lookup returns complete customer profile | `GET /api/accounts/{id}` for existing account | HTTP 200 OK; all 8 fields present (`account_number`, `name`, `address`, `contact`, `type`, `status`, `balance`, `created_at`) | HTTP 200 OK; exact JSON structure returned with accurate data matching creation | **PASS** |
| **UT_FR03_02** | FR-03 | Account lookup returns 404 for unknown or malformed identifier | `GET /api/accounts/0`<br>`GET /api/accounts/not_a_number` | HTTP 404 Not Found with structured error JSON | HTTP 404 Not Found returned for both unknown numeric and non-numeric paths | **PASS** |
| **NT_01** | NFR-02 | Malformed JSON and empty body handling | Empty body `""`<br>Plain text `"not a json"`<br>Truncated `{"name": "Broken` | HTTP 400 Bad Request; server remains healthy; no 500 internal errors or hangs | Clean HTTP 400 Bad Request returned across all malformed variants | **PASS** |
| **NT_02** | NFR-02 | Oversized string payloads and control characters | Name = 10,000 'A's<br>Address = 10,000 'B's<br>Control chars `\u0000`, `\u0007` | HTTP 400 Bad Request; rejected early before DB query execution | HTTP 400 Bad Request; payload length caps and control character checks enforced | **PASS** |
| **NT_03** | NFR-02 | Non-numeric or invalid currency formats in numeric fields | `opening_deposit`: "five-thousand"<br>`opening_deposit`: "₹5000"<br>`opening_deposit`: -500 | HTTP 400 Bad Request; invalid numeric formats rejected cleanly | HTTP 400 Bad Request; negative and non-numeric deposits rejected | **PASS** |

---

## 5. Defect Retest and Verification Summary

During the initial testing phase on 2nd November 2026, three defects were uncovered and addressed:

1. **DEF-02 (Unicode-Escaped Control Characters):**
   - *Issue:* Unicode-escaped sequences (`\u0000`, `\u0007`) in JSON strings bypassed the raw ASCII control character check.
   - *Fix:* Enhanced `has_control_chars` in `backend/common/http_utils.hpp` to parse and detect JSON unicode-escaped control character sequences.
   - *Retest Result:* **PASS** (Verified by test `test_nfr02_oversized_payload_and_string_fields`).

2. **DEF-03 (Client-Supplied Account Number Override):**
   - *Issue:* Client payload containing `"account_number": 99999` was not explicitly stripped before query preparation.
   - *Fix:* Hardened `backend/candidate1_account/account_module.hpp` to discard any client-provided account number and rely strictly on MySQL `AUTO_INCREMENT`.
   - *Retest Result:* **PASS** (Verified by test `test_fr02_client_supplied_account_number_ignored`).

3. **DEF-04 (Structured Error on Malformed Account ID Lookup):**
   - *Issue:* Non-numeric account lookup paths returned a generic 404 without structured JSON error format.
   - *Fix:* Added route regex validation and exception handling in `account_module.hpp`.
   - *Retest Result:* **PASS** (Verified by test `test_fr03_get_account_unknown_and_malformed_returns_404`).

---

## 6. Unit Testing Conclusion & Sign-off

All 16 unit test cases have executed successfully with zero failures and zero regressions. The Candidate 1 account management logic complies fully with the requirements of FR-01, FR-02, FR-03, FR-04, FR-05, and NFR-02.

**Signed off by:**  
**Pavan R Lamani** (`lamanipavan495@gmail.com`)  
Candidate 1 - Account Management Subsystem Owner  
Date: 3rd November 2026  
