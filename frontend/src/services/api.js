
import axios from "axios";

const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000/api"
).replace(/\/+$/, "");

const api = axios.create({
  baseURL: BASE_URL,
  headers: {
    Accept: "application/json",
  },
});

export async function fetchAllPages(url, params = {}) {
  let response = await api.get(url, { params });
  const data = response.data;
  if (Array.isArray(data)) return data;

  const rows = [...(Array.isArray(data?.results) ? data.results : [])];
  let next = data?.next;
  const seen = new Set();
  while (next && !seen.has(next)) {
    seen.add(next);
    response = await api.get(next);
    const page = response.data;
    if (!Array.isArray(page?.results)) break;
    rows.push(...page.results);
    next = page.next;
  }
  return rows;
}

// Attach access token and handle FormData requests.
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem("access_token");

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    // Let the browser set multipart Content-Type and boundary.
    if (config.data instanceof FormData) {
      delete config.headers["Content-Type"];
    }

    return config;
  },
  (error) => Promise.reject(error)
);

// Share one refresh request if multiple API calls fail together.
let refreshPromise = null;

api.interceptors.response.use(
  (response) => response,

  async (error) => {
    const originalRequest = error.config;

    if (
      error.response?.status !== 401 ||
      !originalRequest ||
      originalRequest._retry ||
      originalRequest.url?.includes("/token/")
    ) {
      return Promise.reject(error);
    }

    const refreshToken = localStorage.getItem("refresh_token");

    if (!refreshToken) {
      clearAuthentication();
      return Promise.reject(error);
    }

    originalRequest._retry = true;

    try {
      if (!refreshPromise) {
        refreshPromise = axios
          .post(`${BASE_URL}/token/refresh/`, {
            refresh: refreshToken,
          })
          .then((response) => {
            const newAccess = response.data.access;

            localStorage.setItem("access_token", newAccess);

            if (response.data.refresh) {
              localStorage.setItem(
                "refresh_token",
                response.data.refresh
              );
            }

            return newAccess;
          })
          .finally(() => {
            refreshPromise = null;
          });
      }

      const newAccessToken = await refreshPromise;

      originalRequest.headers.Authorization =
        `Bearer ${newAccessToken}`;

      return api(originalRequest);
    } catch (refreshError) {
      clearAuthentication();
      return Promise.reject(refreshError);
    }
  }
);

function clearAuthentication() {
  localStorage.removeItem("access_token");
  localStorage.removeItem("refresh_token");

  window.dispatchEvent(new Event("auth:logout"));
}

export default api;
