import client from './client';
import axios from 'axios';

export const getCsrfToken = async () => {
  try {
	return await client.get('/api/csrf-token');
  } catch (error) {
	const status = error?.response?.status;
	const shouldTryFallback = !status || status === 404 || status >= 500;
	if (!shouldTryFallback) throw error;

	const fallbackBases = ['http://localhost:5050', 'http://localhost:5000', 'http://localhost:8000'];
	for (const baseURL of fallbackBases) {
	  try {
		return await axios.get(`${baseURL}/api/csrf-token`, { withCredentials: true });
	  } catch (fallbackError) {
		const fallbackStatus = fallbackError?.response?.status;
		const shouldContinue = !fallbackStatus || fallbackStatus === 404 || fallbackStatus >= 500;
		if (!shouldContinue) throw fallbackError;
	  }
	}

	throw error;
  }
};

export const register = (data) => client.post('/auth/register', data);
export const login    = (data) => client.post('/auth/login', data);
export const logout   = ()     => client.post('/auth/logout');
export const refresh  = ()     => client.post('/auth/refresh');

export const changePassword = (data) => client.post('/auth/change-password', data);
export const deleteAccount  = ()     => client.delete('/auth/account');

