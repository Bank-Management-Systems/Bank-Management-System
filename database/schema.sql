```sql
-- ============================================================================
-- Bank Management System - MySQL schema
-- Import: mysql -u root -p < database/schema.sql
-- Business values: minimum balance/initial deposit Rs. 500,
-- account numbers start at 1001.
-- ============================================================================

CREATE DATABASE IF NOT EXISTS bank_db CHARACTER SET utf8mb4;
USE bank_db;

-- ---------------------------------------------------------------------------
-- ACCOUNTS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
  account_number INT AUTO_INCREMENT PRIMARY KEY,
  name           VARCHAR(100) NOT NULL,
  address        VARCHAR(200) NOT NULL,
  contact        VARCHAR(15) NOT NULL,
  type           ENUM('Savings','Current') NOT NULL DEFAULT 'Savings',
  balance        DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  status         ENUM('active','closed') NOT NULL DEFAULT 'active',
  opened_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  closed_at      TIMESTAMP NULL DEFAULT NULL
) AUTO_INCREMENT = 1001;

-- ---------------------------------------------------------------------------
-- USERS
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  username     VARCHAR(50) UNIQUE NOT NULL,
  secret_hash  VARCHAR(64) NOT NULL,
  role         ENUM('staff','customer') NOT NULL,
  failed_tries INT NOT NULL DEFAULT 0,
  created_at   TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- TRANSACTIONS
-- Positive amounts only; each transaction must belong to an existing account.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  account_number  INT NOT NULL,
  type            ENUM('DEPOSIT','WITHDRAWAL','TRANSFER_IN','TRANSFER_OUT') NOT NULL,
  amount          DECIMAL(12,2) NOT NULL CHECK (amount > 0),
  balance_after   DECIMAL(12,2) NOT NULL,
  related_account INT NULL,
  created_at      TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

  INDEX idx_tx_acc (account_number, created_at),

  CONSTRAINT fk_tx_acc
    FOREIGN KEY (account_number)
    REFERENCES accounts (account_number)
);

-- ---------------------------------------------------------------------------
-- TABLE OWNERSHIP
-- Candidate 1: accounts
-- Candidate 2: deposits, withdrawals and transaction records
-- Candidate 3: transfers, transaction history and statements
-- Candidate 4: users and authentication
-- ---------------------------------------------------------------------------
```