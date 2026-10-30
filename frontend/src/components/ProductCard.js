import React from 'react';
import { Link } from 'react-router-dom';
import { Thumb, money } from './ui';

export default function ProductCard({ product: p }) {
  return (
    <Link to={`/products/${p.id}`} className="card" aria-label={`View ${p.name}`}>
      <Thumb src={p.image} alt={p.name} />
      <div className="card-body">
        <h3>{p.name}</h3>
        <div className="price">{money(p.price)} <small>/ {p.unit}</small></div>
        <div className="farm-tag">🌱 {p.farm_name} {p.farm_is_verified && <span className="verified">✔ Verified</span>}</div>
        <div className="farm-tag">📍 {p.farm_district}, {p.farm_state}</div>
        <div className="farm-tag">
          {p.average_rating ? `⭐ ${p.average_rating} (${p.review_count})` : 'No reviews yet'}
          {' · '}{p.in_stock ? `${p.quantity_available} ${p.unit} left` : <span style={{ color: 'var(--danger)' }}>Out of stock</span>}
        </div>
      </div>
    </Link>
  );
}
