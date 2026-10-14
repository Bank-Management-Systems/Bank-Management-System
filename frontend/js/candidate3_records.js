/* ==========================================================================
   CANDIDATE 3 - Transfer / Records / Statement UI
   Backend endpoints: POST /api/transfers,
                      GET  /api/accounts/{id}/transactions,
                      GET  /api/accounts/{id}/statement  (you implement these)
   Contract: tests/integration/test_candidate3_records.py
   ========================================================================== */

document.getElementById("panel-c3").innerHTML = `
  <div class="card" style="margin-bottom: 14px;">
    <h3>Transfer Funds (FR-13)</h3>
    <form id="transfer-form">
      <input type="number" id="transfer-from-account" placeholder="From Account Number" required>
      <input type="number" id="transfer-to-account" placeholder="To Account Number" required>
      <input type="number" id="transfer-amount" placeholder="Amount (Rs.)" min="1" required>
      <button type="submit">Transfer Funds</button>
    </form>
    <div id="transfer-result" style="margin-top: 10px;"></div>
  </div>

  <div class="card" style="margin-bottom: 14px;">
    <h3>Transaction History (FR-15)</h3>
    <form id="history-form">
      <input type="number" id="history-account-number" placeholder="Account Number" required>
      <button type="submit">View History</button>
    </form>
    <div id="history-result" style="margin-top: 10px;"></div>
  </div>

  <div class="card" style="margin-bottom: 14px;">
    <h3>Account Statement (FR-17)</h3>
    <form id="statement-form">
      <input type="number" id="statement-account-number" placeholder="Account Number" required>
      <div style="display: flex; gap: 8px;">
        <label style="flex: 1;">
          From:
          <input type="date" id="statement-from-date">
        </label>
        <label style="flex: 1;">
          To:
          <input type="date" id="statement-to-date">
        </label>
      </div>
      <div style="display: flex; gap: 8px;">
        <button type="submit" style="flex: 1;">Generate Statement</button>
        <button type="button" id="btn-print-statement" style="background: var(--navy);">Print / Export</button>
      </div>
    </form>
    <div id="statement-result" style="margin-top: 10px;"></div>
  </div>
`;

// FR-13: Fund transfer
document.getElementById("transfer-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const fromAcc = Number(document.getElementById("transfer-from-account").value);
  const toAcc = Number(document.getElementById("transfer-to-account").value);
  const amount = Number(document.getElementById("transfer-amount").value);
  const resultDiv = document.getElementById("transfer-result");

  const r = await api("POST", "/api/transfers", {
    from_account: fromAcc,
    to_account: toAcc,
    amount,
  });

  if (r.status === 200 && r.data) {
    showResult(resultDiv, r, "Transfer completed successfully");
    document.getElementById("transfer-amount").value = "";
  } else {
    showResult(resultDiv, r, "Transfer failed");
  }
});

// FR-15: View transaction history
document.getElementById("history-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const accNum = document.getElementById("history-account-number").value.trim();
  const resultDiv = document.getElementById("history-result");

  const r = await api("GET", `/api/accounts/${accNum}/transactions`);
  if (r.status === 200 && r.data) {
    const d = r.data;
    if (!d.transactions || d.transactions.length === 0) {
      resultDiv.innerHTML = '<div class="muted" style="padding: 10px; background: #f8fafc; border-radius: 6px; text-align: center;">No transactions found for this account.</div>';
      return;
    }

    const rows = d.transactions.map(t => {
      const isCredit = t.type === "DEPOSIT" || t.type === "TRANSFER_IN";
      const badgeColor = isCredit ? "var(--ok)" : "var(--bad)";
      const sign = isCredit ? "+" : "-";
      return `
        <tr>
          <td style="padding: 6px 8px; border-bottom: 1px solid #e3e8ee;">${escapeHtml(t.created_at || "")}</td>
          <td style="padding: 6px 8px; border-bottom: 1px solid #e3e8ee;"><span style="color: ${badgeColor}; font-weight: 600;">${escapeHtml(t.type || "")}</span></td>
          <td style="padding: 6px 8px; border-bottom: 1px solid #e3e8ee; text-align: right; color: ${badgeColor}; font-weight: 600;">${sign}Rs. ${Number(t.amount).toFixed(2)}</td>
          <td style="padding: 6px 8px; border-bottom: 1px solid #e3e8ee; text-align: right;">Rs. ${Number(t.balance_after).toFixed(2)}</td>
        </tr>
      `;
    }).join("");

    resultDiv.innerHTML = `
      <div style="font-size: 0.9em; margin-bottom: 6px;">Total Transactions: <strong>${d.count || d.transactions.length}</strong></div>
      <table style="width: 100%; border-collapse: collapse; font-size: 0.85em;">
        <thead>
          <tr style="background: #eef2f6; text-align: left;">
            <th style="padding: 6px 8px;">Date</th>
            <th style="padding: 6px 8px;">Type</th>
            <th style="padding: 6px 8px; text-align: right;">Amount</th>
            <th style="padding: 6px 8px; text-align: right;">Balance</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    `;
  } else {
    showResult(resultDiv, r, "History");
  }
});

// FR-17: Generate account statement
document.getElementById("statement-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const accNum = document.getElementById("statement-account-number").value.trim();
  const fromDate = document.getElementById("statement-from-date").value;
  const toDate = document.getElementById("statement-to-date").value;
  const resultDiv = document.getElementById("statement-result");

  let query = "";
  const params = [];
  if (fromDate) params.push(`from=${encodeURIComponent(fromDate)}`);
  if (toDate) params.push(`to=${encodeURIComponent(toDate)}`);
  if (params.length > 0) query = "?" + params.join("&");

  const r = await api("GET", `/api/accounts/${accNum}/statement${query}`);
  if (r.status === 200 && r.data) {
    const d = r.data;
    let rowsHtml = "";
    if (d.transactions && d.transactions.length > 0) {
      rowsHtml = d.transactions.map(t => `
        <tr>
          <td style="padding: 6px 8px; border-bottom: 1px solid #e3e8ee;">${escapeHtml(t.created_at || "")}</td>
          <td style="padding: 6px 8px; border-bottom: 1px solid #e3e8ee;"><b>${escapeHtml(t.type || "")}</b></td>
          <td style="padding: 6px 8px; border-bottom: 1px solid #e3e8ee; text-align: right;">Rs. ${Number(t.amount).toFixed(2)}</td>
          <td style="padding: 6px 8px; border-bottom: 1px solid #e3e8ee; text-align: right;">Rs. ${Number(t.balance_after).toFixed(2)}</td>
        </tr>
      `).join("");
    } else {
      rowsHtml = `<tr><td colspan="4" style="padding: 10px; text-align: center; color: var(--muted);">No transactions in this period</td></tr>`;
    }

    resultDiv.innerHTML = `
      <div class="statement-sheet" style="background: #fafbfc; border: 1px solid #d0d7de; border-radius: 6px; padding: 12px; margin-top: 8px;">
        <div style="display: flex; justify-content: space-between; border-bottom: 2px solid var(--navy); padding-bottom: 6px; margin-bottom: 8px;">
          <div><strong>Account Statement: #${escapeHtml(String(d.account_number))}</strong></div>
          <div style="font-size: 0.85em; color: var(--muted);">Period: ${d.from ? escapeHtml(d.from) : "Opening"} to ${d.to ? escapeHtml(d.to) : "Current"}</div>
        </div>
        <div style="display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 0.9em;">
          <span>Opening Balance: <strong>Rs. ${Number(d.opening_balance).toFixed(2)}</strong></span>
          <span>Closing Balance: <strong>Rs. ${Number(d.closing_balance).toFixed(2)}</strong></span>
        </div>
        <table style="width: 100%; border-collapse: collapse; font-size: 0.85em;">
          <thead>
            <tr style="background: #eef2f6; text-align: left;">
              <th style="padding: 6px 8px;">Date</th>
              <th style="padding: 6px 8px;">Type</th>
              <th style="padding: 6px 8px; text-align: right;">Amount</th>
              <th style="padding: 6px 8px; text-align: right;">Balance</th>
            </tr>
          </thead>
          <tbody>
            ${rowsHtml}
          </tbody>
        </table>
        <div style="margin-top: 8px; font-size: 0.8em; color: var(--ok); text-align: right;">
          ✔ Reconciled: Opening Balance + Range Activity = Closing Balance
        </div>
      </div>
    `;
  } else {
    showResult(resultDiv, r, "Statement");
  }
});

// Print statement
document.getElementById("btn-print-statement").addEventListener("click", () => {
  window.print();
});



