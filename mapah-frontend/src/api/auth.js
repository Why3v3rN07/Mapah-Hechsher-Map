import client from './client';
import axios from 'axios';
import { storeCsrfToken } from './client';

export const getCsrfToken = async () => {
  try {
    const res = await client.get('/api/csrf-token');
    if (res.data?.csrf_token) storeCsrfToken(res.data.csrf_token);
    return res;
  } catch (error) {
    const status = error?.response?.status;
    const shouldTryFallback = !status || status === 404 || status >= 500;
    if (!shouldTryFallback) throw error;

    const fallbackBases = ['http://localhost:5050', 'http://localhost:5000', 'http://localhost:8000'];
    for (const baseURL of fallbackBases) {
      try {
        const res = await axios.get(`${baseURL}/api/csrf-token`, { withCredentials: true });
        if (res.data?.csrf_token) storeCsrfToken(res.data.csrf_token);
        return res;
      } catch (fallbackError) {
        const fallbackStatus = fallbackError?.response?.status;
        const shouldContinue = !fallbackStatus || fallbackStatus === 404 || fallbackStatus >= 500;
        if (!shouldContinue) throw fallbackError;
      }
    }

    throw error;
  }
};

export const register = async (data) => {
  const res = await client.post('/auth/register', data);
  if (res.data?.csrf_token) storeCsrfToken(res.data.csrf_token);
  return res;
};

export const login = async (data) => {
  const res = await client.post('/auth/login', data);
  if (res.data?.csrf_token) storeCsrfToken(res.data.csrf_token);
  return res;
};

export const logout   = ()     => client.post('/auth/logout');

export const refresh  = async () => {
  const res = await client.post('/auth/refresh');
  if (res.data?.csrf_token) storeCsrfToken(res.data.csrf_token);
  return res;
};

export const changePassword = (data) => client.post('/auth/change-password', data);
export const deleteAccount  = ()     => client.delete('/auth/account');



