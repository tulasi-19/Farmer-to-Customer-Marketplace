import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { cartAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import { useToast } from '../context/ToastContext';
import { Empty, ErrorBox, Spinner, Thumb, money } from '../components/ui';
import { formatApiError } from '../utils/errors';

export default function Cart() {
  const { data: cart, loading, error, reload, setData } = useFetch(() => cartAPI.get(), []);
  const toast = useToast();
  const navigate = useNavigate();
  const [qty, setQty] = useState({});

  const apply = async (fn) => {
    try { setData(await fn()); window.dispatchEvent(new Event('cart:changed')); }
    catch (err) { toast(formatApiError(err), 'error'); reload(); }
  };

  if (loading) return <div className="container"><Spinner /></div>;
  if (error) return <div className="container"><ErrorBox message={error} onRetry={reload} /></div>;
  if (!cart.items.length) return <div className="container"><Empty icon="🛒" title="Your cart is empty"><Link to="/products">Browse products</Link></Empty></div>;

  return (
    <div className="container">
      <h1 className="section-title">Shopping cart</h1>
      <div className="table-wrap">
        <table>
          <thead><tr><th></th><th>Product</th><th>Price</th><th>Quantity</th><th>Total</th><th></th></tr></thead>
          <tbody>
            {cart.items.map((i) => (
              <tr key={i.id}>
                <td style={{ width: 70 }}><Thumb src={i.image} alt={i.product_name} className="cart-thumb" /></td>
                <td><strong>{i.product_name}</strong><div className="muted">{i.farm_name}</div>
                  {i.issue && <div className="error-text">{i.issue}</div>}</td>
                <td>{money(i.unit_price)} / {i.unit}</td>
                <td>
                  <input aria-label={`Quantity of ${i.product_name}`} type="number" min="0.5" step="0.5" style={{ width: 80, padding: 6 }}
                    value={qty[i.id] ?? i.quantity} onChange={(e) => setQty({ ...qty, [i.id]: e.target.value })}
                    onBlur={() => qty[i.id] && qty[i.id] !== i.quantity && apply(() => cartAPI.update(i.id, qty[i.id]))} /> {i.unit}
                </td>
                <td>{money(i.line_total)}</td>
                <td><button className="btn btn-danger btn-sm" onClick={() => apply(() => cartAPI.remove(i.id))} aria-label={`Remove ${i.product_name}`}>Remove</button></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="panel row-between">
        <div><div className="muted">Subtotal (prices are confirmed again at checkout)</div><div className="num" style={{ fontSize: 26, fontWeight: 700 }}>{money(cart.subtotal)}</div></div>
        <div className="row">
          <button className="btn btn-secondary" onClick={() => apply(() => cartAPI.clear())}>Clear cart</button>
          <button className="btn btn-primary" disabled={cart.has_issues} onClick={() => navigate('/checkout')}>Proceed to checkout</button>
        </div>
      </div>
      {cart.has_issues && <div className="alert alert-warn">Fix the highlighted items before checking out.</div>}
    </div>
  );
}
