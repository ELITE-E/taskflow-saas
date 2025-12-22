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

// Add request interceptor to attach access token as Bearer
apiClient.interceptors.request.use((config) => {
  const token = Cookies.get('access_token');
  if (token) {
    config.headers = config.headers || {};
    config.headers['Authorization'] = `Bearer ${token}`;
  }
  return config;
});
// --- Token Refresh Helper ---
export const refreshAccessToken = async () => {
    const refreshToken = Cookies.get('refresh_token');
    if (!refreshToken) return null;

    try {
        const response = await axios.post(`${API_BASE_URL}/auth/token/refresh/`, {
            refresh: refreshToken
        });
        const { access } = response.data;
        Cookies.set('access_token', access, { expires: 1/24 }); // 1 hour
        return access;
    } catch (error) {
        // Refresh token failed (it's expired or invalid)
        console.error("Refresh token failed, forcing logout.");
        Cookies.remove('access_token');
        Cookies.remove('refresh_token');
        return null;
    }
}

// --- Axios Interceptors (The Key to Auto-Refresh) ---
let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
    failedQueue.forEach(prom => {
        if (error) {
            prom.reject(error);
        } else if (token) {
            prom.resolve(token);
        }
    });
    failedQueue = [];
};

apiClient.interceptors.response.use(
    (response) => response,
    async (error) => {
        const originalRequest = error.config;
        
        // Check for 401 AND ensure it's not the refresh endpoint itself
        if (error.response?.status === 401 && originalRequest.url !== '/auth/token/refresh/') {
            
            // 1. If currently refreshing, add to queue
            if (isRefreshing) {
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject });
                }).then(token => {
                    originalRequest.headers['Authorization'] = `Bearer ${token}`;
                    return apiClient(originalRequest);
                }).catch(err => {
                    return Promise.reject(err);
                });
            }

            // 2. Start the refresh process
            isRefreshing = true;
            const newAccessToken = await refreshAccessToken();
            isRefreshing = false;

            if (newAccessToken) {
                // Tokens updated, retry queued requests
                processQueue(null, newAccessToken);
                originalRequest.headers['Authorization'] = `Bearer ${newAccessToken}`;
                return apiClient(originalRequest);
            } else {
                // Refresh failed (refresh token expired) -> Force Logout
                processQueue(error, null); 
                // We dispatch logout outside the interceptor (e.g., in a Redux listener) 
                // to avoid state loop issues within Axios.
            }
        }
        return Promise.reject(error);
    }
);


export default apiClient;