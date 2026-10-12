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
  // Default instance header is application/json; FormData must set multipart boundary
  // automatically or uploads fail (especially on mobile Safari).
  if (typeof FormData !== 'undefined' && config.data instanceof FormData) {
    delete config.headers['Content-Type'];
  }
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
    return 'The request timed out. Try a shorter document or a shorter summary length.';
  }
  if (error?.message === 'Network Error' || error?.code === 'ERR_NETWORK') {
    const onCloud =
      baseURL.includes('awsapprunner.com') ||
      baseURL.includes('onrender.com') ||
      (typeof window !== 'undefined' &&
        /awsapprunner\.com|netlify\.app|onrender\.com/.test(window.location.hostname));
    if (onCloud) {
      return (
        'The request was interrupted (cloud hosts limit responses to about 2 minutes, or the ' +
        'connection dropped). Try Concise style, Short/Medium length, a smaller document, or Wi‑Fi instead of mobile data.'
      );
    }
    if (baseURL) {
      return 'Could not reach the API server. Check your connection and try again.';
    }
    return 'Cannot reach the API. For local dev, ensure the backend is running on port 8000.';
  }
  return error?.message || fallback;
}

export default api;
