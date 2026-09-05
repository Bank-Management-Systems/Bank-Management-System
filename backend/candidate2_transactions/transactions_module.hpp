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
    std::string id = req.matches[1];
    long amount = http_utils::get_number(req.body, "amount", 0);
    
    if (amount <= 0) {
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
    
    std::string update_sql = "UPDATE accounts SET balance = balance + " + std::to_string(amount) + 
                             " WHERE account_number = " + id;
    if (!db.exec(update_sql)) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Failed to update balance");
      return;
    }
    
    std::string insert_sql = "INSERT INTO transactions (account_number, type, amount, balance_after) VALUES (" +
                             id + ", 'DEPOSIT', " + std::to_string(amount) + ", " + std::to_string(new_balance) + ")";
    if (!db.exec(insert_sql)) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Failed to record transaction");
      return;
    }
    
    db.exec("COMMIT");
    
    char buffer[128];
    snprintf(buffer, sizeof(buffer), "%.2f", new_balance);
    std::string json = "{\"account_number\": " + id + ", \"balance\": " + std::string(buffer) + "}";
    res.set_content(json, "application/json");
  });

  // -------------------------------------------------------------------------
  // FR-09  POST /api/accounts/(\d+)/withdraw  body: {"amount": 500}
  // Rules: amount > 0 AND (balance - amount) >= 500 minimum balance.
  // Success -> 200 with new balance | Failure -> 400 with clear message
  // Also: write a row into transactions (type 'WITHDRAWAL')
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/accounts/(\d+)/withdraw)", [](const httplib::Request& req, httplib::Response& res) {
    std::string id = req.matches[1];
    long amount = http_utils::get_number(req.body, "amount", 0);
    
    if (amount <= 0) {
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
      http_utils::error_json(res, 400, "Unknown account");
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
    
    if (balance - amount < 500.0) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 400, "Minimum balance of 500 must be maintained");
      return;
    }
    
    double new_balance = balance - amount;
    
    std::string update_sql = "UPDATE accounts SET balance = balance - " + std::to_string(amount) + 
                             " WHERE account_number = " + id;
    if (!db.exec(update_sql)) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Failed to update balance");
      return;
    }
    
    std::string insert_sql = "INSERT INTO transactions (account_number, type, amount, balance_after) VALUES (" +
                             id + ", 'WITHDRAWAL', " + std::to_string(amount) + ", " + std::to_string(new_balance) + ")";
    if (!db.exec(insert_sql)) {
      db.exec("ROLLBACK");
      http_utils::error_json(res, 500, "Failed to record transaction");
      return;
    }
    
    db.exec("COMMIT");
    
    char buffer[128];
    snprintf(buffer, sizeof(buffer), "%.2f", new_balance);
    std::string json = "{\"account_number\": " + id + ", \"balance\": " + std::string(buffer) + "}";
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
