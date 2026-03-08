import { Link } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

export default function LandingPage() {
  const { user } = useAuth()
  return (
    <div className="min-h-screen bg-gradient-to-b from-surface-50 via-river-50/30 to-eco-50/20">
      <nav className="border-b border-surface-200/80 bg-white/80 backdrop-blur-sm">
        <div className="mx-auto flex h-16 max-w-6xl items-center justify-between px-4">
          <span className="font-display text-xl font-semibold text-river-700">SmartRiver</span>
          <div className="flex items-center gap-4">
            {user ? (
              <Link to="/dashboard" className="btn-primary">
                Go to Dashboard
              </Link>
            ) : (
              <>
                <Link to="/login" className="text-sm font-medium text-surface-600 hover:text-river-600">
                  Log in
                </Link>
                <Link to="/register" className="btn-primary">
                  Get started
                </Link>
              </>
            )}
          </div>
        </div>
      </nav>

      <section className="mx-auto max-w-6xl px-4 py-20 text-center">
        <h1 className="font-display text-4xl font-bold tracking-tight text-surface-900 sm:text-5xl">
          Predictive River Pollution{' '}
          <span className="text-river-600">Monitoring</span> for Malaysia
        </h1>
        <p className="mx-auto mt-6 max-w-2xl text-lg text-surface-600">
          AI-powered water quality insights from DOE Malaysia data. Monitor WQI, forecast trends,
          and get early warnings for pollution anomalies.
        </p>
        <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
          {user ? (
            <Link to="/dashboard" className="btn-primary px-6 py-3 text-base">
              Open Dashboard
            </Link>
          ) : (
            <>
              <Link to="/register" className="btn-primary px-6 py-3 text-base">
                Create free account
              </Link>
              <Link to="/login" className="btn-secondary px-6 py-3 text-base">
                Sign in
              </Link>
            </>
          )}
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="font-display text-2xl font-semibold text-surface-800 text-center mb-12">
          What SmartRiver offers
        </h2>
        <div className="grid gap-8 sm:grid-cols-2 lg:grid-cols-3">
          {[
            { title: 'River health at a glance', desc: 'Real-time WQI and status across stations.', icon: '🌊' },
            { title: '7–30 day forecasts', desc: 'LSTM-based WQI predictions for planning.', icon: '📈' },
            { title: 'Anomaly alerts', desc: 'Early warnings when pollution spikes are detected.', icon: '🔔' },
            { title: 'Interactive maps', desc: 'Explore monitoring stations and status on a map.', icon: '🗺️' },
            { title: 'Export reports', desc: 'Download CSV/PDF reports for your records.', icon: '📄' },
            { title: 'DOE-aligned WQI', desc: 'Water Quality Index following Malaysian DOE standards.', icon: '✓' },
          ].map(({ title, desc, icon }) => (
            <div key={title} className="card animate-fade-in">
              <span className="text-2xl">{icon}</span>
              <h3 className="mt-3 font-display font-semibold text-surface-800">{title}</h3>
              <p className="mt-1 text-sm text-surface-600">{desc}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-surface-200 bg-white/80 mt-20 py-8">
        <div className="mx-auto max-w-6xl px-4 text-center text-sm text-surface-500">
          SmartRiver — Final Year Project · Intelligent Computing / Data Science · DOE Malaysia data
        </div>
      </footer>
    </div>
  )
}
