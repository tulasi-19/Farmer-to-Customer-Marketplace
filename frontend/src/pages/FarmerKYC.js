import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { farmsAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import FarmerNav from '../components/FarmerNav';
import { useToast } from '../context/ToastContext';
import { ErrorBox, Spinner, StatusBadge, fmtDate } from '../components/ui';
import { formatApiError } from '../utils/errors';

export default function FarmerKYC() {
  const toast = useToast();
  const { data, loading, error, reload } = useFetch(() => farmsAPI.kyc(), []);
  const profile = useFetch(() => farmsAPI.profile().catch(() => null), []);
  const [form, setForm] = useState({ id_type: 'aadhaar', id_number: '' });
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  const submit = async (e) => {
    e.preventDefault(); setErr('');
    if (!file) { setErr('Please choose a document to upload.'); return; }
    const fd = new FormData();
    fd.append('id_type', form.id_type); fd.append('id_number', form.id_number); fd.append('document', file);
    setBusy(true);
    try { await farmsAPI.submitKyc(fd); toast('KYC submitted for review'); setFile(null); setForm({ ...form, id_number: '' }); reload(); }
    catch (x) { setErr(formatApiError(x)); } finally { setBusy(false); }
  };

  const view = async (id) => {
    try { window.open(await farmsAPI.document(`/farmer/kyc/${id}/document/`), '_blank', 'noopener'); }
    catch (x) { toast('Could not open the document', 'error'); }
  };

  if (loading || profile.loading) return <div className="container"><Spinner /></div>;
  const status = data?.kyc_status || 'not_submitted';
  const latest = data?.applications?.[0];
  const canSubmit = profile.data && (status === 'not_submitted' || status === 'rejected');

  return (
    <div className="container">
      <FarmerNav />
      <h1 className="section-title" style={{ marginTop: 0 }}>KYC verification</h1>
      <ErrorBox message={error} onRetry={reload} />
      <div className="panel">
        <p>Current status: <StatusBadge value={status} /></p>
        {status === 'approved' && <div className="alert alert-ok">You are verified. You can list products.</div>}
        {status === 'pending' && <div className="alert alert-warn">Submitted {fmtDate(latest?.submitted_at)}. An admin will review it soon.</div>}
        {status === 'rejected' && <div className="alert alert-error"><strong>Rejected:</strong> {latest?.decision_reason || 'No reason given.'} You can submit again below.</div>}
        {!profile.data && <div className="alert alert-warn">Create your <Link to="/farmer/profile">farm profile</Link> first.</div>}
      </div>

      {canSubmit && (
        <form className="panel" onSubmit={submit}>
          <h3 style={{ marginTop: 0 }}>Submit documents</h3>
          <div className="form-group"><label htmlFor="it">ID type</label>
            <select id="it" value={form.id_type} onChange={(e) => setForm({ ...form, id_type: e.target.value })}>
              <option value="aadhaar">Aadhaar</option><option value="pan">PAN</option><option value="voter_id">Voter ID</option>
              <option value="driving_license">Driving licence</option><option value="land_record">Land record</option></select></div>
          <div className="form-group"><label htmlFor="in">ID number</label>
            <input id="in" required minLength={4} value={form.id_number} onChange={(e) => setForm({ ...form, id_number: e.target.value })} />
            <div className="muted">Only the last 4 characters are stored.</div></div>
          <div className="form-group"><label htmlFor="id">Document scan (PDF/JPG/PNG, max 5 MB)</label>
            <input id="id" type="file" accept="application/pdf,image/png,image/jpeg" onChange={(e) => setFile(e.target.files[0])} />
            <div className="muted">Stored privately. Only you and FarmBridge admins can view it.</div></div>
          {err && <div className="alert alert-error" role="alert">{err}</div>}
          <button className="btn btn-secondary" disabled={busy}>{busy ? 'Uploading…' : 'Submit for review'}</button>
        </form>
      )}

      {data?.applications?.length > 0 && (
        <><h3>History</h3><div className="table-wrap"><table>
          <thead><tr><th>Submitted</th><th>ID type</th><th>Status</th><th>Reviewed</th><th>Reason</th><th></th></tr></thead>
          <tbody>{data.applications.map((a) => (
            <tr key={a.id}><td>{fmtDate(a.submitted_at)}</td><td>{a.id_type} ••••{a.id_number_last4}</td><td><StatusBadge value={a.status} /></td>
              <td>{fmtDate(a.reviewed_at)}</td><td>{a.decision_reason || '—'}</td>
              <td><button className="btn btn-secondary btn-sm" onClick={() => view(a.id)}>View document</button></td></tr>
          ))}</tbody></table></div></>
      )}
    </div>
  );
}
