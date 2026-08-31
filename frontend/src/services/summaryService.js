import api from './api.js';

export const summaryService = {
  options: () => api.get('/api/summaries/options').then((r) => r.data),

  supportedTypes: () => api.get('/api/documents/supported-types').then((r) => r.data),

  uploadDocument: (file, onProgress) => {
    const form = new FormData();
    form.append('file', file);
    return api
      .post('/api/documents/upload', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (event) => {
          if (onProgress && event.total) {
            onProgress(Math.round((event.loaded * 100) / event.total));
          }
        },
      })
      .then((r) => r.data);
  },

  listDocuments: (params) => api.get('/api/documents', { params }).then((r) => r.data),

  deleteDocument: (id) => api.delete(`/api/documents/${id}`).then((r) => r.data),

  summarizeText: (payload) => api.post('/api/summaries/text', payload).then((r) => r.data),

  summarizeDocument: (documentId, payload) =>
    api.post(`/api/summaries/document/${documentId}`, payload).then((r) => r.data),

  getSummary: (id) => api.get(`/api/summaries/${id}`).then((r) => r.data),

  history: (params) => api.get('/api/history', { params }).then((r) => r.data),

  deleteSummary: (id) => api.delete(`/api/history/${id}`).then((r) => r.data),

  rate: (summaryId, rating, comment) =>
    api
      .post('/api/feedback', { summary_id: summaryId, rating, comment: comment || null })
      .then((r) => r.data),

  /** Fetches the .txt export and triggers a browser download. */
  download: async (id, title) => {
    const response = await api.get(`/api/summaries/${id}/download`, { responseType: 'blob' });
    const url = URL.createObjectURL(new Blob([response.data], { type: 'text/plain' }));
    const link = document.createElement('a');
    link.href = url;
    link.download = `${(title || 'summary').replace(/[^a-z0-9]+/gi, '_').slice(0, 60)}.txt`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  },
};

export default summaryService;
