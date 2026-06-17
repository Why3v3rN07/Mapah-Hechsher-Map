/* eslint-disable react-refresh/only-export-components */
/**
 * AuthContext – manages the current user session.
 *
 * On mount:
 *  1. Fetch CSRF token cookie.
 *  2. Attempt a silent token refresh to restore session.
 *
 * Exposes: user, loading, login, register, logout, updatePreferences
 */
import { createContext, useCallback, useContext, useEffect, useReducer } from 'react';
import * as authApi from '../api/auth';
import { updatePreferences as apiUpdatePrefs } from '../api/me';

const AuthContext = createContext(null);
const USER_STORAGE_KEY = 'mapah_auth_user';

const initialState = { user: null, loading: true };

function reducer(state, action) {
  switch (action.type) {
    case 'SET_USER':    return { ...state, user: action.payload, loading: false };
    case 'CLEAR_USER':  return { user: null, loading: false };
    case 'LOADING':     return { ...state, loading: true };
    default:            return state;
  }
}

export function AuthProvider({ children }) {
  const [state, dispatch] = useReducer(reducer, initialState);

  // ── Bootstrap on mount ───────────────────────────────────────────────
  useEffect(() => {
    async function bootstrap() {
      const cached = localStorage.getItem(USER_STORAGE_KEY);
      if (cached) {
        try {
          dispatch({ type: 'SET_USER', payload: JSON.parse(cached) });
        } catch {
          localStorage.removeItem(USER_STORAGE_KEY);
        }
      }

      // 1. Ensure we have a CSRF token cookie
      try { await authApi.getCsrfToken(); } catch { /* silent */ }

      // 2. Try silent refresh to restore session
      try {
        await authApi.refresh();
        // If refresh succeeds we don't get a user payload back, so we'll
        // need the /api/me endpoint – but per the spec that doesn't exist;
        // user info is returned on login/register only.
        // We keep user=null until a fresh login (acceptable for MVP).
        // Keep cached user when refresh succeeds.
        dispatch({ type: 'SET_USER', payload: cached ? JSON.parse(cached) : null });
      } catch {
        localStorage.removeItem(USER_STORAGE_KEY);
        dispatch({ type: 'CLEAR_USER' });
      }
    }
    bootstrap();
  }, []);

  // ── Listen for session expiry (from API client) ───────────────────────
  useEffect(() => {
    const handler = () => {
      localStorage.removeItem(USER_STORAGE_KEY);
      dispatch({ type: 'CLEAR_USER' });
    };
    window.addEventListener('auth:expired', handler);
    return () => window.removeEventListener('auth:expired', handler);
  }, []);

  // ── Actions ───────────────────────────────────────────────────────────
  const login = useCallback(async (email, password) => {
    const { data } = await authApi.login({ email, password });
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
    dispatch({ type: 'SET_USER', payload: data.user });
    return data.user;
  }, []);

  const register = useCallback(async (email, username, password) => {
    const { data } = await authApi.register({ email, username, password });
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(data.user));
    dispatch({ type: 'SET_USER', payload: data.user });
    return data.user;
  }, []);

  const logout = useCallback(async () => {
    try { await authApi.logout(); } catch { /* ignore */ }
    localStorage.removeItem(USER_STORAGE_KEY);
    dispatch({ type: 'CLEAR_USER' });
  }, []);

  const updatePreferences = useCallback(async (hechsherIds) => {
    const { data } = await apiUpdatePrefs({ hechsher_ids: hechsherIds });
    const nextUser = { ...state.user, preferred_hechshers: data.hechsher_ids };
    localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(nextUser));
    dispatch({
      type: 'SET_USER',
      payload: nextUser,
    });
  }, [state.user]);

  return (
    <AuthContext.Provider
      value={{ ...state, login, register, logout, updatePreferences }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used inside AuthProvider');
  return ctx;
}



