import { useState } from 'react';
import { useAuth } from '../../contexts/AuthContext';
import './AuthModal.css';

export default function AuthModal({ open, onClose }) {
  const { login, register } = useAuth();
  const [mode, setMode] = useState('login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  if (!open) return null;

  const submit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      if (mode === 'login') {
        await login(email, password);
      } else {
        await register(email, username, password);
      }
      onClose();
    } catch (err) {
      const msg = err?.response?.data?.message || err?.response?.data?.error || 'Request failed';
      setError(msg);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        <h2>{mode === 'login' ? 'Sign in' : 'Create account'}</h2>

        <form onSubmit={submit} className="modal-form">
          <label className="field-label">Email</label>
          <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} required />

          {mode === 'register' && (
            <>
              <label className="field-label">Username</label>
              <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} required />
            </>
          )}

          <label className="field-label">Password</label>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />

          {error && <div className="form-error">{error}</div>}

          <div className="modal-actions">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={submitting}>
              {submitting ? 'Please wait...' : (mode === 'login' ? 'Sign in' : 'Register')}
            </button>
          </div>
        </form>

        <button className="text-btn" onClick={() => setMode(mode === 'login' ? 'register' : 'login')}>
          {mode === 'login' ? 'Need an account? Register' : 'Have an account? Sign in'}
        </button>
      </div>
    </div>
  );
}

