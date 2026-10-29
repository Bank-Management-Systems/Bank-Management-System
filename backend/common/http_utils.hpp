// ============================================================================
// http_utils.hpp - shared HTTP/JSON helpers for all candidate modules
// Owner     : SHARED (read-only; propose changes via a PR if really needed)
// Note      : JSON handling here is intentionally naive (flat key/value bodies)
//             to keep the starter dependency-free. You may swap in a real JSON
//             library later with the team's agreement.
// ============================================================================
#pragma once
#include <cmath>
#include <cstdlib>
#include <string>
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

// Extract a raw value token (quoted or unquoted) for a given key from flat JSON
inline std::string get_raw_field(const std::string& body, const std::string& key) {
  std::string pat = "\"" + key + "\"";
  size_t p = body.find(pat);
  if (p == std::string::npos) return "";
  p = body.find(':', p + pat.size());
  if (p == std::string::npos) return "";
  size_t start = body.find_first_not_of(" \t\r\n", p + 1);
  if (start == std::string::npos) return "";

  if (body[start] == '"') {
    size_t end = start + 1;
    while (end < body.size()) {
      if (body[end] == '"' && body[end - 1] != '\\') break;
      end++;
    }
    if (end >= body.size()) return "";
    return body.substr(start, end - start + 1);
  } else {
    size_t end = body.find_first_of(",} \t\r\n", start);
    if (end == std::string::npos) {
      return body.substr(start);
    }
    return body.substr(start, end - start);
  }
}

// ============================================================================
// FR-11: Amount Validator (Shared)
// Rules:
//   - Numeric and finite
//   - > 0
//   - <= Rs. 1,000,000 per transaction (representative cap)
//   - At most 2 decimal places
// ============================================================================
inline bool validate_amount_str(const std::string& raw_val, double& amount_out, std::string& err_msg) {
  std::string s = trim(raw_val);
  if (s.empty()) {
    err_msg = "Amount is required and must be numeric";
    return false;
  }
  // Strip surrounding quotes if JSON value was string-quoted
  if (s.size() >= 2 && s.front() == '"' && s.back() == '"') {
    s = trim(s.substr(1, s.size() - 2));
  }
  if (s.empty()) {
    err_msg = "Amount cannot be empty";
    return false;
  }

  size_t i = 0;
  if (s[i] == '-' || s[i] == '+') {
    i++;
  }

  if (i >= s.size()) {
    err_msg = "Amount must be numeric";
    return false;
  }

  bool has_dot = false;
  size_t decimals = 0;
  size_t digit_count = 0;

  for (; i < s.size(); ++i) {
    char c = s[i];
    if (c == '.') {
      if (has_dot) {
        err_msg = "Amount must be numeric";
        return false;
      }
      has_dot = true;
    } else if (c >= '0' && c <= '9') {
      if (has_dot) {
        decimals++;
      } else {
        digit_count++;
      }
    } else {
      err_msg = "Amount must be numeric";
      return false;
    }
  }

  if (digit_count == 0 && decimals == 0) {
    err_msg = "Amount must be numeric";
    return false;
  }

  if (decimals > 2) {
    err_msg = "Amount cannot have more than 2 decimal places";
    return false;
  }

  char* endptr = nullptr;
  errno = 0;
  double val = std::strtod(s.c_str(), &endptr);
  if (endptr == s.c_str() || errno != 0 || std::isnan(val) || std::isinf(val)) {
    err_msg = "Amount must be numeric";
    return false;
  }

  if (val <= 0.0) {
    err_msg = "Amount must be greater than zero";
    return false;
  }

  // Representative cap of Rs. 1,000,000 per transaction
  if (val > 1000000.0) {
    err_msg = "Amount cannot exceed Rs. 1,000,000";
    return false;
  }

  amount_out = val;
  return true;
}

// Validate amount from JSON body (defaults to "amount" key)
inline bool validate_amount(const std::string& body, double& amount_out, std::string& err_msg, const std::string& key = "amount") {
  std::string pat = "\"" + key + "\"";
  size_t p = body.find(pat);
  if (p == std::string::npos) {
    // If body does not contain key, check if raw body itself is a plain amount string
    if (body.find('{') == std::string::npos && body.find(':') == std::string::npos && !trim(body).empty()) {
      return validate_amount_str(body, amount_out, err_msg);
    }
    err_msg = "Amount is required and must be numeric";
    return false;
  }
  std::string raw = get_raw_field(body, key);
  return validate_amount_str(raw, amount_out, err_msg);
}

// Overload with key specified second
inline bool validate_amount(const std::string& body, const std::string& key, double& amount_out, std::string& err_msg) {
  return validate_amount(body, amount_out, err_msg, key);
}

// Fallback validator for double values directly
inline bool validate_amount(double amount, std::string& err_msg) {
  if (std::isnan(amount) || std::isinf(amount) || amount <= 0.0) {
    err_msg = "Amount must be greater than zero";
    return false;
  }
  if (amount > 1000000.0) {
    err_msg = "Amount cannot exceed Rs. 1,000,000";
    return false;
  }
  double rounded = std::round(amount * 100.0) / 100.0;
  if (std::abs(amount - rounded) > 0.0001) {
    err_msg = "Amount cannot have more than 2 decimal places";
    return false;
  }
  return true;
}

inline bool validate_amount(double amount) {
  std::string dummy;
  return validate_amount(amount, dummy);
}

}  // namespace http_utils
