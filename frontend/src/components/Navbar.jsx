/**
 * Navbar — Top navigation bar
 * Logo, main links, and user menu (login/logout).
 */
import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function Navbar() {
  const { user, logout } = useAuth()

  return (
    <nav className="border-b border-slate-200 bg-white shadow-sm">
      <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
        <Link to="/" className="font-semibold text-cyan-700">
          SmartRiver
        </Link>
        <div className="flex items-center gap-4">
          <Link to="/dashboard" className="text-sm text-slate-600 hover:text-cyan-600">
            Dashboard
          </Link>
          <Link to="/river-health" className="text-sm text-slate-600 hover:text-cyan-600">
            River Health
          </Link>
          {user ? (
            <>
              <span className="text-sm text-slate-500">{user.email}</span>
              <button
                type="button"
                onClick={logout}
                className="text-sm font-medium text-slate-600 hover:text-cyan-600"
              >
                Log out
              </button>
            </>
          ) : (
            <>
              <Link to="/login" className="text-sm font-medium text-slate-600 hover:text-cyan-600">
                Log in
              </Link>
              <Link
                to="/register"
                className="rounded-lg bg-cyan-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-cyan-700"
              >
                Register
              </Link>
            </>
          )}
        </div>
      </div>
    </nav>
  )
}
