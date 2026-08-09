import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext.jsx'

const NAV = [
  { to: '/', label: 'Dashboard', icon: '◈' },
  { to: '/cameras', label: 'Cameras', icon: '📷' },
  { to: '/live', label: 'Live Monitoring', icon: '▶' },
  { to: '/violations', label: 'Violations', icon: '⚠' },
  { to: '/search', label: 'Search', icon: '🔍' },
  { to: '/quantum-control', label: 'Quantum Control', icon: '∿' },
]

export default function Layout() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="layout">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">◈</span>
          <div>
            <strong>Traffic Monitor</strong>
            <small>Smart Traffic Platform</small>
          </div>
        </div>
        <nav className="nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === '/'}
              className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')}
            >
              <span>{item.icon}</span> {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="user-chip">
            <div>
              <strong>{user?.full_name || user?.username}</strong>
              <small>{user?.role}</small>
            </div>
          </div>
          <button className="btn-ghost" onClick={handleLogout}>
            Logout
          </button>
        </div>
      </aside>
      <main className="content">
        <Outlet />
      </main>
    </div>
  )
}
