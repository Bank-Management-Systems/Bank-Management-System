# Candidate 4 - Security (backend)

**You own this folder.** Nobody else commits here.

| Item | Value |
|---|---|
| Requirements | FR-18 Staff login, FR-19 Customer authentication, FR-20 PIN change |
| Test plan | `docs/Bank_Management_System_Test_Plan_V2.docx` - Chapter 7 (sections 7.1 - 7.3) |
| File to code | `security_module.hpp` (replace the three 501 stubs) |
| Route mounting | Already done in `backend/main.cpp` - do not edit it |
| Acceptance tests | `tests/integration/test_candidate4_security.py` |

## Endpoints you implement

| Method | Path | FR | Success | Typical failure |
|---|---|---|---|---|
| POST | `/api/auth/staff/login` | FR-18 | `200` role=staff | `401` invalid credentials |
| POST | `/api/auth/customer/login` | FR-19 | `200` role=customer | `401` invalid credentials |
| POST | `/api/auth/customer/{id}/pin-change` | FR-20 | `200` PIN changed | `401` wrong old PIN, `400` invalid new PIN |

## Security rules
- Hash passwords/PINs in the `users` table (never plain text; the seed data notes this).
- Auth failures always return the same generic `401 Invalid credentials`.
- PIN is never echoed back in any response, log or error message.
