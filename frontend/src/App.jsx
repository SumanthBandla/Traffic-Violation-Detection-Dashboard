import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './context/AuthContext.jsx'
import Layout from './components/Layout.jsx'
import Login from './pages/Login.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Cameras from './pages/Cameras.jsx'
import LiveMonitoring from './pages/LiveMonitoring.jsx'
import Violations from './pages/Violations.jsx'
import Search from './pages/Search.jsx'
import QuantumControl from './pages/QuantumControl.jsx'

function Protected({ children }) {
  const { token } = useAuth()
  if (!token) return <Navigate to="/login" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Layout />
          </Protected>
        }
      >
        <Route index element={<Dashboard />} />
        <Route path="cameras" element={<Cameras />} />
        <Route path="live" element={<LiveMonitoring />} />
        <Route path="violations" element={<Violations />} />
        <Route path="search" element={<Search />} />
        <Route path="quantum-control" element={<QuantumControl />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
