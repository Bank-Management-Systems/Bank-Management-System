/* ==========================================================================
   CANDIDATE 1 - Account Management UI
   Backend endpoints: POST /api/accounts, PUT /api/accounts/{id},
                      POST /api/accounts/{id}/close   (you implement these)
   Contract: tests/integration/test_candidate1_account.py
   ========================================================================== */

document.getElementById("panel-c1").innerHTML = `
  <div class="card" style="margin-bottom: 12px;">
    <h3>Close Account (FR-05)</h3>
    <form id="close-account-form">
      <input type="number" id="close-account-number" placeholder="Account Number" required>
      <button type="submit" style="background: var(--bad);">Close Account</button>
    </form>
    <div id="close-result" style="margin-top: 8px;"></div>
  </div>
`;

document.getElementById("close-account-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const accNum = document.getElementById("close-account-number").value.trim();
  if (!accNum) return;

  const confirmed = confirm(`Are you sure you want to permanently close account #${accNum}? Closure is permitted only when balance is Rs. 0.`);
  if (!confirmed) {
    return;
  }

  const resultDiv = document.getElementById("close-result");
  const r = await api("POST", `/api/accounts/${accNum}/close`);
  showResult(resultDiv, r, "Account closed successfully");
});

