/* ==========================================================================
   CANDIDATE 3 - Transfer / Records / Statement UI
   Backend endpoints: POST /api/transfers,
                      GET  /api/accounts/{id}/transactions,
                      GET  /api/accounts/{id}/statement  (you implement these)
   Contract: tests/integration/test_candidate3_records.py
   ========================================================================== */

document.getElementById("panel-c3").innerHTML = `
  <!-- FR-13: Atomic Transfer Form -->
  <div class="card" style="margin-bottom:1rem;">
    <h3>Transfer Funds (FR-13)</h3>
    <form id="transfer-form">
      <input type="number" id="tf-from"   placeholder="From Account" required style="margin:4px;padding:6px;width:160px;">
      <input type="number" id="tf-to"     placeholder="To Account"   required style="margin:4px;padding:6px;width:160px;">
      <input type="number" id="tf-amount" placeholder="Amount"       required min="1" step="0.01" style="margin:4px;padding:6px;width:120px;">
      <button type="submit" style="margin:4px;padding:6px 12px;">Transfer</button>
    </form>
    <div id="transfer-result"></div>
  </div>

  <!-- FR-15 and FR-17 placeholders (implemented in subsequent commits) -->
  <div class="card" style="margin-bottom:1rem;">
    <h3>Transaction History (FR-15)</h3>
    <p class="muted">Coming soon.</p>
  </div>
  <div class="card">
    <h3>Account Statement (FR-17)</h3>
    <p class="muted">Coming soon.</p>
  </div>
`;

/* ---- FR-13: Transfer form ---- */
document.getElementById("transfer-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const from   = parseInt(document.getElementById("tf-from").value, 10);
  const to     = parseInt(document.getElementById("tf-to").value, 10);
  const amount = parseFloat(document.getElementById("tf-amount").value);
  const result = document.getElementById("transfer-result");

  const r = await api("POST", "/api/transfers", { from_account: from, to_account: to, amount });
  if (r.status === 200) {
    const d = r.data;
    result.innerHTML = `<span class="msg-ok">&#x2714; Transfer successful</span>
      <p>From #${d.from_account}: &#x20B9;${d.from_balance} &nbsp;|&nbsp; To #${d.to_account}: &#x20B9;${d.to_balance}</p>`;
  } else {
    showResult(result, r, "Transfer");
  }
});
