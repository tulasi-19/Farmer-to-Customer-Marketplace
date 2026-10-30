import React from 'react';
import { StatusBadge, fmtDate, money } from './ui';

const STEPS = [
  ['confirmed', 'Confirmed'], ['processing', 'Processing'], ['shipped', 'Shipped'],
  ['out_for_delivery', 'Out for delivery'], ['delivered', 'Delivered'],
];

/** Progress bar for ONE shipment. */
export function ShipmentProgress({ status }) {
  if (status === 'cancelled') return <div className="alert alert-error">This part of the order was cancelled.</div>;
  if (status === 'pending') return <div className="alert alert-warn">Waiting for payment.</div>;
  const idx = STEPS.findIndex(([s]) => s === status);
  return (
    <ol className="steps" aria-label="Delivery progress">
      {STEPS.map(([s, label], i) => (
        <li key={s} className={i < idx ? 'done' : i === idx ? 'current' : ''}>
          <span className="dot" />{label}
        </li>
      ))}
    </ol>
  );
}

export function EventList({ events }) {
  if (!events?.length) return null;
  return (
    <ul className="timeline">
      {[...events].reverse().map((e) => (
        <li key={e.id}><strong>{e.status_label}</strong> — {e.note || '—'}<div className="muted">{fmtDate(e.created_at)}</div></li>
      ))}
    </ul>
  );
}

/** Customer-facing tracking: one card per farmer shipment + the whole order timeline. */
export default function OrderTracker({ order }) {
  return (
    <div>
      {order.shipments.map((s) => (
        <div className="card card-body shipment" key={s.id}>
          <div className="row-between">
            <h4 style={{ margin: 0 }}>From {s.farm_name}</h4>
            <StatusBadge value={s.status} label={s.status_label} />
          </div>
          <ShipmentProgress status={s.status} />
          {(s.carrier || s.tracking_number) && (
            <p className="muted">Carrier: <strong>{s.carrier || '—'}</strong> · Tracking no: <strong>{s.tracking_number || '—'}</strong></p>
          )}
          <table>
            <tbody>
              {s.items.map((i) => (
                <tr key={i.id}><td>{i.product_name}</td><td>{i.quantity} {i.unit} × {money(i.unit_price)}</td><td>{money(i.line_total)}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <h4>Activity</h4>
      <EventList events={order.events} />
    </div>
  );
}
