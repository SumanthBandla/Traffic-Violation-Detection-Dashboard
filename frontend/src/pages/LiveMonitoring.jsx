import { useEffect, useMemo, useState } from 'react'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import useLiveChannel from '../hooks/useLiveChannel.js'
import StatusBadge from '../components/StatusBadge.jsx'

function densityLabel(count) {
  if (count >= 24) return { label: 'HIGH', cls: 'badge-good' }
  if (count >= 12) return { label: 'MEDIUM', cls: 'badge-warn' }
  return { label: 'LOW', cls: 'badge-neutral' }
}

export default function LiveMonitoring() {
  const { token } = useAuth()
  const [cameras, setCameras] = useState([])
  const [selected, setSelected] = useState(null)
  const [error, setError] = useState('')
  const live = useLiveChannel(token)

  useEffect(() => {
    apiFetch('/api/v1/cameras', { token })
      .then((cams) => {
        setCameras(cams)
        const streaming = cams.find((c) => c.is_streaming)
        setSelected((prev) => prev || (streaming ? streaming.id : null))
      })
      .catch((err) => setError(err.message))
    const timer = setInterval(() => {
      apiFetch('/api/v1/cameras', { token }).then(setCameras).catch(() => {})
    }, 10000)
    return () => clearInterval(timer)
  }, [token])

  useEffect(() => {
    if (selected) live.subscribe(selected)
    return () => {
      if (selected) live.unsubscribe(selected)
    }
  }, [selected])

  const camera = useMemo(() => cameras.find((c) => c.id === selected) || null, [cameras, selected])
  const frame = selected ? live.frames[selected] : null
  const density = densityLabel(frame?.vehicle_count || 0)
  const cameraViolations = live.violations.filter((v) => v.camera_id === selected)

  return (
    <div>
      <h1 className="page-title">Live Traffic Monitoring</h1>
      <p className="page-sub">
        Real-time AI detection from fixed and mobile cameras{' '}
        {live.connected ? <StatusBadge status="CONNECTED" /> : <StatusBadge status="RECONNECTING" />}
      </p>

      {error && <div className="error-box">{error}</div>}

      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        {cameras.map((c) => (
          <button
            key={c.id}
            className={`pill ${selected === c.id ? 'active' : ''}`}
            onClick={() => setSelected(c.id)}
          >
            {c.camera_type === 'mobile' ? '📱' : '🎥'} {c.name}
            {c.is_streaming && <span className="dot good" style={{ margin: 0 }} />}
          </button>
        ))}
        {cameras.length === 0 && <div className="empty-state">No cameras registered</div>}
      </div>

      {camera && (
        <div className="grid grid-2">
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
              <h3 style={{ margin: 0 }}>{camera.name}</h3>
              <StatusBadge status={camera.is_streaming ? 'LIVE' : 'OFFLINE'} />
            </div>

            <div className="video-shell">
              {frame ? (
                <img src={`data:image/jpeg;base64,${frame.image}`} alt="Live stream" />
              ) : (
                <div className="video-empty">
                  {camera.is_streaming
                    ? 'Waiting for first frame from camera…'
                    : 'Camera is not streaming. Start the stream from the mobile app or a source camera.'}
                </div>
              )}
              {frame && (
                <div className="live-hud">
                  <span className="live-tag">● LIVE</span>
                  <span className="live-tag">{frame.camera_name}</span>
                </div>
              )}
            </div>

            <div className="grid grid-4" style={{ marginTop: 14, gap: 10 }}>
              <div className="card stat" style={{ padding: 12 }}>
                <div className="value" style={{ fontSize: 22 }}>{frame?.vehicle_count ?? 0}</div>
                <div className="label">Vehicles</div>
              </div>
              <div className="card stat" style={{ padding: 12 }}>
                <div className="value" style={{ fontSize: 22, color: 'var(--bad)' }}>{cameraViolations.length}</div>
                <div className="label">Violations (session)</div>
              </div>
              <div className="card stat" style={{ padding: 12 }}>
                <div className="value" style={{ fontSize: 22 }}>
                  <span className={`badge ${density.cls}`}>{density.label}</span>
                </div>
                <div className="label">Traffic Density</div>
              </div>
              <div className="card stat" style={{ padding: 12 }}>
                <div className="value" style={{ fontSize: 22 }}>
                  <span className={`dot ${live.connected ? 'good' : 'bad'}`} style={{ verticalAlign: 'middle' }} />
                  {live.connected ? 'Online' : 'Offline'}
                </div>
                <div className="label">Connection</div>
              </div>
            </div>
          </div>

          <div>
            <div className="card" style={{ marginBottom: 16 }}>
              <h3>Live Violations</h3>
              {cameraViolations.length === 0 && <div className="empty-state">No violations detected</div>}
              {cameraViolations.map((v, i) => (
                <div key={`${v.violation_id}-${i}`} className="form-row" style={{ display: 'flex', justifyContent: 'space-between' }}>
                  <span>⚠ {v.violation_type}</span>
                  <span className="muted">{v.violation_id}</span>
                </div>
              ))}
            </div>

            <div className="card">
              <h3>Activity Feed</h3>
              {live.events.length === 0 && <div className="empty-state">Waiting for activity…</div>}
              {live.events.slice(-12).reverse().map((ev, i) => (
                <div key={i} className="form-row" style={{ display: 'flex', gap: 8, fontSize: 13 }}>
                  <span className="muted">{new Date(ev.ts).toLocaleTimeString()}</span>
                  <span>{ev.text}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
