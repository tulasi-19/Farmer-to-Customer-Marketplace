import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { ordersAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import { useToast } from '../context/ToastContext';
import OrderTracker from '../components/OrderTracker';
import { ErrorBox, Spinner, StatusBadge, fmtDate, money } from '../components/ui';
import { formatApiError } from '../utils/errors';

export default function OrderDetail() {
  const { id } = useParams();
  const toast = useToast();
  const { data: o, loading, error, reload } = useFetch(() => ordersAPI.get(id), [id]);
  const [busy, setBusy] = useState(false);

  // Light auto-refresh so tracking updates appear without reloading the page.
  useEffect(() => {
    const t = setInterval(() => { if (document.visibilityState === 'visible') reload(); }, 30000);
    return () => clearInterval(t);
  }, [reload]);

  if (loading && !o) return <div className="container"><Spinner /></div>;
  if (error && !o) return <div className="container"><ErrorBox message={error} onRetry={reload} /></div>;

  const cancel = async () => {
    if (!window.confirm('Cancel this whole order?')) return;
    setBusy(true);
    try { await ordersAPI.cancel(o.id, 'Cancelled by customer'); toast('Order cancelled'); reload(); }
    catch (err) { toast(formatApiError(err), 'error'); } finally { setBusy(false); }
  };
  const deliveredProducts = o.shipments.filter((s) => s.status === 'delivered').flatMap((s) => s.items);

  return (
    <div className="container">
      <div className="row-between">
        <h1 className="section-title">Order #{o.id}</h1>
        <div className="row"><StatusBadge value={o.status} label={o.status_label} /><StatusBadge value={o.payment_status} label={o.payment_status_label} /></div>
      </div>
      <div className="panel">
        <div className="row-between"><span>Placed {fmtDate(o.created_at)}</span><strong>{money(o.total_amount)}</strong></div>
        <p className="muted">Deliver to: {o.shipping_address} · {o.shipping_phone}</p>
        {o.can_cancel && <button className="btn btn-danger" onClick={cancel} disabled={busy}>Cancel order</button>}
      </div>

      <h2 className="section-title">Tracking</h2>
      <OrderTracker order={o} />

      {deliveredProducts.length > 0 && (
        <div className="panel"><strong>Enjoyed it? Leave a review:</strong>
          <div className="row" style={{ marginTop: 8 }}>{deliveredProducts.map((i) => <Link key={i.id} className="chip" to={`/products/${i.product}`}>{i.product_name}</Link>)}</div></div>
      )}
    </div>
  );
}
