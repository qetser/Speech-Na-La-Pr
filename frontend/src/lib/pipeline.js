// Pipeline client. Primary path: call the Python backend (server/app.py).
// Fallback path: a local in-browser STUB mirroring the same contract, so the
// demo keeps working even if the backend is not running.
//
// Contract: generateReport(csvText) -> {
//   slots: [{ id, tokens: [{text, source?}] }],   // source = source_cell_id
//   verification: { ok, total, traceable, unsupported, claims: [{field,value,cell}] }
// }

const API = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'

// Subject + details -> full multi-section grounded report + LaTeX.
export async function generateReportDoc({ subject, reportType, facts, notes, engine = 'auto' }) {
  const res = await fetch(`${API}/api/report`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, report_type: reportType, facts, notes, engine }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || res.statusText)
  return data
}

// Render the grounded report to an official single-page PDF (returns a Blob).
export async function reportPdf({ title, sections, submitted_by, authorised_by, place }) {
  const res = await fetch(`${API}/api/report/pdf`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, sections, submitted_by, authorised_by, place }),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || res.statusText)
  }
  return await res.blob()
}

// Both results side by side: grounded (ours) + ungrounded (plain LLM).
export async function compareReports({ subject, reportType, facts, notes, engine = 'auto' }) {
  const res = await fetch(`${API}/api/report/compare`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ subject, report_type: reportType, facts, notes, engine }),
  })
  const data = await res.json()
  if (!res.ok) throw new Error(data.detail || res.statusText)
  return data
}

// Primary entry used by the UI: try the real backend, fall back to the stub.
export async function generate(csvText, { engine = 'auto' } = {}) {
  try {
    const res = await fetch(`${API}/api/generate`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ csv: csvText, engine }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.detail || res.statusText)
    return { ...data, engine: data.engine || 'backend' }
  } catch (e) {
    // Backend down or errored — degrade gracefully to the local stub.
    return { ...generateReport(csvText), engine: 'stub (offline)' }
  }
}

// --- Component 1: parse CSV into typed records with stable source_cell_ids ---
function parseCsv(csvText) {
  const lines = csvText.trim().split(/\r?\n/)
  if (lines.length < 2) throw new Error('CSV needs a header row and at least one data row.')
  const headers = lines[0].split(',').map((h) => h.trim())
  const values = lines[1].split(',').map((v) => v.trim())
  if (values.length !== headers.length) throw new Error('Row/column count mismatch.')

  const record = {}
  headers.forEach((h, i) => {
    // source_cell_id = R1C<col>  (row 1, column index). The verifier checks against these.
    record[h] = { value: values[i], cell: `R1C${i + 1}` }
  })
  return record
}

function fmtMoney(n) {
  return `₹${Number(n).toLocaleString('en-IN')}`
}

// --- Components 3+4: bind cells to template slots and fill Marathi text ---
// NOTE: numbers come ONLY from bound cells; prose is fixed register-controlled
// scaffolding. The real system generates this with an Indic LLM + lexicon.
export function generateReport(csvText) {
  const r = parseCsv(csvText)
  const need = ['gp_name','taluka','district','period','households','works_done','funds_received','funds_spent','beneficiaries']
  for (const f of need) if (!(f in r)) throw new Error(`Missing column: ${f}`)

  const claims = []
  const claim = (field, rec, display) => {
    claims.push({ field, value: display ?? rec.value, cell: rec.cell })
    return { text: display ?? rec.value, source: rec.cell }
  }

  const slots = [
    {
      id: 'header',
      tokens: [
        claim('gp_name', r.gp_name),
        { text: ', ' },
        claim('taluka', r.taluka),
        { text: ' तालुका, ' },
        claim('district', r.district),
        { text: ' जिल्हा — कार्य अहवाल (' },
        claim('period', r.period),
        { text: ').' },
      ],
    },
    {
      id: 'coverage',
      tokens: [
        { text: 'या कालावधीत एकूण ' },
        claim('households', r.households),
        { text: ' कुटुंबांचा समावेश करण्यात आला.' },
      ],
    },
    {
      id: 'works',
      tokens: [
        { text: 'अहवाल कालावधीत ' },
        claim('works_done', r.works_done),
        { text: ' कामे पूर्ण करण्यात आली.' },
      ],
    },
    {
      id: 'finance',
      tokens: [
        { text: 'प्राप्त निधी ' },
        claim('funds_received', r.funds_received, fmtMoney(r.funds_received.value)),
        { text: ' पैकी ' },
        claim('funds_spent', r.funds_spent, fmtMoney(r.funds_spent.value)),
        { text: ' खर्च करण्यात आला.' },
      ],
    },
    {
      id: 'beneficiaries',
      tokens: [
        { text: 'एकूण ' },
        claim('beneficiaries', r.beneficiaries),
        { text: ' लाभार्थ्यांपर्यंत लाभ पोहोचला.' },
      ],
    },
  ]

  // --- Component 5: verification. Every numeric/entity claim must bind to a cell. ---
  const total = claims.length
  const traceable = claims.filter((c) => /^R\d+C\d+$/.test(c.cell)).length
  const unsupported = total - traceable

  return {
    slots,
    verification: { ok: unsupported === 0, total, traceable, unsupported, claims },
  }
}
