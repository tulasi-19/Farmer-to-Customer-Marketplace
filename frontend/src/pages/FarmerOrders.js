import React, { useState } from 'react';
import { farmerAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import FarmerNav from '../components/FarmerNav';
import { EventList, ShipmentProgress } from '../components/OrderTracker';
import { useToast } from '../context/ToastContext';
import { Empty, ErrorBox, Pagination, Spinner, StatusBadge, fmtDate, money } from '../components/ui';
import { formatApiError } from '../utils/errors';

const LABEL = { processing: 'Start processing', shipped: 'Mark shipped', out_for_delivery: 'Out for delivery', delivered: 'Mark delivered', cancelled: 'Cancel items' };

function ShipmentCard({ s, onChanged }) {
  const toast = useToast();
  const [next, setNext] = useState('');
  const [f, setF] = useState({ note: '', carrier: '', tracking_number: '' });
  const [busy, setBusy] = useState(false);
  const [showLog, setShowLog] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (next === 'cancelled' && !window.confirm('Cancel these items? Stock will be returned and the customer notified.')) return;
    setBusy(true);
    try { await farmerAPI.setStatus(s.id, { status: next, ...f }); toast('Status updated'); setNext(''); setF({ note: '', carrier: '', tracking_number: '' }); onChanged(); }
    catch (x) { toast(formatApiError(x), 'error'); } finally { setBusy(false); }
  };

  return (
    <div className="panel">
      <div className="row-between">
        <strong>Order #{s.order_id} · {fmtDate(s.ordered_at)}</strong>
        <StatusBadge value={s.status} label={s.status_label} />
      </div>
      <p className="muted">Customer: {s.customer_name} · 📞 {s.shipping_phone}<br />📍 {s.shipping_address}</p>
      {s.payment_method === 'cod' && <div className="alert alert-warn">Cash on delivery — collect {money(s.subtotal)} from the customer. An admin records the collection.</div>}
      <table><tbody>{s.items.map((i) => <tr key={i.id}><td>{i.product_name}</td><td>{i.quantity} {i.unit}</td><td>{money(i.line_total)}</td></tr>)}</tbody></table>
      <div className="row-between"><span>Your share:</span><strong>{money(s.subtotal)}</strong></div>
      <ShipmentProgress status={s.status} />
      {(s.carrier || s.tracking_number) && <p className="muted">{s.carrier} {s.tracking_number}</p>}

      {s.allowed_next.length > 0 ? (
        <form onSubmit={submit}>
          <div className="row">
            {s.allowed_next.map((n) => (
              <button type="button" key={n} className={`btn btn-sm ${n === 'cancelled' ? 'btn-danger' : next === n ? 'btn-primary' : 'btn-secondary'}`} onClick={() => setNext(n)}>{LABEL[n]}</button>
            ))}
          </div>
          {next && (
            <div className="row" style={{ marginTop: 10 }}>
              {(next === 'shipped' || next === 'out_for_delivery') && <>
                <input aria-label="Carrier" placeholder="Carrier / vehicle" value={f.carrier} onChange={(e) => setF({ ...f, carrier: e.target.value })} />
                <input aria-label="Tracking number" placeholder="Tracking no. (optional)" value={f.tracking_number} onChange={(e) => setF({ ...f, tracking_number: e.target.value })} /></>}
              <input aria-label="Note" placeholder={next === 'cancelled' ? 'Reason (required)' : 'Note for customer (optional)'} required={next === 'cancelled'} value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} style={{ flex: 1 }} />
              <button className="btn btn-secondary btn-sm" disabled={busy}>{busy ? 'Saving…' : 'Confirm'}</button>
            </div>)}
        </form>
      ) : <p className="muted">No further actions.</p>}
      <button className="link-btn" onClick={() => setShowLog(!showLog)}>{showLog ? 'Hide' : 'Show'} history</button>
      {showLog && <EventList events={s.events} />}
    </div>
  );
}

export default function FarmerOrders() {
  const [status, setStatus] = useState('');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch(() => farmerAPI.shipments({ page, ...(status ? { status } : {}) }), [page, status]);
  return (
    <div className="container">
      <FarmerNav />
      <div className="row-between"><h1 className="section-title" style={{ marginTop: 0 }}>Incoming orders</h1>
        <select aria-label="Filter by status" value={status} onChange={(e) => { setStatus(e.target.value); setPage(1); }}>
          <option value="">All</option><option value="confirmed">To process</option><option value="processing">Processing</option>
          <option value="shipped">Shipped</option><option value="out_for_delivery">Out for delivery</option><option value="delivered">Delivered</option><option value="cancelled">Cancelled</option></select></div>
      <p className="muted">You only see your own items.</p>
      {loading && <Spinner />}
      <ErrorBox message={error} onRetry={reload} />
      {data?.results?.length === 0 && <Empty icon="📦" title="No orders here yet" />}
      {(data?.results || []).map((s) => <ShipmentCard key={s.id} s={s} onChanged={reload} />)}
      <Pagination data={data} page={page} setPage={setPage} />
    </div>
  );
}
