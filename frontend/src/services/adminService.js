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
  modelVersions: () => api.get('/api/admin/model-versions').then((r) => r.data),
  activeModelVersion: () => api.get('/api/admin/model-versions/active').then((r) => r.data),
  approveModelVersion: (versionId) =>
    api.post(`/api/admin/model-versions/${versionId}/approve`).then((r) => r.data),
  promoteModelVersion: (versionId) =>
    api.post(`/api/admin/model-versions/${versionId}/promote`).then((r) => r.data),
  trainingJobs: () => api.get('/api/admin/training-jobs').then((r) => r.data),
  triggerTrainingJob: (notes) =>
    api.post('/api/admin/training-jobs', { notes: notes || null }).then((r) => r.data),
};

export default adminService;
