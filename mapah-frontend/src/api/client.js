/**
 * Axios instance with:
 *  - CSRF double-submit cookie header injected on state-changing requests
 *  - Transparent access-token refresh on 401 (single-retry)
 *  - auth:expired event dispatched when refresh fails (picked up by AuthContext)
 */
import axios from 'axios';

const rawApiBase = import.meta.env.VITE_API_BASE_URL || '/';
const apiBase = rawApiBase.endsWith('/') && rawApiBase !== '/'
  ? rawApiBase.slice(0, -1)
  : rawApiBase;

/** Read a cookie value by name. */
function getCookie(name) {
  const match = document.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

const client = axios.create({
  baseURL: apiBase,
  withCredentials: true, // include httpOnly cookies on every request
});

// ── Request interceptor: attach CSRF token ────────────────────────────────
const STATE_CHANGING = ['post', 'put', 'patch', 'delete'];

client.interceptors.request.use((config) => {
  if (STATE_CHANGING.includes(config.method?.toLowerCase())) {
    const csrf = getCookie('csrf_token');
    if (csrf) config.headers['X-CSRF-Token'] = csrf;
  }
  return config;
});

// ── Response interceptor: auto-refresh on 401 ────────────────────────────
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
        // Notify the app that the session is gone
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

