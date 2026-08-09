import { useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Link } from 'react-router-dom'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

function StatCard({ label, value, accent }) {
  return (
    <div className="card stat">
      <div className="value" style={{ color: accent || 'var(--text)' }}>{value}</div>
      <div className="label">{label}</div>
    </div>
  )
}

export default function Dashboard() {
  const { token } = useAuth()
  const [stats, setStats] = useState(null)
  const [cameras, setCameras] = useState([])
  const [recent, setRecent] = useState([])
  const [error, setError] = useState('')

  useEffect(() => {
    let alive = true
    const load = () => {
      Promise.all([
        apiFetch('/api/v1/dashboard/stats', { token }),
        apiFetch('/api/v1/cameras', { token }),
        apiFetch('/api/v1/violations?limit=8', { token }),
      ])
        .then(([s, c, v]) => {
          if (!alive) return
          setStats(s)
          setCameras(c)
          setRecent(v)
        })
        .catch((err) => alive && setError(err.message))
    }
    load()
    const timer = setInterval(load, 15000)
    return () => {
      alive = false
      clearInterval(timer)
    }
  }, [token])

  const onlineMobile = cameras.filter((c) => c.camera_type === 'mobile' && c.is_streaming)

  return (
    <div>
      <h1 className="page-title">Dashboard</h1>
      <p className="page-sub">Live overview of traffic monitoring activity</p>

      {error && <div className="error-box">{error}</div>}
      {!stats && !error && <div className="empty-state">Loading…</div>}

      {stats && (
        <>
          <div className="grid grid-4" style={{ marginBottom: 16 }}>
            <StatCard label="Total Violations" value={stats.total_violations} accent="var(--bad)" />
            <StatCard label="Recent (7 days)" value={stats.recent_violations} accent="var(--warn)" />
            <StatCard label="Active Cameras" value={`${stats.active_cameras}/${stats.total_cameras}`} accent="var(--good)" />
            <StatCard label="Mobile Cameras" value={stats.mobile_cameras} accent="var(--accent)" />
          </div>

          <div className="grid grid-2" style={{ marginBottom: 16 }}>
            <div className="card">
              <h3>Violations by Type (7 days)</h3>
              <div className="chart-box">
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.violations_by_type}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#24324d" />
                    <XAxis dataKey="type" stroke="#8fa0bd" />
                    <YAxis stroke="#8fa0bd" />
                    <Tooltip contentStyle={{ background: '#182338', border: '1px solid #24324d' }} />
                    <Bar dataKey="count" fill="#22d3ee" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="card">
              <h3>Live Streaming Cameras</h3>
              {cameras.length === 0 && <div className="empty-state">No cameras registered</div>}
              {onlineMobile.length === 0 && cameras.length > 0 && (
                <div className="empty-state">No mobile cameras currently streaming</div>
              )}
              {cameras
                .filter((c) => c.is_streaming || c.camera_type === 'mobile')
                .slice(0, 6)
                .map((c) => (
                  <div key={c.id} className="form-row" style={{ display: 'flex', justifyContent: 'space-between' }}>
                    <span>
                      {c.camera_type === 'mobile' && <span className="dot good" />}
                      {c.name}
                    </span>
                    <StatusBadge status={c.is_streaming ? 'LIVE' : c.status} />
                  </div>
                ))}
            </div>
          </div>

          <div className="card">
            <h3>Recent Violations</h3>
            {recent.length === 0 && <div className="empty-state">No violations yet</div>}
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
                </tr>
              </thead>
              <tbody>
                {recent.map((v) => (
                  <tr key={v.id}>
                    <td>{v.violation_id}</td>
                    <td>{v.violation_type}</td>
                    <td>{v.camera?.name || `Camera ${v.camera_id}`}</td>
                    <td>{v.location}</td>
                    <td>{v.confidence.toFixed(2)}</td>
                    <td><StatusBadge status={v.status} /></td>
                    <td>{new Date(v.detected_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p style={{ marginTop: 12 }}>
              <Link to="/violations" className="muted">View all violations →</Link>
            </p>
          </div>
        </>
      )}
    </div>
  )
}
