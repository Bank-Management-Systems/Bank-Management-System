// ============================================================================
// CANDIDATE 2 - Core Banking Transactions module
// Scope     : FR-08 Deposit | FR-09 Withdrawal | FR-12 Balance inquiry
// Reference : docs/Bank_Management_System_Test_Plan_V2.docx  -> Chapter 5 (5.1 - 5.3)
// Tests     : tests/integration/test_candidate2_transactions.py
// Notes     : business rules: amount > 0; withdrawal must leave balance >= 500
//             (minimum balance); closed accounts reject every operation (400).
// ============================================================================
#pragma once
#include "httplib.h"
#include "../common/http_utils.hpp"
#include "../common/db.hpp"

inline void register_transaction_routes(httplib::Server& svr) {

  // -------------------------------------------------------------------------
  // FR-08  POST /api/accounts/(\d+)/deposit   body: {"amount": 1000}
  // Success -> 200 {"account_number": <id>, "balance": <new_balance>}
  // Failure -> 400 (amount <= 0 / non-numeric / account closed or unknown)
  // Also: write a row into transactions (type 'DEPOSIT') - see database/schema.sql
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/accounts/(\d+)/deposit)", [](const httplib::Request& req, httplib::Response& res) {
    // std::string id = req.matches[1];
    // TODO(Candidate 2): implement (SELECT balance FOR UPDATE -> UPDATE -> INSERT transaction row)
    http_utils::not_implemented(res, "FR-08 deposit",
                                "Candidate 2 (backend/candidate2_transactions/transactions_module.hpp)");
  });

  // -------------------------------------------------------------------------
  // FR-09  POST /api/accounts/(\d+)/withdraw  body: {"amount": 500}
  // Rules: amount > 0 AND (balance - amount) >= 500 minimum balance.
  // Success -> 200 with new balance | Failure -> 400 with clear message
  // Also: write a row into transactions (type 'WITHDRAWAL')
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/accounts/(\d+)/withdraw)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO(Candidate 2): implement
    http_utils::not_implemented(res, "FR-09 withdrawal",
                                "Candidate 2 (backend/candidate2_transactions/transactions_module.hpp)");
  });

  // -------------------------------------------------------------------------
  // FR-12  GET /api/accounts/(\d+)/balance
  // Success -> 200 {"account_number": <id>, "balance": <current_balance>}
  // Failure -> 404 unknown account
  // -------------------------------------------------------------------------
  svr.Get(R"(/api/accounts/(\d+)/balance)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO(Candidate 2): implement (simple SELECT balance ...)
    http_utils::not_implemented(res, "FR-12 balance inquiry",
                                "Candidate 2 (backend/candidate2_transactions/transactions_module.hpp)");
  });
}
