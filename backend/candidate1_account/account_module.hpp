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
  // GET /api/accounts/(\d+)  -  get account details (pre-filling edit forms)
  // -------------------------------------------------------------------------
  svr.Get(R"(/api/accounts/(\d+))", [](const httplib::Request& req, httplib::Response& res) {
    std::string id = req.matches[1];
    Database& db = Database::instance();

    std::string sql = "SELECT account_number, name, address, contact, type, balance, status FROM accounts WHERE account_number = " + id;
    MYSQL_RES* result = db.select(sql);
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

    std::string name = row[1] ? row[1] : "";
    std::string address = row[2] ? row[2] : "";
    std::string contact = row[3] ? row[3] : "";
    std::string type = row[4] ? row[4] : "";
    std::string balance = row[5] ? row[5] : "0.00";
    std::string status = row[6] ? row[6] : "";
    mysql_free_result(result);

    std::string json = "{\"account_number\": " + id +
                       ", \"name\": \"" + name +
                       "\", \"address\": \"" + address +
                       "\", \"contact\": \"" + contact +
                       "\", \"type\": \"" + type +
                       "\", \"balance\": " + balance +
                       ", \"status\": \"" + status + "\"}";
    res.set_content(json, "application/json");
  });

  // -------------------------------------------------------------------------
  // FR-04  PUT /api/accounts/(\d+)  -  modify editable customer details
  // Editable: address, contact (NOT name/balance). Unknown id -> 404.
  // Success -> 200 {"account_number": <id>, "address": ..., "contact": ...}
  // -------------------------------------------------------------------------
  svr.Put(R"(/api/accounts/(\d+))", [](const httplib::Request& req, httplib::Response& res) {
    std::string id = req.matches[1];
    Database& db = Database::instance();

    std::string sql = "SELECT address, contact, status FROM accounts WHERE account_number = " + id;
    MYSQL_RES* result = db.select(sql);
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

    std::string cur_address = row[0] ? row[0] : "";
    std::string cur_contact = row[1] ? row[1] : "";
    std::string status = row[2] ? row[2] : "";
    mysql_free_result(result);

    if (status == "closed") {
      http_utils::error_json(res, 400, "Cannot modify closed account");
      return;
    }

    std::string new_address = http_utils::trim(http_utils::get_string(req.body, "address"));
    std::string new_contact = http_utils::trim(http_utils::get_string(req.body, "contact"));

    std::string final_address = new_address.empty() ? cur_address : new_address;
    std::string final_contact = new_contact.empty() ? cur_contact : new_contact;

    auto sql_escape = [](const std::string& s) {
      std::string out;
      for (char c : s) {
        if (c == '\'') out += "''";
        else if (c == '\\') out += "\\\\";
        else out += c;
      }
      return out;
    };

    std::string update_sql = "UPDATE accounts SET address = '" + sql_escape(final_address) +
                             "', contact = '" + sql_escape(final_contact) +
                             "' WHERE account_number = " + id;

    if (!db.exec(update_sql)) {
      http_utils::error_json(res, 500, "Failed to update account details");
      return;
    }

    res.status = 200;
    std::string json = "{\"account_number\": " + id +
                       ", \"address\": \"" + final_address +
                       "\", \"contact\": \"" + final_contact + "\"}";
    res.set_content(json, "application/json");
  });

  // -------------------------------------------------------------------------
  // FR-05  POST /api/accounts/(\d+)/close  -  close an account
  // Rules (Test Plan 4.3): only when balance is zero (or reconciled);
  // closed accounts must reject further transactions (Candidate 2 checks this).
  // Success -> 200 {"account_number": <id>, "status": "closed"}
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/accounts/(\d+)/close)", [](const httplib::Request& req, httplib::Response& res) {
    std::string id = req.matches[1];
    Database& db = Database::instance();

    std::string sql = "SELECT balance, status FROM accounts WHERE account_number = " + id;
    MYSQL_RES* result = db.select(sql);
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

    std::string status = row[1] ? row[1] : "";
    if (status == "closed") {
      mysql_free_result(result);
      http_utils::error_json(res, 400, "Account is already closed");
      return;
    }

    double balance = row[0] ? std::stod(row[0]) : 0.0;
    mysql_free_result(result);

    if (balance > 0.0 || balance < -0.001) {
      http_utils::error_json(res, 400, "Account balance must be zero before closing");
      return;
    }

    std::string update_sql = "UPDATE accounts SET status = 'closed', closed_at = NOW() WHERE account_number = " + id;
    if (!db.exec(update_sql)) {
      http_utils::error_json(res, 500, "Failed to close account");
      return;
    }

    res.status = 200;
    std::string json = "{\"account_number\": " + id + ", \"status\": \"closed\"}";
    res.set_content(json, "application/json");
  });
}

