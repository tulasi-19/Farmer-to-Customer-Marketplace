import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { productsAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import ProductCard from '../components/ProductCard';
import { Empty, ErrorBox, Pagination, Spinner } from '../components/ui';

export default function Products() {
  const [params, setParams] = useSearchParams();
  const [page, setPage] = useState(1);
  const [form, setForm] = useState({
    search: params.get('search') || '', category: params.get('category') || '',
    min_price: '', max_price: '', available: false, ordering: '-created_at',
  });
  const cats = useFetch(() => productsAPI.categories(), []);

  const query = { page, ordering: form.ordering };
  ['search', 'category', 'min_price', 'max_price'].forEach((k) => { if (form[k]) query[k] = form[k]; });
  if (form.available) query.available = 'true';
  const key = JSON.stringify(query);
  const { data, loading, error, reload } = useFetch(() => productsAPI.list(query), [key]);

  useEffect(() => { setPage(1); }, [form]);
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });
  const clear = () => { setForm({ search: '', category: '', min_price: '', max_price: '', available: false, ordering: '-created_at' }); setParams({}); };

  return (
    <div className="container">
      <h1 className="section-title">Products</h1>
      <div className="filters" role="search">
        <input aria-label="Search" placeholder="Search products…" value={form.search} onChange={set('search')} />
        <select aria-label="Category" value={form.category} onChange={set('category')}>
          <option value="">All categories</option>
          {(cats.data || []).map((c) => <option key={c.id} value={c.slug}>{c.name}</option>)}
        </select>
        <input aria-label="Minimum price" type="number" min="0" placeholder="Min ₹" value={form.min_price} onChange={set('min_price')} style={{ width: 100 }} />
        <input aria-label="Maximum price" type="number" min="0" placeholder="Max ₹" value={form.max_price} onChange={set('max_price')} style={{ width: 100 }} />
        <select aria-label="Sort by" value={form.ordering} onChange={set('ordering')}>
          <option value="-created_at">Newest</option><option value="price">Price: low to high</option>
          <option value="-price">Price: high to low</option><option value="-avg_rating">Top rated</option><option value="name">Name</option>
        </select>
        <label className="row"><input type="checkbox" checked={form.available} onChange={set('available')} /> In stock only</label>
        <button className="btn btn-secondary btn-sm" onClick={clear}>Clear</button>
      </div>
      {loading && <Spinner />}
      <ErrorBox message={error} onRetry={reload} />
      {!loading && !error && data?.results?.length === 0 && <Empty title="No products found">Try different filters.</Empty>}
      <div className="grid">{(data?.results || []).map((p) => <ProductCard key={p.id} product={p} />)}</div>
      <Pagination data={data} page={page} setPage={setPage} />
    </div>
  );
}
