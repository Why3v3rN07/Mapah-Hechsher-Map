/**
 * Axios instance with:
 *  - CSRF token header injected on state-changing requests
 *    (reads from localStorage first, then cookie — supports cross-origin Render deploy
 *     where third-party cookies are blocked by browsers)
 *  - Transparent access-token refresh on 401 (single-retry)
 *  - auth:expired event dispatched when refresh fails (picked up by AuthContext)
 */
import axios from 'axios';

const rawApiBase = import.meta.env.VITE_API_BASE_URL || '/';
const apiBase = rawApiBase.endsWith('/') && rawApiBase !== '/'
  ? rawApiBase.slice(0, -1)
  : rawApiBase;

// ── CSRF token storage ────────────────────────────────────────────────────────
const CSRF_STORAGE_KEY = 'mapah_csrf_token';

/** Called by auth.js whenever a response body contains a fresh csrf_token. */
export function storeCsrfToken(token) {
  if (token) localStorage.setItem(CSRF_STORAGE_KEY, token);
}

/** Read a cookie by name (works on same-origin / local dev). */
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

/**
 * Best-effort CSRF token:
 *   1. localStorage  — set by getCsrfToken/login/register/refresh responses (cross-origin safe)
 *   2. cookie        — fallback for local dev where same-origin cookie works
 */
function readCsrfToken() {
  return localStorage.getItem(CSRF_STORAGE_KEY) || getCookie('csrf_token');
}

// ── Axios instance ────────────────────────────────────────────────────────────
const client = axios.create({
  baseURL: apiBase,
  withCredentials: true,
});

// ── Request interceptor: attach CSRF token ────────────────────────────────────
const STATE_CHANGING = ['post', 'put', 'patch', 'delete'];

client.interceptors.request.use((config) => {
  if (STATE_CHANGING.includes(config.method?.toLowerCase())) {
    const csrf = readCsrfToken();
    if (csrf) config.headers['X-CSRF-Token'] = csrf;
  }
  return config;
});

// ── Response interceptor: auto-refresh on 401 ────────────────────────────────
let _refreshing = false;
let _waitQueue = [];

function processQueue(error) {
  _waitQueue.forEach((cb) => (error ? cb.reject(error) : cb.resolve()));
  _waitQueue = [];
}

client.interceptors.response.use(
  (res) => res,
  async (error) => {
    const orig = error.config;

    if (
      error.response?.status === 401 &&
      !orig._retry &&
      !orig.url?.includes('/auth/refresh') &&
      !orig.url?.includes('/auth/login')
    ) {
      if (_refreshing) {
        return new Promise((resolve, reject) => {
          _waitQueue.push({ resolve, reject });
        })
          .then(() => client(orig))
          .catch((e) => Promise.reject(e));
      }

      orig._retry = true;
      _refreshing = true;

      try {
        await client.post('/auth/refresh');
        processQueue(null);
        return client(orig);
      } catch (refreshErr) {
        processQueue(refreshErr);
        window.dispatchEvent(new CustomEvent('auth:expired'));
        return Promise.reject(refreshErr);
      } finally {
        _refreshing = false;
      }
    }

    return Promise.reject(error);
  },
);

export default client;
