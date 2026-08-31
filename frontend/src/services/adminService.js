import api from './api.js';

export const adminService = {
  users: (params) => api.get('/api/admin/users', { params }).then((r) => r.data),
  setStatus: (userId, isActive) =>
    api.patch(`/api/admin/users/${userId}/status`, { is_active: isActive }).then((r) => r.data),
  setRole: (userId, role) =>
    api.patch(`/api/admin/users/${userId}/role`, { role }).then((r) => r.data),
  stats: () => api.get('/api/admin/stats').then((r) => r.data),
  usage: (days = 14) => api.get('/api/admin/usage', { params: { days } }).then((r) => r.data),
  quality: () => api.get('/api/admin/metrics').then((r) => r.data),
};

export default adminService;
