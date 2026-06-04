import { Navigate, Link, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import HeroBackground from '../components/landing/HeroBackground'
import ParticleCanvas from '../components/landing/ParticleCanvas'
import LandingAuthForm from '../components/landing/LandingAuthForm'
import ReportIssueButton from '../components/feedback/ReportIssueButton'
import '../styles/landing.css'

export default function AuthPage() {
  const { user, loading } = useAuth()
  const location = useLocation()
  const initialTab = location.pathname === '/register' ? 'register' : 'login'

  if (loading) {
    return (
      <div className="landing-page min-h-screen flex items-center justify-center">
        <p className="landing-body-text text-white/50">Loading…</p>
      </div>
    )
  }

  if (user) {
    return <Navigate to="/dashboard" replace />
  }

  return (
    <div className="landing-page min-h-screen relative flex flex-col">
      <div className="absolute inset-0">
        <HeroBackground />
        <ParticleCanvas />
      </div>

      <header className="relative z-10 px-6 py-5">
        <Link
          to="/"
          className="inline-flex items-center gap-2 text-white/75 hover:text-white transition-colors landing-body-text font-medium"
        >
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M19 12H5M12 19l-7-7 7-7" />
          </svg>
          Back to home
        </Link>
      </header>

      <main className="relative z-10 flex-1 flex flex-col items-center justify-center px-6 py-10">
        <div className="text-center mb-10 max-w-lg">
          <Link
            to="/"
            className="landing-hero-title block hover:text-white/90 transition-colors"
          >
            SmartRiver
          </Link>
          <p className="mt-4 landing-hero-desc text-white/65">
            {initialTab === 'register'
              ? 'Create your account to access river monitoring and forecasts.'
              : 'Welcome back — sign in to continue.'}
          </p>
        </div>

        <LandingAuthForm initialTab={initialTab} redirectFrom={location.state?.from} />

        <div className="mt-8 text-center">
          <ReportIssueButton className="landing-body-text text-white/45 hover:text-[var(--color-primary)] underline underline-offset-2" />
        </div>
      </main>
    </div>
  )
}
