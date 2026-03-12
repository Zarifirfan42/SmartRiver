import { NavLink } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

const links = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/river-health', label: 'River Health' },
  { to: '/forecast', label: 'Forecast' },
  { to: '/alerts', label: 'Alerts' },
  { to: '/anomaly-detection', label: 'Anomaly Detection' },
  { to: '/export', label: 'Export' },
]

export default function Sidebar() {
  const { isAdmin } = useAuth()
  return (
    <nav className="space-y-1">
      {links.map(({ to, label }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            `block rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-river-100 text-river-800' : 'text-surface-600 hover:bg-surface-100'}`
          }
        >
          {label}
        </NavLink>
      ))}
      {isAdmin && (
        <NavLink
          to="/upload"
          className={({ isActive }) =>
            `block rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-eco-100 text-eco-800' : 'text-surface-600 hover:bg-surface-100'}`
          }
        >
          Dataset Upload
        </NavLink>
      )}
    </nav>
  )
}
