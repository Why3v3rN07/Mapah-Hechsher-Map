import client from './client';

async function postSubmission(path, data) {
  return client.post(path, data);
}

export const submitPlace = (data) => postSubmission('/api/submissions/place', data);
export const tagPlace = (placeId, data) => postSubmission(`/api/places/${placeId}/tags`, data);
export const addPlaceAliases = (placeId, data) => postSubmission(`/api/places/${placeId}/aliases`, data);

