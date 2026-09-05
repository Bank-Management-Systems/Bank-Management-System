/* ==========================================================================
   app.js - shared API helpers
   Owner: SHARED - candidates CALL these helpers from their own candidate*.js
   file; do not modify this file without team agreement.
   ========================================================================== */

// The API is normally served by the C++ backend on the same origin.
// If you open index.html directly from disk, fall back to localhost:8080.
const API_BASE =
  location.protocol === "http:" || location.protocol === "https:"
    ? ""
    : "http://localhost:8080";

/**
 * Tiny fetch wrapper.
 * @returns {Promise<{status:number, data:object}>}
 */
async function api(method, path, body) {
  const opts = { method, headers: { "Content-Type": "application/json" } };
  if (body !== undefined) opts.body = JSON.stringify(body);
  const res = await fetch(API_BASE + path, opts);
  let data = {};
  try { data = await res.json(); } catch (_) { /* non-JSON body */ }
  return { status: res.status, data };
}

/** True when the endpoint exists but is not implemented yet (501). */
function isNotImplemented(response) {
  return response.status === 501;
}

/** Print a friendly status line into a panel element. */
function showResult(el, response, okLabel) {
  if (response.status >= 200 && response.status < 300) {
    el.innerHTML = `<span class="msg-ok">✔ ${okLabel}</span><pre>${escapeHtml(
      JSON.stringify(response.data, null, 2)
    )}</pre>`;
  } else {
    el.innerHTML = `<span class="msg-bad">✖ HTTP ${response.status}</span><pre>${escapeHtml(
      JSON.stringify(response.data, null, 2)
    )}</pre>`;
  }
}

function escapeHtml(s) {
  return s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

/** Health check in the footer (worked example - do not remove). */
(async function checkHealth() {
  const el = document.getElementById("api-status");
  if (!el) return;
  try {
    const r = await api("GET", "/api/health");
    el.textContent = r.status === 200 ? "API: online ✔" : `API: HTTP ${r.status}`;
  } catch (_) {
    el.textContent = "API: offline (start ./backend/bank_server)";
  }
})();
