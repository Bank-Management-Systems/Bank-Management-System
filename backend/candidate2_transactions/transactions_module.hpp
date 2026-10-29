// ============================================================================
// CANDIDATE 2 - Core Banking Transactions module
// Scope     : FR-08 Deposit | FR-09 / FR-10 Withdrawal | FR-12 Balance inquiry
// Reference : docs/Bank_Management_System_Test_Plan_V2.docx  -> Chapter 5 (5.1 - 5.3)
// Tests     : tests/integration/test_candidate2_transactions.py
// Performance (NFR-01):
//   Interactive endpoint SLA / latency budget:
//     - Target latency: well under 1.0 s under normal load (typically < 100 ms)
//     - Hard latency limit: 2.0 s per V1
//     - Zero per-request overhead on the hot path: indexed primary-key lookups on
//       accounts(account_number) avoid full-table scans. Transactions table inserts
//       append directly and queries use idx_txn_account_created(account_number, created_at).
// Notes     : business rules: amount > 0; withdrawal must leave balance >= 500
//             (minimum balance); closed accounts reject every operation (400).
// ============================================================================
#pragma once
#include <cmath>
#include <string>
#include "httplib.h"
#include "../common/http_utils.hpp"
#include "../common/db.hpp"

namespace candidate2 {
// NFR-01 Performance Latency Budgets (seconds)
constexpr double TARGET_LATENCY_BUDGET_SECONDS = 1.0;     // Target well under 1 s
constexpr double HARD_LIMIT_LATENCY_BUDGET_SECONDS = 2.0; // Hard limit per V1
constexpr long long MIN_BALANCE_CENTS = 50000LL;          // Rs. 500.00 minimum balance (FR-10)
}  // namespace candidate2

inline bool validate_amount(double amount, std::string& err_msg) {
  if (std::isnan(amount) || std::isinf(amount) || amount <= 0.0) {
    err_msg = "Amount must be greater than zero";
    return false;
  }
  return true;
}

inline bool validate_amount(double amount) {
  return !std::isnan(amount) && !std::isinf(amount) && amount > 0.0;
}

inline double get_transaction_amount(const std::string& body, const std::string& key) {
  std::string pat = "\"" + key + "\"";
  size_t p = body.find(pat);
  if (p == std::string::npos) return 0.0;
  p = body.find(':', p + pat.size());
  if (p == std::string::npos) return 0.0;
  return std::strtod(http_utils::trim(body.substr(p + 1)).c_str(), nullptr);
}

inline void register_transaction_routes(httplib::Server& svr) {

  // -------------------------------------------------------------------------
  // FR-08  POST /api/accounts/(\d+)/deposit   body: {"amount": 1000}
  // Success -> 200 {"account_number": <id>, "balance": <new_balance>}
  // Failure -> 400 (amount <= 0 / non-numeric / account closed), 404 unknown account
  // Also: write a row into transactions (type 'DEPOSIT') - see database/schema.sql
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/accounts/(\d+)/deposit)", [](const httplib::Request& req, httplib::Response& res) {
    std::string id = req.matches[1];
    double amount = get_transaction_amount(req.body, "amount");
    
    std::string err_msg;
    if (!validate_amount(amount, err_msg)) {
      http_utils::error_json(res, 400, "Deposit amount must be greater than zero");
      return;
    }
    
    Database& db = Database::instance();
    db.exec("START TRANSACTION");
    
    std::string sql = "SELECT balance, status FROM accounts WHERE account_number = " + id + " FOR UPDATE";
    MYSQL_RES* result = db.select(sql);
    
    if (!result) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Database error");
      return;
    }
    
    MYSQL_ROW row = mysql_fetch_row(result);
    if (!row) {
      mysql_free_result(result);
      db.exec("ROLLBACK");
      http_utils::error_json(res, 404, "Unknown account");
      return;
    }
    
    std::string status = row[1] ? row[1] : "";
    if (status == "closed") {
      mysql_free_result(result);
      db.exec("ROLLBACK");
      http_utils::error_json(res, 400, "Account is closed");
      return;
    }
    
    double balance = row[0] ? std::stod(row[0]) : 0.0;
    mysql_free_result(result);
    
    double new_balance = balance + amount;
    char amt_buf[64], bal_buf[64];
    snprintf(amt_buf, sizeof(amt_buf), "%.2f", amount);
    snprintf(bal_buf, sizeof(bal_buf), "%.2f", new_balance);
    
    std::string update_sql = "UPDATE accounts SET balance = balance + " + std::string(amt_buf) + 
                             " WHERE account_number = " + id;
    if (!db.exec(update_sql)) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Failed to update balance");
      return;
    }
    
    std::string insert_sql = "INSERT INTO transactions (account_number, type, amount, balance_after) VALUES (" +
                             id + ", 'DEPOSIT', " + std::string(amt_buf) + ", " + std::string(bal_buf) + ")";
    if (!db.exec(insert_sql)) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Failed to record transaction");
      return;
    }
    
    db.exec("COMMIT");
    
    std::string json = "{\"account_number\": " + id + ", \"balance\": " + std::string(bal_buf) + "}";
    res.set_content(json, "application/json");
  });

  // -------------------------------------------------------------------------
  // FR-09 / FR-10  POST /api/accounts/(\d+)/withdraw  body: {"amount": 500}
  // Rules:
  //   1. Amount validation: validate_amount(amount) -> positive numeric > 0
  //   2. Overdraft protection: amount > available balance -> 400 (never partial debit)
  //   3. Boundary rule: (balance - amount) >= Rs. 500 -> leaving exactly Rs. 500 succeeds (200),
  //      leaving anything less (e.g. Rs. 499.99) -> 400 with message naming minimum balance
  //   4. State safety: rejected withdrawal writes no transactions row and changes no balance
  // Success -> 200 with new balance | Failure -> 400 with clear message | 404 unknown account
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/accounts/(\d+)/withdraw)", [](const httplib::Request& req, httplib::Response& res) {
    std::string id = req.matches[1];
    double amount = get_transaction_amount(req.body, "amount");
    
    std::string err_msg;
    if (!validate_amount(amount, err_msg)) {
      http_utils::error_json(res, 400, "Withdrawal amount must be greater than zero");
      return;
    }
    
    Database& db = Database::instance();
    db.exec("START TRANSACTION");
    
    std::string sql = "SELECT balance, status FROM accounts WHERE account_number = " + id + " FOR UPDATE";
    MYSQL_RES* result = db.select(sql);
    
    if (!result) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Database error");
      return;
    }
    
    MYSQL_ROW row = mysql_fetch_row(result);
    if (!row) {
      mysql_free_result(result);
      db.exec("ROLLBACK");
      http_utils::error_json(res, 404, "Unknown account");
      return;
    }
    
    std::string status = row[1] ? row[1] : "";
    if (status == "closed") {
      mysql_free_result(result);
      db.exec("ROLLBACK");
      http_utils::error_json(res, 400, "Account is closed");
      return;
    }
    
    double balance = row[0] ? std::stod(row[0]) : 0.0;
    mysql_free_result(result);
    
    long long balance_cents = std::llround(balance * 100.0);
    long long amount_cents = std::llround(amount * 100.0);
    
    // FR-10 Overdraft protection: amount greater than available balance -> 400
    if (amount_cents > balance_cents) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 400, "Insufficient funds: withdrawal amount exceeds available balance");
      return;
    }

    // FR-10 Boundary rule: withdrawal is allowed only when (balance - amount) >= Rs. 500
    // Withdrawing to exactly Rs. 500 remaining must succeed; anything below -> 400 naming minimum balance
    long long remaining_cents = balance_cents - amount_cents;
    if (remaining_cents < candidate2::MIN_BALANCE_CENTS) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 400, "Insufficient funds: minimum balance of Rs. 500 must be maintained");
      return;
    }
    
    double new_balance = static_cast<double>(remaining_cents) / 100.0;
    char amt_buf[64], bal_buf[64];
    snprintf(amt_buf, sizeof(amt_buf), "%.2f", static_cast<double>(amount_cents) / 100.0);
    snprintf(bal_buf, sizeof(bal_buf), "%.2f", new_balance);
    
    std::string update_sql = "UPDATE accounts SET balance = balance - " + std::string(amt_buf) + 
                             " WHERE account_number = " + id;
    if (!db.exec(update_sql)) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Failed to update balance");
      return;
    }
    
    std::string insert_sql = "INSERT INTO transactions (account_number, type, amount, balance_after) VALUES (" +
                             id + ", 'WITHDRAWAL', " + std::string(amt_buf) + ", " + std::string(bal_buf) + ")";
    if (!db.exec(insert_sql)) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Failed to record transaction");
      return;
    }
    
    db.exec("COMMIT");
    
    std::string json = "{\"account_number\": " + id + ", \"balance\": " + std::string(bal_buf) + "}";
    res.set_content(json, "application/json");
  });

  // -------------------------------------------------------------------------
  // FR-12  GET /api/accounts/(\d+)/balance
  // Success -> 200 {"account_number": <id>, "balance": <current_balance>}
  // Failure -> 404 unknown account
  // -------------------------------------------------------------------------
  svr.Get(R"(/api/accounts/(\d+)/balance)", [](const httplib::Request& req, httplib::Response& res) {
    std::string id = req.matches[1];
    std::string sql = "SELECT balance FROM accounts WHERE account_number = " + id;
    
    MYSQL_RES* result = Database::instance().select(sql);
    if (!result) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }
    
    MYSQL_ROW row = mysql_fetch_row(result);
    if (!row) {
      mysql_free_result(result);
      http_utils::error_json(res, 404, "Unknown account");
      return;
    }
    
    std::string balance = row[0] ? row[0] : "0.00";
    mysql_free_result(result);
    
    std::string json = "{\"account_number\": " + id + ", \"balance\": " + balance + "}";
    res.set_content(json, "application/json");
  });
}
