import React, { useState } from 'react';
import { authAPI } from '../api/services';
import { formatApiError } from '../utils/errors';

export default function ForgotPassword() {
  const [value, setValue] = useState('');
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');
  const submit = async (e) => {
    e.preventDefault(); setError('');
    try { setMsg((await authAPI.forgot({ username_or_email: value })).detail); } catch (err) { setError(formatApiError(err)); }
  };
  return (
    <form className="form-card" onSubmit={submit}>
      <h2>Reset password</h2>
      <div className="form-group"><label htmlFor="f">Username or email</label><input id="f" required value={value} onChange={(e) => setValue(e.target.value)} /></div>
      {msg && <div className="alert alert-ok">{msg}</div>}
      {error && <div className="alert alert-error">{error}</div>}
      <button className="btn btn-secondary" style={{ width: '100%' }}>Send reset link</button>
    </form>
  );
}
