import React from 'react';
import { Link } from 'react-router-dom';
import { farmerAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import FarmerNav from '../components/FarmerNav';
import { ErrorBox, Spinner, money } from '../components/ui';

export function KycBanner({ status }) {
  if (status === 'approved') return null;
  const text = {
    not_submitted: ['alert-warn', 'Complete your farm profile and submit KYC to start selling.', '/farmer/kyc', 'Submit KYC'],
    pending: ['alert-warn', 'Your KYC is under review. You will be able to list products once an admin approves it.', '/farmer/kyc', 'View status'],
    rejected: ['alert-error', 'Your KYC was rejected. Please check the reason and resubmit.', '/farmer/kyc', 'See reason & resubmit'],
  }[status] || [];
  return <div className={`alert ${text[0]} row-between`}><span>{text[1]}</span><Link className="btn btn-secondary btn-sm" to={text[2]}>{text[3]}</Link></div>;
}

export default function FarmerDashboard() {
  const { data: d, loading, error, reload } = useFetch(() => farmerAPI.dashboard(), []);
  const max = d ? Math.max(1, ...d.monthly_sales.map((m) => Number(m.total))) : 1;

  return (
    <div className="container">
      <FarmerNav />
      <h1 className="section-title" style={{ marginTop: 0 }}>Farmer dashboard</h1>
      {loading && <Spinner />}
      {error && <div className="alert alert-warn">{error} — <Link to="/farmer/profile">create your farm profile</Link> first.</div>}
      <ErrorBox message="" onRetry={reload} />
      {d && <>
        <KycBanner status={d.kyc_status} />
        <div className="stats">
          <div className="stat"><div className="num">{money(d.total_sales)}</div><div className="lbl">Total sales (confirmed orders)</div></div>
          <div className="stat"><div className="num">{money(d.delivered_sales)}</div><div className="lbl">Delivered sales</div></div>
          <div className="stat"><div className="num">{d.to_fulfil}</div><div className="lbl">Orders to fulfil</div></div>
          <div className="stat"><div className="num">{d.products.active}/{d.products.total}</div><div className="lbl">Active / total products</div></div>
          <div className="stat"><div className="num" style={{ color: d.products.low_stock + d.products.out_of_stock ? 'var(--danger)' : undefined }}>{d.products.low_stock + d.products.out_of_stock}</div>
            <div className="lbl">Low / out of stock (&lt; {d.products.low_stock_threshold})</div></div>
        </div>

        <div className="two-col">
          <div className="panel"><h3 style={{ marginTop: 0 }}>Sales, last 6 months</h3>
            <div className="bars">
              {d.monthly_sales.map((m) => (
                <div className="bar-col" key={m.month} title={`${m.orders} orders`}>
                  <span>{Number(m.total) ? `₹${Math.round(Number(m.total))}` : ''}</span>
                  <div className="bar" style={{ height: `${(Number(m.total) / max) * 100}%` }} />
                  <span>{m.month.slice(5)}/{m.month.slice(2, 4)}</span>
                </div>
              ))}
            </div></div>
          <div className="panel"><h3 style={{ marginTop: 0 }}>Top products</h3>
            {d.top_products.length === 0 ? <p className="muted">No sales yet.</p> : (
              <table><tbody>{d.top_products.map((t) => <tr key={t.name}><td>{t.name}</td><td>{t.units} {t.unit}</td><td>{money(t.revenue)}</td></tr>)}</tbody></table>)}
          </div>
        </div>
        <div className="panel"><h3 style={{ marginTop: 0 }}>Shipments by status</h3>
          <div className="row">{Object.keys(d.shipments_by_status).length === 0 ? <span className="muted">No orders yet.</span>
            : Object.entries(d.shipments_by_status).map(([k, v]) => <span key={k} className="chip">{k.replace(/_/g, ' ')}: {v}</span>)}</div>
          <p><Link to="/farmer/orders">Manage orders →</Link></p></div>
      </>}
    </div>
  );
}
