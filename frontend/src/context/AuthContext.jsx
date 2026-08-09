import { createContext, useContext, useEffect, useState } from 'react'
import { apiFetch } from '../api/client'

const TOKEN_KEY = 'tv_token'
const USER_KEY = 'tv_user'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem(TOKEN_KEY) || null)
  const [user, setUser] = useState(() => {
    try {
      return JSON.parse(localStorage.getItem(USER_KEY) || 'null')
    } catch {
      return null
    }
  })

  const login = async (username, password) => {
    const data = await apiFetch('/api/v1/auth/login', {
      method: 'POST',
      body: { username, password },
    })
    localStorage.setItem(TOKEN_KEY, data.access_token)
    localStorage.setItem(USER_KEY, JSON.stringify(data.user))
    setToken(data.access_token)
    setUser(data.user)
    return data.user
  }

  const logout = () => {
    localStorage.removeItem(TOKEN_KEY)
    localStorage.removeItem(USER_KEY)
    setToken(null)
    setUser(null)
  }

  useEffect(() => {
    if (!token) return
    const timer = setInterval(() => {
      apiFetch('/health', { token }).catch(() => {
        /* keep token; server health check only */
      })
    }, 60000)
    return () => clearInterval(timer)
  }, [token])

  return (
    <AuthContext.Provider value={{ token, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
