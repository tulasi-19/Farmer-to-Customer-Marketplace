import React, { useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { formatApiError } from '../utils/errors';

export const homeFor = (role) => (role === 'farmer' ? '/farmer' : role === 'admin' ? '/admin' : '/');

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: '', password: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('');
    try {
      const me = await login(form.username.trim(), form.password);
      navigate(location.state?.from || homeFor(me.role), { replace: true });
    } catch (err) {
      setError(err.response?.status === 401 ? 'Incorrect username or password.' : formatApiError(err, 'Login failed.'));
    } finally { setBusy(false); }
  };

  return (
    <form className="form-card" onSubmit={submit}>
      <h2>Welcome back</h2>
      <div className="form-group"><label htmlFor="u">Username</label>
        <input id="u" autoComplete="username" required value={form.username} onChange={(e) => setForm({ ...form, username: e.target.value })} /></div>
      <div className="form-group"><label htmlFor="p">Password</label>
        <input id="p" type="password" autoComplete="current-password" required value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} /></div>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <button className="btn btn-secondary" disabled={busy} style={{ width: '100%' }}>{busy ? 'Signing in…' : 'Login'}</button>
      <p className="muted"><Link to="/forgot-password">Forgot password?</Link> · <Link to="/register">Create account</Link></p>
    </form>
  );
}
