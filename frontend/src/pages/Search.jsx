import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'

export default function Search() {
  const { token } = useAuth()
  const [query, setQuery] = useState('')
  const [plates, setPlates] = useState([])
  const [violations, setViolations] = useState([])
  const [searched, setSearched] = useState(false)

  const run = async () => {
    if (!query.trim()) return
    setSearched(true)
    try {
      const [p, v] = await Promise.all([
        apiFetch(`/api/v1/search/plates/${encodeURIComponent(query.trim())}`, { token }),
        apiFetch(`/api/v1/search/violations?q=${encodeURIComponent(query.trim())}`, { token }),
      ])
      setPlates(p)
      setViolations(v)
    } catch (err) {
      setPlates([])
      setViolations([])
    }
  }

  useEffect(() => {
    if (searched) run()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query])

  return (
    <div>
      <h1 className="page-title">Search</h1>
      <p className="page-sub">Look up license plates and violation records</p>

      <div className="card" style={{ marginBottom: 16 }}>
        <div className="form-row">
          <label>Plate number or search term</label>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && run()}
            placeholder="e.g. KA01AB1234 or speeding"
          />
        </div>
        <button className="btn" onClick={run}>Search</button>
      </div>

      {searched && (
        <>
          <div className="card" style={{ marginBottom: 16 }}>
            <h3>Vehicles ({plates.length})</h3>
            {plates.length === 0 && <div className="empty-state">No vehicles found</div>}
            {plates.length > 0 && (
              <table className="data">
                <thead>
                  <tr>
                    <th>Plate</th>
                    <th>Type</th>
                    <th>Brand</th>
                    <th>Model</th>
                    <th>Color</th>
                    <th>Owner</th>
                  </tr>
                </thead>
                <tbody>
                  {plates.map((p) => (
                    <tr key={p.id}>
                      <td>{p.plate_number}</td>
                      <td>{p.vehicle_type}</td>
                      <td>{p.brand}</td>
                      <td>{p.model}</td>
                      <td>{p.color}</td>
                      <td>{p.owner_name}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="card">
            <h3>Violations ({violations.length})</h3>
            {violations.length === 0 && <div className="empty-state">No violations found</div>}
            {violations.length > 0 && (
              <table className="data">
                <thead>
                  <tr>
                    <th>ID</th>
                    <th>Type</th>
                    <th>Location</th>
                    <th>Status</th>
                    <th>Detected</th>
                  </tr>
                </thead>
                <tbody>
                  {violations.map((v) => (
                    <tr key={v.id}>
                      <td>{v.violation_id}</td>
                      <td>{v.violation_type}</td>
                      <td>{v.location}</td>
                      <td>{v.status}</td>
                      <td>{new Date(v.detected_at).toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </div>
  )
}
