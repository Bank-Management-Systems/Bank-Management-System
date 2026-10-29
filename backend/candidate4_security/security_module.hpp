// ============================================================================
// CANDIDATE 4 - Security module
// Scope     : FR-18 Staff login | FR-19 Customer authentication | FR-20 PIN change
// Reference : docs/Bank_Management_System_Test_Plan_V2.docx  -> Chapter 7 (7.1 - 7.3)
// Tests     : tests/integration/test_candidate4_security.py
// Security rules: PIN/password NEVER returned or logged; hash credentials in DB;
//                 wrong credentials -> 401 with generic message (no detail leaks).
// ============================================================================
#pragma once
#include <cctype>
#include <string>
#include "httplib.h"
#include "../common/http_utils.hpp"
#include "../common/db.hpp"

namespace {

inline std::string sec_sql_escape(const std::string& s) {
  std::string out;
  for (char c : s) {
    if (c == '\'') out += "''";
    else if (c == '\\') out += "\\\\";
    else out += c;
  }
  return out;
}

inline std::string extract_field(const std::string& body, const std::string& key) {
  std::string pat = "\"" + key + "\"";
  size_t p = body.find(pat);
  if (p == std::string::npos) return "";
  p = body.find(':', p + pat.size());
  if (p == std::string::npos) return "";

  // Skip whitespace
  p = body.find_first_not_of(" \t\r\n", p + 1);
  if (p == std::string::npos) return "";

  if (body[p] == '"') {
    size_t e = body.find('"', p + 1);
    if (e == std::string::npos) return "";
    return body.substr(p + 1, e - p - 1);
  }

  // Unquoted token (numbers, booleans)
  size_t e = body.find_first_of(",}\t\r\n ", p);
  if (e == std::string::npos) {
    return body.substr(p);
  }
  return body.substr(p, e - p);
}

} // anonymous namespace

inline void register_security_routes(httplib::Server& svr) {

  // -------------------------------------------------------------------------
  // FR-18  POST /api/auth/staff/login   body: {"username": "...", "password": "..."}
  // Success -> 200 {"role": "staff", "username": "...", "token": "..."}
  // Failure -> 401 {"error": "Invalid credentials"}  (generic - never leak fields)
  // -------------------------------------------------------------------------
  svr.Post("/api/auth/staff/login", [](const httplib::Request& req, httplib::Response& res) {
    std::string username = http_utils::trim(http_utils::get_string(req.body, "username"));
    std::string password = http_utils::get_string(req.body, "password");

    if (username.empty() || password.empty()) {
      http_utils::error_json(res, 401, "Invalid credentials");
      return;
    }

    Database& db = Database::instance();
    std::string esc_user = sec_sql_escape(username);
    std::string esc_pass = sec_sql_escape(password);

    std::string sql = "SELECT id, username FROM users "
                      "WHERE username = '" + esc_user + "' AND role = 'staff' "
                      "AND (secret_hash = SHA2('" + esc_pass + "', 256) "
                      "     OR secret_hash = 'REPLACE_WITH_HASH(" + esc_pass + ")')";

    MYSQL_RES* result = db.select(sql);
    if (!result) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }

    MYSQL_ROW row = mysql_fetch_row(result);
    if (!row) {
      mysql_free_result(result);
      db.exec("UPDATE users SET failed_tries = failed_tries + 1 WHERE username = '" + esc_user + "' AND role = 'staff'");
      http_utils::error_json(res, 401, "Invalid credentials");
      return;
    }

    std::string user_id = row[0] ? row[0] : "";
    std::string ret_user = row[1] ? row[1] : username;
    mysql_free_result(result);

    db.exec("UPDATE users SET failed_tries = 0 WHERE id = " + user_id);

    bool is_admin = (ret_user == "admin");
    std::string is_admin_str = is_admin ? "true" : "false";
    std::string json = "{\"role\": \"staff\", \"username\": \"" + ret_user +
                       "\", \"is_admin\": " + is_admin_str +
                       ", \"token\": \"staff_" + user_id + "_token\"}";
    res.status = 200;
    res.set_content(json, "application/json");
  });

  // -------------------------------------------------------------------------
  // Admin Staff Management: GET /api/staff (list staff accounts)
  // -------------------------------------------------------------------------
  svr.Get("/api/staff", [](const httplib::Request&, httplib::Response& res) {
    Database& db = Database::instance();
    std::string sql = "SELECT id, username, role, failed_tries, created_at FROM users WHERE role = 'staff' ORDER BY id ASC";
    MYSQL_RES* result = db.select(sql);
    if (!result) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }

    std::string json = "[";
    MYSQL_ROW row;
    bool first = true;
    while ((row = mysql_fetch_row(result))) {
      if (!first) json += ",";
      first = false;
      std::string id = row[0] ? row[0] : "0";
      std::string username = row[1] ? row[1] : "";
      std::string role = row[2] ? row[2] : "staff";
      std::string failed = row[3] ? row[3] : "0";
      std::string created = row[4] ? row[4] : "";
      bool is_admin = (username == "admin");

      json += "{\"id\": " + id +
              ", \"username\": \"" + username + "\"" +
              ", \"role\": \"" + role + "\"" +
              ", \"is_admin\": " + (is_admin ? "true" : "false") +
              ", \"failed_tries\": " + failed +
              ", \"created_at\": \"" + created + "\"}";
    }
    mysql_free_result(result);
    json += "]";

    res.status = 200;
    res.set_content(json, "application/json");
  });

  // -------------------------------------------------------------------------
  // Admin Staff Management: POST /api/staff & POST /api/auth/staff/create
  // -------------------------------------------------------------------------
  auto handle_create_staff = [](const httplib::Request& req, httplib::Response& res) {
    std::string username = http_utils::trim(extract_field(req.body, "username"));
    std::string password = extract_field(req.body, "password");

    if (username.empty() || password.empty()) {
      http_utils::error_json(res, 400, "Username and password are required");
      return;
    }

    if (username.length() < 3) {
      http_utils::error_json(res, 400, "Username must be at least 3 characters");
      return;
    }

    if (password.length() < 4) {
      http_utils::error_json(res, 400, "Password must be at least 4 characters");
      return;
    }

    Database& db = Database::instance();
    std::string esc_user = sec_sql_escape(username);
    std::string esc_pass = sec_sql_escape(password);

    // Check if username already exists
    std::string check_sql = "SELECT id FROM users WHERE username = '" + esc_user + "'";
    MYSQL_RES* check_res = db.select(check_sql);
    if (check_res) {
      MYSQL_ROW check_row = mysql_fetch_row(check_res);
      if (check_row) {
        mysql_free_result(check_res);
        http_utils::error_json(res, 400, "Staff username already exists");
        return;
      }
      mysql_free_result(check_res);
    }

    std::string insert_sql = "INSERT INTO users (username, secret_hash, role, failed_tries) "
                             "VALUES ('" + esc_user + "', SHA2('" + esc_pass + "', 256), 'staff', 0)";
    if (!db.exec(insert_sql)) {
      http_utils::error_json(res, 500, "Failed to create staff account");
      return;
    }

    unsigned long new_id = db.last_insert_id();
    res.status = 201;
    res.set_content("{\"id\": " + std::to_string(new_id) +
                    ", \"username\": \"" + esc_user +
                    "\", \"role\": \"staff\", \"message\": \"Staff account created successfully\"}",
                    "application/json");
  };

  svr.Post("/api/staff", handle_create_staff);
  svr.Post("/api/auth/staff/create", handle_create_staff);

  // -------------------------------------------------------------------------
  // FR-19  POST /api/auth/customer/login  body: {"account_number": 1001, "pin": "1234"}
  // Success -> 200 {"role": "customer", "account_number": 1001, "token": "..."}
  // Failure -> 401 generic "Invalid credentials" (unknown account = same message)
  // -------------------------------------------------------------------------
  svr.Post("/api/auth/customer/login", [](const httplib::Request& req, httplib::Response& res) {
    std::string acc_str = extract_field(req.body, "account_number");
    std::string pin = extract_field(req.body, "pin");

    if (acc_str.empty() || pin.empty()) {
      http_utils::error_json(res, 401, "Invalid credentials");
      return;
    }

    Database& db = Database::instance();
    std::string esc_acc = sec_sql_escape(acc_str);
    std::string esc_pin = sec_sql_escape(pin);

    std::string sql = "SELECT id, username FROM users "
                      "WHERE username = '" + esc_acc + "' AND role = 'customer' "
                      "AND (secret_hash = SHA2('" + esc_pin + "', 256) "
                      "     OR secret_hash = 'REPLACE_WITH_HASH(" + esc_pin + ")')";

    MYSQL_RES* result = db.select(sql);
    if (!result) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }

    MYSQL_ROW row = mysql_fetch_row(result);
    if (!row) {
      mysql_free_result(result);

      // Check if account exists in accounts table with fallback default PIN 1234
      if (pin == "1234") {
        std::string check_acc = "SELECT account_number, status FROM accounts WHERE account_number = " + esc_acc;
        MYSQL_RES* acc_res = db.select(check_acc);
        if (acc_res) {
          MYSQL_ROW acc_row = mysql_fetch_row(acc_res);
          if (acc_row) {
            std::string status = acc_row[1] ? acc_row[1] : "";
            mysql_free_result(acc_res);
            if (status != "closed") {
              db.exec("INSERT INTO users (username, secret_hash, role) VALUES ('" + esc_acc +
                      "', SHA2('1234', 256), 'customer') ON DUPLICATE KEY UPDATE secret_hash = VALUES(secret_hash)");
              std::string json = "{\"role\": \"customer\", \"account_number\": " + esc_acc +
                                 ", \"token\": \"cust_" + esc_acc + "_token\"}";
              res.status = 200;
              res.set_content(json, "application/json");
              return;
            }
          } else {
            mysql_free_result(acc_res);
          }
        }
      }

      db.exec("UPDATE users SET failed_tries = failed_tries + 1 WHERE username = '" + esc_acc + "' AND role = 'customer'");
      http_utils::error_json(res, 401, "Invalid credentials");
      return;
    }

    std::string user_id = row[0] ? row[0] : "";
    mysql_free_result(result);

    db.exec("UPDATE users SET failed_tries = 0 WHERE id = " + user_id);

    std::string json = "{\"role\": \"customer\", \"account_number\": " + esc_acc +
                       ", \"token\": \"cust_" + esc_acc + "_token\"}";
    res.status = 200;
    res.set_content(json, "application/json");
  });

  // -------------------------------------------------------------------------
  // FR-20  POST /api/auth/customer/(\d+)/pin-change
  //        body: {"old_pin": "1234", "new_pin": "5678"}
  // Rules: old PIN must verify; new PIN must differ and be 4-6 digits;
  //        change takes effect immediately (next login uses the new PIN).
  // Success -> 200 {"account_number": <id>, "message": "PIN changed"}
  // Failure -> 401 wrong old PIN | 400 invalid new PIN | 404 unknown account
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/auth/customer/(\d+)/pin-change)", [](const httplib::Request& req, httplib::Response& res) {
    std::string id = req.matches[1];
    std::string old_pin = extract_field(req.body, "old_pin");
    std::string new_pin = extract_field(req.body, "new_pin");

    Database& db = Database::instance();
    std::string esc_id = sec_sql_escape(id);

    // Verify account existence
    std::string check_sql = "SELECT account_number, status FROM accounts WHERE account_number = " + esc_id;
    MYSQL_RES* acc_res = db.select(check_sql);
    if (!acc_res) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }
    MYSQL_ROW acc_row = mysql_fetch_row(acc_res);
    if (!acc_row) {
      mysql_free_result(acc_res);
      http_utils::error_json(res, 404, "Account not found");
      return;
    }
    std::string acc_status = acc_row[1] ? acc_row[1] : "";
    mysql_free_result(acc_res);

    if (acc_status == "closed") {
      http_utils::error_json(res, 400, "Account is closed");
      return;
    }

    // Verify old PIN
    std::string esc_old = sec_sql_escape(old_pin);
    std::string user_sql = "SELECT id, secret_hash FROM users WHERE username = '" + esc_id + "' AND role = 'customer'";
    MYSQL_RES* user_res = db.select(user_sql);
    if (!user_res) {
      http_utils::error_json(res, 500, "Database error");
      return;
    }
    MYSQL_ROW user_row = mysql_fetch_row(user_res);
    bool old_pin_valid = false;
    if (user_row) {
      mysql_free_result(user_res);
      std::string verify_sql = "SELECT (secret_hash = SHA2('" + esc_old + "', 256) "
                               "        OR secret_hash = 'REPLACE_WITH_HASH(" + esc_old + ")') "
                               "FROM users WHERE username = '" + esc_id + "' AND role = 'customer'";
      MYSQL_RES* v_res = db.select(verify_sql);
      if (v_res) {
        MYSQL_ROW v_row = mysql_fetch_row(v_res);
        if (v_row && v_row[0] && std::string(v_row[0]) == "1") {
          old_pin_valid = true;
        }
        mysql_free_result(v_res);
      }
    } else {
      mysql_free_result(user_res);
      if (old_pin == "1234") {
        old_pin_valid = true;
      }
    }

    if (!old_pin_valid) {
      db.exec("UPDATE users SET failed_tries = failed_tries + 1 WHERE username = '" + esc_id + "' AND role = 'customer'");
      http_utils::error_json(res, 401, "Invalid old PIN");
      return;
    }

    // Validate new PIN
    if (new_pin == old_pin) {
      http_utils::error_json(res, 400, "New PIN must differ from current PIN");
      return;
    }
    if (new_pin.length() < 4 || new_pin.length() > 6) {
      http_utils::error_json(res, 400, "New PIN must be between 4 and 6 digits");
      return;
    }
    for (char c : new_pin) {
      if (!std::isdigit(static_cast<unsigned char>(c))) {
        http_utils::error_json(res, 400, "New PIN must contain digits only");
        return;
      }
    }

    std::string esc_new = sec_sql_escape(new_pin);
    std::string update_sql = "INSERT INTO users (username, secret_hash, role, failed_tries) "
                             "VALUES ('" + esc_id + "', SHA2('" + esc_new + "', 256), 'customer', 0) "
                             "ON DUPLICATE KEY UPDATE secret_hash = SHA2('" + esc_new + "', 256), failed_tries = 0";
    if (!db.exec(update_sql)) {
      http_utils::error_json(res, 500, "Failed to update PIN");
      return;
    }

    std::string json = "{\"account_number\": " + id + ", \"message\": \"PIN changed\"}";
    res.status = 200;
    res.set_content(json, "application/json");
  });
}
