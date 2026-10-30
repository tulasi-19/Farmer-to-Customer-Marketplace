import React, { useState } from 'react';
import { adminAPI, farmsAPI } from '../../api/services';
import useFetch from '../../hooks/useFetch';
import { useToast } from '../../context/ToastContext';
import { Empty, ErrorBox, Pagination, Spinner, StatusBadge, fmtDate } from '../../components/ui';
import { formatApiError } from '../../utils/errors';

function Row({ a, onDone }) {
  const toast = useToast();
  const [rejecting, setRejecting] = useState(false);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);

  const act = async (fn, msg) => {
    setBusy(true);
    try { await fn(); toast(msg); onDone(); } catch (x) { toast(formatApiError(x), 'error'); } finally { setBusy(false); }
  };
  const view = async () => {
    try { window.open(await farmsAPI.document(a.document_url.replace('/api/v1', '')), '_blank', 'noopener'); }
    catch { toast('Could not open the document', 'error'); }
  };

  return (
    <div className="panel">
      <div className="row-between"><strong>{a.farm_name}</strong><StatusBadge value={a.status} /></div>
      <p className="muted">Owner: {a.owner_username} · {a.owner_email} · {a.owner_phone || 'no phone'}<br />
        📍 {a.farm_location} · ID: {a.id_type} ••••{a.id_number_last4} · Submitted {fmtDate(a.submitted_at)}</p>
      {a.status !== 'pending' && <p className="muted">Reviewed {fmtDate(a.reviewed_at)} by {a.reviewed_by_username || '—'}{a.decision_reason ? ` — “${a.decision_reason}”` : ''}</p>}
      <div className="row">
        <button className="btn btn-secondary btn-sm" onClick={view}>View document</button>
        {a.status === 'pending' && <>
          <button className="btn btn-primary btn-sm" disabled={busy} onClick={() => act(() => adminAPI.approveKyc(a.id), 'Approved')}>Approve</button>
          <button className="btn btn-danger btn-sm" disabled={busy} onClick={() => setRejecting(!rejecting)}>Reject…</button></>}
      </div>
      {rejecting && (
        <form className="row" style={{ marginTop: 10 }} onSubmit={(e) => { e.preventDefault(); act(() => adminAPI.rejectKyc(a.id, reason), 'Rejected'); }}>
          <input aria-label="Rejection reason" required placeholder="Reason shown to the farmer (required)" value={reason} onChange={(e) => setReason(e.target.value)} style={{ flex: 1, padding: 8 }} />
          <button className="btn btn-danger btn-sm" disabled={busy}>Confirm rejection</button>
        </form>)}
    </div>
  );
}

export default function AdminKYC() {
  const [status, setStatus] = useState('pending');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch(() => adminAPI.kyc({ page, ...(status ? { status } : {}) }), [page, status]);
  return (
    <>
      <div className="filters"><select aria-label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
        <option value="pending">Pending</option><option value="approved">Approved</option><option value="rejected">Rejected</option><option value="">All</option></select></div>
      {loading && <Spinner />}
      <ErrorBox message={error} onRetry={reload} />
      {data?.results?.length === 0 && <Empty icon="✅" title="Nothing to review" />}
      {(data?.results || []).map((a) => <Row key={a.id} a={a} onDone={reload} />)}
      <Pagination data={data} page={page} setPage={setPage} />
    </>
  );
}
