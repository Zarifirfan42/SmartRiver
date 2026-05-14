import { useState } from 'react'
import { Link } from 'react-router-dom'
import { requestPasswordReset, resetPasswordWithOtp } from '../api/auth'

export default function ForgotPasswordPage() {
  const [step, setStep] = useState('email')
  const [email, setEmail] = useState('')
  const [otp, setOtp] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
  const [error, setError] = useState('')
  const [info, setInfo] = useState('')
  const [success, setSuccess] = useState(false)
  const [loading, setLoading] = useState(false)

  const handleRequestSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setInfo('')
    const emailTrim = (email || '').trim().toLowerCase()
    if (!emailTrim) {
      setError('Email is required.')
      return
    }
    setLoading(true)
    try {
      const data = await requestPasswordReset(emailTrim)
      setEmail(emailTrim)
      setStep('reset')
      setInfo(data?.message || 'Verification code sent to your email.')
    } catch (err) {
      const detail = err.response?.data?.detail
      const msg = Array.isArray(detail) ? detail[0] : detail
      setError(msg || err.message || 'Could not send reset email.')
    } finally {
      setLoading(false)
    }
  }

  const handleResetSubmit = async (e) => {
    e.preventDefault()
    setError('')
    if (!newPassword || newPassword.length < 6) {
      setError('New password must be at least 6 characters.')
      return
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.')
      return
    }
    if (!otp || otp.replace(/\s/g, '').length !== 6) {
      setError('Enter the 6-digit code from your email.')
      return
    }
    setLoading(true)
    try {
      await resetPasswordWithOtp({
        email,
        otp: otp.replace(/\s/g, ''),
        new_password: newPassword,
        confirm_password: confirmPassword,
      })
      setSuccess(true)
    } catch (err) {
      const detail = err.response?.data?.detail
      const msg = Array.isArray(detail) ? detail[0] : detail
      setError(msg || err.message || 'Password reset failed.')
    } finally {
      setLoading(false)
    }
  }

  if (success) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-surface-50 to-river-50/20 px-4">
        <div className="w-full max-w-md">
          <div className="card text-center space-y-4">
            <p className="text-surface-800 font-medium">Password reset successful. Please login.</p>
            <Link to="/login" className="btn-primary inline-block">
              Back to Login
            </Link>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-b from-surface-50 to-river-50/20 px-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <Link to="/" className="font-display text-2xl font-semibold text-river-700">SmartRiver</Link>
          <p className="mt-2 text-surface-600">
            {step === 'email' ? 'Reset your password' : 'Enter code & new password'}
          </p>
        </div>

        {step === 'email' && (
          <form onSubmit={handleRequestSubmit} className="card space-y-5">
            {error && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}
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
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Sending…' : 'Send verification code'}
            </button>
            <p className="text-center text-sm text-surface-500">
              Remember your password?{' '}
              <Link to="/login" className="font-medium text-river-600 hover:text-river-700">
                Back to Login
              </Link>
            </p>
          </form>
        )}

        {step === 'reset' && (
          <form onSubmit={handleResetSubmit} className="card space-y-5">
            {info && (
              <div className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800">{info}</div>
            )}
            {error && (
              <div className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>
            )}
            <p className="text-sm text-surface-600">
              Code sent to <span className="font-medium text-surface-800">{email}</span>
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
            <div>
              <label htmlFor="newPassword" className="label">New password</label>
              <div className="relative">
                <input
                  id="newPassword"
                  type={showNewPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="input-field pr-11"
                  placeholder="••••••••"
                  minLength={6}
                />
                <button
                  type="button"
                  onClick={() => setShowNewPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 px-3 text-surface-500 hover:text-surface-700"
                  aria-label={showNewPassword ? 'Hide password' : 'Show password'}
                  title={showNewPassword ? 'Hide password' : 'Show password'}
                >
                  {showNewPassword ? '🙈' : '👁️'}
                </button>
              </div>
              <p className="text-xs text-surface-500 mt-1">At least 6 characters</p>
            </div>
            <div>
              <label htmlFor="confirmPassword" className="label">Confirm password</label>
              <div className="relative">
                <input
                  id="confirmPassword"
                  type={showConfirmPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="input-field pr-11"
                  placeholder="••••••••"
                />
                <button
                  type="button"
                  onClick={() => setShowConfirmPassword((v) => !v)}
                  className="absolute inset-y-0 right-0 px-3 text-surface-500 hover:text-surface-700"
                  aria-label={showConfirmPassword ? 'Hide password' : 'Show password'}
                  title={showConfirmPassword ? 'Hide password' : 'Show password'}
                >
                  {showConfirmPassword ? '🙈' : '👁️'}
                </button>
              </div>
              {confirmPassword && newPassword !== confirmPassword && (
                <p className="text-xs text-amber-600 mt-1">Passwords do not match</p>
              )}
            </div>
            <button type="submit" disabled={loading} className="btn-primary w-full">
              {loading ? 'Resetting…' : 'Reset password'}
            </button>
            <button
              type="button"
              className="w-full text-sm text-surface-600 hover:text-surface-800"
              onClick={() => { setStep('email'); setOtp(''); setError(''); setInfo('') }}
            >
              Use a different email
            </button>
            <p className="text-center text-sm text-surface-500">
              <Link to="/login" className="font-medium text-river-600 hover:text-river-700">
                Back to Login
              </Link>
            </p>
          </form>
        )}
      </div>
    </div>
  )
}
