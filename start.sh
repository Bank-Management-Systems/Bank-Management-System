#!/usr/bin/env bash
# ============================================================================
# Bank Management System - Startup Script
# Automatically verifies dependencies, checks DB connection, builds & starts backend + frontend
# ============================================================================
set -e

# Change to project root directory
cd "$(dirname "$0")"

# Colors for terminal output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================================${NC}"
echo -e "${BLUE}       Bank Management System - Startup Script      ${NC}"
echo -e "${BLUE}====================================================${NC}"

# 1. Environment File Check
if [ ! -f .env ]; then
    if [ -f .env.example ]; then
        echo -e "${YELLOW}[WARN] .env file not found. Creating from .env.example ...${NC}"
        cp .env.example .env
    else
        echo -e "${RED}[ERROR] Neither .env nor .env.example file was found in root directory!${NC}"
        exit 1
    fi
fi

# Load environment variables from .env
export $(grep -v '^#' .env | xargs 2>/dev/null || true)

DB_HOST="${DB_HOST:-127.0.0.1}"
DB_PORT="${DB_PORT:-3306}"
DB_USER="${DB_USER:-root}"
DB_PASS="${DB_PASS:-root}"
DB_NAME="${DB_NAME:-bank_db}"
PORT="${PORT:-8080}"
FRONTEND_DIR="${FRONTEND_DIR:-frontend}"

# 2. Check System Dependencies
echo -e "${GREEN}[1/4] Checking required system dependencies ...${NC}"
MISSING_PKGS=()

if ! command -v g++ &> /dev/null; then MISSING_PKGS+=("g++"); fi
if ! command -v make &> /dev/null; then MISSING_PKGS+=("make"); fi
if ! command -v mysql &> /dev/null; then MISSING_PKGS+=("mysql-client"); fi

# Check MySQL header file availability
if ! echo '#include <mysql/mysql.h>' | g++ -E - &> /dev/null; then
    MISSING_PKGS+=("libmysqlclient-dev")
fi

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    echo -e "${YELLOW}[INFO] Missing dependencies detected: ${MISSING_PKGS[*]}${NC}"
    echo -e "${YELLOW}[INFO] Attempting automatic package installation ...${NC}"
    if command -v apt-get &> /dev/null; then
        sudo apt-get update || true
        sudo apt-get install -y g++ make mysql-client libmysqlclient-dev || sudo apt-get install -y default-libmysqlclient-dev
    else
        echo -e "${RED}[ERROR] Package manager apt-get not found. Please manually install: ${MISSING_PKGS[*]}${NC}"
        exit 1
    fi
else
    echo -e "${GREEN}[OK] All required dependencies (g++, make, mysql, libmysqlclient-dev) are installed.${NC}"
fi

# 3. Database Connection Check
echo -e "${GREEN}[2/4] Verifying database connection ...${NC}"

if ! mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" -e "USE $DB_NAME;" &> /dev/null; then
    echo -e "\n${RED}==============================================================${NC}"
    echo -e "${RED}[DATABASE ERROR] Could not connect to MySQL database!${NC}"
    echo -e "${RED}Connection Details: Host=$DB_HOST, Port=$DB_PORT, User=$DB_USER, DB=$DB_NAME${NC}"
    echo -e "${RED}==============================================================${NC}"
    echo -e "${YELLOW}Please check your MySQL server status and verify credentials in .env file.${NC}"
    echo -e "${YELLOW}If you have not created the database and user yet, execute in MySQL Workbench:${NC}"
    echo -e "  CREATE DATABASE IF NOT EXISTS $DB_NAME;"
    echo -e "  CREATE USER '$DB_USER'@'localhost' IDENTIFIED BY '$DB_PASS';"
    echo -e "  GRANT ALL PRIVILEGES ON $DB_NAME.* TO '$DB_USER'@'localhost';"
    echo -e "  FLUSH PRIVILEGES;"
    echo -e "${RED}==============================================================${NC}\n"
    exit 1
else
    echo -e "${GREEN}[OK] Database connection to '$DB_NAME' established successfully.${NC}"
fi

# Auto-import schema and seed data if database is empty
TABLE_COUNT=$(mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" -e "SHOW TABLES;" 2>/dev/null | wc -l)
if [ "$TABLE_COUNT" -le 1 ]; then
    echo -e "${YELLOW}[INFO] Database tables missing. Importing schema.sql and seed.sql ...${NC}"
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < database/schema.sql
    mysql -h "$DB_HOST" -P "$DB_PORT" -u "$DB_USER" -p"$DB_PASS" "$DB_NAME" < database/seed.sql
    echo -e "${GREEN}[OK] Schema and seed data imported successfully.${NC}"
fi

# 4. Build Backend
echo -e "${GREEN}[3/4] Compiling C++ backend server ...${NC}"
make -C backend

# 5. Launch Backend + Frontend
echo -e "${GREEN}[4/4] Starting Bank Management System ...${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "${GREEN}  ✓ Frontend URL    : http://localhost:${PORT}${NC}"
echo -e "${GREEN}  ✓ Backend API URL : http://localhost:${PORT}/api${NC}"
echo -e "${GREEN}  ✓ API Health Check: http://localhost:${PORT}/api/health${NC}"
echo -e "${BLUE}====================================================${NC}"
echo -e "${YELLOW}Press Ctrl+C to stop the server.${NC}\n"

# Run server binary directly (serves frontend static assets + API endpoints)
./backend/bank_server
