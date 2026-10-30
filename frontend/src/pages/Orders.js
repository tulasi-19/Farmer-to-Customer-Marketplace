import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ordersAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import { Empty, ErrorBox, Pagination, Spinner, StatusBadge, fmtDate, money } from '../components/ui';

export default function Orders() {
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch(() => ordersAPI.list({ page }), [page]);
  return (
    <div className="container">
      <h1 className="section-title">My orders</h1>
      {loading && <Spinner />}
      <ErrorBox message={error} onRetry={reload} />
      {data?.results?.length === 0 && <Empty icon="📦" title="No orders yet"><Link to="/products">Start shopping</Link></Empty>}
      <div className="table-wrap">
        {data?.results?.length > 0 && (
          <table>
            <thead><tr><th>Order</th><th>Placed</th><th>Total</th><th>Delivery</th><th>Payment</th><th></th></tr></thead>
            <tbody>
              {data.results.map((o) => (
                <tr key={o.id}>
                  <td>#{o.id}</td><td>{fmtDate(o.created_at)}</td><td>{money(o.total_amount)}</td>
                  <td><StatusBadge value={o.status} label={o.status_label} /></td>
                  <td><StatusBadge value={o.payment_status} label={o.payment_status_label} /></td>
                  <td><Link className="btn btn-secondary btn-sm" to={`/orders/${o.id}`}>Track</Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <Pagination data={data} page={page} setPage={setPage} />
    </div>
  );
}
