import './Landing.css'

export default function Landing({ onStart }) {
  return (
    <div className="lp">
      {/* LEFT: pitch + CTA (no login) */}
      <section className="lp-left">
        <div className="lp-brand">
          <span className="lp-logo">अ</span>
          <span className="lp-name">Marathi Report Generator</span>
        </div>

        <div className="lp-hero">
          <h1>Grounded Marathi reports, zero invented numbers.</h1>
          <p className="lp-sub">
            Give a subject and a few details. The system writes a full administrative
            report in Marathi, keeps every figure traceable to what you entered, and
            hands you a compile-ready LaTeX document. No login.
          </p>

          <button className="lp-cta" onClick={onStart}>
            Create a report →
          </button>

          <ul className="lp-points">
            <li><b>100%</b> figures traceable to source</li>
            <li><b>Native Marathi</b>, no English translation step</li>
            <li><b>1.3×</b> fewer tokens than GPT-4o's tokenizer</li>
          </ul>
        </div>

        <p className="lp-foot">An NLP project on retrieval-grounded, verified generation.</p>
      </section>

      {/* RIGHT: showcase */}
      <section className="lp-right">
        <div className="lp-stage">
          <div className="sc-card sc-report">
            <div className="sc-head">अहवाल · Report</div>
            <p>
              या कालावधीत एकूण{' '}
              <mark className="claim">1240<sup>F2</sup></mark> कुटुंबांचा समावेश,{' '}
              <mark className="claim">18<sup>F3</sup></mark> कामे पूर्ण.
            </p>
            <span className="sc-badge">✓ 6/6 traceable</span>
          </div>

          <div className="sc-card sc-metric">
            <div className="sc-metric-label">Tokenizer efficiency</div>
            <div className="sc-metric-val">1.31×</div>
            <div className="sc-bars">
              <div className="sc-bar"><span style={{ width: '100%' }} /> <em>GPT-4o 199</em></div>
              <div className="sc-bar ours"><span style={{ width: '76%' }} /> <em>Ours 152</em></div>
            </div>
          </div>

          <div className="sc-card sc-quote">
            <div className="sc-stars">★★★★★</div>
            <p>“Same model. 37% of numbers wrong ungrounded, zero wrong grounded.”</p>
            <span className="sc-by">B1 vs B4, faithfulness</span>
          </div>
        </div>
        <p className="lp-caption">
          From tabular details to a faithful Marathi report, without translating through English.
        </p>
      </section>
    </div>
  )
}
