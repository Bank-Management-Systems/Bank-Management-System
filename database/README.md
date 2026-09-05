# Database (MySQL 8)

## Import

```bash
mysql -u root -p < database/schema.sql   # creates bank_db + tables
mysql -u root -p < database/seed.sql     # sample rows for local testing
```

The backend reads connection settings from environment variables:

| Variable | Default | Meaning |
|---|---|---|
| `DB_HOST` | 127.0.0.1 | MySQL host |
| `DB_PORT` | 3306 | MySQL port |
| `DB_USER` | root | user name |
| `DB_PASS` | root | password |
| `DB_NAME` | bank_db | database name |

## Table ownership (who may change what)

| Table | Owner | Notes |
|---|---|---|
| `accounts` | **Candidate 1** | create (FR-01), modify details (FR-04), close (FR-05) |
| `accounts.balance` | **Candidate 2** | updated only through deposit / withdraw (FR-08/09) |
| `transactions` | **Candidate 2 + 3** | C2 writes deposit/withdrawal rows; C3 writes transfer rows and reads for history/statement |
| `users` | **Candidate 4** | staff & customer credentials, PIN change (FR-18/19/20) |

Anyone may **SELECT** from any table; schema changes to a table you do not own
require the owner's agreement in your pull request description.
