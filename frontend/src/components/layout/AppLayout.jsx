import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const navPublic = [
  { to: '/dashboard', label: 'Dashboard', icon: '📊' },
  { to: '/river-health', label: 'River Health', icon: '🌊' },
  { to: '/forecast', label: 'Pollution Forecast', icon: '📈' },
  { to: '/alerts', label: 'Alert Monitoring', icon: '🔔' },
  { to: '/export', label: 'Report Export', icon: '📄' },
]
const navAdmin = [
  { to: '/upload', label: 'Dataset Upload', icon: '📤' },
]

export default function AppLayout() {
  const { user, logout, isAdmin } = useAuth()
  const navigate = useNavigate()

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
              {label}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-16 flex-shrink-0 flex items-center justify-between border-b border-surface-200 bg-white px-6 shadow-sm">
          <div className="text-sm text-surface-500">Predictive River Pollution Monitoring</div>
          <div className="flex items-center gap-4">
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
