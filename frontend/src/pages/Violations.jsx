import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

export default function Violations() {
  const { token } = useAuth()
  const [violations, setViolations] = useState([])
  const [detail, setDetail] = useState(null)
  const [error, setError] = useState('')
  const [filters, setFilters] = useState({ type: '', status: '' })

  const load = () => {
    const params = new URLSearchParams({ limit: '100' })
    if (filters.type) params.set('violation_type', filters.type)
    if (filters.status) params.set('status', filters.status)
    apiFetch(`/api/v1/violations?${params}`, { token })
      .then(setViolations)
      .catch((err) => setError(err.message))
  }

  useEffect(load, [token, filters.type, filters.status])

  const openDetail = async (id) => {
    try {
      const data = await apiFetch(`/api/v1/violations/${id}`, { token })
      setDetail(data)
    } catch (err) {
      setError(err.message)
    }
  }

  return (
    <div>
      <h1 className="page-title">Violations</h1>
      <p className="page-sub">Detected traffic violations with evidence</p>
      {error && <div className="error-box">{error}</div>}

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="grid grid-2">
          <div className="form-row">
            <label>Violation Type</label>
            <select value={filters.type} onChange={(e) => setFilters({ ...filters, type: e.target.value })}>
              <option value="">All types</option>
              {['speeding', 'red_light', 'jaywalking', 'wrong_lane', 'no_helmet'].map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
          <div className="form-row">
            <label>Status</label>
            <select value={filters.status} onChange={(e) => setFilters({ ...filters, status: e.target.value })}>
              <option value="">All statuses</option>
              {['pending', 'issued', 'review'].map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
        </div>
      </div>

      <div className="card">
        {violations.length === 0 && <div className="empty-state">No violations found</div>}
        {violations.length > 0 && (
          <table className="data">
            <thead>
              <tr>
                <th>Violation ID</th>
                <th>Type</th>
                <th>Camera</th>
                <th>Location</th>
                <th>Confidence</th>
                <th>Status</th>
                <th>Detected</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {violations.map((v) => (
                <tr key={v.id}>
                  <td>{v.violation_id}</td>
                  <td>{v.violation_type}</td>
                  <td>{v.camera?.name || `Camera ${v.camera_id}`}</td>
                  <td>{v.location}</td>
                  <td>{v.confidence.toFixed(2)}</td>
                  <td><StatusBadge status={v.status} /></td>
                  <td>{new Date(v.detected_at).toLocaleString()}</td>
                  <td>
                    <button className="btn-outline" onClick={() => openDetail(v.violation_id)}>View</button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {detail && (
        <div className="card" style={{ marginTop: 16 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
            <h3>Violation {detail.violation_id}</h3>
            <button className="btn-ghost" style={{ width: 'auto' }} onClick={() => setDetail(null)}>Close</button>
          </div>
          <p>{detail.description}</p>
          <p className="muted">
            Camera: {detail.camera?.name || detail.camera_id} · Location: {detail.location} ·
            Confidence: {detail.confidence.toFixed(2)} · Detected: {new Date(detail.detected_at).toLocaleString()}
          </p>
          {detail.evidence && detail.evidence.length > 0 && (
            <div className="grid grid-3">
              {detail.evidence.map((ev) => (
                <div key={ev.id} className="card" style={{ padding: 10 }}>
                  <img
                    src={`/api/v1/evidence/${ev.id}/content?token=${encodeURIComponent(token)}`}
                    alt={ev.kind}
                    style={{ width: '100%', borderRadius: 8, background: '#000' }}
                    onError={(e) => { e.target.style.display = 'none' }}
                  />
                  <div className="muted" style={{ fontSize: 12, marginTop: 6 }}>{ev.kind} · {ev.mime_type}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
