// ============================================================================
// CANDIDATE 1 - Account Management module
// Scope     : FR-01 Create account | FR-02 Account number hardening & uniqueness
//             FR-03 Account lookup details | NFR-02 Input validation & robustness
//             FR-04 Modify customer details | FR-05 Close account
// Reference : docs/Bank_Management_System_Test_Plan_V2.docx  -> Chapter 4 (4.1 - 4.3)
// Tests     : tests/integration/test_candidate1_account.py  (your acceptance contract)
// ============================================================================
#pragma once
#include "httplib.h"
#include "../common/http_utils.hpp"
#include "../common/db.hpp"

inline void register_account_routes(httplib::Server& svr) {

  // -------------------------------------------------------------------------
  // FR-01 / FR-02 / NFR-02  POST /api/accounts  -  create a new bank account
  // Rules (Test Plan 4.1 & 4.2): mandatory name; opening deposit >= Rs. 500;
  // account number auto-generated (schema starts at 1001).
  // FR-02: Any client-supplied account_number in the request body is strictly
  // ignored and overridden by the system's AUTO_INCREMENT generator.
  // NFR-02: Exception-safe handler; field caps, charset validation, malformed
  // JSON and oversized payload rejection.
  // Success -> 201 {"account_number": <int>, "balance": <opening_deposit>}
  // Failure -> 400 {"error": "..."} (blank name, deposit below minimum, ...)
  // -------------------------------------------------------------------------
  svr.Post("/api/accounts", [](const httplib::Request& req, httplib::Response& res) {
    try {
      if (http_utils::is_payload_oversized(req.body, 16384)) {
        http_utils::error_json(res, 400, "Request payload exceeds maximum allowed size");
        return;
      }
      if (!http_utils::is_valid_json_envelope(req.body)) {
        http_utils::error_json(res, 400, "Malformed JSON request body");
        return;
      }

      // FR-02: Client-supplied account_number is intentionally ignored/overridden.
      // We never extract or insert account_number; the DB generator assigns it.
      std::string err;
      std::string name = http_utils::trim(http_utils::get_string(req.body, "name"));
      if (!http_utils::validate_string(name, 100, "Name", err, false)) {
        http_utils::error_json(res, 400, err);
        return;
      }

      std::string address = http_utils::trim(http_utils::get_string(req.body, "address"));
      if (!http_utils::validate_string(address, 200, "Address", err, false)) {
        http_utils::error_json(res, 400, err);
        return;
      }

      std::string contact = http_utils::trim(http_utils::get_string(req.body, "contact"));
      if (!http_utils::validate_contact(contact, err)) {
        http_utils::error_json(res, 400, err);
        return;
      }

      std::string type = http_utils::trim(http_utils::get_string(req.body, "type"));
      if (type.empty()) {
        type = "Savings";
      } else if (type != "Savings" && type != "Current") {
        http_utils::error_json(res, 400, "Account type must be 'Savings' or 'Current'");
        return;
      }

      double deposit = 0.0;
      std::string deposit_err;
      if (!http_utils::validate_amount(req.body, "opening_deposit", deposit, deposit_err)) {
        http_utils::error_json(res, 400, deposit_err);
        return;
      }

      if (deposit < 500.0) {
        http_utils::error_json(res, 400, "Opening deposit must be at least Rs. 500");
        return;
      }

      auto sql_escape = [](const std::string& s) {
        std::string out;
        for (char c : s) {
          if (c == '\'') out += "''";
          else if (c == '\\') out += "\\\\";
          else out += c;
        }
        return out;
      };

      Database& db = Database::instance();
      char dep_buf[64];
      snprintf(dep_buf, sizeof(dep_buf), "%.2f", deposit);

      std::string sql = "INSERT INTO accounts (name, address, contact, type, balance, status) VALUES ('" +
                        sql_escape(name) + "', '" +
                        sql_escape(address) + "', '" +
                        sql_escape(contact) + "', '" +
                        sql_escape(type) + "', " +
                        std::string(dep_buf) + ", 'active')";

      if (!db.exec(sql)) {
        http_utils::error_json(res, 500, "Failed to create account");
        return;
      }

      unsigned long new_id = db.last_insert_id();
      res.status = 201;
      std::string json = "{\"account_number\": " + std::to_string(new_id) + ", \"balance\": " + std::string(dep_buf) + "}";
      res.set_content(json, "application/json");
    } catch (const std::exception& ex) {
      http_utils::error_json(res, 400, "Invalid request format");
    } catch (...) {
      http_utils::error_json(res, 400, "Malformed request");
    }
  });

  // -------------------------------------------------------------------------
  // FR-03  GET /api/accounts/(\d+)  -  get account details
  // Scope (Test Plan 4.3): look up an account by account_number and view its
  // latest stored details (name, address, contact, type, balance, status, created_at).
  // Unknown or malformed id -> 404.
  // -------------------------------------------------------------------------
  svr.Get(R"(/api/accounts/(\d+))", [](const httplib::Request& req, httplib::Response& res) {
    try {
      std::string id = req.matches[1];
      Database& db = Database::instance();

      std::string sql = "SELECT account_number, name, address, contact, type, balance, status, opened_at FROM accounts WHERE account_number = " + id;
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
      std::string created_at = row[7] ? row[7] : "";
      mysql_free_result(result);

      auto json_escape = [](const std::string& s) {
        std::string out;
        for (char c : s) {
          if (c == '"') out += "\\\"";
          else if (c == '\\') out += "\\\\";
          else out += c;
        }
        return out;
      };

      std::string json = "{\"account_number\": " + id +
                         ", \"name\": \"" + json_escape(name) +
                         "\", \"address\": \"" + json_escape(address) +
                         "\", \"contact\": \"" + json_escape(contact) +
                         "\", \"type\": \"" + json_escape(type) +
                         "\", \"balance\": " + balance +
                         ", \"status\": \"" + json_escape(status) +
                         "\", \"created_at\": \"" + json_escape(created_at) +
                         "\", \"opened_at\": \"" + json_escape(created_at) + "\"}";
      res.set_content(json, "application/json");
    } catch (const std::exception&) {
      http_utils::error_json(res, 404, "Unknown account");
    } catch (...) {
      http_utils::error_json(res, 404, "Unknown account");
    }
  });

  // -------------------------------------------------------------------------
  // FR-04 / NFR-02  PUT /api/accounts/(\d+)  -  modify editable customer details
  // Editable: address, contact (NOT name/balance). Unknown id -> 404.
  // NFR-02: Exception-safe handler; field caps, charset validation, malformed
  // JSON and oversized payload rejection.
  // Success -> 200 {"account_number": <id>, "address": ..., "contact": ...}
  // -------------------------------------------------------------------------
  svr.Put(R"(/api/accounts/(\d+))", [](const httplib::Request& req, httplib::Response& res) {
    try {
      if (http_utils::is_payload_oversized(req.body, 16384)) {
        http_utils::error_json(res, 400, "Request payload exceeds maximum allowed size");
        return;
      }
      if (!http_utils::is_valid_json_envelope(req.body)) {
        http_utils::error_json(res, 400, "Malformed JSON request body");
        return;
      }

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

      std::string err;
      if (!new_address.empty()) {
        if (!http_utils::validate_string(new_address, 200, "Address", err, false)) {
          http_utils::error_json(res, 400, err);
          return;
        }
      }

      if (!new_contact.empty()) {
        if (!http_utils::validate_contact(new_contact, err)) {
          http_utils::error_json(res, 400, err);
          return;
        }
      }

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
    } catch (const std::exception& ex) {
      http_utils::error_json(res, 400, "Invalid request format");
    } catch (...) {
      http_utils::error_json(res, 400, "Malformed request");
    }
  });

  // -------------------------------------------------------------------------
  // FR-05 / NFR-02  POST /api/accounts/(\d+)/close  -  close an account
  // Rules (Test Plan 4.3): only when balance is zero (or reconciled);
  // closed accounts must reject further transactions (Candidate 2 checks this).
  // Success -> 200 {"account_number": <id>, "status": "closed"}
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/accounts/(\d+)/close)", [](const httplib::Request& req, httplib::Response& res) {
    try {
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
    } catch (const std::exception& ex) {
      http_utils::error_json(res, 400, "Invalid request format");
    } catch (...) {
      http_utils::error_json(res, 400, "Malformed request");
    }
  });
}

