import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authAPI } from '../api/services';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { formatApiError } from '../utils/errors';
import { homeFor } from './Login';

export default function Register() {
  const navigate = useNavigate();
  const toast = useToast();
  const { login } = useAuth();
  const [form, setForm] = useState({ username: '', email: '', password: '', role: 'customer', phone: '' });
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  const submit = async (e) => {
    e.preventDefault(); setBusy(true); setError('');
    try {
      await authAPI.register(form);
      const me = await login(form.username, form.password);
      toast(me.role === 'farmer' ? 'Welcome! Create your farm profile and submit KYC to start selling.' : 'Account created!');
      navigate(me.role === 'farmer' ? '/farmer/profile' : homeFor(me.role));
    } catch (err) { setError(formatApiError(err, 'Registration failed.')); } finally { setBusy(false); }
  };

  return (
    <form className="form-card" onSubmit={submit}>
      <h2>Create your account</h2>
      <div className="form-group"><label htmlFor="role">I want to</label>
        <select id="role" value={form.role} onChange={set('role')}>
          <option value="customer">Buy fresh produce (Customer)</option>
          <option value="farmer">Sell my produce (Farmer)</option>
        </select></div>
      <div className="form-group"><label htmlFor="ru">Username</label><input id="ru" required value={form.username} onChange={set('username')} autoComplete="username" /></div>
      <div className="form-group"><label htmlFor="re">Email</label><input id="re" type="email" required value={form.email} onChange={set('email')} autoComplete="email" /></div>
      <div className="form-group"><label htmlFor="rph">Phone</label><input id="rph" value={form.phone} onChange={set('phone')} placeholder="10-digit mobile" autoComplete="tel" /></div>
      <div className="form-group"><label htmlFor="rp">Password</label><input id="rp" type="password" required minLength={8} value={form.password} onChange={set('password')} autoComplete="new-password" />
        <div className="muted">At least 8 characters, not too common or all numbers.</div></div>
      {error && <div className="alert alert-error" role="alert">{error}</div>}
      <button className="btn btn-secondary" disabled={busy} style={{ width: '100%' }}>{busy ? 'Creating…' : 'Register'}</button>
      <p className="muted">Already registered? <Link to="/login">Login</Link></p>
    </form>
  );
}
