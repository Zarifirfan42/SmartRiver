import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/** Before login: only Home, Login, Register. After login: Dashboard, River Health, Forecast, Alerts + Logout */
const navLinksUnauthenticated = [
  { to: '/login', label: 'Login' },
  { to: '/register', label: 'Register' },
]

const navLinksAuthenticated = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/river-health', label: 'River Health' },
  { to: '/forecast', label: 'Forecast' },
  { to: '/alerts', label: 'Alerts' },
]

const keyFeatures = [
  {
    title: 'Dashboard Monitoring',
    description: 'View WQI trends, station summaries, and status distribution at a glance.',
    icon: '📊',
  },
  {
    title: 'River Health Visualization',
    description: 'Explore river health on an interactive map with clear status indicators.',
    icon: '🗺️',
  },
  {
    title: 'Pollution Forecast',
    description: 'Predict future water quality using historical trends and smart forecasting.',
    icon: '🤖',
  },
  {
    title: 'Alert Monitoring',
    description: 'Get alerts when river status is Slightly Polluted or Polluted.',
    icon: '🚨',
  },
]

export default function LandingPage() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)

  const handleLogout = () => {
    logout()
    setMobileMenuOpen(false)
    navigate('/', { replace: true })
  }

  const navLinks = user ? navLinksAuthenticated : navLinksUnauthenticated
  const isActive = (to) => (to === '/' ? location.pathname === '/' : location.pathname.startsWith(to))

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Navigation — Before login: Home, Login, Register. After login: Dashboard, River Health, Forecast, Alerts */}
      <nav className="sticky top-0 z-50 border-b border-surface-200 bg-white shadow-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            <Link to="/" className="flex items-center shrink-0">
              <span className="font-display text-xl font-bold tracking-tight text-river-700 sm:text-2xl">
                SmartRiver
              </span>
            </Link>

            <div className="hidden md:flex md:items-center md:gap-1">
              {navLinks.map(({ to, label }) => (
                <Link
                  key={to}
                  to={to}
                  className={`rounded-lg px-3 py-2 text-sm font-medium transition ${
                    isActive(to)
                      ? 'bg-river-100 text-river-700'
                      : 'text-surface-600 hover:bg-river-50 hover:text-river-700'
                  }`}
                >
                  {label}
                </Link>
              ))}
            </div>

            <div className="hidden md:flex md:items-center md:gap-3">
              {user ? (
                <>
                  <span className="text-sm text-surface-500">{user.email}</span>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="rounded-lg px-3 py-2 text-sm font-medium text-surface-600 hover:bg-surface-100 hover:text-surface-900"
                  >
                    Log out
                  </button>
                </>
              ) : (
                <>
                  <Link
                    to="/login"
                    className="rounded-lg px-3 py-2 text-sm font-medium text-surface-600 transition hover:bg-river-50 hover:text-river-700"
                  >
                    Login
                  </Link>
                  <Link to="/register" className="btn-primary text-sm">
                    Register
                  </Link>
                </>
              )}
            </div>

            <button
              type="button"
              className="inline-flex items-center justify-center rounded-lg p-2 text-surface-600 hover:bg-surface-100 md:hidden"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-expanded={mobileMenuOpen}
              aria-label="Toggle menu"
            >
              {mobileMenuOpen ? (
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>

          {mobileMenuOpen && (
            <div className="border-t border-surface-200 py-4 md:hidden">
              <div className="flex flex-col gap-1">
                {navLinks.map(({ to, label }) => (
                  <Link
                    key={to}
                    to={to}
                    className="rounded-lg px-4 py-3 text-sm font-medium text-surface-700 hover:bg-river-50"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    {label}
                  </Link>
                ))}
                {user ? (
                  <>
                    <div className="mt-2 border-t border-surface-200 pt-2">
                      <span className="block px-4 py-2 text-xs text-surface-500">{user.email}</span>
                      <button
                        type="button"
                        onClick={handleLogout}
                        className="block w-full rounded-lg px-4 py-3 text-left text-sm font-medium text-surface-600 hover:bg-surface-100"
                      >
                        Log out
                      </button>
                    </div>
                  </>
                ) : (
                  <div className="mt-2 border-t border-surface-200 pt-2">
                    <Link
                      to="/login"
                      className="block rounded-lg px-4 py-3 text-sm font-medium text-surface-700 hover:bg-river-50"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Login
                    </Link>
                    <Link
                      to="/register"
                      className="block rounded-lg px-4 py-3 text-sm font-medium text-river-700 hover:bg-river-50"
                      onClick={() => setMobileMenuOpen(false)}
                    >
                      Register
                    </Link>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </nav>

      {/* Hero */}
      <section className="relative overflow-hidden bg-gradient-to-br from-river-50 via-white to-surface-50">
        <div className="mx-auto max-w-4xl px-4 py-16 sm:px-6 sm:py-20 lg:py-24">
          <div className="text-center">
            <h1 className="font-display text-4xl font-bold tracking-tight text-surface-900 sm:text-5xl">
              SmartRiver
            </h1>
            <p className="mt-4 text-xl font-medium text-river-600 sm:text-2xl">
              SmartRiver monitors and predicts river water quality using data analytics and intelligent forecasting.
            </p>
            <p className="mx-auto mt-6 max-w-2xl text-base text-surface-600 sm:text-lg leading-relaxed">
              Track historical river health, simulate today’s conditions, and visualize tomorrow’s risks with clear, actionable insights.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              {user ? (
                <Link to="/dashboard" className="btn-primary px-6 py-3 text-base">
                  Open Dashboard
                </Link>
              ) : (
                <>
                  <Link to="/login" className="btn-primary px-6 py-3 text-base">
                    Login
                  </Link>
                  <Link to="/register" className="btn-secondary px-6 py-3 text-base border-2 border-river-600 text-river-700 hover:bg-river-50">
                    Register
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* About */}
      <section className="border-t border-surface-200 bg-white py-16 sm:py-20">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-display text-2xl font-semibold text-surface-900 sm:text-3xl">
            About SmartRiver
          </h2>
          <p className="mt-6 text-base text-surface-600 leading-relaxed sm:text-lg">
            SmartRiver is a data-driven platform that helps monitor river conditions using Water Quality Index (WQI).
            It provides insights into river health, detects pollution risks, and predicts future water quality trends.
          </p>
        </div>
      </section>

      {/* Key features — 4 cards */}
      <section className="py-16 sm:py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="font-display text-2xl font-semibold text-surface-900 text-center sm:text-3xl">
            Key Features
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-center text-surface-600">
            Everything you need to monitor and act on river water quality.
          </p>
          <div className="mt-12 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
            {keyFeatures.map(({ title, description, icon }) => (
              <div
                key={title}
                className="rounded-xl border border-surface-200 bg-white p-6 shadow-sm transition hover:border-river-200 hover:shadow-md"
              >
                <div className="text-2xl mb-3" aria-hidden>{icon}</div>
                <h3 className="font-display text-lg font-semibold text-surface-900">{title}</h3>
                <p className="mt-3 text-sm text-surface-600 leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t border-surface-200 bg-river-600 py-16 sm:py-20">
        <div className="mx-auto max-w-3xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl">
            Start Monitoring River Health Today
          </h2>
          <p className="mt-4 text-river-100">
            Create an account or sign in to access the dashboard, maps, and forecasts.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            {!user && (
              <>
                <Link
                  to="/register"
                  className="inline-flex items-center rounded-lg bg-white px-6 py-3 text-base font-medium text-river-700 shadow-md transition hover:bg-river-50"
                >
                  Register
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center rounded-lg border-2 border-white px-6 py-3 text-base font-medium text-white transition hover:bg-white/10"
                >
                  Login
                </Link>
              </>
            )}
            {user && (
              <Link
                to="/dashboard"
                className="inline-flex items-center rounded-lg bg-white px-6 py-3 text-base font-medium text-river-700 shadow-md transition hover:bg-river-50"
              >
                Go to Dashboard
              </Link>
            )}
          </div>
        </div>
      </section>

      <footer className="border-t border-surface-200 bg-white py-8">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-surface-500">
            SmartRiver — Water Quality Monitoring and Prediction System
          </p>
        </div>
      </footer>
    </div>
  )
}
