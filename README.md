# Bank Management System

Team project template for 4 candidates · **12 functional requirements (3 per candidate)** ·
Backend **C++17 + cpp-httplib** · Frontend **HTML/CSS/JS** · Database **MySQL** ·
**Integration tests run automatically on every push and pull request.**

## Documentation (docs/)

| File | Purpose |
|---|---|
| `docs/Bank_Management_System_Test_Plan_V2.docx` | The 12 FRS, the 96 test cases and the candidate allocation - your working contract |
| `docs/Bank_Management_System_srs_V2.docx` | Software Requirements Specification *(team lead adds this file)* |
| `contribution.docx` | Step-by-step contribution workflow (clone → branch → switch → code → push → PR) |

## Who codes where

| Candidate | Module | Backend folder | Frontend file | FRs |
|---|---|---|---|---|
| Candidate 1 | Account Management | `backend/candidate1_account/` | `frontend/js/candidate1_accounts.js` | FR-01, FR-04, FR-05 |
| Candidate 2 | Core Transactions | `backend/candidate2_transactions/` | `frontend/js/candidate2_transactions.js` | FR-08, FR-09, FR-12 |
| Candidate 3 | Transfer & Records | `backend/candidate3_records/` | `frontend/js/candidate3_records.js` | FR-13, FR-15, FR-17 |
| Candidate 4 | Security | `backend/candidate4_security/` | `frontend/js/candidate4_security.js` | FR-18, FR-19, FR-20 |

Shared files (`backend/main.cpp`, `database/schema.sql`, `frontend/js/app.js`,
`frontend/css/style.css`) carry ownership comments - add only your own lines.

## Repository layout

```
bank_management_system/
├── docs/                        test plan + SRS uploads
├── backend/                     C++ API (cpp-httplib, single header in third_party/)
│   ├── main.cpp                 server entry - mounts all four modules
│   ├── common/                  shared db.hpp + http_utils.hpp
│   ├── candidate1_account/      ← Candidate 1 codes here
│   ├── candidate2_transactions/ ← Candidate 2 codes here
│   ├── candidate3_records/      ← Candidate 3 codes here
│   └── candidate4_security/     ← Candidate 4 codes here
├── frontend/                    basic HTML/CSS/JS (no framework)
├── database/                    MySQL schema.sql + seed.sql + ownership map
├── tests/integration/           pytest contract tests (skip until implemented)
├── scripts/run_integration_tests.sh
└── .github/workflows/ci.yml     build + tests on push / PR
```

## Prerequisites & Dependencies

Before setting up the project, ensure you have the required compilers, database tools, and libraries installed.

### Option 1: Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install -y g++ make mysql-server mysql-client libmysqlclient-dev python3 python3-pip curl
```
*(On newer Ubuntu distributions, `default-libmysqlclient-dev` may be used if `libmysqlclient-dev` is not found.)*

### Option 2: Windows Setup

For Windows developers, there are two supported paths:

#### Approach A: WSL2 (Windows Subsystem for Linux) — Recommended
Because this project relies on C++17, POSIX threads, `make`, and MySQL C client libraries, running inside **WSL2 (Ubuntu)** provides the smoothest, 100% compatible development environment.

1. Open **PowerShell as Administrator** and install WSL with Ubuntu:
   ```powershell
   wsl --install
   ```
   *(If already installed, launch it by running `wsl` or opening **Ubuntu** from the Start Menu).*
2. Inside your Ubuntu terminal, navigate to your project directory:
   ```bash
   cd /mnt/c/Users/<YourWindowsUsername>/path/to/bank_management_system
   ```
3. Install the Linux dependencies:
   ```bash
   sudo apt update
   sudo apt install -y g++ make mysql-server mysql-client libmysqlclient-dev python3 python3-pip curl
   ```
4. Follow the Linux setup steps below (localhost ports are automatically forwarded to Windows browsers).

#### Approach B: Native Windows (MySQL Workbench + MinGW-w64 / MSYS2)
If you prefer developing directly on Windows without WSL:

1. **Install MySQL 8.0 & MySQL Workbench**:
   * Download and run the [MySQL Installer for Windows](https://dev.mysql.com/downloads/installer/).
   * Select **MySQL Server 8.0** and **MySQL Workbench**.
   * During configuration, set your `root` password (e.g. `root` or `YourSecurePassword123!`).
   * Verify the Windows Service `MySQL80` is running in `services.msc`.
2. **Install C++ Compiler and Make**:
   * Install **MSYS2** from [msys2.org](https://www.msys2.org/) or **MinGW-w64**.
   * In the MSYS2 UCRT64 shell, install the compiler, make, and MySQL/MariaDB client development library:
     ```bash
     pacman -S mingw-w64-ucrt-x86_64-gcc mingw-w64-ucrt-x86_64-make mingw-w64-ucrt-x86_64-libmariadbclient
     ```
   * Add the `bin` directory (e.g., `C:\msys64\ucrt64\bin`) to your Windows system `PATH`.
3. **Install Python 3**:
   * Download from [python.org](https://www.python.org/) (ensure **"Add python.exe to PATH"** is checked).

### Python Test Dependencies (All Platforms)

For running the integration test suite:
```bash
# Linux / macOS / WSL:
pip install -r tests/requirements.txt

# Windows (PowerShell / CMD):
pip install -r tests\requirements.txt
```

---

## Database Setup (MySQL 8)

### Linux & WSL: Using Terminal

#### Step 1: Ensure MySQL Service is Running
```bash
sudo systemctl start mysql
sudo systemctl status mysql
```

#### Step 2: Create Database & User
Open the MySQL shell as `root`:
```bash
sudo mysql
```

Run the following SQL commands:
```sql
CREATE DATABASE IF NOT EXISTS bank_db CHARACTER SET utf8mb4;
CREATE USER IF NOT EXISTS 'bank_user'@'localhost' IDENTIFIED BY 'YourSecurePassword123!';
GRANT ALL PRIVILEGES ON bank_db.* TO 'bank_user'@'localhost';
FLUSH PRIVILEGES;
EXIT;
```

#### Step 3: Import Schema & Seed Data
```bash
# Using bank_user:
mysql -h 127.0.0.1 -u bank_user -p'YourSecurePassword123!' bank_db < database/schema.sql
mysql -h 127.0.0.1 -u bank_user -p'YourSecurePassword123!' bank_db < database/seed.sql

# OR using root:
mysql -u root -p bank_db < database/schema.sql
mysql -u root -p bank_db < database/seed.sql
```

### Windows: Using MySQL Workbench or PowerShell

#### Method 1: Using MySQL Workbench (GUI)
1. Open **MySQL Workbench** and connect to your local MySQL connection as `root`.
2. Open a new SQL Query tab, paste the following SQL, and click the **Execute (⚡)** button:
   ```sql
   CREATE DATABASE IF NOT EXISTS bank_db CHARACTER SET utf8mb4;
   CREATE USER IF NOT EXISTS 'bank_user'@'localhost' IDENTIFIED BY 'YourSecurePassword123!';
   GRANT ALL PRIVILEGES ON bank_db.* TO 'bank_user'@'localhost';
   FLUSH PRIVILEGES;
   ```
3. Import the tables:
   * Go to **File** → **Open SQL Script...**
   * Select `database/schema.sql` and click **Execute (⚡)**.
   * Go to **File** → **Open SQL Script...**
   * Select `database/seed.sql` and click **Execute (⚡)**.

#### Method 2: Using Windows Command Prompt / PowerShell
Ensure `mysql` is in your Windows `PATH` (typically `C:\Program Files\MySQL\MySQL Server 8.0\bin`):

```powershell
# Create database and user:
mysql -u root -p -e "CREATE DATABASE IF NOT EXISTS bank_db; CREATE USER IF NOT EXISTS 'bank_user'@'localhost' IDENTIFIED BY 'YourSecurePassword123!'; GRANT ALL PRIVILEGES ON bank_db.* TO 'bank_user'@'localhost'; FLUSH PRIVILEGES;"

# Import schema and seed:
mysql -u bank_user -pYourSecurePassword123! bank_db < database\schema.sql
mysql -u bank_user -pYourSecurePassword123! bank_db < database\seed.sql
```

---

## Configuration (`.env`)

Create your local `.env` configuration file from the template:

```bash
# Linux / WSL / Git Bash:
cp .env.example .env

# Windows PowerShell:
Copy-Item .env.example .env
```

Adjust the database credentials in `.env` if needed:

```ini
# Database Configuration (MySQL 8)
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=bank_user
DB_PASS=YourSecurePassword123!
DB_NAME=bank_db

# Backend API Server Configuration
PORT=8080
FRONTEND_DIR=frontend

# Integration Test Configuration
API_BASE_URL=http://localhost:8080
```

---

## Running the Application

### Option A: Automated Startup Script (Linux / WSL / Git Bash)

The project includes an all-in-one startup script that checks dependencies, verifies database connectivity, auto-imports tables if missing, builds the C++ backend, and launches the server:

```bash
chmod +x start.sh
./start.sh
```

### Option B: Manual Build & Run

#### On Linux / macOS / WSL:
```bash
# 1. Compile the C++ backend server
make -C backend

# 2. Start the server (serves both API and frontend on port 8080)
./backend/bank_server
```

#### On Windows (MSYS2 / MinGW-w64 / Git Bash):
```bash
# 1. Compile backend with make
cd backend
make

# 2. Start the executable
./bank_server
# Or in PowerShell:
# .\backend\bank_server.exe
```

---

## Accessing the Application

Once the server is running, open your web browser:

* **Main Portal**: [http://localhost:8080](http://localhost:8080)
* **Dedicated Login Page**: [http://localhost:8080/login.html](http://localhost:8080/login.html)
* **API Health Check**: [http://localhost:8080/api/health](http://localhost:8080/api/health)

### Default Demo Credentials (Seed Data)

| Role | Identifier / Username | Secret (Password / PIN) | Initial Balance |
|---|---|---|---|
| **Admin** | `admin` | `admin123` | N/A (Staff management & portal) |
| **Customer A** | `1001` | `1234` | Rs. 5000.00 |
| **Customer B** | `1002` | `1234` | Rs. 3000.00 |

*(New staff accounts can be provisioned by logging in as `admin` under the "Staff Management" tab.)*

---

## Running Integration Tests

Integration contract tests verify all 12 Functional Requirements against the running backend.

### Run via Test Runner Script:
```bash
bash scripts/run_integration_tests.sh
```

### Or run pytest directly (with server already running):
```bash
python3 -m pytest -v tests/integration
```

---

## Continuous Integration (CI)

`.github/workflows/ci.yml` triggers on **every push and pull request**:
* Spins up a MySQL 8 container service.
* Automatically imports `database/schema.sql` and `database/seed.sql`.
* Compiles the C++ backend using `g++` and `make`.
* Boots the server and runs `pytest tests/integration`.
* Pull requests require a passing build and zero failing contract tests.

