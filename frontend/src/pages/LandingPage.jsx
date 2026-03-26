import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import ReportIssueButton from '../components/feedback/ReportIssueButton'

/**
 * Public entry before login: title, one-line description, Login + Register only.
 * Authenticated users are sent straight to the app (feature routes stay protected).
 */
export default function LandingPage() {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-white">
        <p className="text-sm text-surface-500">Loading…</p>
      </div>
    )
  }

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="min-h-screen bg-white text-surface-900 flex flex-col">
      <main className="flex-1 flex flex-col items-center justify-center px-6 py-16 sm:py-24">
        <div className="w-full max-w-lg text-center space-y-8">
          <h1 className="font-display text-4xl sm:text-5xl font-semibold tracking-tight text-surface-900">
            SmartRiver
          </h1>
          <p className="text-base sm:text-lg text-surface-600 leading-relaxed">
            SmartRiver monitors and predicts river water quality using intelligent data analysis.
          </p>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-center gap-3 sm:gap-4 pt-2">
            <Link
              to="/login"
              className="inline-flex items-center justify-center rounded-lg border border-surface-300 bg-white px-6 py-3 text-sm font-medium text-surface-800 transition hover:bg-surface-50"
            >
              Login
            </Link>
            <Link to="/register" className="btn-primary inline-flex justify-center px-6 py-3 text-sm font-medium">
              Register
            </Link>
          </div>
          <div className="pt-6">
            <ReportIssueButton className="text-sm text-surface-500 hover:text-river-600 underline underline-offset-2" />
          </div>
        </div>
      </main>
    </div>
  )
}
