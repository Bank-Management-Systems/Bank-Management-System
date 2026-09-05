// ============================================================================
// CANDIDATE 1 - Account Management module
// Scope     : FR-01 Create account | FR-04 Modify customer details | FR-05 Close account
// Reference : docs/Bank_Management_System_Test_Plan_V2.docx  -> Chapter 4 (4.1 - 4.3)
// Tests     : tests/integration/test_candidate1_account.py  (your acceptance contract)
// ============================================================================
#pragma once
#include "httplib.h"
#include "../common/http_utils.hpp"
#include "../common/db.hpp"

inline void register_account_routes(httplib::Server& svr) {

  // -------------------------------------------------------------------------
  // FR-01  POST /api/accounts  -  create a new bank account
  // Rules (Test Plan 4.1): mandatory name; opening deposit >= Rs. 500;
  // account number auto-generated (schema starts at 1001).
  // Success -> 201 {"account_number": <int>, "balance": <opening_deposit>}
  // Failure -> 400 {"error": "..."} (blank name, deposit below minimum, ...)
  // -------------------------------------------------------------------------
  svr.Post("/api/accounts", [](const httplib::Request& req, httplib::Response& res) {
    // TODO(Candidate 1): implement
    //   1) name  = http_utils::get_string(req.body, "name");
    //      deposit = http_utils::get_number(req.body, "opening_deposit");
    //   2) validate: name not empty, deposit >= 500  -> else http_utils::error_json(res, 400, ...)
    //   3) INSERT INTO accounts (name, address, contact, type, balance) VALUES (...)
    //      using Database::instance().exec(...)  -> then last_insert_id()
    //   4) res.status = 201; return JSON with the new account number
    http_utils::not_implemented(res, "FR-01 create account",
                                "Candidate 1 (backend/candidate1_account/account_module.hpp)");
  });

  // -------------------------------------------------------------------------
  // FR-04  PUT /api/accounts/(\d+)  -  modify editable customer details
  // Editable: address, contact (NOT name/balance). Unknown id -> 404.
  // Success -> 200 {"account_number": <id>, "address": ..., "contact": ...}
  // -------------------------------------------------------------------------
  svr.Put(R"(/api/accounts/(\d+))", [](const httplib::Request& req, httplib::Response& res) {
    // std::string id = req.matches[1];  // captured account number
    // TODO(Candidate 1): implement  (UPDATE accounts SET ... WHERE account_number = id)
    http_utils::not_implemented(res, "FR-04 modify customer details",
                                "Candidate 1 (backend/candidate1_account/account_module.hpp)");
  });

  // -------------------------------------------------------------------------
  // FR-05  POST /api/accounts/(\d+)/close  -  close an account
  // Rules (Test Plan 4.3): only when balance is zero (or reconciled);
  // closed accounts must reject further transactions (Candidate 2 checks this).
  // Success -> 200 {"account_number": <id>, "status": "closed"}
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/accounts/(\d+)/close)", [](const httplib::Request& req, httplib::Response& res) {
    // std::string id = req.matches[1];
    // TODO(Candidate 1): implement  (UPDATE accounts SET status='closed', closed_at=NOW() ...)
    http_utils::not_implemented(res, "FR-05 close account",
                                "Candidate 1 (backend/candidate1_account/account_module.hpp)");
  });
}
