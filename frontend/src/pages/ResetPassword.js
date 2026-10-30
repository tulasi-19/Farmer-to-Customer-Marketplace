import React, { useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { authAPI } from '../api/services';
import { formatApiError } from '../utils/errors';

export default function ResetPassword() {
  const [params] = useSearchParams();
  const [pw, setPw] = useState('');
  const [done, setDone] = useState(false);
  const [error, setError] = useState('');
  const submit = async (e) => {
    e.preventDefault(); setError('');
    try { await authAPI.reset({ uid: params.get('uid'), token: params.get('token'), new_password: pw }); setDone(true); }
    catch (err) { setError(formatApiError(err)); }
  };
  if (done) return <div className="form-card"><h2>Password updated</h2><Link className="btn btn-secondary" to="/login">Go to login</Link></div>;
  return (
    <form className="form-card" onSubmit={submit}>
      <h2>Choose a new password</h2>
      <div className="form-group"><label htmlFor="np">New password</label><input id="np" type="password" required minLength={8} value={pw} onChange={(e) => setPw(e.target.value)} autoComplete="new-password" /></div>
      {error && <div className="alert alert-error">{error}</div>}
      <button className="btn btn-secondary" style={{ width: '100%' }}>Reset password</button>
    </form>
  );
}
