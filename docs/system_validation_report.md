# Bank Management System - System Validation Report
**System:** Bank Management System (Multi-Tier Web Application)  
**Lead Author:** Pavan R Lamani (`lamanipavan495@gmail.com`)  
**Validation Period:** 4th November 2026 – 6th November 2026  
**Document Version:** 1.0 (Final)  
**Status:** System Validated - Production Ready  

---

## 1. Executive Summary

This report presents the system validation and end-to-end integration results for the Bank Management System, focusing on Candidate 1 (Account Management) and its multi-module interactions with Candidate 2 (Core Transactions), Candidate 3 (Records & Transfers), and Candidate 4 (Security).

All end-to-end integration workflows, restart durability checks, hostile fuzz sweeps, and regression test suites were executed against the live multi-threaded backend API server on Ubuntu Linux with MySQL 8.0.

- **Candidate 1 System & Integration Tests:** 18 / 18 Passed (100.0%)
- **Total System Regression Test Suite:** 61 / 61 Passed (100.0%)
- **Critical Defects:** 0
- **High / Medium Defects:** 0 (All resolved and retested)
- **Final Validation Verdict:** **PASSED / ACCEPTED**

---

## 2. System Architecture & Test Setup

```
 +--------------------------------------------------------------------------+
 |                      Client / Test Automation Tier                       |
 |     (Pytest Integration Suite + Chrome Frontend SPA / JS Clients)       |
 +--------------------------------------------------------------------------+
                                      |
                                      | HTTP REST / JSON (Port 8081)
                                      v
 +--------------------------------------------------------------------------+
 |                       C++17 Multi-Threaded API Server                    |
 |  +--------------------+---------------------+--------------------+       |
 |  |  Candidate 1       |  Candidate 2        |  Candidate 3       |       |
 |  |  Account Lifecycle |  Transactions       |  Transfers/History |       |
 |  |  (FR-01 to FR-05)  |  (FR-08,09,12)      |  (FR-13,15,17)     |       |
 |  +--------------------+---------------------+--------------------+       |
 |  |  Candidate 4 Security (FR-18,19,20)      | Common HTTP / DB   |       |
 |  +------------------------------------------+--------------------+       |
 +--------------------------------------------------------------------------+
                                      |
                                      | MySQL C Connector (TCP 3306)
                                      v
 +--------------------------------------------------------------------------+
 |                            MySQL 8.0 Storage                             |
 |           Tables: accounts, transactions, users, statements              |
 +--------------------------------------------------------------------------+
```

---

## 3. Candidate 1 End-to-End System Validation Cases

| Test Case ID | Test Scenario | Preconditions & Steps | Test Data | Expected System Behavior | Observed Result | Status |
|---|---|---|---|---|---|:---:|
| **ST_01** | Dual account creation in single session | 1. Log in as staff.<br>2. Provision Customer A.<br>3. Provision Customer B.<br>4. Search both accounts. | Customer A: Amit Verma, Rs. 6000<br>Customer B: Sneha Iyer, Rs. 5000 | Both accounts created with monotonically increasing IDs ($ID_B > ID_A$); balances match deposits accurately | Account 1001 and 1002 created; lookup confirmed exact balances 6000.00 and 5000.00 | **PASS** |
| **ST_02** | Zero orphan records on failed creations | 1. Record baseline DB count.<br>2. Submit blank name payload.<br>3. Submit deposit < 500.<br>4. Submit 1 valid account.<br>5. Inspect DB count. | Attempt 1: blank name<br>Attempt 2: deposit 100<br>Attempt 3: valid details | Invalid requests return HTTP 400; DB record count increases by exactly 1; zero partial records | HTTP 400 returned for both invalid requests; DB row count increased by exactly +1 | **PASS** |
| **ST_03** | End-to-end customer modification | 1. Create account.<br>2. Modify address and contact in PUT call.<br>3. Query via GET and MySQL. | Account: valid ID<br>New address: "Updated Suite 300"<br>New contact: "9876599999" | Update accepted with HTTP 200; changes immediately visible via GET lookup and in MySQL storage | HTTP 200 returned; GET `/api/accounts/{id}` and MySQL query show updated address and contact | **PASS** |
| **ST_04** | Data integrity under invalid modify | 1. Create account.<br>2. Submit malformed modify (alphabetic contact).<br>3. Inspect stored record. | Attempted contact: "98765ABCDE"<br>Stored contact: "9876543210" | Modification rejected with HTTP 400; existing database record remains completely intact | HTTP 400 returned; original address and contact in DB unchanged | **PASS** |
| **ST_05** | Account closure enforcement across system | 1. Reconcile account balance to Rs. 0.00.<br>2. Call `POST /api/accounts/{id}/close`.<br>3. Query account details.<br>4. Attempt transaction. | Reconciled account with balance = 0.00 | Closure succeeds; status set to 'closed'; GET `/api/accounts/{id}` confirms status 'closed' | HTTP 200 OK; GET lookup returns status 'closed'; subsequent deposits rejected | **PASS** |
| **ST_06** | Mixed closure consistency | 1. Create Account A (balance 6000).<br>2. Create Account B (balance 0).<br>3. Attempt closing Account A.<br>4. Close Account B. | Account A: balance 6000<br>Account B: balance 0 | Account A closure blocked (400); Account B closed (200); ledger remains consistent | Account A rejected with 400 (balance > 0); Account B closed with 200; database state consistent | **PASS** |
| **ST_FR02_01** | Account number anti-reuse validation | 1. Create Account A.<br>2. Close Account A.<br>3. Create Account B.<br>4. Verify Account A preserved. | Account A closed; new account created | Account B receives next incremented ID; Account A number is never reissued; row preserved | Account B number strictly greater than Account A; Account A row preserved in DB with status 'closed' | **PASS** |
| **ST_FR02_02** | Sequence continuity across server restart | 1. Create Account Pre-restart.<br>2. Send SIGTERM to server process.<br>3. Restart server binary.<br>4. Create Account Post-restart. | Live API server restart | Server recovers cleanly; sequence continues monotonically ($ID_{post} = ID_{pre} + 1$) without reset | Server restarted; health check OK; post-restart account received $ID_{pre} + 1$ without gaps | **PASS** |
| **ST_FR03_01** | Read freshness across multi-module updates | 1. Create account.<br>2. Modify customer address (FR-04).<br>3. Deposit funds (FR-08).<br>4. Settle & close account (FR-05). | Sequence of operations on single account | GET `/api/accounts/{id}` immediately reflects each state change without delay | Address updated in GET response; balance updated after deposit; status updated to 'closed' | **PASS** |
| **NT_04** | Hostile fuzz sweep and server recovery | 1. Burst of hostile payloads (10k chars, control chars, malformed JSON, invalid types).<br>2. Issue valid create request.<br>3. Verify DB row count. | 8 hostile payloads followed by 1 valid payload | Server remains alive and responsive; hostile payloads return 400; valid request succeeds; DB uncorrupted | All hostile payloads rejected with 400; valid request returned 201; exactly 1 row added to DB | **PASS** |

---

## 4. Integration with Peer Modules (Candidates 2, 3, and 4)

System-wide integration verification was performed by running the complete 61-test suite across all candidate boundaries:

| Module Boundary | Interactions Tested | Result | Verification Notes |
|---|---|:---:|---|
| **Candidate 1 x Candidate 2** | • Newly created account accepted for cash deposit (FR-08)<br>• Withdrawal leaves balance consistent for lookup (FR-09)<br>• Balance inquiry matches account lookup balance (FR-12)<br>• Closed account rejects deposit and withdrawal | **PASS** | All 14 Candidate 2 integration tests passed. |
| **Candidate 1 x Candidate 3** | • Transfer between Candidate 1 created accounts (FR-13)<br>• Transaction history displays opening deposit and modifications (FR-15)<br>• Account statement includes correct customer header details (FR-17) | **PASS** | All 6 Candidate 3 integration tests passed. |
| **Candidate 1 x Candidate 4** | • Staff login allows account provisioning (FR-18)<br>• Customer PIN authenticated against account number (FR-19)<br>• PIN change works on newly created accounts (FR-20) | **PASS** | All 6 Candidate 4 integration tests passed. |
| **Platform Health Check** | • `/api/health` monitoring endpoint returns 200 OK | **PASS** | Health probe healthy and responsive under load. |

---

## 5. Traceability Matrix Summary

| Requirement ID | Requirement Description | Allocated Owner | Associated Test Cases | Pass Rate |
|---|---|---|---|:---:|
| **FR-01** | Create New Bank Account | Candidate 1 | UT_01–UT_03, IT_01–IT_03, ST_01–ST_02 | **100%** |
| **FR-02** | Account Numbering & Monotonic Continuity | Candidate 1 | UT_FR02_01–02, IT_FR02_01, ST_FR02_01–02 | **100%** |
| **FR-03** | Account Details Lookup & Freshness | Candidate 1 | UT_FR03_01–02, IT_FR03_01, ST_FR03_01 | **100%** |
| **FR-04** | Modify Customer Details | Candidate 1 | UT_04–UT_06, IT_04–IT_06, ST_03–ST_04 | **100%** |
| **FR-05** | Close Bank Account | Candidate 1 | UT_07–UT_09, IT_07–IT_09, ST_05–ST_06 | **100%** |
| **NFR-02** | Input Validation & Robustness Sweep | Candidate 1 | NT_01, NT_02, NT_03, NT_04 | **100%** |
| **FR-08, 09, 12** | Core Banking Transactions | Candidate 2 | UT_10–18, IT_10–18, ST_07–12 | **100%** |
| **FR-13, 15, 17** | Transfers, History, Statements | Candidate 3 | UT_19–27, IT_19–27, ST_13–18 | **100%** |
| **FR-18, 19, 20** | Staff & Customer Security | Candidate 4 | UT_28–36, IT_28–36, ST_19–24 | **100%** |

---

## 6. System Validation Sign-off

The Bank Management System has met all functional and non-functional requirements allocated to Candidate 1 and satisfied end-to-end integration criteria across all subsystems. The application demonstrates exceptional resilience against hostile inputs, seamless data consistency across operations, and zero data loss across server restarts.

**System Validation Status:** **PASSED & APPROVED FOR PRODUCTION**

**Sign-off:**  
**Pavan R Lamani** (`lamanipavan495@gmail.com`)  
Candidate 1 Subsystem Owner  
Date: 6th November 2026  
