-- ============================================================================
-- Bank Management System - MySQL schema
-- Import:  mysql -u root -p < database/schema.sql
-- Owner comments mark which candidate owns which table. Edit ONLY your tables.
-- Business values (Test Plan V2): minimum balance/initial deposit Rs. 500,
-- account numbers start at 1001.
-- ============================================================================
CREATE DATABASE IF NOT EXISTS bank_db CHARACTER SET utf8mb4;
USE bank_db;

-- ---------------------------------------------------------------------------
-- accounts  (OWNER: CANDIDATE 1 - FR-01 create, FR-04 modify, FR-05 close)
-- Candidates 2 and 3 READ this table; only Candidate 1 changes account rows.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS accounts (
  account_number INT AUTO_INCREMENT PRIMARY KEY,
  name           VARCHAR(100)  NOT NULL,
  address        VARCHAR(200)  NOT NULL,
  contact        VARCHAR(15)   NOT NULL,
  type           ENUM('Savings','Current') NOT NULL DEFAULT 'Savings',
  balance        DECIMAL(12,2) NOT NULL DEFAULT 0.00,
  status         ENUM('active','closed')   NOT NULL DEFAULT 'active',
  opened_at      TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
  closed_at      TIMESTAMP     NULL DEFAULT NULL
) AUTO_INCREMENT = 1001;

-- ---------------------------------------------------------------------------
-- users  (OWNER: CANDIDATE 4 - FR-18 staff login, FR-19 customer auth, FR-20 PIN)
-- Store HASHES, never plain text (e.g., SHA-256 or better; seed data is
-- illustrative only and must be replaced by hashes during implementation).
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
  id            INT AUTO_INCREMENT PRIMARY KEY,
  username      VARCHAR(50)  UNIQUE NOT NULL,          -- staff username OR account number as string
  secret_hash   VARCHAR(64)  NOT NULL,                 -- hashed password / PIN
  role          ENUM('staff','customer') NOT NULL,
  failed_tries  INT          NOT NULL DEFAULT 0,
  created_at    TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ---------------------------------------------------------------------------
-- transactions  (WRITTEN by Candidate 2 for deposit/withdrawal;
--                WRITTEN by Candidate 3 for transfers; READ by Candidate 3
--                for history FR-15 and statement FR-17. Discuss schema changes
--                together before editing.)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS transactions (
  id              BIGINT AUTO_INCREMENT PRIMARY KEY,
  account_number  INT          NOT NULL,
  type            ENUM('DEPOSIT','WITHDRAWAL','TRANSFER_IN','TRANSFER_OUT') NOT NULL,
  amount          DECIMAL(12,2) NOT NULL,
  balance_after   DECIMAL(12,2) NOT NULL,
  related_account INT          NULL,          -- set for TRANSFER_IN / TRANSFER_OUT
  created_at      TIMESTAMP    NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_tx_acc (account_number, created_at),
  CONSTRAINT fk_tx_acc FOREIGN KEY (account_number)
    REFERENCES accounts (account_number)
);

-- Quick ownership check:
--   Candidate 1 -> accounts           (INSERT / UPDATE identity + status)
--   Candidate 2 -> accounts.balance   (via deposit / withdraw), transactions rows
--   Candidate 3 -> transfers (two rows), reads transactions for FR-15 / FR-17
--   Candidate 4 -> users              (authentication only)
