import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

export default function Login() {
  const { login } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const friendlyError = (msg) => {
    const m = String(msg || '')
    if (/incorrect username or password/i.test(m))
      return 'Incorrect username or password. Check your credentials and try again.'
    if (/account disabled/i.test(m)) return 'This account is disabled. Contact your administrator.'
    if (/cannot reach the server/i.test(m)) return 'Cannot reach the server. Is the backend running?'
    if (/session expired/i.test(m)) return 'Session expired. Please log in again.'
    return m || 'Login failed. Please try again.'
  }

  const submit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(username, password)
      navigate('/')
    } catch (err) {
      setError(friendlyError(err.message))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-wrap">
      <form className="login-card" onSubmit={submit}>
        <h1>Traffic Violation Detection</h1>
        <p>Sign in to the monitoring dashboard</p>
        {error && (
          <div className="error-box" role="alert">
            {error}
          </div>
        )}
        <div className="form-row">
          <label>Username</label>
          <input
            value={username}
            onChange={(e) => {
              setUsername(e.target.value)
              if (error) setError('')
            }}
            autoComplete="username"
            required
          />
        </div>
        <div className="form-row">
          <label>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => {
              setPassword(e.target.value)
              if (error) setError('')
            }}
            autoComplete="current-password"
            required
          />
        </div>
        <button className="btn" style={{ width: '100%' }} disabled={loading}>
          {loading ? 'Signing in…' : 'Login'}
        </button>
        <p className="muted" style={{ marginTop: 18, fontSize: 13 }}>
          Demo accounts — admin / admin123 · officer / officer123 · analyst / analyst123
        </p>
      </form>
    </div>
  )
}
