import { useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import ReportIssueModal from './ReportIssueModal'

/**
 * Opens the report/feedback modal. Optional className for header vs landing styles.
 */
export default function ReportIssueButton({ className = '' }) {
  const [open, setOpen] = useState(false)
  const { user } = useAuth()

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className={className || 'text-sm font-medium text-surface-600 hover:text-river-600'}
      >
        Report Issue
      </button>
      <ReportIssueModal
        open={open}
        onClose={() => setOpen(false)}
        defaultValues={{ email: user?.email || '' }}
      />
    </>
  )
}
