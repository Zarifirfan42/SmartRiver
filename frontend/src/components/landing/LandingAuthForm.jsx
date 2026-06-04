import { useState, useEffect } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../../context/AuthContext'

function apiErrorMessage(err, fallback) {
  if (err.code === 'ECONNABORTED' || String(err.message || '').toLowerCase().includes('timeout')) {
    return 'The server took too long to respond. Ensure the backend is running and try again.'
  }
  const detail = err.response?.data?.detail
  const msg = Array.isArray(detail) ? detail[0] : detail
  return msg || err.message || fallback
}

export default function LandingAuthForm({ initialTab = 'login', redirectFrom }) {
  const [tab, setTab] = useState(initialTab)
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [loading, setLoading] = useState(false)

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [fullName, setFullName] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [otp, setOtp] = useState('')
  const [registerStep, setRegisterStep] = useState('form')

  const { login, register, verifyEmail, resendVerification } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const switchTab = (next) => {
    setTab(next)
    setError('')
    setInfo('')
    setRegisterStep('form')
    setOtp('')
    navigate(next === 'register' ? '/register' : '/login', { replace: true, state: location.state })
  }

  useEffect(() => {
    setTab(initialTab)
  }, [initialTab])

  const handleLogin = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      await login(email, password)
      const from = redirectFrom?.pathname || location.state?.from?.pathname || '/dashboard'
      navigate(from, { replace: true })
    } catch (err) {
      const isNetworkError =
        !err.response &&
        (err.code === 'ERR_NETWORK' || err.code === 'ECONNABORTED' || err.message === 'Network Error')
      const is404 = err.response?.status === 404
      const is503 = err.response?.status === 503
      const raw = err.response?.data?.detail
      const detail =
        typeof raw === 'string'
          ? raw
          : Array.isArray(raw)
            ? raw.map((x) => (typeof x?.msg === 'string' ? x.msg : JSON.stringify(x))).join(' ')
            : raw != null
              ? JSON.stringify(raw)
              : err.message || 'Login failed'
      setError(
        is404
          ? 'Login service unavailable. Make sure the backend is running, then try again.'
          : isNetworkError
            ? 'Cannot connect to the server. Start the backend first: python -m uvicorn backend.app.main:app --reload --port 8000'
            : is503
              ? 'Server is busy or the auth database failed to open. Restart the backend and try again.'
              : detail
      )
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e) => {
    e.preventDefault()
    setError('')
    setInfo('')
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }
    setLoading(true)
    try {
      const result = await register(email, password, fullName)
      if (result?.requiresVerification) {
        setRegisterStep('verify')
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
          ? 'Registration service unavailable. Make sure the backend is running, then try again.'
          : isNetworkError
            ? 'Cannot connect to the server. Start the backend first: python -m uvicorn backend.app.main:app --reload --port 8000'
            : apiErrorMessage(err, 'Registration failed')
      )
    } finally {
      setLoading(false)
    }
  }

  const handleVerify = async (e) => {
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
    <div className="landing-auth-card w-full max-w-md mx-auto p-6 sm:p-8">
      {registerStep === 'form' && (
        <div className="flex gap-1 p-1 rounded-lg bg-white/5 mb-6">
          <button
            type="button"
            className={`landing-auth-tab ${tab === 'login' ? 'is-active' : ''}`}
            onClick={() => switchTab('login')}
          >
            Login
          </button>
          <button
            type="button"
            className={`landing-auth-tab ${tab === 'register' ? 'is-active' : ''}`}
            onClick={() => switchTab('register')}
          >
            Register
          </button>
        </div>
      )}

      {error && (
        <div className="rounded-lg bg-red-500/15 border border-red-500/30 px-3 py-2.5 landing-body-text text-red-200 mb-4">
          {error}
        </div>
      )}
      {info && (
        <div className="rounded-lg bg-emerald-500/15 border border-emerald-500/30 px-3 py-2.5 landing-body-text text-emerald-200 mb-4">
          {info}
        </div>
      )}

      {tab === 'login' && (
        <form key="login" onSubmit={handleLogin} className="landing-auth-panel space-y-4">
          <div>
            <label htmlFor="landing-email" className="landing-label">Email</label>
            <input
              id="landing-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="landing-input"
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <label htmlFor="landing-password" className="landing-label">Password</label>
            <div className="relative">
              <input
                id="landing-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="landing-input pr-11"
                placeholder="••••••••"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-0 px-3 text-white/40 hover:text-white/70"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>
          <button type="submit" disabled={loading} className="landing-submit-btn">
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
          <p className="text-center landing-body-text">
            <Link to="/forgot-password" className="text-[var(--color-primary)] hover:underline">
              Forgot password?
            </Link>
          </p>
        </form>
      )}

      {tab === 'register' && registerStep === 'form' && (
        <form key="register" onSubmit={handleRegister} className="landing-auth-panel space-y-4">
          <div>
            <label htmlFor="landing-name" className="landing-label">Full name</label>
            <input
              id="landing-name"
              type="text"
              autoComplete="name"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              className="landing-input"
              placeholder="Your name"
            />
          </div>
          <div>
            <label htmlFor="landing-reg-email" className="landing-label">Email</label>
            <input
              id="landing-reg-email"
              type="email"
              autoComplete="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="landing-input"
              placeholder="you@example.com"
              required
            />
          </div>
          <div>
            <label htmlFor="landing-reg-password" className="landing-label">Password</label>
            <div className="relative">
              <input
                id="landing-reg-password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="new-password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="landing-input pr-11"
                placeholder="At least 6 characters"
                required
                minLength={6}
              />
              <button
                type="button"
                onClick={() => setShowPassword((v) => !v)}
                className="absolute inset-y-0 right-0 px-3 text-white/40 hover:text-white/70"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? '🙈' : '👁️'}
              </button>
            </div>
          </div>
          <div>
            <label htmlFor="landing-confirm" className="landing-label">Confirm password</label>
            <input
              id="landing-confirm"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              className="landing-input"
              placeholder="Repeat password"
              required
            />
          </div>
          <button type="submit" disabled={loading} className="landing-submit-btn">
            {loading ? 'Creating account…' : 'Create account'}
          </button>
        </form>
      )}

      {tab === 'register' && registerStep === 'verify' && (
        <form key="verify" onSubmit={handleVerify} className="landing-auth-panel space-y-4">
          <p className="landing-body-text text-white/75">
            Enter the 6-digit code sent to{' '}
            <span className="font-medium text-white">{email}</span>
          </p>
          <div>
            <label htmlFor="landing-otp" className="landing-label">Verification code</label>
            <input
              id="landing-otp"
              type="text"
              inputMode="numeric"
              autoComplete="one-time-code"
              value={otp}
              onChange={(e) => setOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
              className="landing-input tracking-widest text-center text-lg"
              placeholder="000000"
              maxLength={6}
            />
          </div>
          <button type="submit" disabled={loading || otp.length !== 6} className="landing-submit-btn">
            {loading ? 'Verifying…' : 'Verify and continue'}
          </button>
          <button
            type="button"
            onClick={handleResend}
            disabled={loading}
            className="w-full landing-body-text font-medium text-[var(--color-primary)] hover:underline"
          >
            Resend code
          </button>
          <button
            type="button"
            className="w-full landing-body-text text-white/55 hover:text-white/85"
            onClick={() => { setRegisterStep('form'); setOtp(''); setError(''); setInfo('') }}
          >
            Back to registration
          </button>
        </form>
      )}
    </div>
  )
}
