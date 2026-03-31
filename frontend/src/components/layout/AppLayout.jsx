import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import ReportIssueButton from '../feedback/ReportIssueButton'
import * as feedbackApi from '../../api/feedback'

const navPublic = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/river-health', label: 'River Health', icon: '🌊' },
  { to: '/forecast', label: 'Pollution Forecast', icon: '📈' },
  { to: '/alerts', label: 'Alert Monitoring', icon: '🔔' },
]
const navAdmin = [
  { to: '/anomaly-detection', label: 'Anomaly Detection', icon: '⚠️' },
  { to: '/upload', label: 'Dataset Upload', icon: '📤' },
  { to: '/feedback-reports', label: 'Issue Reports', icon: '📝' },
]

export default function AppLayout() {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()
  const [issueCount, setIssueCount] = useState(0)

  useEffect(() => {
    if (!isAdmin) return
    let cancelled = false

    const load = async () => {
      try {
        const list = await feedbackApi.getFeedbackReports()
        if (!cancelled) setIssueCount(Array.isArray(list) ? list.length : 0)
      } catch {
        if (!cancelled) setIssueCount(0)
      }
    }

    load()
    const timer = setInterval(load, 30000)
    return () => {
      cancelled = true
      clearInterval(timer)
    }
  }, [isAdmin])

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen flex bg-surface-50">
      <aside className="w-60 flex-shrink-0 border-r border-surface-200 bg-white shadow-sm">
        <div className="flex h-16 items-center gap-2 border-b border-surface-200 px-4">
          <span className="text-xl font-display font-semibold text-river-700">SmartRiver</span>
        </div>
        <nav className="p-3 space-y-0.5">
          {navPublic.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-river-100 text-river-800' : 'text-surface-700 hover:bg-river-50 hover:text-river-700'}`
              }
            >
              <span>{icon}</span>
              {label}
            </NavLink>
          ))}
          {isAdmin && navAdmin.map(({ to, label, icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium ${isActive ? 'bg-eco-100 text-eco-800' : 'text-surface-700 hover:bg-eco-50 hover:text-eco-700'}`
              }
            >
              <span>{icon}</span>
              <span className="flex items-center gap-2">
                <span>{label}</span>
                {to === '/feedback-reports' && issueCount > 0 && (
                  <span className="inline-flex min-w-[1.25rem] items-center justify-center rounded-full bg-amber-100 px-1.5 py-0.5 text-[11px] font-semibold text-amber-800">
                    {issueCount}
                  </span>
                )}
              </span>
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 flex-shrink-0 flex items-center justify-between border-b border-surface-200 bg-white px-6 shadow-sm">
          <div className="text-sm text-surface-500">Predictive River Pollution Monitoring</div>
          <div className="flex items-center gap-4">
            <ReportIssueButton />
            <span className="text-sm text-surface-600">{user?.full_name || user?.email}</span>
            <button
              type="button"
              onClick={handleLogout}
              className="text-sm font-medium text-surface-600 hover:text-river-600"
            >
              Log out
            </button>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
