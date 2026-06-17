import axios from 'axios';
import client from './client';

function getCookie(name) {
  const match = document.cookie.match(new RegExp('(?:^|;\\s*)' + name + '=([^;]*)'));
  return match ? decodeURIComponent(match[1]) : null;
}

async function postWithFallback(path, data) {
  try {
	return await client.post(path, data);
  } catch (error) {
	// Keep behavior aligned with getPlaces fallback for local dev environments.
	const status = error?.response?.status;
	const shouldTryFallback = !status || status === 404 || status >= 500;
	if (!shouldTryFallback) throw error;

	const csrf = getCookie('csrf_token');
	const headers = csrf ? { 'X-CSRF-Token': csrf } : {};
	const fallbackBases = ['http://localhost:5050', 'http://localhost:5000', 'http://localhost:8000'];

	for (const baseURL of fallbackBases) {
	  try {
		return await axios.post(`${baseURL}${path}`, data, {
		  withCredentials: true,
		  headers,
		});
	  } catch (fallbackError) {
		const fallbackStatus = fallbackError?.response?.status;
		const shouldContinue = !fallbackStatus || fallbackStatus === 404 || fallbackStatus >= 500;
		if (!shouldContinue) throw fallbackError;
	  }
	}

	throw error;
  }
}

export const submitPlace = (data) => postWithFallback('/api/submissions/place', data);
export const tagPlace = (placeId, data) => postWithFallback(`/api/places/${placeId}/tags`, data);

