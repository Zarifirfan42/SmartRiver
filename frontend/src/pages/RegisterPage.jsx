import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

function apiErrorMessage(err, fallback) {
  if (err.code === 'ECONNABORTED' || String(err.message || '').toLowerCase().includes('timeout')) {
    return 'The server took too long to respond. Ensure the backend is running and try again.'
  }
  const detail = err.response?.data?.detail
  const msg = Array.isArray(detail) ? detail[0] : detail
  return msg || err.message || fallback
}

export default function RegisterPage() {
  const [step, setStep] = useState('form')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [fullName, setFullName] = useState('')
  const [otp, setOtp] = useState('')
  const [info, setInfo] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const { register, verifyEmail, resendVerification } = useAuth()
  const navigate = useNavigate()

  const handleRegisterSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setInfo('')
    setLoading(true)
    try {
      const result = await register(email, password, fullName)
      if (result?.requiresVerification) {
        setStep('verify')
        setInfo(result.message || 'Verification code sent to your email.')
        return
      }
      if (result?.user) {
        navigate('/dashboard', { replace: true })
      }
    } catch (err) {
      const isNetworkError = !err.response && (err.code === 'ERR_NETWORK' || err.message === 'Network Error')
      const is404 = err.response?.status === 404
      setError(
        is404
          ? 'Registration service unavailable. Make sure the backend is running (see HOW_TO_RUN.md), then try again.'
          : isNetworkError
            ? 'Cannot connect to the server. Start the backend first (see HOW_TO_RUN.md): run "python -m uvicorn backend.app.main:app --reload --port 8000" from the project root.'
            : apiErrorMessage(err, 'Registration failed')
      )
    } finally {
      setLoading(false)
    }
  }

  const handleVerifySubmit = async (e) => {
    e.preventDefault()
    setError('')
    setInfo('')
    setLoading(true)
    try {
      await verifyEmail(email, otp)
      navigate('/dashboard', { replace: true })
    } catch (err) {
      setError(apiErrorMessage(err, 'Verification failed'))
    } finally {
      setLoading(false)
    }
  }

  const handleResend = async () => {
    setError('')
    setInfo('')
    setLoading(true)
    try {
      const data = await resendVerification(email)
      setInfo(data?.message || 'Verification code sent to your email.')
    } catch (err) {
      setError(apiErrorMessage(err, 'Could not resend code'))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-surface-50 to-river-50/20 px-4 py-12">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="font-display text-2xl font-semibold text-river-700">SmartRiver</Link>
          <p className="mt-2 text-surface-600">
            {step === 'form' ? 'Create your account' : 'Verify your email'}
          </p>
        </div>

        {step === 'form' && (
          <form onSubmit={handleRegisterSubmit} className="card space-y-5">
            {error && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}
            <div>
              <label htmlFor="fullName" className="label">Full name</label>
              <input
                id="fullName"
                type="text"
                autoComplete="name"
                value={fullName}
                onChange={(e) => setFullName(e.target.value)}
                className="input-field"
                placeholder="Your name"
              />
            </div>
            <div>
              <label htmlFor="email" className="label">Email</label>
              <input
                id="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field"
                placeholder="you@example.com"
              />
            </div>
            <div>
              <label htmlFor="password" className="label">Password</label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input-field pr-11"
                  placeholder="At least 6 characters"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 px-3 text-surface-500 hover:text-surface-700"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? '🙈' : '👁️'}
                </button>
              </div>
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Creating account…' : 'Create account'}
            </button>
            <p className="text-center text-sm text-surface-500">
              Already have an account?{' '}
              <Link to="/login" className="font-medium text-river-600 hover:text-river-700">
                Sign in
              </Link>
            </p>
          </form>
        )}

        {step === 'verify' && (
          <form onSubmit={handleVerifySubmit} className="card space-y-5">
            {info && (
              <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{info}</div>
            )}
            {error && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}
            <p className="text-sm text-surface-600">
              Enter the 6-digit code we sent to{' '}
              <span className="font-medium text-surface-800">{email}</span>
            </p>
            <div>
              <label htmlFor="otp" className="label">Verification code</label>
              <input
                id="otp"
                type="text"
                inputMode="numeric"
                autoComplete="one-time-code"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                className="input-field tracking-widest text-center text-lg"
                placeholder="000000"
                maxLength={6}
              />
            </div>
            <button type="submit" disabled={loading || otp.length !== 6} className="btn-primary w-full">
              {loading ? 'Verifying…' : 'Verify and continue'}
            </button>
            <button
              type="button"
              onClick={handleResend}
              disabled={loading}
              className="w-full text-sm font-medium text-river-600 hover:text-river-700"
            >
              Resend code
            </button>
            <p className="text-center text-sm text-surface-500">
              <button
                type="button"
                className="font-medium text-river-600 hover:text-river-700"
                onClick={() => { setStep('form'); setOtp(''); setError(''); setInfo('') }}
              >
                Back
              </button>
              {' · '}
              <Link to="/login" className="font-medium text-river-600 hover:text-river-700">
                Sign in
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
