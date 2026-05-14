import { useState, useEffect } from 'react'
import * as feedbackApi from '../../api/feedback'

/**
 * Modal: Report Issue / Feedback — name (optional), email, message.
 * @param {boolean} open
 * @param {function} onClose
 * @param {{ email?: string }} defaultValues - pre-fill email when logged in
 */
export default function ReportIssueModal({ open, onClose, defaultValues = {} }) {
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [message, setMessage] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  useEffect(() => {
    if (!open) return
    setError(null)
    setSuccess(false)
    setName('')
    setMessage('')
    setEmail(defaultValues.email || '')
  }, [open, defaultValues.email])

  if (!open) return null

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError(null)
    if (!email.trim()) {
      setError('Please enter your email.')
      return
    }
    if (!message.trim()) {
      setError('Please enter a message.')
      return
    }
    setSubmitting(true)
    try {
      await feedbackApi.submitFeedback({ name, email, message })
      setSuccess(true)
    } catch (err) {
      const d = err.response?.data?.detail
      let msg = err.message || 'Something went wrong.'
      if (typeof d === 'string') msg = d
      else if (Array.isArray(d) && d.length) {
        msg = d.map((x) => (typeof x === 'string' ? x : x.msg || JSON.stringify(x))).join(' ')
      }
      setError(msg)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/40"
      role="dialog"
      aria-modal="true"
      aria-labelledby="report-issue-title"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        className="w-full max-w-md rounded-xl border border-surface-200 bg-white shadow-lg"
        onMouseDown={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between border-b border-surface-200 px-4 py-3">
          <h2 id="report-issue-title" className="font-display text-lg font-semibold text-surface-900">
            Report issue / Feedback
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg p-1 text-surface-500 hover:bg-surface-100 hover:text-surface-800"
            aria-label="Close"
          >
            ✕
          </button>
        </div>

        {success ? (
          <div className="px-4 py-8 text-center">
            <p className="text-surface-800 font-medium">Your report has been submitted successfully.</p>
            <button type="button" onClick={onClose} className="btn-primary mt-6">
              Close
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="px-4 py-4 space-y-4">
            {error && (
              <div className="rounded-lg border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
                {error}
              </div>
            )}
            <div>
              <label htmlFor="feedback-name" className="label">Name <span className="text-surface-400 font-normal">(optional)</span></label>
              <input
                id="feedback-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                className="input-field w-full"
                autoComplete="name"
                disabled={submitting}
              />
            </div>
            <div>
              <label htmlFor="feedback-email" className="label">Email</label>
              <input
                id="feedback-email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input-field w-full"
                autoComplete="email"
                disabled={submitting}
              />
            </div>
            <div>
              <label htmlFor="feedback-message" className="label">Message</label>
              <textarea
                id="feedback-message"
                required
                rows={5}
                value={message}
                onChange={(e) => setMessage(e.target.value)}
                className="input-field w-full resize-y min-h-[120px]"
                placeholder="Describe the issue or your feedback…"
                disabled={submitting}
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={onClose} className="btn-secondary" disabled={submitting}>
                Cancel
              </button>
              <button type="submit" className="btn-primary" disabled={submitting}>
                {submitting ? 'Sending…' : 'Submit'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  )
}
