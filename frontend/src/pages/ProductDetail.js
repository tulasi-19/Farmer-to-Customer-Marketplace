import React, { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { cartAPI, productsAPI, reviewsAPI } from '../api/services';
import { useAuth } from '../context/AuthContext';
import { useToast } from '../context/ToastContext';
import useFetch from '../hooks/useFetch';
import { Empty, ErrorBox, Spinner, Thumb, money, fmtDate } from '../components/ui';
import { formatApiError } from '../utils/errors';

function Stars({ value, onChange }) {
  return (
    <div className="stars" role="radiogroup" aria-label="Rating">
      {[1, 2, 3, 4, 5].map((n) => (
        <button type="button" key={n} className={n <= value ? 'on' : ''} onClick={() => onChange(n)}
          role="radio" aria-checked={n === value} aria-label={`${n} star${n > 1 ? 's' : ''}`}>★</button>
      ))}
    </div>
  );
}

function Reviews({ productId, canWrite }) {
  const toast = useToast();
  const list = useFetch(() => reviewsAPI.list(productId), [productId]);
  const elig = useFetch(() => (canWrite ? reviewsAPI.eligibility(productId) : Promise.resolve(null)), [productId, canWrite]);
  const [rating, setRating] = useState(5);
  const [comment, setComment] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      await reviewsAPI.create({ product: productId, rating, comment });
      toast('Thanks for your review!'); setComment(''); list.reload(); elig.reload();
    } catch (err) { toast(formatApiError(err), 'error'); } finally { setBusy(false); }
  };

  return (
    <div className="panel">
      <h3 style={{ marginTop: 0 }}>Reviews</h3>
      {canWrite && elig.data && (elig.data.can_review ? (
        <form onSubmit={submit}>
          <Stars value={rating} onChange={setRating} />
          <label htmlFor="rev" className="muted">Your review (optional)</label>
          <textarea id="rev" rows={3} maxLength={1000} style={{ width: '100%' }} value={comment} onChange={(e) => setComment(e.target.value)} />
          <button className="btn btn-secondary" disabled={busy}>{busy ? 'Posting…' : 'Post review'}</button>
        </form>
      ) : <p className="muted">{elig.data.reason}</p>)}
      {list.loading && <Spinner />}
      {list.data?.results?.length === 0 && <Empty icon="⭐" title="No reviews yet" />}
      {(list.data?.results || []).map((r) => (
        <div className="review" key={r.id}>
          <strong>{r.username}</strong> {'★'.repeat(r.rating)}<span style={{ color: '#cfd8dc' }}>{'★'.repeat(5 - r.rating)}</span>
          <div>{r.comment}</div><div className="muted">{fmtDate(r.created_at)}</div>
        </div>
      ))}
    </div>
  );
}

export default function ProductDetail() {
  const { id } = useParams();
  const { user } = useAuth();
  const toast = useToast();
  const navigate = useNavigate();
  const { data: p, loading, error, reload } = useFetch(() => productsAPI.get(id), [id]);
  const [qty, setQty] = useState('1');
  const [busy, setBusy] = useState(false);

  if (loading) return <div className="container"><Spinner /></div>;
  if (error) return <div className="container"><ErrorBox message={error} onRetry={reload} /></div>;

  const add = async () => {
    if (!user) return navigate('/login');
    setBusy(true);
    try {
      await cartAPI.add(p.id, qty);
      window.dispatchEvent(new Event('cart:changed'));
      toast('Added to cart');
    } catch (err) { toast(formatApiError(err), 'error'); } finally { setBusy(false); }
  };

  return (
    <div className="container">
      <div className="two-col">
        <Thumb src={p.image} alt={p.name} className="detail-img" />
        <div>
          <h1 style={{ marginTop: 0 }}>{p.name}</h1>
          <div className="price" style={{ fontSize: 24 }}>{money(p.price)} <small>/ {p.unit}</small></div>
          <p>{p.description || 'No description provided.'}</p>
          <p className="muted">Category: {p.category_name} · Origin: {p.origin || p.farm_district}</p>
          <p>{p.average_rating ? `⭐ ${p.average_rating} (${p.review_count} reviews)` : 'No reviews yet'}</p>
          <p>Sold by <Link to={`/farms/${p.farm_id}`}><strong>{p.farm_name}</strong></Link> {p.farm_is_verified && <span className="verified">✔ Verified farmer</span>}<br />
            <span className="muted">📍 {p.farm_district}, {p.farm_state}</span></p>
          <p>{p.in_stock ? <strong>{p.quantity_available} {p.unit} in stock</strong> : <strong style={{ color: 'var(--danger)' }}>Out of stock</strong>}</p>
          {(!user || user.role === 'customer') && p.in_stock && (
            <div className="row">
              <label htmlFor="qty" className="muted">Quantity ({p.unit})</label>
              <input id="qty" type="number" min="0.5" step="0.5" max={p.quantity_available} value={qty} onChange={(e) => setQty(e.target.value)} style={{ width: 90, padding: 8 }} />
              <button className="btn btn-primary" onClick={add} disabled={busy}>{busy ? 'Adding…' : 'Add to cart'}</button>
            </div>
          )}
          {user && user.role !== 'customer' && <p className="muted">Log in with a customer account to buy.</p>}
        </div>
      </div>
      <Reviews productId={p.id} canWrite={user?.role === 'customer'} />
    </div>
  );
}
