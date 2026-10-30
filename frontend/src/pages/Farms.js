import React from 'react';
import { Link, useParams } from 'react-router-dom';
import { farmsAPI, productsAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import ProductCard from '../components/ProductCard';
import { Empty, ErrorBox, Spinner, Thumb } from '../components/ui';

export function FarmList() {
  const { data, loading, error, reload } = useFetch(() => farmsAPI.list({ page_size: 50 }), []);
  return (
    <div className="container">
      <h1 className="section-title">Verified farms</h1>
      {loading && <Spinner />}
      <ErrorBox message={error} onRetry={reload} />
      {data?.results?.length === 0 && <Empty title="No verified farms yet" />}
      <div className="grid">
        {(data?.results || []).map((f) => (
          <Link key={f.id} to={`/farms/${f.id}`} className="card">
            <Thumb src={f.farm_image} alt={f.farm_name} />
            <div className="card-body"><h3>{f.farm_name}</h3>
              <div className="farm-tag">📍 {f.district}, {f.state}</div>
              <div className="farm-tag">{f.product_count} products <span className="verified">✔ Verified</span></div></div>
          </Link>
        ))}
      </div>
    </div>
  );
}

export function FarmProfile() {
  const { id } = useParams();
  const farm = useFetch(() => farmsAPI.get(id), [id]);
  const products = useFetch(() => productsAPI.list({ farm: id, page_size: 50 }), [id]);
  if (farm.loading) return <div className="container"><Spinner /></div>;
  if (farm.error) return <div className="container"><ErrorBox message="This farm was not found or is not verified yet." /></div>;
  const f = farm.data;
  return (
    <div className="container">
      <div className="two-col">
        <Thumb src={f.farm_image} alt={f.farm_name} className="detail-img" />
        <div>
          <h1 style={{ marginTop: 0 }}>{f.farm_name} <span className="verified" style={{ fontSize: 16 }}>✔ Verified</span></h1>
          <p>{f.description || 'This farm has not added a description yet.'}</p>
          <p className="muted">📍 {[f.village, f.district, f.state].filter(Boolean).join(', ')}<br />Joined {new Date(f.created_at).toLocaleDateString('en-IN')}</p>
        </div>
      </div>
      <h2 className="section-title">Products from this farm</h2>
      {products.data?.results?.length === 0 && <Empty title="No products listed right now" />}
      <div className="grid">{(products.data?.results || []).map((p) => <ProductCard key={p.id} product={p} />)}</div>
    </div>
  );
}
