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

  <!-- FR-15: Transaction History -->
  <div class="card" style="margin-bottom:1rem;">
    <h3>Transaction History (FR-15)</h3>
    <form id="history-form">
      <input type="number" id="hist-acc" placeholder="Account Number" required style="margin:4px;padding:6px;width:160px;">
      <button type="submit" style="margin:4px;padding:6px 12px;">Load History</button>
    </form>
    <div id="history-result"></div>
  </div>

  <!-- FR-17 placeholder (implemented in next commit) -->
  <div class="card">
    <h3>Account Statement (FR-17)</h3>
    <p class="muted">Coming soon.</p>
  </div>
`;

/* ---- Helper: render a transactions array as an HTML table ---- */
function renderTxTable(transactions) {
  if (!transactions || transactions.length === 0)
    return '<p class="muted">No transactions found.</p>';

  const typeColor = {
    DEPOSIT:      "#2a9d4e",
    WITHDRAWAL:   "#c0392b",
    TRANSFER_IN:  "#1a6fb5",
    TRANSFER_OUT: "#e67e22",
  };

  const rows = transactions.map(tx => {
    const color = typeColor[tx.type] || "#555";
    const badge = `<span style="background:${color};color:#fff;border-radius:4px;padding:2px 7px;font-size:.8em;">${tx.type}</span>`;
    return `<tr>
      <td style="padding:5px;">${tx.id ?? ""}</td>
      <td style="padding:5px;">${badge}</td>
      <td style="padding:5px;text-align:right;">&#x20B9;${tx.amount}</td>
      <td style="padding:5px;text-align:right;">&#x20B9;${tx.balance_after}</td>
      <td style="padding:5px;">${tx.related_account ?? "&#x2014;"}</td>
      <td style="padding:5px;">${tx.created_at ?? ""}</td>
    </tr>`;
  }).join("");

  return `<table style="width:100%;border-collapse:collapse;font-size:.9em;margin-top:.5rem;">
    <thead style="background:#f4f4f4;">
      <tr>
        <th style="padding:6px;text-align:left;">ID</th>
        <th style="padding:6px;text-align:left;">Type</th>
        <th style="padding:6px;text-align:right;">Amount</th>
        <th style="padding:6px;text-align:right;">Balance After</th>
        <th style="padding:6px;">Related Acc</th>
        <th style="padding:6px;text-align:left;">Date/Time</th>
      </tr>
    </thead>
    <tbody>${rows}</tbody>
  </table>`;
}

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

/* ---- FR-15: History table ---- */
document.getElementById("history-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const acc    = document.getElementById("hist-acc").value;
  const result = document.getElementById("history-result");

  const r = await api("GET", `/api/accounts/${acc}/transactions`);
  if (r.status === 200) {
    const d = r.data;
    result.innerHTML =
      `<span class="msg-ok">&#x2714; ${d.count} transaction(s) for account #${d.account_number}</span>` +
      renderTxTable(d.transactions);
  } else {
    showResult(result, r, "History");
  }
});
