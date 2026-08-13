import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import { Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import './styles.css';
import './background.css';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const copy = {
  en: {
    eyebrow:'Production intelligence', title:'Factory demand prediction', intro:'Import monthly product data, compare regression models, and turn the best forecast into a production recommendation.', badge:'ML · Regression', choose:'Choose a demand CSV', fileHelp:'CSV only · maximum 10 MB · data stays on this API', analyze:'Analyze dataset', training:'Training models…', template:'Download template', required:'Required columns: forecast_month, product_type, month, season, previous_sales, stock_quantity, price, promotion, customer_order_quantity, previous_production_quantity, target_demand.', chooseError:'Choose a CSV file first.', failed:'Analysis failed.', offline:'Cannot reach the API. Start it on port 8000.', rows:'Rows', products:'Products', unique:'Unique categories', best:'Best model', selected:'Selected by lowest RMSE', modelPerformance:'Model performance', metricHelp:'Lower MAE and RMSE are better; higher R² is better.', importance:'What influences demand predictions', importanceHelp:'Shows how much each input affects the prediction. A higher score means the input is more important.', recommendations:'Production recommendations', recommendationHelp:'Illustrative rule: predicted demand + 10% safety stock − current stock.', product:'Product', predicted:'Predicted demand', currentStock:'Current stock', safetyStock:'Safety stock', recommended:'Recommended production', heldOut:'Held-out predictions', heldOutHelp:'The latest 20% of imported records are kept out of training.', month:'Month', actual:'Actual', predictedShort:'Predicted', absoluteError:'Absolute error', train:'train', test:'test', footer:'Demonstration decision support — review capacity, lead time, and batch constraints before operational use.', language:'Language', theme:'Color theme', light:'Light mode', dark:'Dark mode'
  },
  km: {
    eyebrow:'ព័ត៌មានឆ្លាតវៃសម្រាប់ផលិតកម្ម', title:'ការព្យាករណ៍តម្រូវការរោងចក្រ', intro:'នាំចូលទិន្នន័យផលិតផលប្រចាំខែ ប្រៀបធៀបម៉ូដែលតំរែតំរង់ និងបម្លែងការព្យាករណ៍ល្អបំផុតទៅជាអនុសាសន៍ផលិតកម្ម។', badge:'ML · តំរែតំរង់', choose:'ជ្រើសរើសឯកសារ CSV តម្រូវការ', fileHelp:'ទទួលតែ CSV · អតិបរមា 10 MB · ទិន្នន័យរក្សានៅ API នេះ', analyze:'វិភាគទិន្នន័យ', training:'កំពុងបង្ហាត់ម៉ូដែល…', template:'ទាញយកគំរូ', required:'ជួរឈរចាំបាច់៖ forecast_month, product_type, month, season, previous_sales, stock_quantity, price, promotion, customer_order_quantity, previous_production_quantity, target_demand។', chooseError:'សូមជ្រើសរើសឯកសារ CSV ជាមុនសិន។', failed:'ការវិភាគមិនបានជោគជ័យ។', offline:'មិនអាចភ្ជាប់ទៅ API បានទេ។ សូមដំណើរការវានៅច្រក 8000។', rows:'ចំនួនជួរ', products:'ផលិតផល', unique:'ប្រភេទខុសៗគ្នា', best:'ម៉ូដែលល្អបំផុត', selected:'ជ្រើសតាម RMSE ទាបបំផុត', modelPerformance:'ប្រសិទ្ធភាពម៉ូដែល', metricHelp:'MAE និង RMSE កាន់តែទាបកាន់តែល្អ; R² កាន់តែខ្ពស់កាន់តែល្អ។', importance:'កត្តាដែលមានឥទ្ធិពលលើការព្យាករណ៍តម្រូវការ', importanceHelp:'បង្ហាញថាទិន្នន័យនីមួយៗមានឥទ្ធិពលលើការព្យាករណ៍កម្រិតណា។ ពិន្ទុកាន់តែខ្ពស់ មានន័យថាទិន្នន័យនោះកាន់តែសំខាន់។', recommendations:'អនុសាសន៍ផលិតកម្ម', recommendationHelp:'រូបមន្តបង្ហាញ៖ តម្រូវការព្យាករណ៍ + ស្តុកសុវត្ថិភាព 10% − ស្តុកបច្ចុប្បន្ន។', product:'ផលិតផល', predicted:'តម្រូវការព្យាករណ៍', currentStock:'ស្តុកបច្ចុប្បន្ន', safetyStock:'ស្តុកសុវត្ថិភាព', recommended:'ផលិតកម្មដែលណែនាំ', heldOut:'លទ្ធផលព្យាករណ៍លើទិន្នន័យសាកល្បង', heldOutHelp:'ទិន្នន័យ 20% ចុងក្រោយដែលបាននាំចូល ត្រូវបានទុកសម្រាប់សាកល្បង។', month:'ខែ', actual:'តម្រូវការពិត', predictedShort:'ការព្យាករណ៍', absoluteError:'កំហុសដាច់ខាត', train:'បង្ហាត់', test:'សាកល្បង', footer:'ឧបករណ៍គាំទ្រការសម្រេចចិត្តសម្រាប់បង្ហាញ — សូមពិនិត្យសមត្ថភាពផលិត ពេលវេលារង់ចាំ និងកម្រិតផលិតកម្មមុនប្រើប្រាស់ជាក់ស្តែង។', language:'ភាសា', theme:'រូបរាងពណ៌', light:'រូបរាងភ្លឺ', dark:'រូបរាងងងឹត'
  }
};

function Table({ columns, rows }) {
  return <div className="table-wrap"><table><thead><tr>{columns.map(c => <th key={c.key}>{c.label}</th>)}</tr></thead><tbody>{rows.map((row, i) => <tr key={i}>{columns.map(c => <td key={c.key}>{c.format ? c.format(row[c.key]) : row[c.key]}</td>)}</tr>)}</tbody></table></div>;
}

function localizeError(message, lang) {
  if (lang !== 'km') return message;
  if (message.startsWith('Missing required columns:')) return `ខ្វះជួរឈរចាំបាច់៖${message.slice('Missing required columns:'.length)}`;
  if (message.includes('larger than the 10 MB')) return 'ឯកសារ CSV ធំជាងទំហំអតិបរមា 10 MB។';
  if (message.includes('at least 15 rows')) return 'ទិន្នន័យត្រូវមានយ៉ាងតិច 15 ជួរ សម្រាប់ការបែងចែកបង្ហាត់ និងសាកល្បង។';
  if (message.includes('target_demand cannot contain')) return 'ជួរឈរ target_demand មិនអាចមានតម្លៃទទេ ឬមិនមែនជាលេខទេ។';
  if (message.includes('Please upload a CSV')) return 'សូមបញ្ចូលឯកសារ CSV។';
  if (message.includes('not a valid CSV')) return 'ឯកសារនេះមិនមែនជា CSV ត្រឹមត្រូវទេ។';
  return message;
}

function App() {
  const [lang, setLang] = useState(() => localStorage.getItem('factory-demand-language') || 'en');
  const [theme, setTheme] = useState(() => localStorage.getItem('factory-demand-theme') || (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'));
  const [file, setFile] = useState(null), [result, setResult] = useState(null);
  const [validation, setValidation] = useState(null);
  const [loading, setLoading] = useState(false), [error, setError] = useState('');
  const t = copy[lang];
  const number = (value, digits = 0) => value == null ? '—' : Number(value).toLocaleString(lang === 'km' ? 'km-KH' : 'en-US', { maximumFractionDigits: digits });
  useEffect(() => { localStorage.setItem('factory-demand-language', lang); document.documentElement.lang = lang; }, [lang]);
  useEffect(() => { localStorage.setItem('factory-demand-theme', theme); document.documentElement.dataset.theme = theme; }, [theme]);
  async function submit(event) {
    event.preventDefault(); if (!file) return setError(t.chooseError);
    setLoading(true); setError(''); setResult(null); setValidation(null);
    const form = new FormData(); form.append('file', file);
    try { const response = await fetch(`${API}/api/validate`, { method: 'POST', body: form }); const body = await response.json(); if (!response.ok) throw new Error(body.detail || t.failed); setValidation(body); }
    catch (e) { setError(e.message === 'Failed to fetch' ? t.offline : localizeError(e.message, lang)); }
    finally { setLoading(false); }
  }
  async function train() {
    if (!file || !validation?.valid) return;
    setLoading(true); setError(''); setResult(null);
    const form = new FormData(); form.append('file', file);
    try { const response = await fetch(`${API}/api/analyze`, { method: 'POST', body: form }); const body = await response.json(); if (!response.ok) throw new Error(body.detail || t.failed); setResult(body); }
    catch (e) { setError(e.message === 'Failed to fetch' ? t.offline : localizeError(e.message, lang)); }
    finally { setLoading(false); }
  }
  const reportDate = new Date().toLocaleString(lang === 'km' ? 'km-KH' : 'en-US');
  return <main>
    <header><div><span className="eyebrow">{t.eyebrow}</span><h1>{t.title}</h1><p>{t.intro}</p></div><div className="header-tools"><div className="control-row"><div className="language" aria-label={t.language}><button type="button" className={lang === 'en' ? 'active' : ''} onClick={() => setLang('en')}>English</button><button type="button" className={lang === 'km' ? 'active' : ''} onClick={() => setLang('km')}>ខ្មែរ</button></div><div className="theme-switch" aria-label={t.theme}><button type="button" className={theme === 'light' ? 'active' : ''} aria-label={t.light} title={t.light} onClick={() => setTheme('light')}>☀</button><button type="button" className={theme === 'dark' ? 'active' : ''} aria-label={t.dark} title={t.dark} onClick={() => setTheme('dark')}>☾</button></div></div><div className="badge">{t.badge}</div></div></header>
    <section className="upload-card"><form onSubmit={submit}><label className="drop"><input type="file" accept=".csv,text/csv" onChange={e => { setFile(e.target.files[0]); setValidation(null); setResult(null); setError(''); }}/><span className="icon">↥</span><strong>{file ? file.name : t.choose}</strong><small>{t.fileHelp}</small></label><div className="actions"><button disabled={loading}>{loading ? (lang === 'km' ? 'កំពុងពិនិត្យ…' : 'Validating…') : (lang === 'km' ? 'ពិនិត្យ និងមើលជាមុន' : 'Validate & preview')}</button><a href={`${API}/api/template`}>{t.template}</a></div></form><p className="hint">{t.required}</p>{error && <div className="error">{error}</div>}</section>
    {validation && <section className={`panel validation-panel ${validation.valid ? 'valid' : 'invalid'}`}><div className="validation-heading"><div><span className="status-mark">{validation.valid ? '✓' : '!'}</span><div><h2>{validation.valid ? (lang === 'km' ? 'ទិន្នន័យត្រឹមត្រូវ' : 'Dataset is ready') : (lang === 'km' ? 'ត្រូវកែទិន្នន័យ' : 'Dataset needs attention')}</h2><p>{validation.valid ? (lang === 'km' ? 'ការត្រួតពិនិត្យចាំបាច់បានជោគជ័យ។ អ្នកអាចបង្ហាត់ម៉ូដែលបាន។' : 'Required checks passed. You can train the models.') : (lang === 'km' ? 'សូមកែកំហុសខាងក្រោម រួចបញ្ចូលឯកសារម្តងទៀត។' : 'Fix the errors below, then upload the file again.')}</p></div></div>{validation.valid && <button type="button" disabled={loading} onClick={train}>{loading ? t.training : (lang === 'km' ? 'បង្ហាត់ម៉ូដែល' : 'Train models')}</button>}</div><div className="validation-stats"><span><b>{number(validation.summary.rows)}</b>{lang === 'km' ? ' ជួរ' : ' rows'}</span><span><b>{number(validation.summary.columns)}</b>{lang === 'km' ? ' ជួរឈរ' : ' columns'}</span>{validation.summary.products != null && <span><b>{number(validation.summary.products)}</b>{lang === 'km' ? ' ផលិតផល' : ' products'}</span>}<span><b>{number(validation.summary.duplicates || 0)}</b>{lang === 'km' ? ' ស្ទួន' : ' duplicates'}</span></div>{validation.errors.map((message, index) => <div className="quality-message error" key={`e-${index}`}>{localizeError(message, lang)}</div>)}{validation.warnings.map((message, index) => <div className="quality-message warning" key={`w-${index}`}>⚠ {message}</div>)}<h3>{lang === 'km' ? 'ទិន្នន័យគំរូ 8 ជួរដំបូង' : 'Preview of first 8 rows'}</h3><Table rows={validation.preview} columns={validation.columns.map(column => ({key:column,label:column}))}/></section>}
    {result && <section className="report-toolbar"><div><strong>{lang === 'km' ? 'របាយការណ៍វិភាគ' : 'Analysis report'}</strong><small>{lang === 'km' ? 'បានបង្កើតនៅ' : 'Generated'}: {reportDate}</small></div><button type="button" onClick={() => window.print()}>⎙ {lang === 'km' ? 'បោះពុម្ពរបាយការណ៍' : 'Print report'}</button></section>}
    {result && <><section className="stats"><article><span>{t.rows}</span><b>{number(result.summary.rows)}</b><small>{number(result.summary.training_rows)} {t.train} / {number(result.summary.test_rows)} {t.test}</small></article><article><span>{t.products}</span><b>{number(result.summary.products)}</b><small>{t.unique}</small></article><article className="accent"><span>{t.best}</span><b>{result.summary.best_model}</b><small>{t.selected}</small></article></section>
      <section className="grid two"><article className="panel"><h2>{t.modelPerformance}</h2><p>{t.metricHelp}</p><ResponsiveContainer width="100%" height={260}><BarChart data={result.models}><CartesianGrid strokeDasharray="3 3" vertical={false}/><XAxis dataKey="model" tick={{fontSize:12}}/><YAxis/><Tooltip/><Legend/><Bar dataKey="mae" fill="#33b6aa" name="MAE" radius={[5,5,0,0]}/><Bar dataKey="rmse" fill="#163f59" name="RMSE" radius={[5,5,0,0]}/></BarChart></ResponsiveContainer></article><article className="panel"><h2>{t.importance}</h2><p>{t.importanceHelp}</p><ResponsiveContainer width="100%" height={260}><BarChart data={result.feature_importance.slice(0,7)} layout="vertical"><CartesianGrid strokeDasharray="3 3" horizontal={false}/><XAxis type="number"/><YAxis dataKey="feature" type="category" width={145} tick={{fontSize:11}}/><Tooltip/><Bar dataKey="importance" fill="#f4a261" radius={[0,5,5,0]}/></BarChart></ResponsiveContainer></article></section>
      <section className="panel"><h2>{t.recommendations}</h2><p>{t.recommendationHelp}</p><Table rows={result.recommendations} columns={[{key:'product_type',label:t.product},{key:'predicted_demand',label:t.predicted,format:number},{key:'stock_quantity',label:t.currentStock,format:number},{key:'safety_stock',label:t.safetyStock,format:number},{key:'recommended_production',label:t.recommended,format:number}]}/></section>
      <section className="panel"><h2>{t.heldOut}</h2><p>{t.heldOutHelp}</p><Table rows={result.predictions} columns={[{key:'forecast_month',label:t.month},{key:'product_type',label:t.product},{key:'actual_demand',label:t.actual,format:number},{key:'predicted_demand',label:t.predictedShort,format:v=>number(v,2)},{key:'absolute_error',label:t.absoluteError,format:v=>number(v,2)}]}/></section></>}
    <footer>{t.footer}</footer>
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
