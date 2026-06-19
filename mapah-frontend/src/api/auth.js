import client from './client';
import axios from 'axios';
import { clearSessionTokens, storeCsrfToken, storeSessionTokens } from './client';

function storeAuthPayload(data) {
  if (data?.csrf_token) storeCsrfToken(data.csrf_token);
  storeSessionTokens(data?.access_token, data?.refresh_token);
}

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
  storeAuthPayload(res.data);
  return res;
};

export const login = async (data) => {
  const res = await client.post('/auth/login', data);
  storeAuthPayload(res.data);
  return res;
};

export const logout = async () => {
  try {
    return await client.post('/auth/logout');
  } finally {
    clearSessionTokens();
  }
};

export const refresh  = async () => {
  const res = await client.post('/auth/refresh', null, { _useRefreshToken: true });
  storeAuthPayload(res.data);
  return res;
};

export const changePassword = (data) => client.post('/auth/change-password', data);
export const deleteAccount  = ()     => client.delete('/auth/account');



