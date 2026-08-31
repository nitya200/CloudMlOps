import axios from 'axios';

export const TOKEN_KEY = 'cloudmlops.token';

/**
 * When VITE_API_BASE_URL is empty the app uses same-origin relative URLs,
 * which the Vite dev proxy (development) and nginx (Docker) forward to the
 * FastAPI service. Set it to an absolute URL when the API lives elsewhere.
 */
const baseURL = import.meta.env.VITE_API_BASE_URL || '';

const api = axios.create({
  baseURL,
  // CPU inference on a small instance can take a while for long documents,
  // so the summarization calls need a generous ceiling.
  timeout: 240000,
  headers: { 'Content-Type': 'application/json' },
});

export function getStoredToken() {
  try {
    return localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setStoredToken(token) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token);
    else localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* storage can be unavailable in private browsing modes */
  }
}

let onUnauthorized = null;

/** Registered by AuthContext so a rejected token clears the session once. */
export function setUnauthorizedHandler(handler) {
  onUnauthorized = handler;
}

api.interceptors.request.use((config) => {
  const token = getStoredToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    // Do not bounce the user out of the login screen on a bad password.
    const isAuthAttempt = error.config?.url?.includes('/api/auth/login');
    if (status === 401 && !isAuthAttempt && onUnauthorized) onUnauthorized();
    return Promise.reject(error);
  },
);

/** Turn any axios failure into a human readable sentence. */
export function readError(error, fallback = 'Something went wrong. Please try again.') {
  if (error?.response?.data) {
    const data = error.response.data;
    if (typeof data === 'string') return data;
    if (data.message) return data.message;
    if (data.detail) {
      return typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail);
    }
  }
  if (error?.code === 'ECONNABORTED') {
    return 'The request timed out. Large documents can take a few minutes to summarize.';
  }
  if (error?.message === 'Network Error') {
    return 'Cannot reach the API. Is the backend running on port 8000?';
  }
  return error?.message || fallback;
}

export default api;
