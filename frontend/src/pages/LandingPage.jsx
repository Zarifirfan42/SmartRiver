import { useState } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

const navLinks = [
  { to: '/', label: 'Home' },
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/river-health', label: 'River Health' },
  { to: '/forecast', label: 'Pollution Forecast' },
]

const features = [
  {
    title: 'Monitoring',
    description: 'Real-time Water Quality Index (WQI) and status across DOE monitoring stations. View trends and station-level data at a glance.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
    color: 'river',
  },
  {
    title: 'Forecasting',
    description: 'LSTM-based WQI predictions for the next 7–30 days. Plan ahead with AI-driven pollution trend forecasts.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
      </svg>
    ),
    color: 'eco',
  },
  {
    title: 'Alerts',
    description: 'Early warnings when pollution spikes or anomalies are detected. Stay informed with configurable notifications.',
    icon: (
      <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24" aria-hidden="true">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
      </svg>
    ),
    color: 'river',
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

  const isActive = (to) => (to === '/' ? location.pathname === '/' : location.pathname.startsWith(to))

  return (
    <div className="min-h-screen bg-surface-50">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 border-b border-surface-200 bg-white/95 backdrop-blur-md shadow-sm">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="flex h-16 items-center justify-between">
            {/* Logo - left */}
            <Link to="/" className="flex items-center gap-2 shrink-0">
              <span className="font-display text-xl font-bold tracking-tight text-river-700 sm:text-2xl">
                SmartRiver
              </span>
            </Link>

            {/* Desktop nav links */}
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

            {/* Right: Login/Register or Dashboard + Logout */}
            <div className="hidden md:flex md:items-center md:gap-3">
              {user ? (
                <>
                  <Link to="/dashboard" className="btn-primary text-sm">
                    Dashboard
                  </Link>
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
                    Log in
                  </Link>
                  <Link to="/register" className="btn-primary text-sm">
                    Register
                  </Link>
                </>
              )}
            </div>

            {/* Mobile menu button */}
            <button
              type="button"
              className="inline-flex items-center justify-center rounded-lg p-2 text-surface-600 hover:bg-surface-100 hover:text-surface-900 md:hidden"
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

          {/* Mobile menu panel */}
          {mobileMenuOpen && (
            <div className="border-t border-surface-200 py-4 md:hidden">
              <div className="flex flex-col gap-1">
                {navLinks.map(({ to, label }) => (
                  <Link
                    key={to}
                    to={to}
                    className="rounded-lg px-4 py-3 text-sm font-medium text-surface-700 hover:bg-river-50 hover:text-river-700"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    {label}
                  </Link>
                ))}
                <div className="mt-2 border-t border-surface-200 pt-2">
                  {user ? (
                    <>
                      <Link
                        to="/dashboard"
                        className="block rounded-lg px-4 py-3 text-sm font-medium text-river-700 hover:bg-river-50"
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        Dashboard
                      </Link>
                      <button
                        type="button"
                        onClick={handleLogout}
                        className="block w-full rounded-lg px-4 py-3 text-left text-sm font-medium text-surface-600 hover:bg-surface-100"
                      >
                        Log out
                      </button>
                    </>
                  ) : (
                    <>
                      <Link
                        to="/login"
                        className="block rounded-lg px-4 py-3 text-sm font-medium text-surface-700 hover:bg-river-50"
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        Log in
                      </Link>
                      <Link
                        to="/register"
                        className="block rounded-lg px-4 py-3 text-sm font-medium text-river-700 hover:bg-river-50"
                        onClick={() => setMobileMenuOpen(false)}
                      >
                        Register
                      </Link>
                    </>
                  )}
                </div>
              </div>
            </div>
          )}
        </div>
      </nav>

      {/* Hero section */}
      <section className="relative overflow-hidden bg-gradient-to-br from-river-50 via-white to-eco-50/50">
        <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6 sm:py-24 lg:px-8 lg:py-28">
          <div className="text-center">
            <h1 className="font-display text-4xl font-bold tracking-tight text-surface-900 sm:text-5xl lg:text-6xl">
              Predictive River Pollution{' '}
              <span className="text-river-600">Monitoring</span>
              <br className="hidden sm:block" />
              <span className="text-surface-700">for Malaysia</span>
            </h1>
            <p className="mx-auto mt-6 max-w-2xl text-lg text-surface-600 sm:text-xl">
              AI-powered water quality insights from DOE Malaysia data. Monitor WQI, forecast trends,
              and get early warnings for pollution anomalies.
            </p>
            <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
              {user ? (
                <Link to="/dashboard" className="btn-primary px-6 py-3 text-base shadow-lg shadow-river-600/25 hover:shadow-river-600/30">
                  Open Dashboard
                </Link>
              ) : (
                <>
                  <Link
                    to="/register"
                    className="btn-primary px-6 py-3 text-base shadow-lg shadow-river-600/25 hover:shadow-river-600/30"
                  >
                    Get started free
                  </Link>
                  <Link to="/login" className="btn-secondary px-6 py-3 text-base">
                    Sign in
                  </Link>
                </>
              )}
            </div>
          </div>
        </div>
      </section>

      {/* System description */}
      <section className="border-y border-surface-200/80 bg-white py-16 sm:py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <div className="mx-auto max-w-3xl text-center">
            <h2 className="font-display text-2xl font-semibold text-surface-900 sm:text-3xl">
              About SmartRiver
            </h2>
            <p className="mt-4 text-base text-surface-600 sm:text-lg leading-relaxed">
              SmartRiver is an AI-based river water quality monitoring system that helps authorities and
              researchers track pollution levels, predict trends, and respond to anomalies. It uses
              official DOE Malaysia monitoring data and applies machine learning for classification,
              forecasting, and anomaly detection—all in one clean dashboard.
            </p>
          </div>
        </div>
      </section>

      {/* Feature cards: Monitoring, Forecasting, Alerts */}
      <section className="py-16 sm:py-20">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <h2 className="font-display text-2xl font-semibold text-surface-900 text-center sm:text-3xl">
            Key features
          </h2>
          <p className="mx-auto mt-2 max-w-xl text-center text-surface-600">
            Everything you need to understand and act on river water quality.
          </p>
          <div className="mt-12 grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
            {features.map(({ title, description, icon, color }) => (
              <div
                key={title}
                className="group relative rounded-2xl border border-surface-200 bg-white p-6 shadow-sm transition hover:border-river-200 hover:shadow-md hover:shadow-river-500/5 sm:p-8"
              >
                <div
                  className={`inline-flex rounded-xl p-3 ${
                    color === 'river' ? 'bg-river-100 text-river-600' : 'bg-eco-100 text-eco-600'
                  }`}
                >
                  {icon}
                </div>
                <h3 className="mt-4 font-display text-lg font-semibold text-surface-900">{title}</h3>
                <p className="mt-2 text-sm text-surface-600 leading-relaxed">{description}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA strip */}
      <section className="bg-river-600 py-12 sm:py-16">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 text-center">
          <h2 className="font-display text-2xl font-semibold text-white sm:text-3xl">
            Ready to monitor river health?
          </h2>
          <p className="mt-2 text-river-100">
            Create a free account or sign in to access the dashboard.
          </p>
          <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
            {!user && (
              <>
                <Link
                  to="/register"
                  className="inline-flex items-center rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-river-700 shadow transition hover:bg-river-50"
                >
                  Create account
                </Link>
                <Link
                  to="/login"
                  className="inline-flex items-center rounded-lg border-2 border-white/80 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-white/10"
                >
                  Sign in
                </Link>
              </>
            )}
            {user && (
              <Link
                to="/dashboard"
                className="inline-flex items-center rounded-lg bg-white px-5 py-2.5 text-sm font-medium text-river-700 shadow transition hover:bg-river-50"
              >
                Go to Dashboard
              </Link>
            )}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-surface-200 bg-white py-8">
        <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
          <p className="text-center text-sm text-surface-500">
            SmartRiver — Final Year Project · Intelligent Computing / Data Science · DOE Malaysia data
          </p>
        </div>
      </footer>
    </div>
  )
}
