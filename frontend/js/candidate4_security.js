/**
 * Candidate 4 Security Module - Enterprise Authentication & Staff Management
 * FR-18 Staff login | FR-19 Customer authentication | FR-20 PIN change
 * Admin Staff Provisioning: POST /api/staff, GET /api/staff
 */

// Global Quick-Fill Helpers
window.fillStaffCredentials = function(username, password) {
  const userEl = document.getElementById("main-staff-user");
  const passEl = document.getElementById("main-staff-pass");
  if (userEl) userEl.value = username;
  if (passEl) passEl.value = password;
};

window.fillCustomerCredentials = function(account, pin) {
  const accEl = document.getElementById("main-cust-acc");
  const pinEl = document.getElementById("main-cust-pin");
  if (accEl) accEl.value = account;
  if (pinEl) pinEl.value = pin;
};

// Input sanitization (FR-20 helper)
function sanitizeInput(inputString) {
  if (typeof inputString !== 'string') return inputString;
  return inputString
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function getAuthHeaders() {
  const token = localStorage.getItem('session_token');
  return {
    'Content-Type': 'application/json',
    'Authorization': token ? `Bearer ${token}` : ''
  };
}

function checkAuthStatus() {
  return Boolean(localStorage.getItem('session_token'));
}

window.logoutUser = function() {
  localStorage.removeItem('session_token');
  localStorage.removeItem('user_role');
  localStorage.removeItem('user_name');
  localStorage.removeItem('is_admin');
  localStorage.removeItem('customer_account');
  updatePortalViewState();
};

// Switch active tabs inside the dashboard
window.switchTab = function(tabId) {
  document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active'));
  document.querySelectorAll('.tab-btn').forEach(el => {
    el.classList.remove('active');
    el.classList.remove('active-admin');
  });

  const targetTab = document.getElementById(tabId);
  if (targetTab) targetTab.classList.add('active');

  const activeBtn = document.getElementById(`btn-tab-${tabId}`);
  if (activeBtn) {
    activeBtn.classList.add(tabId === 'tab-staff-mgmt' ? 'active-admin' : 'active');
  }
};

// Load staff roster (Admin only)
async function loadStaffDirectory() {
  const tbody = document.getElementById('staff-roster-tbody');
  if (!tbody) return;

  try {
    const r = await api('GET', '/api/staff');
    if (r.status === 200 && Array.isArray(r.data)) {
      if (r.data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="muted" style="text-align: center;">No staff accounts found.</td></tr>';
        return;
      }
      tbody.innerHTML = r.data.map(staff => {
        const isAdmin = staff.is_admin || staff.username === 'admin';
        const roleBadge = isAdmin
          ? '<span class="badge badge-admin">👑 Admin</span>'
          : '<span class="badge badge-staff">👔 Staff</span>';
        return `
          <tr>
            <td><code>#${staff.id}</code></td>
            <td><strong>${escapeHtml(staff.username)}</strong></td>
            <td>${roleBadge}</td>
            <td class="muted">${escapeHtml(staff.created_at || 'Recently')}</td>
          </tr>
        `;
      }).join('');
    } else {
      tbody.innerHTML = '<tr><td colspan="4" class="msg-bad" style="text-align: center;">Failed to load staff list.</td></tr>';
    }
  } catch (err) {
    tbody.innerHTML = '<tr><td colspan="4" class="msg-bad" style="text-align: center;">Error connecting to staff API.</td></tr>';
  }
}

// Update UI based on active session
function updatePortalViewState() {
  const authView = document.getElementById('auth-view');
  const portalView = document.getElementById('portal-view');
  const chipContainer = document.getElementById('session-chip-container');
  const roleTabsNav = document.getElementById('role-tabs-nav');
  const bannerTitle = document.getElementById('banner-role-title');
  const bannerDesc = document.getElementById('banner-role-desc');
  const bannerBadge = document.getElementById('banner-badge-container');

  const token = localStorage.getItem('session_token');
  const role = localStorage.getItem('user_role');
  const userName = localStorage.getItem('user_name') || 'User';
  const isAdmin = localStorage.getItem('is_admin') === 'true' || userName === 'admin';
  const custAcc = localStorage.getItem('customer_account') || '';

  // If NOT logged in -> show login screen
  if (!token || !role) {
    if (authView) authView.style.display = 'block';
    if (portalView) portalView.style.display = 'none';
    if (chipContainer) {
      chipContainer.innerHTML = '<span class="user-badge"><span style="color:#94a3b8;">🔒 Not Authenticated</span></span>';
    }
    return;
  }

  // If logged in -> show dashboard
  if (authView) authView.style.display = 'none';
  if (portalView) portalView.style.display = 'block';

  // Render Top Header Chip
  if (chipContainer) {
    if (role === 'staff') {
      if (isAdmin) {
        chipContainer.innerHTML = `
          <span class="user-badge admin">👑 Admin (${escapeHtml(userName)})</span>
          <button type="button" class="btn-signout" onclick="logoutUser()">Sign Out</button>
        `;
      } else {
        chipContainer.innerHTML = `
          <span class="user-badge staff">👔 Staff (${escapeHtml(userName)})</span>
          <button type="button" class="btn-signout" onclick="logoutUser()">Sign Out</button>
        `;
      }
    } else {
      chipContainer.innerHTML = `
        <span class="user-badge customer">👤 Customer (Acc #${escapeHtml(custAcc)})</span>
        <button type="button" class="btn-signout" onclick="logoutUser()">Sign Out</button>
      `;
    }
  }

  // Render Greeting Banner
  if (bannerTitle && bannerDesc && bannerBadge) {
    if (role === 'staff' && isAdmin) {
      bannerTitle.textContent = `Welcome, Administrator (${userName})`;
      bannerDesc.textContent = "Full administrative access: Staff member provisioning, account management, counter operations, and audit records.";
      bannerBadge.innerHTML = '<span class="badge badge-admin" style="font-size: 0.9rem; padding: 6px 14px;">ADMIN ACCESS</span>';
    } else if (role === 'staff') {
      bannerTitle.textContent = `Welcome, Bank Officer (${userName})`;
      bannerDesc.textContent = "Branch counter terminal: Authorized for customer account creation, deposits, withdrawals, and account statements.";
      bannerBadge.innerHTML = '<span class="badge badge-staff" style="font-size: 0.9rem; padding: 6px 14px;">STAFF TERMINAL</span>';
    } else {
      bannerTitle.textContent = `Customer Self-Service (Account #${custAcc})`;
      bannerDesc.textContent = "Manage your bank account: View balance, transfer funds securely, download statements, and update your security PIN.";
      bannerBadge.innerHTML = '<span class="badge" style="background:#dbeafe; color:#1e40af; font-size: 0.9rem; padding: 6px 14px;">CUSTOMER PORTAL</span>';
    }
  }

  // Render Role-Tailored Navigation Tabs
  if (roleTabsNav) {
    if (role === 'staff' && isAdmin) {
      // ADMIN: Has Staff Management + All Candidate Modules
      roleTabsNav.innerHTML = `
        <button type="button" class="tab-btn active-admin" id="btn-tab-tab-staff-mgmt" onclick="switchTab('tab-staff-mgmt')">
          👥 Staff Management
        </button>
        <button type="button" class="tab-btn" id="btn-tab-tab-accounts" onclick="switchTab('tab-accounts')">
          🏛️ Account Management
        </button>
        <button type="button" class="tab-btn" id="btn-tab-tab-transactions" onclick="switchTab('tab-transactions')">
          💳 Cash Counter
        </button>
        <button type="button" class="tab-btn" id="btn-tab-tab-records" onclick="switchTab('tab-records')">
          📊 Transfers & Statements
        </button>
        <button type="button" class="tab-btn" id="btn-tab-tab-security" onclick="switchTab('tab-security')">
          🔒 PIN & Security
        </button>
      `;
      switchTab('tab-staff-mgmt');
      loadStaffDirectory();
    } else if (role === 'staff') {
      // REGULAR STAFF: Has Counter Tabs, NO Staff Management!
      roleTabsNav.innerHTML = `
        <button type="button" class="tab-btn active" id="btn-tab-tab-accounts" onclick="switchTab('tab-accounts')">
          🏛️ Account Management
        </button>
        <button type="button" class="tab-btn" id="btn-tab-tab-transactions" onclick="switchTab('tab-transactions')">
          💳 Cash Counter
        </button>
        <button type="button" class="tab-btn" id="btn-tab-tab-records" onclick="switchTab('tab-records')">
          📊 Transfers & Statements
        </button>
        <button type="button" class="tab-btn" id="btn-tab-tab-security" onclick="switchTab('tab-security')">
          🔒 PIN Service
        </button>
      `;
      switchTab('tab-accounts');
    } else {
      // CUSTOMER: Self-service tabs only
      roleTabsNav.innerHTML = `
        <button type="button" class="tab-btn active" id="btn-tab-tab-transactions" onclick="switchTab('tab-transactions')">
          💳 Check Balance
        </button>
        <button type="button" class="tab-btn" id="btn-tab-tab-records" onclick="switchTab('tab-records')">
          📊 Transfer & Statements
        </button>
        <button type="button" class="tab-btn" id="btn-tab-tab-security" onclick="switchTab('tab-security')">
          🔒 Change My PIN
        </button>
      `;
      switchTab('tab-transactions');
    }
  }

  // Pre-populate customer account numbers into forms if customer logged in
  if (role === 'customer' && custAcc) {
    const balAcc = document.getElementById('balance-account-number');
    const pinAcc = document.getElementById('pin-account-number');
    const histAcc = document.getElementById('history-account-number');
    const stmtAcc = document.getElementById('statement-account-number');
    const fromAcc = document.getElementById('transfer-from');
    if (balAcc) balAcc.value = custAcc;
    if (pinAcc) pinAcc.value = custAcc;
    if (histAcc) histAcc.value = custAcc;
    if (stmtAcc) stmtAcc.value = custAcc;
    if (fromAcc) fromAcc.value = custAcc;
  }
}

// Render security panel inside Candidate 4 card
function renderCandidate4Panel() {
  const panelC4 = document.getElementById('panel-c4');
  if (!panelC4) return;

  const custAcc = localStorage.getItem('customer_account') || '';

  panelC4.innerHTML = `
    <div class="card" style="margin-bottom: 14px;">
      <h3>Customer Security PIN Change (FR-20)</h3>
      <p class="muted" style="margin-bottom: 12px;">Update your 4 to 6 digit security PIN. Changes take effect immediately.</p>
      <form id="pin-change-form">
        <label>
          Account Number
          <input type="number" id="pin-account-number" placeholder="Account Number" value="${escapeHtml(custAcc)}" required>
        </label>
        <label>
          Current PIN
          <input type="password" id="pin-old" placeholder="Current PIN" maxlength="6" required>
        </label>
        <label>
          New PIN (4-6 digits)
          <input type="password" id="pin-new" placeholder="New PIN" minlength="4" maxlength="6" required>
        </label>
        <button type="submit">Update Security PIN</button>
      </form>
      <div id="pin-change-result" style="margin-top: 10px;"></div>
    </div>
  `;

  const pinForm = document.getElementById('pin-change-form');
  if (pinForm) {
    pinForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const accNum = document.getElementById('pin-account-number').value.trim();
      const old_pin = document.getElementById('pin-old').value.trim();
      const new_pin = document.getElementById('pin-new').value.trim();
      const resultDiv = document.getElementById('pin-change-result');

      const r = await api('POST', `/api/auth/customer/${accNum}/pin-change`, { old_pin, new_pin });
      showResult(resultDiv, r, 'PIN updated successfully');
      if (r.status === 200) {
        document.getElementById('pin-old').value = '';
        document.getElementById('pin-new').value = '';
      }
    });
  }
}

// Initialize Auth Event Handlers
function setupAuthEventHandlers() {
  // Auth view tab switcher
  const btnStaffTab = document.getElementById('btn-auth-tab-staff');
  const btnCustTab = document.getElementById('btn-auth-tab-cust');
  const staffPanel = document.getElementById('auth-form-staff-panel');
  const custPanel = document.getElementById('auth-form-cust-panel');

  if (btnStaffTab && btnCustTab && staffPanel && custPanel) {
    btnStaffTab.addEventListener('click', () => {
      btnStaffTab.classList.add('active');
      btnCustTab.classList.remove('active');
      staffPanel.style.display = 'block';
      custPanel.style.display = 'none';
    });

    btnCustTab.addEventListener('click', () => {
      btnCustTab.classList.add('active');
      btnStaffTab.classList.remove('active');
      staffPanel.style.display = 'none';
      custPanel.style.display = 'block';
    });
  }

  // Main Staff Login Form
  const staffForm = document.getElementById('main-staff-form');
  if (staffForm) {
    staffForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = sanitizeInput(document.getElementById('main-staff-user').value.trim());
      const password = document.getElementById('main-staff-pass').value;
      const msgEl = document.getElementById('main-staff-msg');

      msgEl.innerHTML = '<span class="muted">Authenticating credentials…</span>';
      const r = await api('POST', '/api/auth/staff/login', { username, password });
      if (r.status === 200) {
        localStorage.setItem('session_token', r.data.token || `staff_${username}`);
        localStorage.setItem('user_role', 'staff');
        localStorage.setItem('user_name', username);
        localStorage.setItem('is_admin', (r.data.is_admin || username === 'admin') ? 'true' : 'false');
        msgEl.innerHTML = `<span class="msg-ok">✔ Authentication successful. Entering terminal…</span>`;
        setTimeout(() => updatePortalViewState(), 400);
      } else {
        msgEl.innerHTML = `<span class="msg-bad">✖ ${escapeHtml(r.data.error || 'Invalid credentials')}</span>`;
      }
    });
  }

  // Main Customer Login Form
  const custForm = document.getElementById('main-cust-form');
  if (custForm) {
    custForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const account_number = Number(document.getElementById('main-cust-acc').value.trim());
      const pin = document.getElementById('main-cust-pin').value.trim();
      const msgEl = document.getElementById('main-cust-msg');

      msgEl.innerHTML = '<span class="muted">Verifying PIN…</span>';
      const r = await api('POST', '/api/auth/customer/login', { account_number, pin });
      if (r.status === 200) {
        localStorage.setItem('session_token', r.data.token || `cust_${account_number}`);
        localStorage.setItem('user_role', 'customer');
        localStorage.setItem('customer_account', String(account_number));
        localStorage.setItem('is_admin', 'false');
        msgEl.innerHTML = `<span class="msg-ok">✔ PIN verified. Entering account portal…</span>`;
        setTimeout(() => updatePortalViewState(), 400);
      } else {
        msgEl.innerHTML = `<span class="msg-bad">✖ ${escapeHtml(r.data.error || 'Invalid account number or PIN')}</span>`;
      }
    });
  }

  // Admin Create Staff Form
  const createStaffForm = document.getElementById('admin-create-staff-form');
  if (createStaffForm) {
    createStaffForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = sanitizeInput(document.getElementById('new-staff-user').value.trim());
      const password = document.getElementById('new-staff-pass').value;
      const msgEl = document.getElementById('admin-create-staff-msg');

      msgEl.innerHTML = '<span class="muted">Provisioning staff account…</span>';
      const r = await api('POST', '/api/staff', { username, password });
      if (r.status === 201 || r.status === 200) {
        msgEl.innerHTML = `<span class="msg-ok">✔ Staff account <strong>${escapeHtml(username)}</strong> created successfully! They can now log in.</span>`;
        document.getElementById('new-staff-user').value = '';
        document.getElementById('new-staff-pass').value = '';
        loadStaffDirectory();
      } else {
        msgEl.innerHTML = `<span class="msg-bad">✖ ${escapeHtml(r.data.error || 'Failed to create staff account')}</span>`;
      }
    });
  }

  // Refresh staff roster button
  const btnRefresh = document.getElementById('btn-refresh-staff');
  if (btnRefresh) {
    btnRefresh.addEventListener('click', loadStaffDirectory);
  }

  // Also wire legacy login.html forms if visited directly
  const loginStaffForm = document.getElementById('staff-form');
  if (loginStaffForm) {
    loginStaffForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const username = sanitizeInput(document.getElementById('staff-user').value.trim());
      const password = document.getElementById('staff-pass').value;
      const msgEl = document.getElementById('staff-msg');

      msgEl.innerHTML = '<span class="muted">Authenticating...</span>';
      const r = await api('POST', '/api/auth/staff/login', { username, password });
      if (r.status === 200) {
        localStorage.setItem('session_token', r.data.token || `staff_${username}`);
        localStorage.setItem('user_role', 'staff');
        localStorage.setItem('user_name', username);
        localStorage.setItem('is_admin', (r.data.is_admin || username === 'admin') ? 'true' : 'false');
        msgEl.innerHTML = `<span class="msg-ok">✔ Signed in as ${escapeHtml(username)}. Redirecting...</span>`;
        setTimeout(() => { window.location.href = 'index.html'; }, 600);
      } else {
        msgEl.innerHTML = `<span class="msg-bad">✖ ${escapeHtml(r.data.error || 'Invalid credentials')}</span>`;
      }
    });
  }

  const loginCustForm = document.getElementById('customer-form');
  if (loginCustForm) {
    loginCustForm.addEventListener('submit', async (e) => {
      e.preventDefault();
      const account_number = Number(document.getElementById('cust-acc').value.trim());
      const pin = document.getElementById('cust-pin').value.trim();
      const msgEl = document.getElementById('cust-msg');

      msgEl.innerHTML = '<span class="muted">Authenticating...</span>';
      const r = await api('POST', '/api/auth/customer/login', { account_number, pin });
      if (r.status === 200) {
        localStorage.setItem('session_token', r.data.token || `cust_${account_number}`);
        localStorage.setItem('user_role', 'customer');
        localStorage.setItem('customer_account', String(account_number));
        localStorage.setItem('is_admin', 'false');
        msgEl.innerHTML = `<span class="msg-ok">✔ Signed in as Account #${account_number}. Redirecting...</span>`;
        setTimeout(() => { window.location.href = 'index.html'; }, 600);
      } else {
        msgEl.innerHTML = `<span class="msg-bad">✖ ${escapeHtml(r.data.error || 'Invalid credentials')}</span>`;
      }
    });
  }
}

// Run initialization
document.addEventListener('DOMContentLoaded', () => {
  renderCandidate4Panel();
  setupAuthEventHandlers();
  updatePortalViewState();
});

// Immediate execution fallback
renderCandidate4Panel();
setupAuthEventHandlers();
updatePortalViewState();