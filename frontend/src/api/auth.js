import axios from 'axios';

const API_BASE = '/api';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

let isRefreshing = false;
let refreshQueue = [];

function resolveRefreshQueue(error, token = null) {
  refreshQueue.forEach(({ resolve, reject }) => {
    if (error) {
      reject(error);
    } else {
      resolve(token);
    }
  });
  refreshQueue = [];
}

// Interceptor: tự động attach token vào request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Interceptor: xử lý 401 → thử refresh token
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      originalRequest._retry = true;

      if (isRefreshing) {
        try {
          const token = await new Promise((resolve, reject) => {
            refreshQueue.push({ resolve, reject });
          });
          originalRequest.headers.Authorization = `Bearer ${token}`;
          return api(originalRequest);
        } catch (refreshError) {
          return Promise.reject(refreshError);
        }
      }

      isRefreshing = true;
      try {
        const refreshToken = localStorage.getItem('refresh_token');
        if (!refreshToken) throw new Error('No refresh token');

        const { data } = await axios.post(`${API_BASE}/auth/refresh`, {
          refresh_token: refreshToken,
        });

        localStorage.setItem('access_token', data.access_token);
        localStorage.setItem('refresh_token', data.refresh_token);
        resolveRefreshQueue(null, data.access_token);

        originalRequest.headers.Authorization = `Bearer ${data.access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        resolveRefreshQueue(refreshError, null);
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/auth/login';
        return Promise.reject(refreshError);
      } finally {
        isRefreshing = false;
      }
    }
    return Promise.reject(error);
  }
);

// ── Auth API ──────────────────────────────────────────
export const authAPI = {
  register: (email, password) =>
    api.post('/auth/register', { email, password }),

  verifyEmail: (email, otp) =>
    api.post('/auth/verify-email', { email, otp }),

  login: (email, password) =>
    api.post('/auth/login', { email, password }),

  logout: () => {
    const refreshToken = localStorage.getItem('refresh_token');
    return api.post('/auth/logout', { refresh_token: refreshToken }).finally(() => {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    });
  },

  getMe: () => api.get('/auth/me'),

  updateProfile: (payload) => api.put('/auth/profile', payload),

  uploadAvatar: (file) => {
    const formData = new FormData();
    formData.append('avatar', file);
    return api.post('/auth/avatar', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  deleteAvatar: () => api.delete('/auth/avatar'),

  changePassword: (oldPassword, newPassword) =>
    api.post('/auth/change-password', { old_password: oldPassword, new_password: newPassword }),

  forgotPassword: (email) =>
    api.post('/auth/forgot-password', { email }),

  resetPassword: (email, otp, newPassword) =>
    api.post('/auth/reset-password', { email, otp, new_password: newPassword }),
};

// ── CV API ────────────────────────────────────────────
export const cvAPI = {
  list: () => api.get('/cvs'),

  upload: (file, title) => {
    const formData = new FormData();
    formData.append('cv_pdf', file);
    if (title) formData.append('title', title);
    return api.post('/cvs/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  delete: (cvId) => api.delete(`/cvs/delete/${cvId}`),

  getSignedUrl: (cvId) => {
    return api.get(`/cvs/file/${cvId}`);
  },

  downloadFile: (cvId) => api.get(`/cvs/file/${cvId}/content`, {
    responseType: 'blob',
  }),
};

// ── JD API ────────────────────────────────────────────
export const jdAPI = {
  list: () => api.get('/jds'),

  upload: (text, title, file = null) => {
    const formData = new FormData();
    if (text) formData.append('jd_text', text);
    if (title) formData.append('title', title);
    if (file) formData.append('jd_file', file);
    return api.post('/jds/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  delete: (jdId) => api.delete(`/jds/delete/${jdId}`),

  getSignedUrl: (jdId) => {
    return api.get(`/jds/file/${jdId}`);
  },

  downloadFile: (jdId) => api.get(`/jds/file/${jdId}/content`, {
    responseType: 'blob',
  }),
};

// ── Match API ──────────────────────────────────────────
export const matchAPI = {
  list: (limit = 20, offset = 0) =>
    api.get(`/matches?limit=${limit}&offset=${offset}`),

  get: (matchId) => api.get(`/matches/${matchId}`),

  delete: (matchId) => api.delete(`/matches/${matchId}`),

  create: (cvId, jdId) =>
    api.post('/matches', { cv_id: cvId, jd_id: jdId }),

  download: (matchId) => {
    return api.get(`/matches/download/${matchId}`, {
      responseType: 'blob',
    });
  },
};

export default api;
