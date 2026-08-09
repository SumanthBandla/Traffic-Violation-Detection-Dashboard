import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

export default function QuantumControl() {
  const { token, user } = useAuth()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)

  const canControl = user && ['admin', 'officer'].includes(user.role)

  const load = () => {
    apiFetch('/api/v1/quantum/overview', { token })
      .then(setData)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const optimise = async (id) => {
    setBusy(true)
    try {
      await apiFetch(`/api/v1/quantum/intersections/${id}/optimise`, { method: 'POST', token, body: {} })
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const setPhase = async (id, phase) => {
    setBusy(true)
    try {
      await apiFetch(`/api/v1/quantum/intersections/${id}/phase/${phase}`, { method: 'POST', token, body: {} })
      load()
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div>
      <h1 className="page-title">Quantum Traffic Control</h1>
      <p className="page-sub">
        Quantum-inspired signal optimisation (simulation only — operator approval required)
      </p>
      {error && <div className="error-box">{error}</div>}

      {data && (
        <>
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 14 }}>
              <h3 style={{ margin: 0 }}>Network Status</h3>
              <StatusBadge status={data.network_status.toUpperCase()} />
            </div>
            <div className="grid grid-4">
              <div className="stat"><span className="value" style={{ fontSize: 22 }}>{data.active_cameras}</span><span className="label">Active Cameras</span></div>
              <div className="stat"><span className="value" style={{ fontSize: 22 }}>{data.total_vehicles}</span><span className="label">Total Vehicles</span></div>
              <div className="stat"><span className="value" style={{ fontSize: 22 }}>{data.estimated_queue}</span><span className="label">Estimated Queue</span></div>
              <div className="stat"><span className="value" style={{ fontSize: 22 }}>{data.estimated_delay_min} min</span><span className="label">Estimated Delay</span></div>
            </div>
            <div className="muted" style={{ marginTop: 12, fontSize: 13 }}>
              Fixed Cameras: {data.fixed_cameras} · Mobile Cameras: {data.mobile_cameras} ·
              Pending Safety Alerts: <span style={{ color: 'var(--warn)' }}>{data.pending_safety_alerts}</span>
            </div>
            <p className="muted" style={{ fontSize: 12, marginTop: 10 }}>
              ⚠ {data.disclaimer}
            </p>
          </div>

          <div className="grid grid-2">
            {data.intersections.map((ix) => (
              <div key={ix.id} className="card">
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                  <h3 style={{ margin: 0 }}>{ix.name}</h3>
                  <StatusBadge status={ix.vehicle_demand} />
                </div>

                <div style={{ marginBottom: 12 }}>
                  <div className="muted" style={{ fontSize: 12, marginBottom: 6 }}>Camera Sources</div>
                  {ix.fixed_cameras.map((c) => (
                    <div key={c}>● {c}</div>
                  ))}
                  {ix.mobile_cameras.map((c) => (
                    <div key={c}>● <span className="phase-pill">{c}</span> <span className="muted">(mobile)</span></div>
                  ))}
                  {ix.camera_sources.length === 0 && <div className="muted">No cameras assigned</div>}
                </div>

                <div className="grid grid-2" style={{ gap: 8, marginBottom: 12 }}>
                  <div className="card stat" style={{ padding: 10 }}>
                    <span className="value" style={{ fontSize: 20 }}>{ix.queue}</span>
                    <span className="label">Queue</span>
                  </div>
                  <div className="card stat" style={{ padding: 10 }}>
                    <span className="value" style={{ fontSize: 20, color: 'var(--accent)' }}>{ix.green}s</span>
                    <span className="label">Green Duration</span>
                  </div>
                </div>

                <div style={{ marginBottom: 14 }}>
                  <span className="muted">Recommended Phase: </span>
                  <span className="phase-pill">{ix.phase}</span>
                </div>

                <div style={{ display: 'flex', gap: 8 }}>
                  <button className="btn" disabled={!canControl || busy} onClick={() => optimise(ix.id)}>
                    Optimise
                  </button>
                  <button className="btn-outline" disabled={!canControl || busy} onClick={() => setPhase(ix.id, 'all_red')}>
                    All Red
                  </button>
                  <button className="btn-outline" disabled={!canControl || busy} onClick={() => setPhase(ix.id, 'pedestrian')}>
                    Pedestrian
                  </button>
                </div>
                {!canControl && <p className="muted" style={{ fontSize: 12, marginTop: 8 }}>Admin/officer role required for control actions.</p>}
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
