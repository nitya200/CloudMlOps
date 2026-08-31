import api from './api.js';

export const authService = {
  register: (payload) => api.post('/api/auth/register', payload).then((r) => r.data),
  login: (email, password) =>
    api.post('/api/auth/login', { email, password }).then((r) => r.data),
  logout: () => api.post('/api/auth/logout').then((r) => r.data),
  me: () => api.get('/api/auth/me').then((r) => r.data),
  health: () => api.get('/health').then((r) => r.data),
};

export default authService;
