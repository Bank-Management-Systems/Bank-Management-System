/**
 * Candidate 4 Security Module - FR-18, FR-19, FR-20
 */

// FR-20: Prevent Cross-Site Scripting (XSS) by sanitizing input fields
function sanitizeInput(inputString) {
    if (typeof inputString !== 'string') return inputString;
    return inputString
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

// Attach Auth Header to outgoing API fetch requests
function getAuthHeaders() {
    const token = localStorage.getItem('session_token');
    return {
        'Content-Type': 'application/json',
        'Authorization': token ? `Bearer ${token}` : ''
    };
}

// Session auto-logout check
function checkAuthStatus() {
    const token = localStorage.getItem('session_token');
    if (!token) {
        console.warn("No active session found. Redirecting to login...");
        return false;
    }
    return true;
}