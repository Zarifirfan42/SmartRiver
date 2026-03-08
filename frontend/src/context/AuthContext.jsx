import { createContext, useContext, useState, useCallback } from 'react'

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

  const login = useCallback((email, password) => {
    // Mock login – replace with API call
    const mockUser = {
      id: 1,
      email: email || 'user@example.com',
      full_name: 'Demo User',
      role: email && email.includes('admin') ? 'admin' : 'public',
    }
    setUser(mockUser)
    localStorage.setItem('smartriver_user', JSON.stringify(mockUser))
    localStorage.setItem('smartriver_token', 'mock-jwt-token')
    return Promise.resolve(mockUser)
  }, [])

  const register = useCallback((email, password, fullName) => {
    // Mock register – replace with API call
    return Promise.resolve().then(() => {
      const mockUser = {
        id: 2,
        email: email || 'new@example.com',
        full_name: fullName || 'New User',
        role: 'public',
      }
      setUser(mockUser)
      localStorage.setItem('smartriver_user', JSON.stringify(mockUser))
      localStorage.setItem('smartriver_token', 'mock-jwt-token')
      return mockUser
    })
  }, [])

  const logout = useCallback(() => {
    setUser(null)
    localStorage.removeItem('smartriver_user')
    localStorage.removeItem('smartriver_token')
  }, [])

  const isAdmin = user?.role === 'admin'

  return (
    <AuthContext.Provider value={{ user, login, register, logout, isAdmin }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
