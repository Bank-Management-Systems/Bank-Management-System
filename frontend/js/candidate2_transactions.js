/* ==========================================================================
   CANDIDATE 2 - Transactions UI
   Backend endpoints: POST /api/accounts/{id}/deposit,
                      POST /api/accounts/{id}/withdraw,
                      GET  /api/accounts/{id}/balance  (you implement these)
   Contract: tests/integration/test_candidate2_transactions.py
   ========================================================================== */

document.getElementById("panel-c2").innerHTML =
  '<p class="muted">Owned by Candidate 2. Replace this panel with the ' +
  'deposit / withdraw / balance screens.</p>';

// TODO(Candidate 2): build the deposit, withdraw and balance forms.
// Example call once your endpoint works:
//
// async function deposit(accountNumber, amount) {
//   const r = await api("POST", `/api/accounts/${accountNumber}/deposit`, { amount });
//   showResult(document.getElementById("panel-c2"), r, "Deposit posted");
// }
//
// async function balance(accountNumber) {
//   const r = await api("GET", `/api/accounts/${accountNumber}/balance`);
//   showResult(document.getElementById("panel-c2"), r, "Balance fetched");
// }
