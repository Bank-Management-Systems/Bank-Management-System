
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

namespace candidate3_records {

inline long long to_cents(const char* value) {
  if (!value) return 0;
  long double amount = std::strtold(value, nullptr);
  return static_cast<long long>(std::llround(amount * 100.0L));
}

inline std::string money(long long cents) {
  std::ostringstream out;
  out << (cents < 0 ? "-" : "")
      << std::llabs(cents) / 100 << "."
      << std::setw(2) << std::setfill('0') << std::llabs(cents) % 100;
  return out.str();
}

inline std::string json_escape(const char* value) {
  std::string result;
  if (!value) return result;

  for (unsigned char c : std::string(value)) {
    switch (c) {
      case '"': result += "\\\""; break;
      case '\\': result += "\\\\"; break;
      case '\n': result += "\\n"; break;
      case '\r': result += "\\r"; break;
      case '\t': result += "\\t"; break;
      default:
        if (c >= 0x20) result += static_cast<char>(c);
    }
  }
  return result;
}

inline long path_account(const httplib::Request& req) {
  if (req.matches.size() < 2) return 0;
  return std::strtol(req.matches[1].str().c_str(), nullptr, 10);
}

inline std::string transaction_json(
    const char* id, const char* type, const char* amount,
    const char* balance_after, const char* related_account,
    const char* created_at) {
  std::ostringstream out;
  out << "{\"id\":" << (id ? id : "0")
      << ",\"type\":\"" << json_escape(type)
      << "\",\"amount\":" << money(to_cents(amount))
      << ",\"balance_after\":" << money(to_cents(balance_after))
      << ",\"related_account\":";

  if (related_account) out << related_account;
  else out << "null";

  out << ",\"created_at\":\"" << json_escape(created_at) << "\"}";
  return out.str();
}

inline MYSQL_RES* select_or_throw(Database& db, const std::string& sql) {
  MYSQL_RES* result = db.select(sql);
  if (!result) {
    throw std::runtime_error(mysql_error(db.handle()));
  }
  return result;
}

}  // namespace candidate3_records


inline void register_record_routes(httplib::Server& svr) {

  // FR-13: Atomic funds transfer
  svr.Post("/api/transfers",
      [](const httplib::Request& req, httplib::Response& res) {
    long from = http_utils::get_number(req.body, "from_account", 0);
    long to = http_utils::get_number(req.body, "to_account", 0);

    // Parse amount as a decimal number, then convert to cents.
    long long amount_cents = 0;
    try {
      std::size_t key = req.body.find("\"amount\"");
      if (key != std::string::npos) {
        std::size_t colon = req.body.find(':', key);
        if (colon != std::string::npos) {
          const char* start = req.body.c_str() + colon + 1;
          while (*start == ' ' || *start == '\t' ||
                 *start == '\n' || *start == '\r') ++start;

          char* end = nullptr;
          long double amount = std::strtold(start, &end);
          if (end != start && std::isfinite(amount) && amount > 0 &&
              amount <= 9999999999.99L) {
            amount_cents = static_cast<long long>(
                std::llround(amount * 100.0L));
          }
        }
      }
    } catch (...) {
      amount_cents = 0;
    }

    if (from <= 0 || to <= 0 || from == to || amount_cents <= 0) {
      http_utils::error_json(res, 400, "Invalid transfer details");
      return;
    }

    Database& db = Database::instance();
    MYSQL* conn = nullptr;
    bool started = false;

    auto rollback = [&]() {
      if (started && conn) {
        mysql_query(conn, "ROLLBACK");
        started = false;
      }
    };

    try {
      conn = db.handle();

      if (mysql_query(conn, "START TRANSACTION") != 0) {
        http_utils::error_json(res, 500, "Could not start transaction");
        return;
      }
      started = true;

      // Lock both accounts in a consistent order to prevent concurrent
      // transfers from spending the same balance.
      std::string lock_sql =
          "SELECT account_number, balance, status FROM accounts "
          "WHERE account_number IN (" + std::to_string(from) + "," +
          std::to_string(to) + ") ORDER BY account_number FOR UPDATE";

      MYSQL_RES* result = candidate3_records::select_or_throw(db, lock_sql);

      long long from_balance = -1;
      long long to_balance = -1;
      bool from_active = false;
      bool to_active = false;

      MYSQL_ROW row;
      while ((row = mysql_fetch_row(result))) {
        long account = std::strtol(row[0], nullptr, 10);
        long long balance = candidate3_records::to_cents(row[1]);
        bool active = row[2] && std::string(row[2]) == "active";

        if (account == from) {
          from_balance = balance;
          from_active = active;
        } else if (account == to) {
          to_balance = balance;
          to_active = active;
        }
      }
      mysql_free_result(result);

      if (from_balance < 0 || to_balance < 0 ||
          !from_active || !to_active) {
        rollback();
        http_utils::error_json(res, 400, "Unknown or closed account");
        return;
      }

      if (from_balance - amount_cents < 50000) {
        rollback();
        http_utils::error_json(
            res, 400, "Insufficient funds: minimum balance is 500");
        return;
      }

      const std::string debit =
          "UPDATE accounts SET balance = balance - " +
          candidate3_records::money(amount_cents) +
          " WHERE account_number = " + std::to_string(from) +
          " AND status = 'active'";

      const std::string credit =
          "UPDATE accounts SET balance = balance + " +
          candidate3_records::money(amount_cents) +
          " WHERE account_number = " + std::to_string(to) +
          " AND status = 'active'";

      if (mysql_query(conn, debit.c_str()) != 0 ||
          mysql_affected_rows(conn) != 1 ||
          mysql_query(conn, credit.c_str()) != 0 ||
          mysql_affected_rows(conn) != 1) {
        rollback();
        http_utils::error_json(res, 500, "Transfer failed; rolled back");
        return;
      }

      long long new_from = from_balance - amount_cents;
      long long new_to = to_balance + amount_cents;

      std::string out_sql =
          "INSERT INTO transactions "
          "(account_number,type,amount,balance_after,related_account) VALUES (" +
          std::to_string(from) + ",'TRANSFER_OUT'," +
          candidate3_records::money(amount_cents) + "," +
          candidate3_records::money(new_from) + "," +
          std::to_string(to) + ")";

      std::string in_sql =
          "INSERT INTO transactions "
          "(account_number,type,amount,balance_after,related_account) VALUES (" +
          std::to_string(to) + ",'TRANSFER_IN'," +
          candidate3_records::money(amount_cents) + "," +
          candidate3_records::money(new_to) + "," +
          std::to_string(from) + ")";

      if (mysql_query(conn, out_sql.c_str()) != 0 ||
          mysql_query(conn, in_sql.c_str()) != 0) {
        rollback();
        http_utils::error_json(res, 500, "Could not record transfer");
        return;
      }

      if (mysql_query(conn, "COMMIT") != 0) {
        rollback();
        http_utils::error_json(res, 500, "Could not commit transfer");
        return;
      }
      started = false;

      res.status = 200;
      res.set_content(
          "{\"from_account\":" + std::to_string(from) +
          ",\"to_account\":" + std::to_string(to) +
          ",\"amount\":" + candidate3_records::money(amount_cents) +
          ",\"from_balance\":" + candidate3_records::money(new_from) +
          ",\"to_balance\":" + candidate3_records::money(new_to) + "}",
          "application/json");

    } catch (const std::exception&) {
      rollback();
      http_utils::error_json(res, 500, "Unexpected transfer error");
    }
  });


  // FR-15: Transaction history
  svr.Get(R"(/api/accounts/(\d+)/transactions)",
      [](const httplib::Request& req, httplib::Response& res) {
    long account = candidate3_records::path_account(req);
    if (account <= 0) {
      http_utils::error_json(res, 400, "Invalid account number");
      return;
    }

    try {
      Database& db = Database::instance();

      std::string account_sql =
          "SELECT account_number FROM accounts WHERE account_number = " +
          std::to_string(account);

      MYSQL_RES* account_result = db.select(account_sql);
      if (!account_result) {
        http_utils::error_json(res, 500, "Could not read account");
        return;
      }

      bool exists = mysql_num_rows(account_result) > 0;
      mysql_free_result(account_result);

      if (!exists) {
        http_utils::error_json(res, 404, "Account not found");
        return;
      }

      std::string sql =
          "SELECT id,type,amount,balance_after,related_account,created_at "
          "FROM transactions WHERE account_number = " +
          std::to_string(account) + " ORDER BY created_at ASC,id ASC";

      MYSQL_RES* result = candidate3_records::select_or_throw(db, sql);
      std::ostringstream items;
      unsigned long count = 0;
      MYSQL_ROW row;

      while ((row = mysql_fetch_row(result))) {
        if (count) items << ",";
        items << candidate3_records::transaction_json(
            row[0], row[1], row[2], row[3], row[4], row[5]);
        ++count;
      }
      mysql_free_result(result);

      res.status = 200;
      res.set_content(
          "{\"account_number\":" + std::to_string(account) +
          ",\"count\":" + std::to_string(count) +
          ",\"transactions\":[" + items.str() + "]}",
          "application/json");

    } catch (const std::exception&) {
      http_utils::error_json(res, 500, "Could not retrieve transaction history");
    }
  });


  // FR-17: Account statement
  // This statement covers all recorded activity for the account.
  svr.Get(R"(/api/accounts/(\d+)/statement)",
      [](const httplib::Request& req, httplib::Response& res) {
    long account = candidate3_records::path_account(req);
    if (account <= 0) {
      http_utils::error_json(res, 400, "Invalid account number");
      return;
    }

    try {
      Database& db = Database::instance();

      std::string account_sql =
          "SELECT balance FROM accounts WHERE account_number = " +
          std::to_string(account);

      MYSQL_RES* account_result = candidate3_records::select_or_throw(
          db, account_sql);

      MYSQL_ROW account_row = mysql_fetch_row(account_result);
      if (!account_row) {
        mysql_free_result(account_result);
        http_utils::error_json(res, 404, "Account not found");
        return;
      }

      long long closing_balance =
          candidate3_records::to_cents(account_row[0]);
      mysql_free_result(account_result);

      std::string sql =
          "SELECT id,type,amount,balance_after,related_account,created_at "
          "FROM transactions WHERE account_number = " +
          std::to_string(account) + " ORDER BY created_at ASC,id ASC";

      MYSQL_RES* result = candidate3_records::select_or_throw(db, sql);
      std::ostringstream items;
      unsigned long count = 0;
      long long net_change = 0;
      MYSQL_ROW row;

      while ((row = mysql_fetch_row(result))) {
        long long amount = candidate3_records::to_cents(row[2]);
        std::string type = row[1] ? row[1] : "";

        if (type == "DEPOSIT" || type == "TRANSFER_IN")
          net_change += amount;
        else if (type == "WITHDRAWAL" || type == "TRANSFER_OUT")
          net_change -= amount;

        if (count) items << ",";
        items << candidate3_records::transaction_json(
            row[0], row[1], row[2], row[3], row[4], row[5]);
        ++count;
      }
      mysql_free_result(result);

      // Reconcile the statement to the stored account balance.
      // For accounts with no transactions, opening balance equals closing.
      long long opening_balance = closing_balance - net_change;

      res.status = 200;
      res.set_content(
          "{\"account_number\":" + std::to_string(account) +
          ",\"from\":null,\"to\":null" +
          ",\"opening_balance\":" +
          candidate3_records::money(opening_balance) +
          ",\"closing_balance\":" +
          candidate3_records::money(closing_balance) +
          ",\"count\":" + std::to_string(count) +
          ",\"transactions\":[" + items.str() + "]}",
          "application/json");

    } catch (const std::exception&) {
      http_utils::error_json(res, 500, "Could not generate account statement");
    }
  });
}
