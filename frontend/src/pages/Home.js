import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { productsAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import ProductCard from '../components/ProductCard';
import { ErrorBox, Spinner } from '../components/ui';

export default function Home() {
  const navigate = useNavigate();
  const [q, setQ] = useState('');
  const featured = useFetch(() => productsAPI.list({ ordering: '-avg_rating', available: 'true', page_size: 8 }), []);
  const cats = useFetch(() => productsAPI.categories(), []);

  const search = (e) => { e.preventDefault(); navigate(`/products?search=${encodeURIComponent(q)}`); };

  return (
    <>
      <section className="hero">
        <h1>Fresh from the farm, straight to you</h1>
        <p>Buy directly from verified farmers. Farmers get fair prices and AI-assisted demand and price insights.</p>
        <form onSubmit={search} role="search">
          <label htmlFor="home-search" className="sr-only" style={{ position: 'absolute', left: -9999 }}>Search products</label>
          <input id="home-search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search tomatoes, mangoes, rice…" />
          <button className="btn btn-primary" type="submit">Search</button>
        </form>
      </section>

      <div className="container">
        <h2 className="section-title">Shop by category</h2>
        <div className="chips">
          {(cats.data || []).map((c) => <Link key={c.id} className="chip" to={`/products?category=${c.slug}`}>{c.name}</Link>)}
        </div>

        <h2 className="section-title">Featured products</h2>
        {featured.loading && <Spinner />}
        <ErrorBox message={featured.error} onRetry={featured.reload} />
        <div className="grid">{(featured.data?.results || []).map((p) => <ProductCard key={p.id} product={p} />)}</div>

        <h2 className="section-title">Why FarmBridge AI</h2>
        <div className="benefits">
          <div className="benefit"><div className="ico">✅</div><strong>Verified farmers</strong><p className="muted">Every seller passes an admin-reviewed KYC check.</p></div>
          <div className="benefit"><div className="ico">🚚</div><strong>Track every order</strong><p className="muted">See each farmer’s shipment from confirmation to delivery.</p></div>
          <div className="benefit"><div className="ico">💵</div><strong>Pay on delivery</strong><p className="muted">No online payment needed. Pay cash when your order arrives.</p></div>
          <div className="benefit"><div className="ico">📈</div><strong>AI insights for farmers</strong><p className="muted">Demand forecasts and price suggestions (demo model).</p></div>
        </div>

        <div className="cta">
          <h2 style={{ marginTop: 0 }}>Are you a farmer?</h2>
          <p>List your produce, manage stock and receive orders directly.</p>
          <Link to="/register" className="btn btn-secondary">Join as a farmer</Link>
        </div>
      </div>
    </>
  );
}
