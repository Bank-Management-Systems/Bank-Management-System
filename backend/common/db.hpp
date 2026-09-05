// ============================================================================
// db.hpp - minimal MySQL connection wrapper shared by all candidate modules
// Owner  : SHARED (read-only; propose changes via a PR if really needed)
// Config : environment variables (never hard-code credentials!)
//          DB_HOST (default 127.0.0.1)  DB_PORT (3306)
//          DB_USER (root)               DB_PASS (root)   DB_NAME (bank_db)
// Build  : requires libmysqlclient-dev  (Ubuntu: sudo apt install libmysqlclient-dev)
// ============================================================================
#pragma once
#include <cstdlib>
#include <stdexcept>
#include <string>
#include <mysql/mysql.h>

class Database {
 public:
  static Database& instance() {
    static Database db;
    return db;
  }

  MYSQL* handle() {
    if (!connected_) connect();
    return conn_;
  }

  void connect() {
    if (connected_) return;
    conn_ = mysql_init(nullptr);
    if (!conn_) throw std::runtime_error("mysql_init failed");

    const char* host = env_or("DB_HOST", "127.0.0.1");
    const char* user = env_or("DB_USER", "root");
    const char* pass = env_or("DB_PASS", "root");
    const char* name = env_or("DB_NAME", "bank_db");
    unsigned port = static_cast<unsigned>(std::atoi(env_or("DB_PORT", "3306")));

    if (!mysql_real_connect(conn_, host, user, pass, name, port, nullptr, 0)) {
      std::string err = mysql_error(conn_);
      mysql_close(conn_);
      conn_ = nullptr;
      throw std::runtime_error(
          "MySQL connection failed: " + err +
          " (check DB_HOST/DB_USER/DB_PASS/DB_NAME env vars and that the schema in "
          "database/schema.sql was imported)");
    }
    connected_ = true;
  }

  // INSERT / UPDATE / DELETE -> true on success
  bool exec(const std::string& sql) {
    return mysql_query(handle(), sql.c_str()) == 0;
  }

  // SELECT -> result set; CALLER MUST free with mysql_free_result()
  MYSQL_RES* select(const std::string& sql) {
    if (mysql_query(handle(), sql.c_str()) != 0) return nullptr;
    return mysql_store_result(handle());
  }

  // id of the row inserted by the last exec()
  unsigned long last_insert_id() { return mysql_insert_id(handle()); }

  ~Database() {
    if (conn_) mysql_close(conn_);
  }

 private:
  static const char* env_or(const char* k, const char* d) {
    const char* v = std::getenv(k);
    return (v && *v) ? v : d;
  }
  MYSQL* conn_ = nullptr;
  bool connected_ = false;
};
