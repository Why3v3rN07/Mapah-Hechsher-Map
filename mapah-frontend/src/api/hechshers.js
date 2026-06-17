import client from './client';

export const searchHechshers = (q, limit = 10) =>
  client.get('/api/hechshers/search', { params: { q, limit } });

