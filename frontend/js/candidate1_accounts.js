/* ==========================================================================
   CANDIDATE 1 - Account Management UI
   Backend endpoints: POST /api/accounts, PUT /api/accounts/{id},
                      POST /api/accounts/{id}/close   (you implement these)
   Contract: tests/integration/test_candidate1_account.py
   ========================================================================== */

// Placeholder panel content until you build your screens.
document.getElementById("panel-c1").innerHTML =
  '<p class="muted">Owned by Candidate 1. Replace this panel with the ' +
  'create / modify / close account screens.</p>';

// TODO(Candidate 1): build the account-creation form.
// Example call once your endpoint works:
//
// async function createAccount(form) {
//   const r = await api("POST", "/api/accounts", {
//     name: form.name.value,
//     address: form.address.value,
//     contact: form.contact.value,
//     type: form.type.value,                 // "Savings" | "Current"
//     opening_deposit: Number(form.deposit.value),
//   });
//   showResult(document.getElementById("panel-c1"), r, "Account created");
// }
