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

  <!-- FR-17: Account Statement with date pickers and printable layout -->
  <div class="card">
    <h3>Account Statement (FR-17)</h3>
    <form id="statement-form">
      <input type="number" id="stmt-acc"  placeholder="Account Number" required style="margin:4px;padding:6px;width:160px;">
      <input type="date"   id="stmt-from" style="margin:4px;padding:6px;" title="From date (optional)">
      <input type="date"   id="stmt-to"   style="margin:4px;padding:6px;" title="To date (optional)">
      <button type="submit" style="margin:4px;padding:6px 12px;">Generate Statement</button>
    </form>
    <div id="statement-result"></div>
    <button id="print-btn" style="display:none;margin-top:8px;padding:6px 12px;" onclick="window.print()">&#x1F5A8; Print Statement</button>
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

/* ---- FR-17: Statement with from/to date pickers and printable layout ---- */
document.getElementById("statement-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const acc      = document.getElementById("stmt-acc").value;
  const from     = document.getElementById("stmt-from").value;
  const to       = document.getElementById("stmt-to").value;
  const result   = document.getElementById("statement-result");
  const printBtn = document.getElementById("print-btn");

  let path = `/api/accounts/${acc}/statement`;
  const params = [];
  if (from) params.push(`from=${encodeURIComponent(from)}`);
  if (to)   params.push(`to=${encodeURIComponent(to)}`);
  if (params.length) path += "?" + params.join("&");

  const r = await api("GET", path);
  if (r.status === 200) {
    const d = r.data;
    result.innerHTML = `
      <span class="msg-ok">&#x2714; Statement for account #${d.account_number}</span>
      <table style="margin:.5rem 0;border-collapse:collapse;font-size:.95em;">
        <tr><td style="padding:4px 12px 4px 0;"><strong>Period</strong></td>
            <td>${d.from ?? "All time"} &rarr; ${d.to ?? "today"}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;"><strong>Opening Balance</strong></td>
            <td>&#x20B9;${d.opening_balance}</td></tr>
        <tr><td style="padding:4px 12px 4px 0;"><strong>Closing Balance</strong></td>
            <td><strong>&#x20B9;${d.closing_balance}</strong></td></tr>
      </table>` +
      renderTxTable(d.transactions);
    printBtn.style.display = "inline-block";
  } else {
    showResult(result, r, "Statement");
    printBtn.style.display = "none";
  }
});
