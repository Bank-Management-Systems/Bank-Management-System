/* ==========================================================================
   CANDIDATE 4 - Security UI
   Backend endpoints: POST /api/auth/staff/login,
                      POST /api/auth/customer/login,
                      POST /api/auth/customer/{id}/pin-change (you implement these)
   Contract: tests/integration/test_candidate4_security.py
   ========================================================================== */

document.getElementById("panel-c4").innerHTML =
  '<p class="muted">Owned by Candidate 4. Replace this panel with the ' +
  'login status / PIN change screens.</p>';

// The login page forms are already wired to the IDs below - implement the calls:
const staffForm = document.getElementById("staff-form");
if (staffForm) {
  staffForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    // TODO(Candidate 4): call POST /api/auth/staff/login with
    //   { username: staff-user value, password: staff-pass value }
    // and print the result into #staff-msg (show errors generically!).
    document.getElementById("staff-msg").textContent =
      "FR-18 staff login not implemented yet (Candidate 4).";
  });
}

const custForm = document.getElementById("customer-form");
if (custForm) {
  custForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    // TODO(Candidate 4): call POST /api/auth/customer/login with
    //   { account_number: Number(cust-acc value), pin: cust-pin value }
    document.getElementById("cust-msg").textContent =
      "FR-19 customer login not implemented yet (Candidate 4).";
  });
}

// TODO(Candidate 4): PIN change form -> POST /api/auth/customer/{id}/pin-change
// with { old_pin, new_pin } (see contract test file for the exact rules).
