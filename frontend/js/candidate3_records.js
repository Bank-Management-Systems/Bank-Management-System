/* ==========================================================================
   CANDIDATE 3 - Transfer / Records / Statement UI
   Backend endpoints: POST /api/transfers,
                      GET  /api/accounts/{id}/transactions,
                      GET  /api/accounts/{id}/statement  (you implement these)
   Contract: tests/integration/test_candidate3_records.py
   ========================================================================== */

document.getElementById("panel-c3").innerHTML =
  '<p class="muted">Owned by Candidate 3. Replace this panel with the ' +
  'transfer / history / statement screens.</p>';

// TODO(Candidate 3): build the transfer form, history table and statement view.
// Example call once your endpoint works:
//
// async function transfer(fromAcc, toAcc, amount) {
//   const r = await api("POST", "/api/transfers", {
//     from_account: fromAcc, to_account: toAcc, amount,
//   });
//   showResult(document.getElementById("panel-c3"), r, "Transfer completed");
// }
//
// async function history(accountNumber) {
//   const r = await api("GET", `/api/accounts/${accountNumber}/transactions`);
//   showResult(document.getElementById("panel-c3"), r, "History loaded");
// }
