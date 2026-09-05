-- ============================================================================
-- Bank Management System - seed data for local testing
-- Import:  mysql -u root -p < database/seed.sql
-- NOTE: secrets below are PLACEHOLDERS. Candidate 4 replaces them with real
--       hashes when FR-18/19/20 are implemented (users.secret_hash).
-- ============================================================================
USE bank_db;

-- Staff account (Candidate 4 scope)
INSERT INTO users (username, secret_hash, role)
VALUES ('admin', 'REPLACE_WITH_HASH(admin123)', 'staff')
ON DUPLICATE KEY UPDATE username = username;

-- Two starter accounts (Candidate 1 creates more via FR-01)
INSERT INTO accounts (name, address, contact, type, balance) VALUES
  ('Rahul Sharma', '12 MG Road',    '9876543210', 'Savings', 5000.00),
  ('Priya Patel',  '34 Station Rd', '9123456780', 'Current', 3000.00);

-- Customer auth rows (Candidate 4 scope; PIN placeholder '1234' for both)
INSERT INTO users (username, secret_hash, role) VALUES
  ('1001', 'REPLACE_WITH_HASH(1234)', 'customer'),
  ('1002', 'REPLACE_WITH_HASH(1234)', 'customer');
