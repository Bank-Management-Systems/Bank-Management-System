// ============================================================================
// CANDIDATE 4 - Security module
// Scope     : FR-18 Staff login | FR-19 Customer authentication | FR-20 PIN change
// Reference : docs/Bank_Management_System_Test_Plan_V2.docx  -> Chapter 7 (7.1 - 7.3)
// Tests     : tests/integration/test_candidate4_security.py
// Security rules: PIN/password NEVER returned or logged; hash credentials in DB;
//                 wrong credentials -> 401 with generic message (no detail leaks).
// ============================================================================
#pragma once
#include "httplib.h"
#include "../common/http_utils.hpp"
#include "../common/db.hpp"

inline void register_security_routes(httplib::Server& svr) {

  // -------------------------------------------------------------------------
  // FR-18  POST /api/auth/staff/login   body: {"username": "...", "password": "..."}
  // Success -> 200 {"role": "staff", "username": "..."}   (add a session token later)
  // Failure -> 401 {"error": "Invalid credentials"}  (generic - never say which part was wrong)
  // -------------------------------------------------------------------------
  svr.Post("/api/auth/staff/login", [](const httplib::Request& req, httplib::Response& res) {
    // TODO(Candidate 4): implement (users table, role='staff'; hash check!)
    http_utils::not_implemented(res, "FR-18 staff login",
                                "Candidate 4 (backend/candidate4_security/security_module.hpp)");
  });

  // -------------------------------------------------------------------------
  // FR-19  POST /api/auth/customer/login  body: {"account_number": 1001, "pin": "1234"}
  // Success -> 200 {"role": "customer", "account_number": 1001}
  // Failure -> 401 generic "Invalid credentials" (unknown account = same message)
  // -------------------------------------------------------------------------
  svr.Post("/api/auth/customer/login", [](const httplib::Request& req, httplib::Response& res) {
    // TODO(Candidate 4): implement
    http_utils::not_implemented(res, "FR-19 customer authentication",
                                "Candidate 4 (backend/candidate4_security/security_module.hpp)");
  });

  // -------------------------------------------------------------------------
  // FR-20  POST /api/auth/customer/(\d+)/pin-change
  //        body: {"old_pin": "1234", "new_pin": "5678"}
  // Rules: old PIN must verify; new PIN must differ and be 4-6 digits;
  //       change takes effect immediately (next login uses the new PIN).
  // Success -> 200 {"account_number": <id>, "message": "PIN changed"}
  // Failure -> 401 wrong old PIN | 400 invalid new PIN | 404 unknown account
  // -------------------------------------------------------------------------
  svr.Post(R"(/api/auth/customer/(\d+)/pin-change)", [](const httplib::Request& req, httplib::Response& res) {
    // std::string id = req.matches[1];
    // TODO(Candidate 4): implement
    http_utils::not_implemented(res, "FR-20 PIN change",
                                "Candidate 4 (backend/candidate4_security/security_module.hpp)");
  });
}
