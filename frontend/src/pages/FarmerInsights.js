import React, { useState } from 'react';
import { aiAPI, productsAPI } from '../api/services';
import useFetch from '../hooks/useFetch';
import FarmerNav from '../components/FarmerNav';
import { useToast } from '../context/ToastContext';
import { ErrorBox, Spinner, money } from '../components/ui';
import { formatApiError } from '../utils/errors';

function Meta({ r }) {
  return (
    <>
      {r.warnings.length > 0 && <div className="alert alert-warn"><strong>Reliability: low.</strong><ul style={{ margin: '4px 0 0 18px' }}>{r.warnings.map((w) => <li key={w}>{w}</li>)}</ul></div>}
      <p className="muted">{r.disclaimer}<br />Model v{r.model.version} · trained {new Date(r.model.trained_at).toLocaleDateString('en-IN')} · data: <strong>{r.model.data_source}</strong> · test R² {r.model.metrics.r2.toFixed(2)}</p>
    </>
  );
}

export default function FarmerInsights() {
  const toast = useToast();
  const products = useFetch(() => productsAPI.mine({ page_size: 50 }), []);
  const info = useFetch(() => aiAPI.info(), []);
  const [pid, setPid] = useState('');
  const [supply, setSupply] = useState('1.0');
  const [grade, setGrade] = useState('B');
  const [market, setMarket] = useState('');
  const [demand, setDemand] = useState(null);
  const [price, setPrice] = useState(null);
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState('');

  const run = async (kind) => {
    if (!pid) { setErr('Choose a product first.'); return; }
    setErr(''); setBusy(kind);
    try {
      if (kind === 'demand') setDemand(await aiAPI.demand({ product_id: Number(pid), supply_index: Number(supply) }));
      else setPrice(await aiAPI.price({ product_id: Number(pid), supply_index: Number(supply), grade, ...(market ? { market_price_per_kg: Number(market) } : {}) }));
    } catch (x) { setErr(formatApiError(x)); } finally { setBusy(''); }
  };

  const apply = async () => {
    if (!window.confirm(`Change the listing price to ${money(price.recommended_price)} per ${price.unit}? This is only an estimate.`)) return;
    try { await productsAPI.update(price.product.id, { price: price.recommended_price.toFixed(2) }); toast('Listing price updated'); }
    catch (x) { toast(formatApiError(x), 'error'); }
  };

  return (
    <div className="container">
      <FarmerNav />
      <h1 className="section-title" style={{ marginTop: 0 }}>AI insights</h1>
      <div className="alert alert-warn"><strong>Demonstration models.</strong> They are trained on synthetic data generated for this project, so use them to see how the feature works, not for real pricing decisions.</div>
      {products.loading && <Spinner />}
      <ErrorBox message={products.error} />
      <div className="panel">
        <div className="two-col">
          <div className="form-group"><label htmlFor="ap">Product</label>
            <select id="ap" value={pid} onChange={(e) => { setPid(e.target.value); setDemand(null); setPrice(null); }}>
              <option value="">Select a product…</option>{(products.data?.results || []).map((p) => <option key={p.id} value={p.id}>{p.name} ({p.unit})</option>)}</select></div>
          <div className="form-group"><label htmlFor="as">Local supply level (0.6 scarce – 1.5 plentiful)</label><input id="as" type="number" min="0.1" max="5" step="0.1" value={supply} onChange={(e) => setSupply(e.target.value)} /></div>
          <div className="form-group"><label htmlFor="ag">Quality grade</label><select id="ag" value={grade} onChange={(e) => setGrade(e.target.value)}><option>A</option><option>B</option><option>C</option></select></div>
          <div className="form-group"><label htmlFor="am">Recent local market price (₹/kg, optional)</label><input id="am" type="number" min="0" step="0.1" value={market} onChange={(e) => setMarket(e.target.value)} /></div>
        </div>
        {err && <div className="alert alert-error" role="alert">{err}</div>}
        <div className="row">
          <button className="btn btn-secondary" onClick={() => run('demand')} disabled={!!busy}>{busy === 'demand' ? 'Predicting…' : 'Predict 30-day demand'}</button>
          <button className="btn btn-secondary" onClick={() => run('price')} disabled={!!busy}>{busy === 'price' ? 'Estimating…' : 'Recommend a price'}</button>
        </div>
      </div>

      <div className="two-col">
        <div className="panel"><h3 style={{ marginTop: 0 }}>📈 Demand forecast</h3>
          {!demand ? <p className="muted">Pick a product and run a forecast.</p> : <>
            <div className="num" style={{ fontSize: 30, fontWeight: 700, color: 'var(--primary)' }}>{demand.predicted_units} {demand.unit}</div>
            <p>expected sales from <strong>{demand.forecast_period.start}</strong> to <strong>{demand.forecast_period.end}</strong> ({demand.forecast_period.days} days)</p>
            <p className="muted">Likely range {demand.range.low}–{demand.range.high} {demand.unit} (spread between model trees, not a guarantee)</p>
            <p className="muted">Based on {demand.assumptions.recent_weekly_units_kg} kg/week — {demand.assumptions.recent_sales_source}; region {demand.region}.</p>
            <Meta r={demand} /></>}
        </div>
        <div className="panel"><h3 style={{ marginTop: 0 }}>💰 Price recommendation</h3>
          {!price ? <p className="muted">Pick a product and request a price estimate.</p> : <>
            <div className="num" style={{ fontSize: 30, fontWeight: 700, color: 'var(--primary)' }}>{money(price.recommended_price)} <small>/ {price.unit}</small></div>
            <p>Your current price: {money(price.product.current_price)} ({price.difference_from_current_pct > 0 ? '+' : ''}{price.difference_from_current_pct}% difference)</p>
            <p className="muted">Likely range {money(price.range.low)}–{money(price.range.high)} · grade {price.assumptions.grade} · market ₹{price.assumptions.market_price_per_kg}/kg ({price.assumptions.market_price_source})</p>
            <Meta r={price} />
            <button className="btn btn-primary btn-sm" onClick={apply}>Use this price…</button>
            <div className="muted">Your listing is never changed automatically.</div></>}
        </div>
      </div>

      {info.data && (
        <div className="panel"><h3 style={{ marginTop: 0 }}>Model quality (held-out test set, synthetic data)</h3>
          <div className="table-wrap"><table><thead><tr><th>Model</th><th>MAE</th><th>RMSE</th><th>R²</th><th>Trained on</th></tr></thead>
            <tbody>{['demand', 'price'].map((k) => info.data[k].trained
              ? <tr key={k}><td>{k}</td><td>{info.data[k].metrics.mae.toFixed(2)}</td><td>{info.data[k].metrics.rmse.toFixed(2)}</td><td>{info.data[k].metrics.r2.toFixed(3)}</td><td>{info.data[k].n_rows} rows ({info.data[k].data_source})</td></tr>
              : <tr key={k}><td>{k}</td><td colSpan={4} className="error-text">{info.data[k].detail}</td></tr>)}</tbody></table></div></div>
      )}
    </div>
  );
}
