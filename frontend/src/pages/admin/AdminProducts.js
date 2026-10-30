import React, { useState } from 'react';
import { adminAPI } from '../../api/services';
import useFetch from '../../hooks/useFetch';
import { useToast } from '../../context/ToastContext';
import { ErrorBox, Pagination, Spinner, StatusBadge, money } from '../../components/ui';
import { formatApiError } from '../../utils/errors';

export default function AdminProducts() {
  const toast = useToast();
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch(() => adminAPI.products({ page, ...(search ? { search } : {}) }), [page, search]);
  const toggle = async (p) => {
    try { await adminAPI.setProductActive(p.id, !p.is_active); toast(p.is_active ? 'Product hidden' : 'Product visible'); reload(); }
    catch (x) { toast(formatApiError(x), 'error'); }
  };
  return (
    <>
      <div className="filters"><input aria-label="Search products" placeholder="Search product / farm" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} /></div>
      {loading && <Spinner />}<ErrorBox message={error} onRetry={reload} />
      <div className="table-wrap"><table><thead><tr><th>Product</th><th>Farm</th><th>Price</th><th>Stock</th><th>Visibility</th><th></th></tr></thead>
        <tbody>{(data?.results || []).map((p) => (
          <tr key={p.id}><td>{p.name}</td><td>{p.farm_name}</td><td>{money(p.price)} / {p.unit}</td><td>{p.quantity_available}</td>
            <td><StatusBadge value={p.is_active ? 'published' : 'hidden'} label={p.is_active ? 'Visible' : 'Hidden'} /></td>
            <td><button className="btn btn-secondary btn-sm" onClick={() => toggle(p)}>{p.is_active ? 'Hide' : 'Unhide'}</button></td></tr>))}</tbody></table></div>
      <Pagination data={data} page={page} setPage={setPage} />
    </>
  );
}
