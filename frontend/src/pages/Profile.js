import React, { useState } from 'react';
import { authAPI } from '../api/services';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import { formatApiError } from '../utils/errors';

export default function Profile() {
  const { user, setUser } = useAuth();
  const toast = useToast();
  const [form, setForm] = useState({ email: user.email, phone: user.phone || '', address: user.address || '' });
  const [pw, setPw] = useState({ old_password: '', new_password: '' });
  const [err, setErr] = useState('');

  const save = async (e) => {
    e.preventDefault(); setErr('');
    try { setUser(await authAPI.updateMe(form)); toast('Profile saved'); } catch (x) { setErr(formatApiError(x)); }
  };
  const changePw = async (e) => {
    e.preventDefault();
    try { await authAPI.changePassword(pw); setPw({ old_password: '', new_password: '' }); toast('Password changed'); }
    catch (x) { toast(formatApiError(x), 'error'); }
  };

  return (
    <div className="container wide-form">
      <h1 className="section-title">My profile</h1>
      <form className="panel" onSubmit={save}>
        <p className="muted">Username: <strong>{user.username}</strong> · Role: <strong>{user.role}</strong></p>
        <div className="form-group"><label htmlFor="pe">Email</label><input id="pe" type="email" value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} /></div>
        <div className="form-group"><label htmlFor="pp">Phone</label><input id="pp" value={form.phone} onChange={(e) => setForm({ ...form, phone: e.target.value })} /></div>
        <div className="form-group"><label htmlFor="pa">Default address</label><textarea id="pa" rows={3} value={form.address} onChange={(e) => setForm({ ...form, address: e.target.value })} /></div>
        {err && <div className="alert alert-error">{err}</div>}
        <button className="btn btn-secondary">Save changes</button>
      </form>
      <form className="panel" onSubmit={changePw}>
        <h3 style={{ marginTop: 0 }}>Change password</h3>
        <div className="form-group"><label htmlFor="op">Current password</label><input id="op" type="password" required autoComplete="current-password" value={pw.old_password} onChange={(e) => setPw({ ...pw, old_password: e.target.value })} /></div>
        <div className="form-group"><label htmlFor="npw">New password</label><input id="npw" type="password" required minLength={8} autoComplete="new-password" value={pw.new_password} onChange={(e) => setPw({ ...pw, new_password: e.target.value })} /></div>
        <button className="btn btn-secondary">Change password</button>
      </form>
    </div>
  );
}
