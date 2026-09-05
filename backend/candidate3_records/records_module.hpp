// ============================================================================
// CANDIDATE 3 - Transfer, Records and Statements module
// Scope     : FR-13 Transfer (atomic) | FR-15 Transaction history | FR-17 Statement
// Reference : docs/Bank_Management_System_Test_Plan_V2.docx  -> Chapter 6 (6.1 - 6.3)
// Tests     : tests/integration/test_candidate3_records.py
// ============================================================================
#pragma once
#include "httplib.h"
#include "../common/http_utils.hpp"
#include "../common/db.hpp"

inline void register_record_routes(httplib::Server& svr) {

  // -------------------------------------------------------------------------
  // FR-13  POST /api/transfers
  //        body: {"from_account": 1001, "to_account": 1002, "amount": 250}
  // Rules: ATOMIC - debit and credit succeed or fail together (single SQL
  //        transaction: START TRANSACTION ... COMMIT / ROLLBACK); sender keeps
  //        >= 500 minimum; accounts must be open.
  // Success -> 200 {"from_account":..., "to_account":..., "amount":...,
  //                 "from_balance":..., "to_balance":...}
  // Failure -> 400 (insufficient funds / unknown or closed account / amount<=0)
  // -------------------------------------------------------------------------
  svr.Post("/api/transfers", [](const httplib::Request& req, httplib::Response& res) {
    // TODO(Candidate 3): implement with an explicit SQL transaction
    http_utils::not_implemented(res, "FR-13 transfer",
                                "Candidate 3 (backend/candidate3_records/records_module.hpp)");
  });

  // -------------------------------------------------------------------------
  // FR-15  GET /api/accounts/(\d+)/transactions
  // Returns the account's activity, newest last or first but CONSISTENT IN
  // ORDER, including transfers (TRANSFER_IN / TRANSFER_OUT rows).
  // Success -> 200 {"account_number": <id>, "count": N,
  //                 "transactions": [ {"type":..., "amount":..., "created_at":...}, ... ]}
  // -------------------------------------------------------------------------
  svr.Get(R"(/api/accounts/(\d+)/transactions)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO(Candidate 3): implement (SELECT ... FROM transactions WHERE account_number = id ORDER BY created_at)
    http_utils::not_implemented(res, "FR-15 transaction history",
                                "Candidate 3 (backend/candidate3_records/records_module.hpp)");
  });

  // -------------------------------------------------------------------------
  // FR-17  GET /api/accounts/(\d+)/statement
  // Formal statement: opening context, each transaction, closing balance that
  // reconciles exactly with the account balance.
  // Success -> 200 {"account_number":..., "from":..., "to":...,
  //                 "opening_balance":..., "closing_balance":..., "transactions":[...]}
  // -------------------------------------------------------------------------
  svr.Get(R"(/api/accounts/(\d+)/statement)", [](const httplib::Request& req, httplib::Response& res) {
    // TODO(Candidate 3): implement
    http_utils::not_implemented(res, "FR-17 statement",
                                "Candidate 3 (backend/candidate3_records/records_module.hpp)");
  });
}
