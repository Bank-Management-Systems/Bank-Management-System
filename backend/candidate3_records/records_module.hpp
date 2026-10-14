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
    std::string id = req.matches[1];
    Database& db = Database::instance();

    std::string acc_sql = "SELECT account_number FROM accounts WHERE account_number = " + id;
    MYSQL_RES* acc_res = db.select(acc_sql);
    if (!acc_res) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }

    MYSQL_ROW acc_row = mysql_fetch_row(acc_res);
    if (!acc_row) {
      mysql_free_result(acc_res);
      http_utils::error_json(res, 404, "Unknown account");
      return;
    }
    mysql_free_result(acc_res);

    std::string sql = "SELECT id, type, amount, balance_after, related_account, created_at "
                      "FROM transactions WHERE account_number = " + id +
                      " ORDER BY created_at ASC, id ASC";

    MYSQL_RES* tx_res = db.select(sql);
    if (!tx_res) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }

    auto format_money = [](double val) {
      char buf[64];
      snprintf(buf, sizeof(buf), "%.2f", val);
      return std::string(buf);
    };

    std::string tx_json = "[";
    MYSQL_ROW row;
    bool first = true;
    size_t count = 0;

    while ((row = mysql_fetch_row(tx_res))) {
      std::string tx_id = row[0] ? row[0] : "0";
      std::string type = row[1] ? row[1] : "";
      double amount = row[2] ? std::stod(row[2]) : 0.0;
      std::string balance_after = row[3] ? row[3] : "0.00";
      std::string related = row[4] ? row[4] : "null";
      std::string created_at = row[5] ? row[5] : "";

      if (!first) tx_json += ",";
      first = false;

      tx_json += "{\"id\":" + tx_id +
                 ",\"type\":\"" + type + "\"" +
                 ",\"amount\":" + format_money(amount) +
                 ",\"balance_after\":" + balance_after +
                 ",\"related_account\":" + (related == "null" ? "null" : related) +
                 ",\"created_at\":\"" + created_at + "\"}";
      count++;
    }
    tx_json += "]";
    mysql_free_result(tx_res);

    std::string json = "{\"account_number\":" + id +
                       ",\"count\":" + std::to_string(count) +
                       ",\"transactions\":" + tx_json + "}";

    res.status = 200;
    res.set_content(json, "application/json");
  });

  // -------------------------------------------------------------------------
  // FR-17  GET /api/accounts/(\d+)/statement
  // Formal statement: opening context, each transaction, closing balance that
  // reconciles exactly with the account balance.
  // Success -> 200 {"account_number":..., "from":..., "to":...,
  //                 "opening_balance":..., "closing_balance":..., "transactions":[...]}
  // -------------------------------------------------------------------------
  svr.Get(R"(/api/accounts/(\d+)/statement)", [](const httplib::Request& req, httplib::Response& res) {
    std::string id = req.matches[1];
    Database& db = Database::instance();

    std::string acc_sql = "SELECT balance FROM accounts WHERE account_number = " + id;
    MYSQL_RES* acc_res = db.select(acc_sql);
    if (!acc_res) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }

    MYSQL_ROW acc_row = mysql_fetch_row(acc_res);
    if (!acc_row) {
      mysql_free_result(acc_res);
      http_utils::error_json(res, 404, "Unknown account");
      return;
    }

    double current_balance = acc_row[0] ? std::stod(acc_row[0]) : 0.0;
    mysql_free_result(acc_res);

    std::string from_date = req.has_param("from") ? http_utils::trim(req.get_param_value("from")) : "";
    std::string to_date = req.has_param("to") ? http_utils::trim(req.get_param_value("to")) : "";

    // If to_date is provided, calculate any future net change after to_date to determine closing balance at to_date
    double future_net_change = 0.0;
    if (!to_date.empty()) {
      std::string to_clause = (to_date.find(' ') != std::string::npos) ? to_date : (to_date + " 23:59:59");
      std::string future_sql = "SELECT type, amount FROM transactions WHERE account_number = " + id +
                               " AND created_at > '" + to_clause + "'";
      MYSQL_RES* future_res = db.select(future_sql);
      if (future_res) {
        MYSQL_ROW f_row;
        while ((f_row = mysql_fetch_row(future_res))) {
          std::string f_type = f_row[0] ? f_row[0] : "";
          double f_amt = f_row[1] ? std::stod(f_row[1]) : 0.0;
          if (f_type == "DEPOSIT" || f_type == "TRANSFER_IN") {
            future_net_change += f_amt;
          } else if (f_type == "WITHDRAWAL" || f_type == "TRANSFER_OUT") {
            future_net_change -= f_amt;
          }
        }
        mysql_free_result(future_res);
      }
    }

    double statement_closing_balance = current_balance - future_net_change;

    // Fetch transactions in range
    std::string tx_sql = "SELECT id, type, amount, balance_after, related_account, created_at "
                         "FROM transactions WHERE account_number = " + id;
    if (!from_date.empty()) {
      std::string from_clause = (from_date.find(' ') != std::string::npos) ? from_date : (from_date + " 00:00:00");
      tx_sql += " AND created_at >= '" + from_clause + "'";
    }
    if (!to_date.empty()) {
      std::string to_clause = (to_date.find(' ') != std::string::npos) ? to_date : (to_date + " 23:59:59");
      tx_sql += " AND created_at <= '" + to_clause + "'";
    }
    tx_sql += " ORDER BY created_at ASC, id ASC";

    MYSQL_RES* tx_res = db.select(tx_sql);
    if (!tx_res) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }

    auto format_money = [](double val) {
      char buf[64];
      snprintf(buf, sizeof(buf), "%.2f", val);
      return std::string(buf);
    };

    std::string tx_json = "[";
    MYSQL_ROW row;
    bool first = true;
    double range_net_change = 0.0;
    size_t count = 0;

    while ((row = mysql_fetch_row(tx_res))) {
      std::string tx_id = row[0] ? row[0] : "0";
      std::string type = row[1] ? row[1] : "";
      double amount = row[2] ? std::stod(row[2]) : 0.0;
      std::string balance_after = row[3] ? row[3] : "0.00";
      std::string related = row[4] ? row[4] : "null";
      std::string created_at = row[5] ? row[5] : "";

      if (type == "DEPOSIT" || type == "TRANSFER_IN") {
        range_net_change += amount;
      } else if (type == "WITHDRAWAL" || type == "TRANSFER_OUT") {
        range_net_change -= amount;
      }

      if (!first) tx_json += ",";
      first = false;

      tx_json += "{\"id\":" + tx_id +
                 ",\"type\":\"" + type + "\"" +
                 ",\"amount\":" + format_money(amount) +
                 ",\"balance_after\":" + balance_after +
                 ",\"related_account\":" + (related == "null" ? "null" : related) +
                 ",\"created_at\":\"" + created_at + "\"}";
      count++;
    }
    tx_json += "]";
    mysql_free_result(tx_res);

    double statement_opening_balance = statement_closing_balance - range_net_change;

    std::string from_val = from_date.empty() ? "null" : ("\"" + from_date + "\"");
    std::string to_val = to_date.empty() ? "null" : ("\"" + to_date + "\"");

    std::string json = "{\"account_number\":" + id +
                       ",\"from\":" + from_val +
                       ",\"to\":" + to_val +
                       ",\"opening_balance\":" + format_money(statement_opening_balance) +
                       ",\"closing_balance\":" + format_money(statement_closing_balance) +
                       ",\"count\":" + std::to_string(count) +
                       ",\"transactions\":" + tx_json + "}";

    res.status = 200;
    res.set_content(json, "application/json");
  });
}

