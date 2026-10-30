import React, { useEffect, useState } from 'react';
import { farmsAPI } from '../api/services';
import FarmerNav from '../components/FarmerNav';
import { useToast } from '../context/ToastContext';
import { Spinner, StatusBadge } from '../components/ui';
import { formatApiError } from '../utils/errors';

const EMPTY = { farm_name: '', description: '', state: '', district: '', village: '', pincode: '', area_in_acres: '0' };

export default function FarmerProfile() {
  const toast = useToast();
  const [form, setForm] = useState(EMPTY);
  const [image, setImage] = useState(null);
  const [exists, setExists] = useState(false);
  const [kyc, setKyc] = useState('not_submitted');
  const [loading, setLoading] = useState(true);
  const [err, setErr] = useState('');

  useEffect(() => {
    farmsAPI.profile()
      .then((f) => { setForm({ ...EMPTY, ...f }); setExists(true); setKyc(f.kyc_status); })
      .catch(() => {}).finally(() => setLoading(false));
  }, []);

  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault(); setErr('');
    const fd = new FormData();
    Object.keys(EMPTY).forEach((k) => fd.append(k, form[k] ?? ''));
    if (image) fd.append('farm_image', image);
    try {
      const f = await farmsAPI.saveProfile(fd, exists);
      setExists(true); setKyc(f.kyc_status); toast('Farm profile saved');
    } catch (x) { setErr(formatApiError(x)); }
  };

  if (loading) return <div className="container"><Spinner /></div>;
  return (
    <div className="container">
      <FarmerNav />
      <h1 className="section-title" style={{ marginTop: 0 }}>Farm profile</h1>
      <p>KYC status: <StatusBadge value={kyc} /></p>
      <form className="panel" onSubmit={save}>
        <div className="form-group"><label htmlFor="fn">Farm name</label><input id="fn" required value={form.farm_name} onChange={set('farm_name')} /></div>
        <div className="form-group"><label htmlFor="fd">About your farm</label><textarea id="fd" rows={3} value={form.description} onChange={set('description')} /></div>
        <div className="two-col">
          <div className="form-group"><label htmlFor="fs">State</label><input id="fs" required value={form.state} onChange={set('state')} placeholder="e.g. Andhra Pradesh" /></div>
          <div className="form-group"><label htmlFor="fdi">District</label><input id="fdi" required value={form.district} onChange={set('district')} /></div>
          <div className="form-group"><label htmlFor="fv">Village / town</label><input id="fv" value={form.village} onChange={set('village')} /></div>
          <div className="form-group"><label htmlFor="fp">Pincode</label><input id="fp" value={form.pincode} onChange={set('pincode')} /></div>
          <div className="form-group"><label htmlFor="fa">Area (acres)</label><input id="fa" type="number" min="0" step="0.1" value={form.area_in_acres} onChange={set('area_in_acres')} /></div>
          <div className="form-group"><label htmlFor="fi">Farm photo (JPG/PNG, max 5 MB)</label><input id="fi" type="file" accept="image/png,image/jpeg" onChange={(e) => setImage(e.target.files[0])} /></div>
        </div>
        <p className="muted">The state is also used by the AI models as your region.</p>
        {err && <div className="alert alert-error" role="alert">{err}</div>}
        <button className="btn btn-secondary">{exists ? 'Save changes' : 'Create farm profile'}</button>
      </form>
    </div>
  );
}
