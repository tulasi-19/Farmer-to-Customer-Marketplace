import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { cartAPI, ordersAPI } from '../api/services';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import useFetch from '../hooks/useFetch';
import { Empty, ErrorBox, Spinner, money } from '../components/ui';
import { formatApiError } from '../utils/errors';

export default function Checkout() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const { data: cart, loading, error, reload } = useFetch(() => cartAPI.get(), []);
  const [form, setForm] = useState({ shipping_address: user?.address || '', shipping_phone: user?.phone || '' });
  const [busy, setBusy] = useState(false);
  const [formError, setFormError] = useState('');
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });

  if (loading) return <div className="container"><Spinner /></div>;
  if (error) return <div className="container"><ErrorBox message={error} onRetry={reload} /></div>;
  if (!cart.items.length) return <div className="container"><Empty icon="🛒" title="Nothing to check out"><Link to="/products">Browse products</Link></Empty></div>;

  const placeOrder = async (e) => {
    e.preventDefault(); setBusy(true); setFormError('');
    try {
      // The server builds the order from the SERVER-side cart and recalculates every price.
      const order = await ordersAPI.checkout(form);
      window.dispatchEvent(new Event('cart:changed'));
      toast('Order placed! Pay cash on delivery.');
      navigate(`/orders/${order.id}`);
    } catch (err) {
      setFormError(formatApiError(err, 'Could not place the order.'));
      setBusy(false);
    }
  };

  return (
    <div className="container">
      <h1 className="section-title">Checkout</h1>
      <div className="two-col">
        <form className="panel" onSubmit={placeOrder}>
          <div className="form-group"><label htmlFor="addr">Delivery address</label>
            <textarea id="addr" rows={3} required minLength={10} value={form.shipping_address} onChange={set('shipping_address')} /></div>
          <div className="form-group"><label htmlFor="ph">Phone</label>
            <input id="ph" required value={form.shipping_phone} onChange={set('shipping_phone')} /></div>
          <div className="alert alert-ok">💵 <strong>Cash on delivery</strong> — pay when your order arrives.</div>
          {formError && <div className="alert alert-error" role="alert">{formError}</div>}
          <button className="btn btn-primary" disabled={busy || cart.has_issues} style={{ width: '100%', marginTop: 12 }}>
            {busy ? 'Placing order…' : `Place order · ${money(cart.subtotal)}`}
          </button>
          {cart.has_issues && <div className="alert alert-warn">Some cart items have problems — <Link to="/cart">review your cart</Link>.</div>}
        </form>
        <div className="panel">
          <h3 style={{ marginTop: 0 }}>Order summary</h3>
          {cart.items.map((i) => (
            <div className="row-between" key={i.id}><span>{i.product_name} × {i.quantity} {i.unit}</span><span>{money(i.line_total)}</span></div>
          ))}
          <hr />
          <div className="row-between"><strong>Total</strong><strong>{money(cart.subtotal)}</strong></div>
          <p className="muted">Items from different farms ship separately and can be tracked individually.</p>
        </div>
      </div>
    </div>
  );
}
