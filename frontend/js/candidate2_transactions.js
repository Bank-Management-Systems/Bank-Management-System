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
  
  <div class="card">
    <h3>Check Balance (FR-12)</h3>
    <form id="balance-form">
      <input type="number" id="balance-account-number" placeholder="Account Number" required>
      <button type="submit">Check Balance</button>
    </form>
    <div id="balance-result"></div>
  </div>
  
  <div class="card">
    <h3>Withdraw Cash (FR-09)</h3>
    <form id="withdraw-form">
      <input type="number" id="withdraw-account-number" placeholder="Account Number" required>
      <input type="number" id="withdraw-amount" placeholder="Amount" min="1" required>
      <button type="submit">Withdraw</button>
    </form>
    <div id="withdraw-result"></div>
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

document.getElementById("balance-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const accNum = document.getElementById("balance-account-number").value;
  const resultDiv = document.getElementById("balance-result");
  
  const r = await api("GET", \`/api/accounts/\${accNum}/balance\`);
  showResult(resultDiv, r, "Balance fetched");
});

document.getElementById("withdraw-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const accNum = document.getElementById("withdraw-account-number").value;
  const amount = parseInt(document.getElementById("withdraw-amount").value, 10);
  const resultDiv = document.getElementById("withdraw-result");
  
  const r = await api("POST", \`/api/accounts/\${accNum}/withdraw\`, { amount });
  showResult(resultDiv, r, "Withdrawal successful");
});
