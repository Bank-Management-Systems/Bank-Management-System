/* ==========================================================================
   CANDIDATE 2 - Transactions UI
   Backend endpoints: POST /api/accounts/{id}/deposit,
                      POST /api/accounts/{id}/withdraw,
                      GET  /api/accounts/{id}/balance  (you implement these)
   Contract: tests/integration/test_candidate2_transactions.py
   ========================================================================== */

(function initCandidate2() {
  const panelC2 = document.getElementById("panel-c2");
  if (!panelC2) return;

  panelC2.innerHTML = `
    <div class="card" style="margin-bottom: 14px;">
      <h3>Deposit Cash (FR-08)</h3>
      <form id="deposit-form">
        <input type="number" id="deposit-account-number" placeholder="Account Number" required>
        <input type="number" id="deposit-amount" placeholder="Amount (Rs.)" min="1" step="any" required>
        <button type="submit">Deposit</button>
      </form>
      <div id="deposit-result" style="margin-top: 8px;"></div>
    </div>
    
    <div class="card" style="margin-bottom: 14px;">
      <h3>Check Balance (FR-12)</h3>
      <form id="balance-form">
        <input type="number" id="balance-account-number" placeholder="Account Number" required>
        <button type="submit">Check Balance</button>
      </form>
      <div id="balance-result" style="margin-top: 8px;"></div>
    </div>
    
    <div class="card" style="margin-bottom: 14px;">
      <h3>Withdraw Cash (FR-09, FR-10)</h3>
      <form id="withdraw-form">
        <input type="number" id="withdraw-account-number" placeholder="Account Number" required>
        <input type="number" id="withdraw-amount" placeholder="Amount (Min. Rs. 500 must remain)" min="0.01" step="any" required>
        <small class="muted" style="display:block; margin: 4px 0 8px;">
          Minimum balance rule: account must retain at least Rs. 500.00. Overdrafts are rejected with no state change.
        </small>
        <button type="submit">Withdraw</button>
      </form>
      <div id="withdraw-result" style="margin-top: 8px;"></div>
    </div>
  `;

  const depositForm = document.getElementById("deposit-form");
  if (depositForm) {
    depositForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accNum = document.getElementById("deposit-account-number").value.trim();
      const amount = parseFloat(document.getElementById("deposit-amount").value);
      const resultDiv = document.getElementById("deposit-result");
      
      const r = await api("POST", `/api/accounts/${accNum}/deposit`, { amount });
      showResult(resultDiv, r, "Deposit successful");
    });
  }

  const balanceForm = document.getElementById("balance-form");
  if (balanceForm) {
    balanceForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accNum = document.getElementById("balance-account-number").value.trim();
      const resultDiv = document.getElementById("balance-result");
      
      const r = await api("GET", `/api/accounts/${accNum}/balance`);
      showResult(resultDiv, r, "Balance fetched");
    });
  }

  const withdrawForm = document.getElementById("withdraw-form");
  if (withdrawForm) {
    withdrawForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const accNum = document.getElementById("withdraw-account-number").value.trim();
      const amount = parseFloat(document.getElementById("withdraw-amount").value);
      const resultDiv = document.getElementById("withdraw-result");
      
      const r = await api("POST", `/api/accounts/${accNum}/withdraw`, { amount });
      if (r.status === 200) {
        showResult(resultDiv, r, "Withdrawal successful");
      } else {
        const errDetail = (r.data && r.data.error) ? r.data.error : "Withdrawal rejected";
        resultDiv.innerHTML = `<span class="msg-bad">✖ ${escapeHtml(errDetail)} — Minimum Balance Rule: Accounts must maintain at least Rs. 500.00 at all times.</span><pre>${escapeHtml(
          JSON.stringify(r.data, null, 2)
        )}</pre>`;
      }
    });
  }
})();
