import { useState } from 'react'
import { compareReports } from '../lib/pipeline'
import './Dashboard.css'

const REPORT_TYPES = ['Activity report', 'Agricultural advisory', 'Financial summary',
  'Health filing', 'Custom']

const SAMPLE = {
  subject: 'शिरूर ग्रामपंचायत त्रैमासिक कार्य अहवाल',
  reportType: 'Activity report',
  notes: 'पाणीपुरवठा व रस्ते कामांवर भर.',
  facts: [
    { label: 'गाव', value: 'शिरूर' },
    { label: 'कालावधी', value: 'एप्रिल-जून २०२६' },
    { label: 'कुटुंबे', value: '1240' },
    { label: 'पूर्ण कामे', value: '18' },
    { label: 'प्राप्त निधी', value: '2500000' },
    { label: 'खर्च', value: '2135000' },
    { label: 'लाभार्थी', value: '860' },
  ],
}

const fmtMs = (ms) => (ms >= 1000 ? `${(ms / 1000).toFixed(2)} s` : `${Math.round(ms)} ms`)
const pct = (v) => `${Math.round(v.traceable / Math.max(v.total, 1) * 100)}%`

export default function Dashboard({ onHome }) {
  const [nav, setNav] = useState('generate') // 'generate' | 'results' | 'about'
  const [subject, setSubject] = useState(SAMPLE.subject)
  const [reportType, setReportType] = useState(SAMPLE.reportType)
  const [notes, setNotes] = useState(SAMPLE.notes)
  const [facts, setFacts] = useState(SAMPLE.facts)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const setFact = (i, k, v) => setFacts((f) => f.map((r, j) => (j === i ? { ...r, [k]: v } : r)))
  const addFact = () => setFacts((f) => [...f, { label: '', value: '' }])
  const rmFact = (i) => setFacts((f) => f.filter((_, j) => j !== i))

  async function generate() {
    setError(null); setBusy(true)
    try {
      const data = await compareReports({ subject, reportType, notes, facts })
      setResult(data)
      setNav('results')            // jump straight to the results
    } catch (e) {
      setError(e.message); setResult(null)
    } finally { setBusy(false) }
  }

  function downloadTex() {
    const blob = new Blob([result.grounded.latex], { type: 'text/x-tex' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a'); a.href = url; a.download = 'report.tex'; a.click()
    URL.revokeObjectURL(url)
  }

  const title = nav === 'generate' ? 'Generate' : nav === 'results' ? 'Results' : 'Method'

  return (
    <div className="db">
      {/* ---------- sidebar ---------- */}
      <aside className="sb">
        <div className="sb-brand">
          <span className="sb-logo">अ</span>
          <div className="sb-brand-txt">
            <b>Report Gen</b>
            <span>Marathi · grounded</span>
          </div>
        </div>

        <nav className="sb-nav">
          <div className="sb-group">Main</div>
          <button className={`sb-item ${nav === 'generate' ? 'active' : ''}`} onClick={() => setNav('generate')}>
            <svg viewBox="0 0 24 24" className="sb-ic" aria-hidden="true">
              <path d="M5 4h14v4H5zM5 11h8v9H5zM16 11h3v9h-3z" />
            </svg>
            New report
          </button>
          <button className={`sb-item ${nav === 'results' ? 'active' : ''}`} onClick={() => setNav('results')}>
            <svg viewBox="0 0 24 24" className="sb-ic" aria-hidden="true">
              <path d="M4 6h16M4 12h16M4 18h10" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            Results
          </button>

          <div className="sb-group">General</div>
          <button className={`sb-item ${nav === 'about' ? 'active' : ''}`} onClick={() => setNav('about')}>
            <svg viewBox="0 0 24 24" className="sb-ic" aria-hidden="true">
              <circle cx="12" cy="12" r="9" fill="none" stroke="currentColor" strokeWidth="2" />
              <path d="M12 11v5M12 8h.01" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
            </svg>
            About the method
          </button>
        </nav>

        <button className="sb-home" onClick={onHome}>
          <svg viewBox="0 0 24 24" className="sb-ic" aria-hidden="true">
            <path d="M14 7l-5 5 5 5" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
          Back to home
        </button>
      </aside>

      {/* ---------- main ---------- */}
      <main className="mn">
        <div className="mn-top">
          <div className="crumb">Report Generator <span>/</span> {title}</div>
          {nav === 'results' && result?.grounded && (
            <span className={`badge ${result.grounded.verification.ok ? 'ok' : 'warn'}`}>
              {result.grounded.verification.ok
                ? `✓ ${result.grounded.verification.traceable}/${result.grounded.verification.total} traceable`
                : `⚠ ${result.grounded.verification.unsupported} unsupported`}
            </span>)}
        </div>

        {nav === 'about' && <MethodView />}
        {nav === 'results' && <ResultsView result={result} onDownload={downloadTex} onNew={() => setNav('generate')} />}

        {nav === 'generate' && (
          <>
            <h1 className="mn-title">New report</h1>
            <p className="mn-hint">Enter what the report is about and the details. We generate it two ways and show the results.</p>

            <div className="card form-card">
              <div className="fc-grid">
                <div className="field span2">
                  <label>Subject</label>
                  <input value={subject} onChange={(e) => setSubject(e.target.value)} />
                </div>
                <div className="field">
                  <label>Report type</label>
                  <select value={reportType} onChange={(e) => setReportType(e.target.value)}>
                    {REPORT_TYPES.map((t) => <option key={t}>{t}</option>)}
                  </select>
                </div>
                <div className="field">
                  <label>Context notes <i>optional</i></label>
                  <input value={notes} onChange={(e) => setNotes(e.target.value)} placeholder="focus areas…" />
                </div>
              </div>

              <div className="field">
                <label>Details <i>label + value</i></label>
                <div className="facts">
                  {facts.map((f, i) => (
                    <div className="fact" key={i}>
                      <input placeholder="label" value={f.label} onChange={(e) => setFact(i, 'label', e.target.value)} />
                      <input placeholder="value" value={f.value} onChange={(e) => setFact(i, 'value', e.target.value)} />
                      <button className="rm" onClick={() => rmFact(i)}>×</button>
                    </div>
                  ))}
                </div>
                <button className="add" onClick={addFact}>+ Add detail</button>
              </div>

              <button className="gen" onClick={generate} disabled={busy}>
                {busy ? 'Generating & comparing…' : 'Generate report →'}
              </button>
              {error && <p className="err">⚠ {error}</p>}
            </div>
          </>
        )}
      </main>
    </div>
  )
}

/* ================= Results view (live output + benchmark) ================= */
function ResultsView({ result, onDownload, onNew }) {
  const g = result?.grounded
  const u = result?.ungrounded
  const m = result?.metrics
  const tk = m?.tokenization

  return (
    <div className="doc">
      <h1 className="mn-title">Results</h1>
      <p className="mn-hint">
        {g ? 'Your generated report, compared two ways.' : 'Generate a report to see your live result here.'}
      </p>

      {!g && (
        <div className="card doc-card empty">
          <p>No report yet.</p>
          <button className="gen small" onClick={onNew}>Create a report →</button>
        </div>
      )}

      {/* ---- live result ---- */}
      {g && (
        <>
          {m && (
            <div className="stats">
              <div className="stat">
                <div className="stat-label">Generation time (GPT-4o)</div>
                <div className="stat-val">{fmtMs(m.llm_ms)}</div>
                <div className="stat-sub">total pipeline {fmtMs(m.total_ms)}</div>
              </div>
              <div className="stat">
                <div className="stat-label">Faithfulness: ungrounded → ours</div>
                <div className="stat-val">
                  {u ? <span className="bad-txt">{pct(u.verification)}</span> : '—'}
                  {' → '}<span className="ok-txt">{pct(g.verification)}</span>
                </div>
                <div className="stat-sub">{u ? `${u.verification.unsupported} fabricated number(s) removed` : 'grounded'}</div>
              </div>
              {tk?.our && tk?.gpt && (
                <div className="stat">
                  <div className="stat-label">Tokenizer: ours vs GPT-4o</div>
                  <div className="stat-val">{tk.token_saving_x}× fewer</div>
                  <div className="stat-sub">{tk.our.tokens} vs {tk.gpt.tokens} tokens</div>
                </div>
              )}
              {tk?.our && tk?.gpt && (
                <div className="stat">
                  <div className="stat-label">Tokenize time (ours / GPT)</div>
                  <div className="stat-val">{tk.our.ms} / {tk.gpt.ms} <span className="u">ms</span></div>
                  <div className="stat-sub">fertility {tk.our.fertility} vs {tk.gpt.fertility} tok/word</div>
                </div>
              )}
            </div>
          )}

          <div className="compare">
            {u && (
              <div className="card col bad-col">
                <div className="col-head">
                  <div>
                    <span className="col-tag bad">Plain ChatGPT · ungrounded</span>
                    <h3>Baseline (B1)</h3>
                  </div>
                  <span className="badge warn">{pct(u.verification)} faithful</span>
                </div>
                <p className="col-body">
                  {u.tokens.map((t, j) => t.number
                    ? <mark key={j} className={t.valid ? 'claim' : 'claim bad'}>{t.text}</mark>
                    : <span key={j}>{t.text}</span>)}
                </p>
                <p className="col-foot bad-foot">Red = number not found in your details (fabricated / distorted).</p>
              </div>
            )}

            <div className="card col ok-col">
              <div className="col-head">
                <div>
                  <span className="col-tag ok">Grounded + verified · ours</span>
                  <h3>Our system (B4)</h3>
                </div>
                <div className="col-actions">
                  <span className="badge ok">{pct(g.verification)} faithful</span>
                  <button className="tex" onClick={onDownload}>.tex</button>
                </div>
              </div>
              <h4 className="rc-title">{g.title}</h4>
              {g.sections.map((s, i) => (
                <div className="rc-sec" key={i}>
                  <h5>{s.heading}</h5>
                  <p>{s.tokens.map((t, j) => t.source
                    ? <mark key={j} className="claim">{t.text}<sup>{t.source}</sup></mark>
                    : <span key={j}>{t.text}</span>)}</p>
                </div>
              ))}
              <p className="col-foot">Every figure bound to a detail you entered. Download compiles with XeLaTeX.</p>
            </div>
          </div>

          {tk?.our && tk?.gpt && (
            <div className="card cmp">
              <div className="cmp-head">Tokens to encode this report ({tk.report_words} words)</div>
              <div className="cmp-row">
                <span className="cmp-name">GPT-4o</span>
                <div className="cmp-track"><div className="cmp-fill gpt" style={{ width: '100%' }} /></div>
                <span className="cmp-num">{tk.gpt.tokens}</span>
              </div>
              <div className="cmp-row">
                <span className="cmp-name">Ours</span>
                <div className="cmp-track"><div className="cmp-fill" style={{ width: `${(tk.our.tokens / tk.gpt.tokens) * 100}%` }} /></div>
                <span className="cmp-num">{tk.our.tokens}</span>
              </div>
            </div>
          )}
        </>
      )}

      {/* ---- scale audit (500 reports) ---- */}
      <div className="bench-head">Scale audit — 500 reports</div>
      <div className="card doc-card">
        <h2>Tested at scale</h2>
        <div className="scale-stats">
          <div><span className="ss-val ok-txt">1.000</span><span className="ss-lbl">faithfulness over all 500 (deterministic)</span></div>
          <div><span className="ss-val">1.95×</span><span className="ss-lbl">fewer tokens than GPT-4o (29,983 vs 58,350)</span></div>
          <div><span className="ss-val"><span className="bad-txt">0.871</span> → <span className="ok-txt">1.000</span></span><span className="ss-lbl">ungrounded → grounded (20 LLM runs)</span></div>
        </div>
        <img className="audit-fig" src="/scale_audit.png" alt="Scale audit over 500 reports: tokenization cost, faithfulness audit, and per-report token comparison" />
        <p className="doc-note">
          Left: our tokenizer encodes each report in ~half the tokens of GPT-4o. Middle:
          grounded (B4) stays at 1.0 while ungrounded (B1) drops wherever the model invented
          a figure. Right: per-report tokens, every point below parity. (Benchmark is synthetic.)
        </p>
      </div>

      {/* ---- benchmark (static reference) ---- */}
      <div className="bench-head">Benchmark (10 reports, GPT-4o)</div>
      <div className="card doc-card">
        <h2>Faithfulness</h2>
        <table className="res-table">
          <thead><tr><th>System</th><th>Faithfulness</th><th>chrF++</th><th>Code-mix</th><th>Tokens</th></tr></thead>
          <tbody>
            <tr><td>B2 · deterministic</td><td>1.000</td><td>0.993</td><td>0.000</td><td>38.1</td></tr>
            <tr className="bad-row"><td>B1 · ungrounded LLM <i>(control)</i></td><td>0.629</td><td>0.406</td><td>0.000</td><td>120.2</td></tr>
            <tr className="ok-row"><td>B4 · grounded + verified <b>(ours)</b></td><td>1.000</td><td>0.454</td><td>0.000</td><td>32.7</td></tr>
          </tbody>
        </table>
        <p className="doc-note">Same model: ungrounded leaves <b>37% of numbers unsupported</b>; grounded reaches <b>zero invented figures</b>.</p>
      </div>

      <div className="card doc-card">
        <h2>Tokenizer fertility — across tokenizers (tokens / word, held-out Marathi)</h2>
        <table className="res-table">
          <thead><tr><th>Tokenizer</th><th>Fertility</th><th>vs ours</th></tr></thead>
          <tbody>
            <tr><td>char baseline</td><td>6.76</td><td>3.2×</td></tr>
            <tr className="bad-row"><td>GPT-3.5 / GPT-4 (cl100k_base)</td><td>7.98</td><td>3.7×</td></tr>
            <tr><td>GPT-4o (o200k_base)</td><td>2.80</td><td>1.3×</td></tr>
            <tr className="ok-row"><td>Marathi-BPE <b>(ours, trained)</b></td><td>2.18</td><td>1.0×</td></tr>
          </tbody>
        </table>
        <p className="doc-note">
          Ours is <b>1.3× more efficient than GPT-4o</b> and <b>3.7× more efficient than
          GPT-3.5/4</b> — whose older tokenizer is worse than character-level on Marathi.
        </p>
      </div>

      {/* multi-model experiment */}
      <div className="card doc-card">
        <h2>Across models — grounding fixes every model</h2>
        <table className="res-table">
          <thead><tr><th>Generator</th><th>B1 ungrounded</th><th>B4 grounded (ours)</th></tr></thead>
          <tbody>
            <tr><td>GPT-4o</td><td className="bad-cell">0.588</td><td className="ok-cell">1.000</td></tr>
            <tr><td>GPT-4o-mini</td><td className="bad-cell">0.831</td><td className="ok-cell">1.000</td></tr>
          </tbody>
        </table>
        <p className="doc-note">
          Faithfulness (figures traceable), 3 reports each. Ungrounded hallucination varies by
          model; <b>grounding + verification reaches 1.000 on every model</b> — the method is
          model-independent.
        </p>
      </div>

      {/* literature */}
      <div className="bench-head">What the base papers report</div>
      <div className="card doc-card">
        <h2>IndicGenBench (Google Research, 2024) — Marathi</h2>
        <table className="res-table">
          <thead><tr><th>Model</th><th>Marathi (chrF)</th><th>English (chrF)</th></tr></thead>
          <tbody>
            <tr><td>GPT-4 · summarization</td><td>22.4</td><td>30.3</td></tr>
            <tr><td>PaLM-2-L · summarization</td><td>25.4</td><td>41.1</td></tr>
            <tr><td>GPT-4 · En→Marathi MT</td><td>39.2</td><td>—</td></tr>
          </tbody>
        </table>
        <p className="doc-note">
          A large English↔Indic gap persists even for frontier models. Crucially, the benchmark
          reports <b>chrF, not BLEU</b> — stating token metrics “are not reliable for low-resource
          languages.” This is exactly why our evaluation is chrF + faithfulness, not BLEU.{' '}
          <a href="https://www.alphaxiv.org/abs/2404.16816" target="_blank" rel="noreferrer">arXiv:2404.16816</a>
        </p>
      </div>

      <div className="card doc-card">
        <h2>The Tokenizer Tax (2026) — Marathi fertility multiplier vs English</h2>
        <table className="res-table">
          <thead><tr><th>Tokenizer</th><th>Marathi tax ×</th></tr></thead>
          <tbody>
            <tr><td>GPT-2</td><td>9.04×</td></tr>
            <tr className="bad-row"><td>cl100k (GPT-3.5/4)</td><td>5.84×</td></tr>
            <tr><td>o200k (GPT-4o)</td><td>2.11×</td></tr>
            <tr className="ok-row"><td>XLM-R (multilingual)</td><td>1.41×</td></tr>
          </tbody>
        </table>
        <p className="doc-note">
          Standard tokenizers tax Marathi 5.8× vs English; a language-aware tokenizer nearly erases it.
          Our trained Marathi-BPE follows this exact trajectory. Mean Indic tax drops <b>73%</b> from
          cl100k to o200k.{' '}
          <a href="https://www.alphaxiv.org/abs/2607.24276" target="_blank" rel="noreferrer">arXiv:2607.24276</a>
        </p>
      </div>
    </div>
  )
}

/* ================= Method (About) view ================= */
const COMPONENTS = [
  ['1 · Parse', 'Each detail you enter becomes a typed record with a stable source id (F1, F2…). That id is what makes a figure traceable.'],
  ['2 · Ground', 'Every section of the report is bound to the specific details it is allowed to use, before any text is written — so the model cannot wander off the data.'],
  ['3 · Generate', 'The LLM (GPT-4o) writes the Marathi report, but it must write each value as a {{placeholder}} token, never a raw number.'],
  ['4 · Resolve', 'Each placeholder is substituted with its bound value and its source id. Figures are therefore traceable by construction, not by luck.'],
  ['5 · Verify', 'A checker scans the output: every number must map to a source detail. Any figure written outside the placeholder contract is flagged as unsupported.'],
]
const PAPERS = [
  ['★ SymGen: symbolically grounded generation (our core method, COLM 2024)', '2311.09188'],
  ['Controlled table-to-text (ToTTo)', '2004.14373'],
  ['IndicNLG Benchmark: NLG tasks in 11 Indic languages (EMNLP 2022)', '2203.05437'],
  ['IndicTrans2: MT for all 22 Indian languages (TMLR 2023)', '2305.16307'],
  ['IndicGenBench: Indic generation benchmark (Google, 2024)', '2404.16816'],
  ['The tokenizer tax for Indian languages', '2607.24276'],
  ['Plan-based retrieval grounding', '2408.10490'],
  ['Morphology-grounded Indic tokenization (MorphTok)', '2504.10335'],
]

function MethodView() {
  return (
    <div className="doc">
      <h1 className="mn-title">The method</h1>
      <p className="mn-hint">How a subject + a few details become a faithful Marathi report with zero invented numbers.</p>

      <div className="card doc-card">
        <h2>The task</h2>
        <p>
          This is <b>controlled, retrieval-grounded data-to-text generation</b> in a low-resource,
          morphologically rich language. Given a subject and structured details, the system writes
          a template-faithful administrative report in Marathi where <b>every numeric claim is
          traceable to a source detail</b> — generated natively, without translating through English.
        </p>
      </div>

      <div className="card doc-card">
        <h2>The pipeline</h2>
        <ol className="doc-steps">
          {COMPONENTS.map(([name, desc]) => (
            <li key={name}>
              <div className="doc-step-name">{name}</div>
              <div className="doc-step-desc">{desc}</div>
            </li>
          ))}
        </ol>
      </div>

      <div className="doc-two">
        <div className="card doc-card">
          <h2>Why it can’t hallucinate numbers</h2>
          <p>
            The generator writes <code>{'{{households}}'}</code>, never <code>1240</code>. We substitute
            the real value afterward and tag it with its source cell. A free-form LLM, by contrast, is
            free to invent plausible figures — which it does.
          </p>
          <p className="doc-note">This is <b>SymGen's</b> symbolic-reference mechanism (COLM 2024) applied to Marathi — plus our verifier, which <i>rejects</i> ungrounded numbers rather than only flagging them for a human.</p>
        </div>
        <div className="card doc-card">
          <h2>How we prove it works</h2>
          <p>We compare the same model under several scaffolds (an ablation ladder):</p>
          <ul className="doc-list">
            <li><b>B1</b> — ungrounded LLM, no verifier <i>(the control: it hallucinates)</i></li>
            <li><b>B2</b> — deterministic template (grounded, trivially faithful)</li>
            <li><b>B4</b> — grounded LLM + verifier <i>(our system)</i></li>
          </ul>
        </div>
      </div>

      <div className="card doc-card">
        <h2>Tokenization (a trained component)</h2>
        <p>
          Standard tokenizers fragment Devanagari, raising cost. We trained a Marathi BPE tokenizer and
          measured <b>fertility</b> (tokens per word): ours uses <b>~1.3× fewer tokens</b> than GPT-4o’s
          English-centric tokenizer on held-out Marathi.
        </p>
      </div>

      <div className="card doc-card">
        <h2>Evaluation beyond BLEU</h2>
        <p>
          BLEU correlates poorly for inflectional low-resource languages, so we report
          <b> faithfulness</b> (fraction of figures traceable), <b>chrF++</b>, <b>code-mix rate</b>,
          and token cost. Faithfulness is the headline, defensible metric.
        </p>
      </div>

      <div className="card doc-card">
        <h2>Grounded in the literature</h2>
        <ul className="doc-refs">
          {PAPERS.map(([title, id]) => (
            <li key={id}>
              <a href={`https://www.alphaxiv.org/abs/${id}`} target="_blank" rel="noreferrer">{title}</a>
              <span className="doc-id">arXiv:{id}</span>
            </li>
          ))}
        </ul>
      </div>
    </div>
  )
}
