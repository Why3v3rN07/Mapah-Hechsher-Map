import client from './client';

export const getPreferences    = ()      => client.get('/api/me/preferences/hechshers');
export const updatePreferences = (data)  => client.put('/api/me/preferences/hechshers', data);
export const getMySubmissions  = (params) => client.get('/api/me/submissions', { params });

