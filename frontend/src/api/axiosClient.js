import axios from 'axios';

// All endpoints live under /api/v1/. Override with REACT_APP_API_URL in frontend/.env
export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

// NOTE: tokens are kept in localStorage for simplicity (beginner friendly). That is readable by any
// script on the page, so keep the site free of XSS (React escapes output by default). For higher
// security use httpOnly cookies - see README "Security notes".
export const tokens = {
  access: () => localStorage.getItem('access'),
  refresh: () => localStorage.getItem('refresh'),
  set: ({ access, refresh }) => {
    if (access) localStorage.setItem('access', access);
    if (refresh) localStorage.setItem('refresh', refresh);
  },
  clear: () => { localStorage.removeItem('access'); localStorage.removeItem('refresh'); },
};

const api = axios.create({ baseURL: API_URL });

api.interceptors.request.use((config) => {
  const t = tokens.access();
  if (t) config.headers.Authorization = `Bearer ${t}`;
  return config;
});

// --- automatic refresh: when a request gets 401, refresh ONCE and replay every waiting request ---
let refreshing = null;

function refreshAccessToken() {
  if (!refreshing) {
    refreshing = axios
      .post(`${API_URL}/auth/token/refresh/`, { refresh: tokens.refresh() })
      .then((res) => { tokens.set(res.data); return res.data.access; }) // store the ROTATED refresh token too
      .finally(() => { refreshing = null; });
  }
  return refreshing;
}

api.interceptors.response.use(
  (r) => r,
  async (error) => {
    const original = error.config;
    const isAuthCall = original?.url?.includes('/auth/login/') || original?.url?.includes('/auth/token/refresh/');
    if (error.response?.status === 401 && !original._retry && !isAuthCall && tokens.refresh()) {
      original._retry = true;
      try {
        const access = await refreshAccessToken();
        original.headers.Authorization = `Bearer ${access}`;
        return api(original);
      } catch (e) {
        tokens.clear();
        window.dispatchEvent(new Event('auth:logout'));
      }
    }
    return Promise.reject(error);
  }
);

export default api;
