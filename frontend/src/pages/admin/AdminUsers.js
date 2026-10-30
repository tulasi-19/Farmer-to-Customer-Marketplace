import React, { useState } from 'react';
import { adminAPI } from '../../api/services';
import useFetch from '../../hooks/useFetch';
import { useToast } from '../../context/ToastContext';
import { useAuth } from '../../context/AuthContext';
import { ErrorBox, Pagination, Spinner, StatusBadge, fmtDate } from '../../components/ui';
import { formatApiError } from '../../utils/errors';

export default function AdminUsers() {
  const toast = useToast();
  const { user: me } = useAuth();
  const [role, setRole] = useState('');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);
  const { data, loading, error, reload } = useFetch(() => adminAPI.users({ page, ...(role ? { role } : {}), ...(search ? { search } : {}) }), [page, role, search]);

  const toggle = async (u) => {
    try { await adminAPI.setUserActive(u.id, !u.is_active); toast(u.is_active ? 'User suspended' : 'User re-activated'); reload(); }
    catch (x) { toast(formatApiError(x), 'error'); }
  };
  return (
    <>
      <div className="filters">
        <input aria-label="Search users" placeholder="Search username / email" value={search} onChange={(e) => { setSearch(e.target.value); setPage(1); }} />
        <select aria-label="Role" value={role} onChange={(e) => { setRole(e.target.value); setPage(1); }}><option value="">All roles</option><option value="customer">Customers</option><option value="farmer">Farmers</option><option value="admin">Admins</option></select>
      </div>
      {loading && <Spinner />}<ErrorBox message={error} onRetry={reload} />
      <div className="table-wrap"><table><thead><tr><th>User</th><th>Email</th><th>Role</th><th>Joined</th><th>Status</th><th></th></tr></thead>
        <tbody>{(data?.results || []).map((u) => (
          <tr key={u.id}><td>{u.username}</td><td>{u.email}</td><td>{u.role}</td><td>{fmtDate(u.created_at)}</td>
            <td><StatusBadge value={u.is_active ? 'published' : 'hidden'} label={u.is_active ? 'Active' : 'Suspended'} /></td>
            <td>{u.id !== me.id && <button className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-secondary'}`} onClick={() => toggle(u)}>{u.is_active ? 'Suspend' : 'Activate'}</button>}</td></tr>))}</tbody></table></div>
      <Pagination data={data} page={page} setPage={setPage} />
    </>
  );
}
