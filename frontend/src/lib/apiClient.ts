// /src/lib/auth-api.ts (MODIFIED/EXTENDED)

import axios from 'axios';
import Cookies from 'js-cookie';

// --- Base Setup ---
const API_BASE_URL = 'http://localhost:8000/api/v1'; // Change to the base API URL (e.g., /api/v1)

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: { 'Content-Type': 'application/json' },
  withCredentials: true,
});

// Helper to resolve a possibly-relative url to a pathname
const getPathname = (url?: string) => {
  try {
    return new URL(url || '', API_BASE_URL).pathname;
  } catch {
    return String(url || '');
  }
};

// Request interceptor: inject Authorization header from cookies only.
// Never read tokens from Redux / localStorage.
apiClient.interceptors.request.use((config) => {
  const token = Cookies.get('access_token');
  if (token) {
    config.headers = config.headers || {};
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});

// Refresh helper: POST to refresh endpoint, return new access token or null.
// Does not dispatch redux actions; caller decides what to do on null.
export const refreshAccessToken = async (): Promise<string | null> => {
  const refreshToken = Cookies.get('refresh_token');
  if (!refreshToken) return null;

  try {
    const resp = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, { refresh: refreshToken }, {
      headers: { 'Content-Type': 'application/json' },
      withCredentials: true,
    });
    const access = resp.data?.access;
    if (access) {
      // store the new access token in cookie (HTTP-only cookies are preferred in prod)
      Cookies.set('access_token', access, { expires: 1 / 24 }); // short expiry
      return access;
    }
    return null;
  } catch (err) {
    // On refresh failure clear tokens and return null.
    Cookies.remove('access_token');
    Cookies.remove('refresh_token');
    return null;
  }
};

// Response interceptor: attempt single refresh on 401 ONLY.
// Queue concurrent 401-failures while refresh is in progress.
// NEVER attempt refresh on 403 / 405 / 500 / network errors.
let isRefreshing = false;
let failedQueue: Array<{ resolve: (t: string) => void; reject: (e: any) => void }> = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach((p) => {
    if (error) p.reject(error);
    else p.resolve(token as string);
  });
  failedQueue = [];
};

apiClient.interceptors.response.use(
  (res) => res,
  async (err) => {
    const originalRequest = err.config;

    // If there's no response or no config, just forward the error
    if (!err.response || !originalRequest) return Promise.reject(err);

    const status = err.response.status;
    // Only attempt refresh for 401 status (unauthenticated). All other codes are not retriable here.
    if (status !== 401) {
      return Promise.reject(err);
    }

    // Avoid trying to refresh if this request is the refresh endpoint itself.
    const reqPath = getPathname(originalRequest.url);
    if (reqPath.endsWith('/auth/token/refresh/')) {
      return Promise.reject(err);
    }

    // Prevent infinite retry loops
    if (originalRequest._retry) {
      return Promise.reject(err);
    }
    originalRequest._retry = true;

    if (isRefreshing) {
      // Queue this request until refresh completes
      return new Promise((resolve, reject) => {
        failedQueue.push({
          resolve: (token: string) => {
            originalRequest.headers = originalRequest.headers || {};
            originalRequest.headers['Authorization'] = `Bearer ${token}`;
            resolve(apiClient(originalRequest));
          },
          reject: (e) => reject(e),
        });
      });
    }

    isRefreshing = true;
    try {
      const newToken = await refreshAccessToken();
      isRefreshing = false;

      if (newToken) {
        processQueue(null, newToken);
        originalRequest.headers = originalRequest.headers || {};
        originalRequest.headers['Authorization'] = `Bearer ${newToken}`;
        return apiClient(originalRequest);
      } else {
        // Refresh failed: reject queued requests and propagate original 401 up
        processQueue(err, null);
        return Promise.reject(err);
      }
    } catch (refreshErr) {
      isRefreshing = false;
      processQueue(refreshErr, null);
      return Promise.reject(refreshErr);
    }
  }
);


export default apiClient;