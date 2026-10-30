import React, { useState } from 'react';
import { adminAPI } from '../../api/services';
import useFetch from '../../hooks/useFetch';
import { useToast } from '../../context/ToastContext';
import { Empty, ErrorBox, Pagination, Spinner, StatusBadge, fmtDate } from '../../components/ui';
import { formatApiError } from '../../utils/errors';

export default function AdminReviews() {
  const toast = useToast();
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch(() => adminAPI.reviews({ page, ...(status ? { status } : {}) }), [page, status]);
  const set = async (r, s) => {
    try { await adminAPI.moderateReview(r.id, s); toast(s === 'hidden' ? 'Review hidden' : 'Review published'); reload(); }
    catch (x) { toast(formatApiError(x), 'error'); }
  };
  return (
    <>
      <div className="filters"><select aria-label="Status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">All</option><option value="published">Published</option><option value="hidden">Hidden</option></select></div>
      {loading && <Spinner />}<ErrorBox message={error} onRetry={reload} />
      {data?.results?.length === 0 && <Empty icon="⭐" title="No reviews" />}
      {(data?.results || []).map((r) => (
        <div className="panel" key={r.id}>
          <div className="row-between"><span><strong>{r.product_name}</strong> · {r.username} · {'★'.repeat(r.rating)}</span><StatusBadge value={r.status} /></div>
          <p>{r.comment || <em className="muted">(no text)</em>}</p><div className="muted">{fmtDate(r.created_at)}</div>
          <button className="btn btn-secondary btn-sm" onClick={() => set(r, r.status === 'hidden' ? 'published' : 'hidden')}>{r.status === 'hidden' ? 'Publish' : 'Hide'}</button>
        </div>))}
      <Pagination data={data} page={page} setPage={setPage} />
    </>
  );
}
