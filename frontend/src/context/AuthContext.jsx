import { createContext, useContext, useState, useCallback, useEffect } from 'react'
import api from '../api/client'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('smartriver_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })
  const [loading, setLoading] = useState(!!localStorage.getItem('smartriver_token'))

  // Validate token on mount and restore user
  useEffect(() => {
    const token = localStorage.getItem('smartriver_token')
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get('/auth/me')
      .then((res) => {
        const u = res.data
        setUser({ id: u.id, email: u.email, full_name: u.full_name, role: u.role })
        localStorage.setItem('smartriver_user', JSON.stringify({ id: u.id, email: u.email, full_name: u.full_name, role: u.role }))
      })
      .catch(() => {
        localStorage.removeItem('smartriver_token')
        localStorage.removeItem('smartriver_user')
        setUser(null)
      })
      .finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const res = await api.post('/auth/login', { email, password })
    const { access_token, user: u } = res.data
    localStorage.setItem('smartriver_token', access_token)
    localStorage.setItem('smartriver_user', JSON.stringify(u))
    setUser(u)
    return u
  }, [])

  const register = useCallback(async (email, password, fullName) => {
    const res = await api.post('/auth/register', { email, password, full_name: fullName || undefined })
    const { access_token, user: u } = res.data
    localStorage.setItem('smartriver_token', access_token)
    localStorage.setItem('smartriver_user', JSON.stringify(u))
    setUser(u)
    return u
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    localStorage.removeItem('smartriver_user')
    localStorage.removeItem('smartriver_token')
  }, [])

  useEffect(() => {
    const onLogout = () => logout()
    window.addEventListener('smartriver:auth-logout', onLogout)
    return () => window.removeEventListener('smartriver:auth-logout', onLogout)
  }, [logout])

  const isAdmin = user?.role === 'admin'

  return (
    <AuthContext.Provider value={{ user, login, register, logout, isAdmin, loading }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
