import axios from "axios";

export const TOKEN_STORAGE_KEY = "legal_assistance_access_token";
export const REFRESH_TOKEN_STORAGE_KEY = "legal_assistance_refresh_token";

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || "",
  timeout: 65000,
  headers: {
    Accept: "application/json",
  },
});

// ─────────────────────────────────────────────
// Request interceptor — attach access token
// ─────────────────────────────────────────────

api.interceptors.request.use((config) => {
  const token = sessionStorage.getItem(
    TOKEN_STORAGE_KEY
  );

  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }

  return config;
});

// ─────────────────────────────────────────────
// Response interceptor — automatic token refresh
//
// Single-flight: if multiple requests fail with 401
// at the same time, only ONE refresh request is made.
// All waiting requests are retried after refresh.
// ─────────────────────────────────────────────

let isRefreshing = false;
let refreshSubscribers = [];

function onRefreshed(newAccessToken) {
  refreshSubscribers.forEach((callback) => callback(newAccessToken));
  refreshSubscribers = [];
}

function onRefreshFailed() {
  refreshSubscribers.forEach((callback) => callback(null));
  refreshSubscribers = [];
}

function addRefreshSubscriber(callback) {
  refreshSubscribers.push(callback);
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Only attempt refresh for 401 errors on non-auth endpoints
    if (
      error.response?.status !== 401 ||
      originalRequest._retry ||
      originalRequest.url?.includes("/api/v1/auth/login") ||
      originalRequest.url?.includes("/api/v1/auth/register") ||
      originalRequest.url?.includes("/api/v1/auth/refresh")
    ) {
      return Promise.reject(error);
    }

    const refreshToken = sessionStorage.getItem(REFRESH_TOKEN_STORAGE_KEY);
    if (!refreshToken) {
      // No refresh token — cannot refresh, let the error propagate
      return Promise.reject(error);
    }

    if (isRefreshing) {
      // Another refresh is in progress — queue this request
      return new Promise((resolve, reject) => {
        addRefreshSubscriber((newAccessToken) => {
          if (newAccessToken) {
            originalRequest.headers.Authorization = `Bearer ${newAccessToken}`;
            originalRequest._retry = true;
            resolve(api(originalRequest));
          } else {
            reject(error);
          }
        });
      });
    }

    // Start refresh
    isRefreshing = true;
    originalRequest._retry = true;

    try {
      // Use a fresh axios instance to avoid interceptor loops
      const refreshResponse = await axios.post(
        `${api.defaults.baseURL || ""}/api/v1/auth/refresh`,
        { refresh_token: refreshToken },
        { headers: { Accept: "application/json" } }
      );

      const { access_token, refresh_token: newRefreshToken } = refreshResponse.data;

      // Store new tokens
      sessionStorage.setItem(TOKEN_STORAGE_KEY, access_token);
      if (newRefreshToken) {
        sessionStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, newRefreshToken);
      }

      isRefreshing = false;
      onRefreshed(access_token);

      // Retry the original request with new token
      originalRequest.headers.Authorization = `Bearer ${access_token}`;
      return api(originalRequest);

    } catch (refreshError) {
      isRefreshing = false;
      onRefreshFailed();

      // Clear all auth state — session is truly expired
      sessionStorage.removeItem(TOKEN_STORAGE_KEY);
      sessionStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY);

      // Dispatch a custom event so AuthContext can react
      window.dispatchEvent(new CustomEvent("auth:session-expired"));

      return Promise.reject(refreshError);
    }
  }
);

// ─────────────────────────────────────────────
// Error message helper
// ─────────────────────────────────────────────

export function getApiErrorMessage(
  error,
  fallback = "Something went wrong."
) {
  const detail = error?.response?.data?.detail;

  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }

  if (Array.isArray(detail) && detail.length > 0) {
    return detail
      .map((item) => item?.msg)
      .filter(Boolean)
      .join(" ");
  }

  if (error?.code === "ECONNABORTED") {
    return "The server took too long to respond.";
  }

  if (!error?.response) {
    return "Could not connect to the backend.";
  }

  return fallback;
}

export default api;