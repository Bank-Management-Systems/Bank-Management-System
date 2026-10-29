// ============================================================================
// env.hpp - helper to parse and load .env file into process environment variables
// ============================================================================
#pragma once
#include <cstdlib>
#include <fstream>
#include <iostream>
#include <string>

inline void load_env_file(const std::string& filename = ".env") {
  std::ifstream file(filename);
  if (!file.is_open()) {
    std::ifstream parent_file("../" + filename);
    if (parent_file.is_open()) {
      file = std::move(parent_file);
    }
  }
  if (!file.is_open()) return;

  std::string line;
  while (std::getline(file, line)) {
    size_t start = line.find_first_not_of(" \t\r\n");
    if (start == std::string::npos || line[start] == '#') continue;
    line = line.substr(start);

    size_t eq = line.find('=');
    if (eq == std::string::npos) continue;

    std::string key = line.substr(0, eq);
    size_t key_end = key.find_last_not_of(" \t");
    if (key_end != std::string::npos) key = key.substr(0, key_end + 1);

    std::string val = line.substr(eq + 1);
    size_t val_start = val.find_first_not_of(" \t");
    if (val_start != std::string::npos) val = val.substr(val_start);
    size_t val_end = val.find_last_not_of(" \t\r\n");
    if (val_end != std::string::npos) val = val.substr(0, val_end + 1);

    if (val.size() >= 2 && ((val.front() == '"' && val.back() == '"') ||
                           (val.front() == '\'' && val.back() == '\''))) {
      val = val.substr(1, val.size() - 2);
    }

    if (!key.empty()) {
      setenv(key.c_str(), val.c_str(), 0);
    }
  }
}
