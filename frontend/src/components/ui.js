import React from 'react';

export const Spinner = ({ text = 'Loading…' }) => <div className="center-note" aria-busy="true">{text}</div>;
export const ErrorBox = ({ message, onRetry }) => message ? (
  <div className="alert alert-error" role="alert">
    {message} {onRetry && <button className="link-btn" onClick={onRetry}>Retry</button>}
  </div>
) : null;
export const Empty = ({ icon = '🌱', title, children }) => (
  <div className="empty"><div className="empty-icon">{icon}</div><strong>{title}</strong><div>{children}</div></div>
);

export const money = (v) => `₹${Number(v || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
export const fmtDate = (d) => d ? new Date(d).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' }) : '—';

const GOOD = ['delivered', 'approved', 'published', 'cod_paid', 'confirmed'];
const BAD = ['cancelled', 'rejected', 'hidden'];
export function StatusBadge({ value, label }) {
  const cls = GOOD.includes(value) ? '' : BAD.includes(value) ? 'badge-rejected' : 'badge-pending';
  return <span className={`badge-status ${cls}`}>{label || String(value || '').replace(/_/g, ' ')}</span>;
}

export function Pagination({ data, page, setPage }) {
  if (!data || (!data.next && !data.previous)) return null;
  return (
    <div className="pagination">
      <button className="btn btn-secondary" disabled={!data.previous} onClick={() => setPage(page - 1)}>← Previous</button>
      <span>Page {page}</span>
      <button className="btn btn-secondary" disabled={!data.next} onClick={() => setPage(page + 1)}>Next →</button>
    </div>
  );
}

export function Field({ label, id, children, error }) {
  return (
    <div className="form-group">
      <label htmlFor={id}>{label}</label>
      {children}
      {error && <div className="error-text">{error}</div>}
    </div>
  );
}

export const productImage = (p) => p.image || null;
export function Thumb({ src, alt, className = '' }) {
  return src
    ? <img src={src} alt={alt} className={className} loading="lazy" />
    : <div className={`img-fallback ${className}`} aria-label={alt} role="img">🌿</div>;
}
