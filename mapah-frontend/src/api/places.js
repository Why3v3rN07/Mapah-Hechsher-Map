import client from './client';
import axios from 'axios';

/**
 * @param {Object} params – q, hechsher, hechsher_id, tags, bbox
 */
export const getPlaces = async (params = {}) => {
  try {
	return await client.get('/api/places', { params });
  } catch (error) {
	// Fallbacks for local dev when proxy is not configured/running.
	const status = error?.response?.status;
	const shouldTryFallback = !status || status === 404 || status >= 500;
	if (!shouldTryFallback) throw error;

	const fallbackBases = ['http://localhost:5050', 'http://localhost:5000', 'http://localhost:8000'];
	for (const baseURL of fallbackBases) {
	  try {
		return await axios.get(`${baseURL}/api/places`, {
		  params,
		  withCredentials: true,
		});
	  } catch (fallbackError) {
		const fallbackStatus = fallbackError?.response?.status;
		const shouldContinue = !fallbackStatus || fallbackStatus === 404 || fallbackStatus >= 500;
		if (!shouldContinue) throw fallbackError;
	  }
	}

	throw error;
  }
};

