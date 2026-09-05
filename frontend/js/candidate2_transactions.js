/* ==========================================================================
   CANDIDATE 2 - Transactions UI
   Backend endpoints: POST /api/accounts/{id}/deposit,
                      POST /api/accounts/{id}/withdraw,
                      GET  /api/accounts/{id}/balance  (you implement these)
   Contract: tests/integration/test_candidate2_transactions.py
   ========================================================================== */

document.getElementById("panel-c2").innerHTML = `
  <div class="card">
    <h3>Check Balance (FR-12)</h3>
    <form id="balance-form">
      <input type="number" id="balance-account-number" placeholder="Account Number" required>
      <button type="submit">Check Balance</button>
    </form>
    <div id="balance-result"></div>
  </div>
`;

document.getElementById("balance-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const accNum = document.getElementById("balance-account-number").value;
  const resultDiv = document.getElementById("balance-result");
  
  const r = await api("GET", \`/api/accounts/\${accNum}/balance\`);
  showResult(resultDiv, r, "Balance fetched");
});
