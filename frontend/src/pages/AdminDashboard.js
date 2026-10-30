import React, { useState } from 'react';
import { adminAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import { ErrorBox, Spinner, money } from '../components/ui';
import AdminKYC from './admin/AdminKYC';
import AdminUsers from './admin/AdminUsers';
import AdminProducts from './admin/AdminProducts';
import AdminOrders from './admin/AdminOrders';
import AdminReviews from './admin/AdminReviews';

const TABS = [['overview', 'Overview'], ['kyc', 'KYC applications'], ['users', 'Users'], ['products', 'Products'], ['orders', 'Orders'], ['reviews', 'Reviews']];

function Overview() {
  const { data: s, loading, error, reload } = useFetch(() => adminAPI.stats(), []);
  if (loading) return <Spinner />;
  if (error) return <ErrorBox message={error} onRetry={reload} />;
  const u = s.users;
  return (
    <div className="stats">
      <div className="stat"><div className="num">{(u.customer || 0) + (u.farmer || 0) + (u.admin || 0)}</div><div className="lbl">Users ({u.farmer || 0} farmers, {u.customer || 0} customers)</div></div>
      <div className="stat"><div className="num">{s.products.active}/{s.products.total}</div><div className="lbl">Active / total products</div></div>
      <div className="stat"><div className="num">{s.orders.total}</div><div className="lbl">Orders</div></div>
      <div className="stat"><div className="num">{money(s.cash_collected)}</div><div className="lbl">Cash collected (COD)</div></div>
      <div className="stat"><div className="num" style={{ color: s.kyc_pending ? 'var(--danger)' : undefined }}>{s.kyc_pending}</div><div className="lbl">KYC awaiting review</div></div>
      <div className="stat"><div className="num">{s.reviews.total}</div><div className="lbl">Reviews ({s.reviews.hidden} hidden)</div></div>
      <div className="panel" style={{ gridColumn: '1 / -1' }}><strong>Orders by status</strong>
        <div className="row" style={{ marginTop: 8 }}>{Object.entries(s.orders.by_status).map(([k, v]) => <span className="chip" key={k}>{k.replace(/_/g, ' ')}: {v}</span>)}</div></div>
    </div>
  );
}

export default function AdminDashboard() {
  const [tab, setTab] = useState('overview');
  return (
    <div className="container">
      <h1 className="section-title" style={{ marginTop: 0 }}>Admin dashboard</h1>
      <div className="tabs" role="tablist">{TABS.map(([k, l]) => <button key={k} role="tab" aria-selected={tab === k} className={tab === k ? 'active' : ''} onClick={() => setTab(k)}>{l}</button>)}</div>
      {tab === 'overview' && <Overview />}
      {tab === 'kyc' && <AdminKYC />}
      {tab === 'users' && <AdminUsers />}
      {tab === 'products' && <AdminProducts />}
      {tab === 'orders' && <AdminOrders />}
      {tab === 'reviews' && <AdminReviews />}
    </div>
  );
}
