import React, { useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import './styles.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const number = (value, digits = 0) => value == null ? '—' : Number(value).toLocaleString(undefined, { maximumFractionDigits: digits });

function Table({ columns, rows }) {
  return <div className="table-wrap"><table><thead><tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead>
    <tbody>{rows.map((row, i) => <tr key={i}>{columns.map(c => <td key={c.key}>{c.format ? c.format(row[c.key]) : row[c.key]}</td>)}</tr>)}</tbody></table></div>;
}

function App() {
  const [file, setFile] = useState(null), [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false), [error, setError] = useState('');
  async function submit(event) {
    event.preventDefault(); if (!file) return setError('Choose a CSV file first.');
    setLoading(true); setError(''); setResult(null);
    const form = new FormData(); form.append('file', file);
    try {
      const response = await fetch(`${API}/api/analyze`, { method: 'POST', body: form });
      const body = await response.json(); if (!response.ok) throw new Error(body.detail || 'Analysis failed.');
      setResult(body);
    } catch (e) { setError(e.message === 'Failed to fetch' ? 'Cannot reach the API. Start it on port 8000.' : e.message); }
    finally { setLoading(false); }
  }
  return <main>
    <header><div><span className="eyebrow">Production intelligence</span><h1>Factory demand prediction</h1><p>Import monthly product data, compare regression models, and turn the best forecast into a production recommendation.</p></div><div className="badge">ML · Regression</div></header>
    <section className="upload-card">
      <form onSubmit={submit}><label className="drop"><input type="file" accept=".csv,text/csv" onChange={e => setFile(e.target.files[0])}/><span className="icon">↥</span><strong>{file ? file.name : 'Choose a demand CSV'}</strong><small>CSV only · maximum 10 MB · data stays on this API</small></label>
        <div className="actions"><button disabled={loading}>{loading ? 'Training models…' : 'Analyze dataset'}</button><a href={`${API}/api/template`}>Download template</a></div></form>
      <p className="hint">Required columns: forecast_month, product_type, month, season, previous_sales, stock_quantity, price, promotion, customer_order_quantity, previous_production_quantity, target_demand.</p>
      {error && <div className="error">{error}</div>}
    </section>
    {result && <>
      <section className="stats"><article><span>Rows</span><b>{number(result.summary.rows)}</b><small>{result.summary.training_rows} train / {result.summary.test_rows} test</small></article><article><span>Products</span><b>{result.summary.products}</b><small>Unique categories</small></article><article className="accent"><span>Best model</span><b>{result.summary.best_model}</b><small>Selected by lowest RMSE</small></article></section>
      <section className="grid two"><article className="panel"><h2>Model performance</h2><p>Lower MAE and RMSE are better; higher R² is better.</p><ResponsiveContainer width="100%" height={260}><BarChart data={result.models}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="model" tick={{fontSize:12}}/><YAxis/><Tooltip/><Legend/><Bar dataKey="mae" fill="#33b6aa" name="MAE" radius={[5,5,0,0]}/><Bar dataKey="rmse" fill="#163f59" name="RMSE" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></article>
        <article className="panel"><h2>Feature importance</h2><p>Error increase after shuffling a feature.</p><ResponsiveContainer width="100%" height={260}><BarChart data={result.feature_importance.slice(0,7)} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number"/><YAxis dataKey="feature" type="category" width={145} tick={{fontSize:11}}/><Tooltip/><Bar dataKey="importance" fill="#f4a261" radius={[0,5,5,0]}/></BarChart></ResponsiveContainer></article></section>
      <section className="panel"><h2>Production recommendations</h2><p>Illustrative rule: predicted demand + 10% safety stock − current stock.</p><Table rows={result.recommendations} columns={[{key:'product_type',label:'Product'},{key:'predicted_demand',label:'Predicted demand',format:number},{key:'stock_quantity',label:'Current stock',format:number},{key:'safety_stock',label:'Safety stock',format:number},{key:'recommended_production',label:'Recommended production',format:number}]}/></section>
      <section className="panel"><h2>Held-out predictions</h2><p>The latest 20% of imported records are kept out of training.</p><Table rows={result.predictions} columns={[{key:'forecast_month',label:'Month'},{key:'product_type',label:'Product'},{key:'actual_demand',label:'Actual',format:number},{key:'predicted_demand',label:'Predicted',format:v=>number(v,2)},{key:'absolute_error',label:'Absolute error',format:v=>number(v,2)}]}/></section>
    </>}
    <footer>Demonstration decision support — review capacity, lead time, and batch constraints before operational use.</footer>
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
