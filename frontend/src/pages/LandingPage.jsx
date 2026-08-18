import { useRef, useCallback, useState, useEffect } from 'react'
import { Link, Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import HeroBackground from '../components/landing/HeroBackground'
import ParticleCanvas from '../components/landing/ParticleCanvas'
import FeatureCards from '../components/landing/FeatureCards'
import ReportIssueButton from '../components/feedback/ReportIssueButton'
import '../styles/landing.css'

function EntryChoiceModal({ open, onClose }) {
  if (!open) return null

  return (
    <div
      className="landing-choice-overlay"
      onClick={onClose}
      role="presentation"
    >
      <div
        className="landing-choice-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="entry-choice-title"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="entry-choice-title" className="landing-choice-title">
          How would you like to continue?
        </h2>
        <p className="landing-choice-desc">
          Guests can explore the full river dashboard. Admins sign in to manage data and notices.
        </p>
        <div className="landing-choice-actions">
          <Link to="/dashboard" className="landing-btn-primary landing-choice-btn">
            Continue as Guest
          </Link>
          <Link to="/login" className="landing-btn-ghost landing-choice-btn">
            Continue as Admin
          </Link>
        </div>
        <button type="button" className="landing-choice-cancel" onClick={onClose}>
          Cancel
        </button>
      </div>
    </div>
  )
}

export default function LandingPage() {
  const { user, loading } = useAuth()
  const heroRef = useRef(null)
  const glowRef = useRef(null)
  const [showEntryChoice, setShowEntryChoice] = useState(false)

  const handleCursorMove = useCallback((e) => {
    const glow = glowRef.current
    const hero = heroRef.current
    if (!glow || !hero) return
    const rect = hero.getBoundingClientRect()
    const x = e.clientX - rect.left
    const y = e.clientY - rect.top
    glow.style.setProperty('--cursor-x', `${x}px`)
    glow.style.setProperty('--cursor-y', `${y}px`)
    glow.classList.add('is-active')
  }, [])

  const handleCursorLeave = useCallback(() => {
    glowRef.current?.classList.remove('is-active')
  }, [])

  useEffect(() => {
    if (!showEntryChoice) return undefined
    const onKey = (e) => {
      if (e.key === 'Escape') setShowEntryChoice(false)
    }
    window.addEventListener('keydown', onKey)
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      window.removeEventListener('keydown', onKey)
      document.body.style.overflow = previousOverflow
    }
  }, [showEntryChoice])

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
    <div className="landing-page min-h-screen">
      <section
        ref={heroRef}
        className="relative min-h-screen flex flex-col"
        onMouseMove={handleCursorMove}
        onMouseLeave={handleCursorLeave}
      >
        <HeroBackground />
        <div ref={glowRef} className="hero-cursor-glow" />
        <ParticleCanvas />

        <div className="relative z-10 flex-1 flex flex-col justify-center max-w-7xl mx-auto w-full px-6 py-16 lg:py-24">
          <div className="max-w-2xl">
            <h1 className="landing-enter landing-enter-1 landing-hero-title">
              SmartRiver
            </h1>
            <p className="landing-enter landing-enter-2 mt-5 landing-hero-subtitle">
              Predictive Water Quality Intelligence for Malaysian Rivers
            </p>
            <p className="landing-enter landing-enter-3 mt-5 landing-hero-desc max-w-xl">
              Real-time WQI monitoring, ML-powered forecasts, and river health analytics
              across Peninsular Malaysia and Borneo.
            </p>

            <div className="landing-enter landing-enter-4 mt-10">
              <button
                type="button"
                className="landing-btn-primary"
                onClick={() => setShowEntryChoice(true)}
              >
                Get Started
              </button>
            </div>

            <div className="landing-enter landing-enter-5 mt-10 flex flex-wrap gap-x-6 gap-y-3">
              <span className="trust-badge">🌊 Live River Data</span>
              <span className="trust-badge hidden sm:inline text-white/20">|</span>
              <span className="trust-badge">🤖 ML Forecast 2026</span>
              <span className="trust-badge hidden sm:inline text-white/20">|</span>
              <span className="trust-badge">📊 Historical Data 2023–2025</span>
            </div>

            <p className="landing-enter landing-enter-5 mt-8 landing-body-text text-white/55">
              New here?{' '}
              <Link to="/register" className="text-[var(--color-primary)] hover:underline font-semibold">
                Create an account
              </Link>
            </p>
          </div>
        </div>
      </section>

      <div id="features">
        <FeatureCards />
      </div>

      <section className="py-20 px-6 text-center border-t border-white/5">
        <h2 className="landing-section-title mb-4">Ready to monitor Malaysia&apos;s rivers?</h2>
        <p className="landing-hero-desc text-white/65 mb-10 max-w-lg mx-auto">
          Join SmartRiver to access live WQI data, ML forecasts, and historical analytics.
        </p>
        <button
          type="button"
          className="landing-btn-primary"
          onClick={() => setShowEntryChoice(true)}
        >
          Get Started
        </button>
        <div className="mt-10">
          <ReportIssueButton className="landing-body-text text-white/45 hover:text-[var(--color-primary)] underline underline-offset-2" />
        </div>
      </section>

      <footer className="py-8 text-center landing-footer-text text-white/35 border-t border-white/5">
        SmartRiver · Water Quality Intelligence for Malaysia
      </footer>

      <EntryChoiceModal open={showEntryChoice} onClose={() => setShowEntryChoice(false)} />
    </div>
  )
}
