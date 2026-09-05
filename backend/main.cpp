// ============================================================================
// Bank Management System - API server entry point
// Tech stack : C++17 + cpp-httplib (single header) + MySQL C API
// Owner      : SHARED (each candidate adds exactly ONE registration line below)
// ============================================================================
#include <cstdlib>
#include <iostream>
#include <string>

#include "httplib.h"

#include "common/http_utils.hpp"
// Candidate module headers - each candidate implements their own file:
#include "candidate1_account/account_module.hpp"       // Candidate 1: FR-01, FR-04, FR-05
#include "candidate2_transactions/transactions_module.hpp" // Candidate 2: FR-08, FR-09, FR-12
#include "candidate3_records/records_module.hpp"       // Candidate 3: FR-13, FR-15, FR-17
#include "candidate4_security/security_module.hpp"     // Candidate 4: FR-18, FR-19, FR-20

int main() {
  httplib::Server svr;

  // --------------------------------------------------------------------------
  // Worked example (implemented): health check used by CI to know the API is up
  // --------------------------------------------------------------------------
  svr.Get("/api/health", [](const httplib::Request&, httplib::Response& res) {
    res.status = 200;
    res.set_content(R"({"status": "ok", "service": "bank-management-api"})", "application/json");
  });

  // --------------------------------------------------------------------------
  // Route registration - ONE line per candidate. Do not remove each other's lines.
  // --------------------------------------------------------------------------
  register_account_routes(svr);      // Candidate 1 - /api/accounts...
  register_transaction_routes(svr);  // Candidate 2 - /api/accounts/{id}/deposit|withdraw|balance
  register_record_routes(svr);       // Candidate 3 - /api/transfers, /api/accounts/{id}/transactions|statement
  register_security_routes(svr);     // Candidate 4 - /api/auth/...

  // --------------------------------------------------------------------------
  // Serve the frontend (basic HTML/CSS/JS) from the repository root
  // --------------------------------------------------------------------------
  const char* fe = std::getenv("FRONTEND_DIR");
  std::string frontend_dir = (fe && *fe) ? fe : "frontend";
  if (!svr.set_mount_point("/", frontend_dir)) {
    std::cerr << "[warn] frontend dir not found at '" << frontend_dir
              << "' - API-only mode (open frontend/index.html manually)\n";
  }

  const char* port_env = std::getenv("PORT");
  int port = port_env ? std::atoi(port_env) : 8080;

  std::cout << "Bank Management System API listening on http://0.0.0.0:" << port << "\n";
  std::cout << "Health check: http://localhost:" << port << "/api/health\n";
  if (!svr.listen("0.0.0.0", port)) {
    std::cerr << "[fatal] could not bind port " << port << "\n";
    return 1;
  }
  return 0;
}
