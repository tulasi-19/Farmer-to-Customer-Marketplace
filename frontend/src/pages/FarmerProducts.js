import React, { useState } from 'react';
import { productsAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import FarmerNav from '../components/FarmerNav';
import { KycBanner } from './FarmerDashboard';
import { useToast } from '../context/ToastContext';
import { Empty, ErrorBox, Pagination, Spinner, StatusBadge, Thumb, money } from '../components/ui';
import { formatApiError } from '../utils/errors';
import { farmsAPI } from '../api/services';

const EMPTY = { name: '', category: '', price: '', quantity_available: '', unit: 'kg', origin: '', description: '', is_active: true };

export default function FarmerProducts() {
  const toast = useToast();
  const [page, setPage] = useState(1);
  const list = useFetch(() => productsAPI.mine({ page }), [page]);
  const cats = useFetch(() => productsAPI.categories(), []);
  const farm = useFetch(() => farmsAPI.profile().catch(() => null), []);
  const [editing, setEditing] = useState(null);        // null | 'new' | product
  const [form, setForm] = useState(EMPTY);
  const [image, setImage] = useState(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const approved = farm.data?.kyc_status === 'approved';

  const open = (p) => {
    setErr(''); setImage(null);
    if (p === 'new') { setForm({ ...EMPTY, category: cats.data?.[0]?.id || '' }); }
    else setForm({ name: p.name, category: p.category, price: p.price, quantity_available: p.quantity_available, unit: p.unit, origin: p.origin, description: p.description, is_active: p.is_active });
    setEditing(p);
  };
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.type === 'checkbox' ? e.target.checked : e.target.value });

  const save = async (e) => {
    e.preventDefault(); setErr(''); setBusy(true);
    try {
      if (editing === 'new') {
        const fd = new FormData();
        Object.entries(form).forEach(([k, v]) => fd.append(k, v));
        if (image) fd.append('image', image);
        await productsAPI.create(fd);
      } else {
        const fd = new FormData();
        Object.entries(form).forEach(([k, v]) => fd.append(k, v));
        if (image) fd.append('image', image);
        await productsAPI.update(editing.id, fd);
      }
      toast('Product saved'); setEditing(null); list.reload();
    } catch (x) { setErr(formatApiError(x)); } finally { setBusy(false); }
  };

  const remove = async (p) => {
    if (!window.confirm(`Delete "${p.name}"?`)) return;
    try { const r = await productsAPI.remove(p.id); toast(r?.detail || 'Deleted'); list.reload(); }
    catch (x) { toast(formatApiError(x), 'error'); }
  };
  const quickStock = async (p) => {
    const v = window.prompt(`New stock for ${p.name} (${p.unit}):`, p.quantity_available);
    if (v === null) return;
    try { await productsAPI.update(p.id, { quantity_available: v }); toast('Stock updated'); list.reload(); }
    catch (x) { toast(formatApiError(x), 'error'); }
  };

  return (
    <div className="container">
      <FarmerNav />
      <div className="row-between"><h1 className="section-title" style={{ marginTop: 0 }}>My products</h1>
        <button className="btn btn-secondary" disabled={!approved} onClick={() => open('new')}>+ Add product</button></div>
      {farm.data && <KycBanner status={farm.data.kyc_status} />}

      {editing && (
        <form className="panel" onSubmit={save}>
          <h3 style={{ marginTop: 0 }}>{editing === 'new' ? 'Add product' : `Edit ${editing.name}`}</h3>
          <div className="two-col">
            <div className="form-group"><label htmlFor="pn">Name</label><input id="pn" required value={form.name} onChange={set('name')} /></div>
            <div className="form-group"><label htmlFor="pc">Category</label>
              <select id="pc" required value={form.category} onChange={set('category')}><option value="">Select…</option>{(cats.data || []).map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}</select></div>
            <div className="form-group"><label htmlFor="pp">Price per unit (₹)</label><input id="pp" type="number" required min="0.01" step="0.01" value={form.price} onChange={set('price')} /></div>
            <div className="form-group"><label htmlFor="pq">Stock quantity</label><input id="pq" type="number" required min="0" step="0.01" value={form.quantity_available} onChange={set('quantity_available')} /></div>
            <div className="form-group"><label htmlFor="pu">Unit</label>
              <select id="pu" value={form.unit} onChange={set('unit')}>{['kg', 'quintal', 'gram', 'dozen', 'litre', 'piece'].map((u) => <option key={u}>{u}</option>)}</select>
              <div className="muted">AI insights work for kg and quintal only.</div></div>
            <div className="form-group"><label htmlFor="po">Origin (village / plot)</label><input id="po" value={form.origin} onChange={set('origin')} /></div>
          </div>
          <div className="form-group"><label htmlFor="pd">Description</label><textarea id="pd" rows={3} value={form.description} onChange={set('description')} /></div>
          <div className="form-group"><label htmlFor="pi">Image (JPG/PNG, max 5 MB)</label><input id="pi" type="file" accept="image/png,image/jpeg" onChange={(e) => setImage(e.target.files[0])} /></div>
          <label className="row"><input type="checkbox" checked={form.is_active} onChange={set('is_active')} /> Visible to customers</label>
          {err && <div className="alert alert-error" role="alert">{err}</div>}
          <div className="row" style={{ marginTop: 10 }}>
            <button className="btn btn-secondary" disabled={busy}>{busy ? 'Saving…' : 'Save'}</button>
            <button type="button" className="btn btn-outline" style={{ color: 'var(--text)', borderColor: 'var(--border)' }} onClick={() => setEditing(null)}>Cancel</button>
          </div>
        </form>
      )}

      {list.loading && <Spinner />}
      <ErrorBox message={list.error} onRetry={list.reload} />
      {list.data?.results?.length === 0 && <Empty title="No products yet">{approved ? 'Add your first product.' : 'Get KYC-approved to start listing.'}</Empty>}
      {list.data?.results?.length > 0 && (
        <div className="table-wrap"><table>
          <thead><tr><th></th><th>Product</th><th>Price</th><th>Stock</th><th>Status</th><th></th></tr></thead>
          <tbody>{list.data.results.map((p) => (
            <tr key={p.id}>
              <td style={{ width: 64 }}><Thumb src={p.image} alt={p.name} /></td>
              <td><strong>{p.name}</strong><div className="muted">{p.category_name}</div></td>
              <td>{money(p.price)} / {p.unit}</td>
              <td style={{ color: Number(p.quantity_available) < 10 ? 'var(--danger)' : undefined }}>{p.quantity_available} {p.unit}</td>
              <td><StatusBadge value={p.is_active ? 'published' : 'hidden'} label={p.is_active ? 'Visible' : 'Hidden'} /></td>
              <td className="row"><button className="btn btn-secondary btn-sm" onClick={() => quickStock(p)}>Stock</button>
                <button className="btn btn-secondary btn-sm" onClick={() => open(p)}>Edit</button>
                <button className="btn btn-danger btn-sm" onClick={() => remove(p)}>Delete</button></td>
            </tr>))}</tbody></table></div>
      )}
      <Pagination data={list.data} page={page} setPage={setPage} />
    </div>
  );
}
