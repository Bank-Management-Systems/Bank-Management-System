// ============================================================================
// http_utils.hpp - shared HTTP/JSON helpers for all candidate modules
// Owner     : SHARED (read-only; propose changes via a PR if really needed)
// Note      : JSON handling here is intentionally naive (flat key/value bodies)
//             to keep the starter dependency-free. You may swap in a real JSON
//             library later with the team's agreement.
// ============================================================================
#pragma once
#include <string>
#include <cstdlib>
#include "httplib.h"

namespace http_utils {

// Uniform error JSON: {"error": "<message>"}
inline void error_json(httplib::Response& res, int status, const std::string& message) {
  res.status = status;
  std::string safe;
  for (char c : message) { if (c != '"' && c != '\\') safe += c; }  // naive escape
  res.set_content("{\"error\": \"" + safe + "\"}", "application/json");
}

// 501 = "not implemented yet". CI integration tests SKIP cases that answer 501,
// so the pipeline stays green on the skeleton and turns strict as you implement.
inline void not_implemented(httplib::Response& res, const std::string& feature,
                            const std::string& owner_hint) {
  error_json(res, 501, feature + ": not implemented yet - " + owner_hint);
}

// ---- naive flat-JSON body parsing ({"key": "value"} / {"key": 123}) --------
inline std::string trim(const std::string& s) {
  size_t a = s.find_first_not_of(" \t\r\n");
  size_t b = s.find_last_not_of(" \t\r\n");
  return a == std::string::npos ? "" : s.substr(a, b - a + 1);
}

// Extract a string field; returns "" when absent
inline std::string get_string(const std::string& body, const std::string& key) {
  std::string pat = "\"" + key + "\"";
  size_t p = body.find(pat);
  if (p == std::string::npos) return "";
  p = body.find(':', p + pat.size());
  if (p == std::string::npos) return "";
  p = body.find('"', p);
  if (p == std::string::npos) return "";
  size_t e = body.find('"', p + 1);
  if (e == std::string::npos) return "";
  return body.substr(p + 1, e - p - 1);
}

// Extract a numeric field; returns def when absent or unparsable
inline long get_number(const std::string& body, const std::string& key, long def = 0) {
  std::string pat = "\"" + key + "\"";
  size_t p = body.find(pat);
  if (p == std::string::npos) return def;
  p = body.find(':', p + pat.size());
  if (p == std::string::npos) return def;
  return std::strtol(trim(body.substr(p + 1)).c_str(), nullptr, 10);
}

}  // namespace http_utils
