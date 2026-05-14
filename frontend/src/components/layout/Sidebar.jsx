import { NavLink } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

export default function Sidebar() {
  const { isAdmin } = useAuth()
  return (
    <nav className="space-y-1">
      <NavLink
        to="/dashboard"
        className={({ isActive }) =>
          `block rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-river-100 text-river-800' : 'text-surface-600 hover:bg-surface-100'}`
        }
      >
        Dashboard
      </NavLink>
      <NavLink
        to="/river-health"
        className={({ isActive }) =>
          `block rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-river-100 text-river-800' : 'text-surface-600 hover:bg-surface-100'}`
        }
      >
        River Health
      </NavLink>
      <NavLink
        to="/forecast"
        className={({ isActive }) =>
          `block rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-river-100 text-river-800' : 'text-surface-600 hover:bg-surface-100'}`
        }
      >
        Forecast
      </NavLink>
      <NavLink
        to="/alerts"
        className={({ isActive }) =>
          `block rounded-lg px-3 py-2 text-sm font-medium ${isActive ? 'bg-river-100 text-river-800' : 'text-surface-600 hover:bg-surface-100'}`
        }
      >
        Alerts
      </NavLink>
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
