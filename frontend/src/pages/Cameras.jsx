import { useEffect, useState } from 'react'
import { apiFetch } from '../api/client.js'
import { useAuth } from '../context/AuthContext.jsx'
import StatusBadge from '../components/StatusBadge.jsx'

export default function Cameras() {
  const { token } = useAuth()
  const [cameras, setCameras] = useState([])
  const [error, setError] = useState('')
  const [filter, setFilter] = useState('all')
  const [showForm, setShowForm] = useState(false)
  const [form, setForm] = useState({
    name: '',
    location: '',
    latitude: '',
    longitude: '',
    stream_url: '',
    camera_type: 'fixed',
  })

  const load = () => {
    apiFetch('/api/v1/cameras', { token })
      .then(setCameras)
      .catch((err) => setError(err.message))
  }

  useEffect(() => {
    load()
    const timer = setInterval(load, 10000)
    return () => clearInterval(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  const register = async (e) => {
    e.preventDefault()
    setError('')
    try {
      await apiFetch('/api/v1/cameras', {
        method: 'POST',
        token,
        body: {
          name: form.name,
          location: form.location || form.name,
          latitude: parseFloat(form.latitude) || 0,
          longitude: parseFloat(form.longitude) || 0,
          stream_url: form.stream_url,
          camera_type: form.camera_type,
        },
      })
      setShowForm(false)
      setForm({ name: '', location: '', latitude: '', longitude: '', stream_url: '', camera_type: 'fixed' })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const updateStatus = async (camera, status) => {
    try {
      await apiFetch(`/api/v1/cameras/${camera.id}`, {
        method: 'PATCH',
        token,
        body: { status },
      })
      load()
    } catch (err) {
      setError(err.message)
    }
  }

  const visible = cameras.filter((c) => filter === 'all' || c.camera_type === filter)

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 className="page-title">Cameras</h1>
          <p className="page-sub">Fixed and mobile traffic cameras registered in the network</p>
        </div>
        <button className="btn" onClick={() => setShowForm((v) => !v)}>
          {showForm ? 'Cancel' : '+ Register Camera'}
        </button>
      </div>

      {error && <div className="error-box">{error}</div>}

      {showForm && (
        <div className="card" style={{ marginBottom: 16 }}>
          <h3>Register a camera</h3>
          <form onSubmit={register} className="grid grid-3">
            <div className="form-row">
              <label>Camera Name</label>
              <input required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="Junction Camera 01" />
            </div>
            <div className="form-row">
              <label>Location</label>
              <input value={form.location} onChange={(e) => setForm({ ...form, location: e.target.value })} placeholder="Main Road Junction" />
            </div>
            <div className="form-row">
              <label>Camera Type</label>
              <select value={form.camera_type} onChange={(e) => setForm({ ...form, camera_type: e.target.value })}>
                <option value="fixed">Fixed</option>
                <option value="mobile">Mobile (phone)</option>
              </select>
            </div>
            <div className="form-row">
              <label>Latitude</label>
              <input value={form.latitude} onChange={(e) => setForm({ ...form, latitude: e.target.value })} placeholder="16.5062" />
            </div>
            <div className="form-row">
              <label>Longitude</label>
              <input value={form.longitude} onChange={(e) => setForm({ ...form, longitude: e.target.value })} placeholder="80.6480" />
            </div>
            <div className="form-row">
              <label>Stream URL (optional)</label>
              <input value={form.stream_url} onChange={(e) => setForm({ ...form, stream_url: e.target.value })} placeholder="rtsp://…" />
            </div>
            <button className="btn" type="submit">Register</button>
          </form>
        </div>
      )}

      <div className="card">
        <div style={{ display: 'flex', gap: 8, marginBottom: 14 }}>
          {['all', 'fixed', 'mobile'].map((f) => (
            <button key={f} className={`pill ${filter === f ? 'active' : ''}`} onClick={() => setFilter(f)}>
              {f === 'all' ? 'All' : f === 'fixed' ? 'Fixed Cameras' : 'Mobile Cameras'}
            </button>
          ))}
        </div>

        {visible.length === 0 && <div className="empty-state">No cameras match the filter</div>}
        {visible.length > 0 && (
          <table className="data">
            <thead>
              <tr>
                <th>#</th>
                <th>Camera</th>
                <th>Type</th>
                <th>Location</th>
                <th>Status</th>
                <th>Stream</th>
                <th>Last Seen</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {visible.map((c) => (
                <tr key={c.id}>
                  <td>{c.id}</td>
                  <td>
                    {c.name}
                    {c.camera_type === 'mobile' && <div className="muted" style={{ fontSize: 12 }}>{c.device_id}</div>}
                  </td>
                  <td>
                    <span className={`pill ${c.camera_type === 'mobile' ? 'active' : ''}`}>
                      {c.camera_type === 'mobile' ? '📱 Phone' : '🎥 Fixed'}
                    </span>
                  </td>
                  <td>{c.location}</td>
                  <td>
                    {c.is_streaming ? (
                      <StatusBadge status="LIVE" />
                    ) : (
                      <StatusBadge status={c.status} />
                    )}
                  </td>
                  <td>
                    <span className="dot" style={{ background: c.is_streaming ? 'var(--good)' : 'var(--bad)' }} />
                    {c.is_streaming ? 'Live' : 'Off'}
                  </td>
                  <td className="muted">
                    {c.last_seen ? new Date(c.last_seen).toLocaleString() : '—'}
                  </td>
                  <td>
                    <button className="btn-outline" onClick={() => updateStatus(c, c.status === 'online' ? 'inactive' : 'online')}>
                      {c.status === 'online' || c.is_streaming ? 'Suspend' : 'Activate'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
