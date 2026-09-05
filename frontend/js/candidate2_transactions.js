/* ==========================================================================
   CANDIDATE 2 - Transactions UI
   Backend endpoints: POST /api/accounts/{id}/deposit,
                      POST /api/accounts/{id}/withdraw,
                      GET  /api/accounts/{id}/balance  (you implement these)
   Contract: tests/integration/test_candidate2_transactions.py
   ========================================================================== */

document.getElementById("panel-c2").innerHTML = `
  <div class="card">
    <h3>Deposit Cash (FR-08)</h3>
    <form id="deposit-form">
      <input type="number" id="deposit-account-number" placeholder="Account Number" required>
      <input type="number" id="deposit-amount" placeholder="Amount" min="1" required>
      <button type="submit">Deposit</button>
    </form>
    <div id="deposit-result"></div>
  </div>
`;

document.getElementById("deposit-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const accNum = document.getElementById("deposit-account-number").value;
  const amount = parseInt(document.getElementById("deposit-amount").value, 10);
  const resultDiv = document.getElementById("deposit-result");
  
  const r = await api("POST", \`/api/accounts/\${accNum}/deposit\`, { amount });
  showResult(resultDiv, r, "Deposit successful");
});
