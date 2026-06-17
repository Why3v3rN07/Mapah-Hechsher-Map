import client from './client';

export const listAdminSubmissions = (params) =>
  client.get('/api/admin/submissions', { params });

export const getAdminSubmission = (id) =>
  client.get(`/api/admin/submissions/${id}`);

export const approveSubmission = (id) =>
  client.post(`/api/admin/submissions/${id}/approve`);

export const rejectSubmission = (id, reason = '') =>
  client.post(`/api/admin/submissions/${id}/reject`, { reason });

