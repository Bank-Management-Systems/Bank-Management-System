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

#include <algorithm>
#include <cmath>
#include <cstdlib>
#include <iomanip>
#include <sstream>
#include <stdexcept>
#include <string>

namespace c3 {

// Convert a MySQL DECIMAL string like "1234.56" to integer cents (123456).
inline long long to_cents(const char* value) {
  if (!value) return 0;
  long double v = std::strtold(value, nullptr);
  return static_cast<long long>(std::llround(v * 100.0L));
}

// Format integer cents back to "1234.56" (two decimal places).
inline std::string money(long long cents) {
  std::ostringstream out;
  if (cents < 0) { out << '-'; cents = -cents; }
  out << cents / 100 << '.'
      << std::setw(2) << std::setfill('0') << cents % 100;
  return out.str();
}

// Minimal JSON-string escaping.
inline std::string esc(const char* v) {
  std::string r;
  if (!v) return r;
  for (unsigned char c : std::string(v)) {
    if      (c == '"')  r += "\\\"";
    else if (c == '\\') r += "\\\\";
    else if (c == '\n') r += "\\n";
    else if (c == '\r') r += "\\r";
    else if (c == '\t') r += "\\t";
    else if (c >= 0x20) r += static_cast<char>(c);
  }
  return r;
}

// Build a single transaction JSON object from a MySQL result row.
// Columns: id, type, amount, balance_after, related_account, created_at
inline std::string tx_json(MYSQL_ROW row) {
  std::ostringstream o;
  o << "{\"id\":"            << (row[0] ? row[0] : "0")
    << ",\"type\":\""        << esc(row[1]) << "\""
    << ",\"amount\":"        << money(to_cents(row[2]))
    << ",\"balance_after\":" << money(to_cents(row[3]))
    << ",\"related_account\":";
  if (row[4]) o << row[4]; else o << "null";
  o << ",\"created_at\":\""  << esc(row[5]) << "\"}";
  return o.str();
}

// Extract numeric account id from URL capture group 1.
inline long path_id(const httplib::Request& req) {
  if (req.matches.size() < 2) return 0;
  return std::strtol(req.matches[1].str().c_str(), nullptr, 10);
}

// Run a SELECT and throw on DB error.
inline MYSQL_RES* query(Database& db, const std::string& sql) {
  MYSQL_RES* r = db.select(sql);
  if (!r) throw std::runtime_error(mysql_error(db.handle()));
  return r;
}

}  // namespace c3


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
    long from = http_utils::get_number(req.body, "from_account", 0);
    long to   = http_utils::get_number(req.body, "to_account",   0);

    // Parse amount as decimal to preserve cents (e.g. 250.50).
    long long amount_cents = 0;
    {
      std::size_t k = req.body.find("\"amount\"");
      if (k != std::string::npos) {
        std::size_t c = req.body.find(':', k);
        if (c != std::string::npos) {
          const char* s = req.body.c_str() + c + 1;
          while (*s == ' ' || *s == '\t' || *s == '\n' || *s == '\r') ++s;
          char* e = nullptr;
          long double a = std::strtold(s, &e);
          if (e != s && std::isfinite(a) && a > 0 && a <= 9999999999.99L)
            amount_cents = static_cast<long long>(std::llround(a * 100.0L));
        }
      }
    }

    if (from <= 0 || to <= 0 || from == to || amount_cents <= 0) {
      http_utils::error_json(res, 400, "Invalid transfer details");
      return;
    }

    Database& db = Database::instance();
    MYSQL* conn  = nullptr;
    bool   tx    = false;

    auto rollback = [&]() {
      if (tx && conn) { mysql_query(conn, "ROLLBACK"); tx = false; }
    };

    try {
      conn = db.handle();

      if (mysql_query(conn, "START TRANSACTION") != 0)
        throw std::runtime_error("cannot start transaction");
      tx = true;

      // Lock both rows in primary-key order to prevent deadlocks.
      std::string lock_sql =
          "SELECT account_number, balance, status FROM accounts "
          "WHERE account_number IN (" +
          std::to_string(from) + "," + std::to_string(to) +
          ") ORDER BY account_number FOR UPDATE";

      MYSQL_RES* rs = c3::query(db, lock_sql);

      long long from_bal = -1, to_bal = -1;
      bool from_ok = false, to_ok = false;

      MYSQL_ROW row;
      while ((row = mysql_fetch_row(rs))) {
        long acc      = std::strtol(row[0], nullptr, 10);
        long long bal = c3::to_cents(row[1]);
        bool active   = row[2] && std::string(row[2]) == "active";
        if (acc == from) { from_bal = bal; from_ok = active; }
        else if (acc == to) { to_bal = bal; to_ok = active; }
      }
      mysql_free_result(rs);

      if (from_bal < 0 || to_bal < 0 || !from_ok || !to_ok) {
        rollback();
        http_utils::error_json(res, 400, "Unknown or closed account");
        return;
      }

      // Minimum balance rule: sender must retain >= 500.00 after deduction.
      if (from_bal - amount_cents < 50000LL) {
        rollback();
        http_utils::error_json(res, 400, "Insufficient funds: minimum balance is 500");
        return;
      }

      // Debit sender, credit receiver.
      std::string debit =
          "UPDATE accounts SET balance = balance - " + c3::money(amount_cents) +
          " WHERE account_number = " + std::to_string(from) + " AND status = 'active'";
      std::string credit =
          "UPDATE accounts SET balance = balance + " + c3::money(amount_cents) +
          " WHERE account_number = " + std::to_string(to)   + " AND status = 'active'";

      if (mysql_query(conn, debit.c_str())  != 0 || mysql_affected_rows(conn) != 1 ||
          mysql_query(conn, credit.c_str()) != 0 || mysql_affected_rows(conn) != 1) {
        rollback();
        http_utils::error_json(res, 500, "Transfer update failed");
        return;
      }

      long long new_from = from_bal - amount_cents;
      long long new_to   = to_bal   + amount_cents;

      // Record TRANSFER_OUT for sender and TRANSFER_IN for receiver.
      std::string out_sql =
          "INSERT INTO transactions (account_number,type,amount,balance_after,related_account) VALUES (" +
          std::to_string(from) + ",'TRANSFER_OUT'," +
          c3::money(amount_cents) + "," + c3::money(new_from) + "," +
          std::to_string(to) + ")";
      std::string in_sql =
          "INSERT INTO transactions (account_number,type,amount,balance_after,related_account) VALUES (" +
          std::to_string(to) + ",'TRANSFER_IN'," +
          c3::money(amount_cents) + "," + c3::money(new_to) + "," +
          std::to_string(from) + ")";

      if (mysql_query(conn, out_sql.c_str()) != 0 ||
          mysql_query(conn, in_sql.c_str())  != 0) {
        rollback();
        http_utils::error_json(res, 500, "Could not record transfer");
        return;
      }

      if (mysql_query(conn, "COMMIT") != 0) {
        rollback();
        http_utils::error_json(res, 500, "Could not commit transfer");
        return;
      }
      tx = false;

      res.status = 200;
      res.set_content(
          "{\"from_account\":"  + std::to_string(from) +
          ",\"to_account\":"    + std::to_string(to) +
          ",\"amount\":"        + c3::money(amount_cents) +
          ",\"from_balance\":"  + c3::money(new_from) +
          ",\"to_balance\":"    + c3::money(new_to) + "}",
          "application/json");

    } catch (const std::exception&) {
      rollback();
      http_utils::error_json(res, 500, "Unexpected transfer error");
    }
  });

  // -------------------------------------------------------------------------
  // FR-15  GET /api/accounts/(\d+)/transactions
  // Returns the account's activity, newest last or first but CONSISTENT IN
  // ORDER, including transfers (TRANSFER_IN / TRANSFER_OUT rows).
  // Success -> 200 {"account_number": <id>, "count": N,
  //                 "transactions": [ {"type":..., "amount":..., "created_at":...}, ... ]}
  // -------------------------------------------------------------------------
  svr.Get(R"(/api/accounts/(\d+)/transactions)",
      [](const httplib::Request& req, httplib::Response& res) {
    long account = c3::path_id(req);
    if (account <= 0) {
      http_utils::error_json(res, 400, "Invalid account number");
      return;
    }

    try {
      Database& db = Database::instance();

      // Verify account exists.
      MYSQL_RES* chk = db.select(
          "SELECT 1 FROM accounts WHERE account_number = " + std::to_string(account));
      if (!chk) { http_utils::error_json(res, 500, "Database error"); return; }
      bool exists = mysql_num_rows(chk) > 0;
      mysql_free_result(chk);
      if (!exists) { http_utils::error_json(res, 404, "Account not found"); return; }

      // Return all transactions in consistent chronological order.
      MYSQL_RES* rs = c3::query(db,
          "SELECT id,type,amount,balance_after,related_account,created_at "
          "FROM transactions WHERE account_number = " + std::to_string(account) +
          " ORDER BY created_at ASC, id ASC");

      std::ostringstream items;
      unsigned long count = 0;
      MYSQL_ROW row;
      while ((row = mysql_fetch_row(rs))) {
        if (count) items << ',';
        items << c3::tx_json(row);
        ++count;
      }
      mysql_free_result(rs);

      res.status = 200;
      res.set_content(
          "{\"account_number\":" + std::to_string(account) +
          ",\"count\":"          + std::to_string(count) +
          ",\"transactions\":["  + items.str() + "]}",
          "application/json");

    } catch (const std::exception&) {
      http_utils::error_json(res, 500, "Could not retrieve transaction history");
    }
  });

  // -------------------------------------------------------------------------
  // FR-17  GET /api/accounts/(\d+)/statement
  // Formal statement: opening context, each transaction, closing balance that
  // reconciles exactly with the account balance.
  // Success -> 200 {"account_number":..., "from":..., "to":...,
  //                 "opening_balance":..., "closing_balance":..., "transactions":[...]}
  // -------------------------------------------------------------------------
  svr.Get(R"(/api/accounts/(\d+)/statement)",
      [](const httplib::Request& req, httplib::Response& res) {
    // TODO: implemented in FR-17 commit
    http_utils::not_implemented(res, "FR-17 statement",
                                "Candidate 3 (backend/candidate3_records/records_module.hpp)");
  });
}
