import React, { useState } from 'react';
import { adminAPI } from '../../api/services';
import useFetch from '../../hooks/useFetch';
import { useToast } from '../../context/ToastContext';
import OrderTracker from '../../components/OrderTracker';
import { ErrorBox, Pagination, Spinner, StatusBadge, fmtDate, money } from '../../components/ui';
import { formatApiError } from '../../utils/errors';

const NEXT = { confirmed: ['processing', 'cancelled'], processing: ['shipped', 'cancelled'], shipped: ['out_for_delivery', 'delivered'], out_for_delivery: ['delivered'], pending: ['cancelled'] };

function Detail({ o, onChanged }) {
  const toast = useToast();
  const act = async (fn, msg) => { try { await fn(); toast(msg); onChanged(); } catch (x) { toast(formatApiError(x), 'error'); } };
  const move = (s, status) => {
    const note = status === 'cancelled' ? window.prompt('Reason for cancelling (required):') : '';
    if (status === 'cancelled' && !note) return;
    act(() => adminAPI.setShipmentStatus(s.id, { status, note: note || '' }), 'Status updated');
  };
  return (
    <div className="panel">
      <p className="muted">Customer: {o.customer_username} ({o.customer_email}) · {o.shipping_address} · {o.shipping_phone}</p>
      {o.payment_status === 'cod_pending' && o.status === 'delivered' && <button className="btn btn-primary btn-sm" onClick={() => act(() => adminAPI.markCodPaid(o.id), 'Marked as collected')}>Mark cash collected</button>}
      <OrderTracker order={o} />
      <h4>Admin actions</h4>
      {o.shipments.map((s) => (
        <div className="row" key={s.id}><span>{s.farm_name}:</span>
          {(NEXT[s.status] || []).map((n) => <button key={n} className={`btn btn-sm ${n === 'cancelled' ? 'btn-danger' : 'btn-secondary'}`} onClick={() => move(s, n)}>{n.replace(/_/g, ' ')}</button>)}
          {!(NEXT[s.status] || []).length && <span className="muted">no actions</span>}</div>))}
    </div>
  );
}

export default function AdminOrders() {
  const [status, setStatus] = useState('');
  const [pay, setPay] = useState('');
  const [open, setOpen] = useState(null);
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch(() => adminAPI.orders({ page, ...(status ? { status } : {}), ...(pay ? { payment_status: pay } : {}) }), [page, status, pay]);
  return (
    <>
      <div className="filters">
        <select aria-label="Order status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}><option value="">All delivery statuses</option>
          {['pending', 'confirmed', 'processing', 'shipped', 'out_for_delivery', 'delivered', 'cancelled'].map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}</select>
        <select aria-label="Payment status" value={pay} onChange={(e) => { setPay(e.target.value); setPage(1); }}><option value="">All cash statuses</option>
          {['cod_pending', 'cod_paid'].map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}</select>
      </div>
      {loading && <Spinner />}<ErrorBox message={error} onRetry={reload} />
      {(data?.results || []).map((o) => (
        <div key={o.id}>
          <div className="panel row-between" style={{ marginBottom: 0 }}>
            <span><strong>#{o.id}</strong> · {o.customer_username} · {fmtDate(o.created_at)} · {money(o.total_amount)}</span>
            <span className="row"><StatusBadge value={o.status} label={o.status_label} /><StatusBadge value={o.payment_status} label={o.payment_status_label} />
              <button className="btn btn-secondary btn-sm" onClick={() => setOpen(open === o.id ? null : o.id)}>{open === o.id ? 'Close' : 'Manage'}</button></span>
          </div>
          {open === o.id && <Detail o={o} onChanged={reload} />}
        </div>))}
      <Pagination data={data} page={page} setPage={setPage} />
    </>
  );
}
