import client from './client';

export const getHechshers = () =>
  client.get('/api/hechshers');

export const searchHechshers = (q, limit = 10) =>
  client.get('/api/hechshers/search', { params: { q, limit } });

export const createHechsher = (formData) =>
  client.post('/api/hechshers', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });

export const getPlaceAliases = (placeId) =>
  client.get(`/api/places/${placeId}/aliases`);

