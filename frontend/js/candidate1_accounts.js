/* ==========================================================================
   CANDIDATE 1 - Account Management UI
   Backend endpoints: POST /api/accounts, PUT /api/accounts/{id},
                      POST /api/accounts/{id}/close   (you implement these)
   Contract: tests/integration/test_candidate1_account.py
   ========================================================================== */

document.getElementById("panel-c1").innerHTML = `
  <div class="card" style="margin-bottom: 14px;">
    <h3>Modify Customer Details (FR-04)</h3>
    <form id="modify-details-form">
      <div style="display: flex; gap: 8px;">
        <input type="number" id="modify-account-number" placeholder="Account Number" style="flex: 1;" required>
        <button type="button" id="btn-fetch-details" style="white-space: nowrap;">Load Details</button>
      </div>
      <input type="text" id="modify-address" placeholder="Address" required>
      <input type="text" id="modify-contact" placeholder="Contact (e.g. 9876543210)" required>
      <button type="submit">Update Details</button>
    </form>
    <div id="modify-result" style="margin-top: 8px;"></div>
  </div>

  <div class="card" style="margin-bottom: 14px;">
    <h3>Close Account (FR-05)</h3>
    <form id="close-account-form">
      <input type="number" id="close-account-number" placeholder="Account Number" required>
      <button type="submit" style="background: var(--bad);">Close Account</button>
    </form>
    <div id="close-result" style="margin-top: 8px;"></div>
  </div>
`;

// FR-04: Load existing details to pre-fill the form
document.getElementById("btn-fetch-details").addEventListener("click", async () => {
  const accNum = document.getElementById("modify-account-number").value.trim();
  const resultDiv = document.getElementById("modify-result");
  if (!accNum) {
    resultDiv.innerHTML = '<span class="msg-bad">Please enter an account number first.</span>';
    return;
  }
  const r = await api("GET", `/api/accounts/${accNum}`);
  if (r.status === 200 && r.data) {
    document.getElementById("modify-address").value = r.data.address || "";
    document.getElementById("modify-contact").value = r.data.contact || "";
    resultDiv.innerHTML = '<span class="msg-ok">Loaded existing details for Account #' + escapeHtml(accNum) + '</span>';
  } else {
    showResult(resultDiv, r, "Account details");
  }
});

// FR-04: Submit modifications
document.getElementById("modify-details-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const accNum = document.getElementById("modify-account-number").value.trim();
  const address = document.getElementById("modify-address").value.trim();
  const contact = document.getElementById("modify-contact").value.trim();
  const resultDiv = document.getElementById("modify-result");

  const r = await api("PUT", `/api/accounts/${accNum}`, { address, contact });
  showResult(resultDiv, r, "Details updated successfully");
});

// FR-05: Close account
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


