/**
 * API client — Axios instance with base URL and auth header.
 * In dev we use relative /api/v1 so Vite proxies to the backend (avoids network/CORS issues).
 */
import axios from 'axios'

const baseURL =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? '/api/v1' : 'http://localhost:8000/api/v1')

const resolvedBase = baseURL.startsWith('http')
  ? (baseURL.includes('/api/v1') ? baseURL.replace(/\/$/, '') : `${baseURL.replace(/\/$/, '')}/api/v1`)
  : baseURL

export const api = axios.create({
  baseURL: resolvedBase,
  headers: { 'Content-Type': 'application/json' },
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('smartriver_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('smartriver_token')
      localStorage.removeItem('smartriver_user')
      window.dispatchEvent(new CustomEvent('smartriver:auth-logout'))
    }
    return Promise.reject(err)
  }
)

export default api
