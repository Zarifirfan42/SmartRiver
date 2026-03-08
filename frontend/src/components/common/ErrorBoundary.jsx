import { Component } from 'react'

/**
 * Catches React render errors and shows a message instead of a blank white page.
 * Open DevTools (F12) → Console for the full error.
 */
export default class ErrorBoundary extends Component {
  state = { error: null }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    console.error('SmartRiver ErrorBoundary:', error, info?.componentStack)
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          padding: '2rem',
          fontFamily: 'system-ui, sans-serif',
          maxWidth: '600px',
          margin: '2rem auto',
          background: '#fef2f2',
          border: '1px solid #fecaca',
          borderRadius: '8px',
        }}>
          <h1 style={{ color: '#b91c1c', marginTop: 0 }}>Something went wrong</h1>
          <p style={{ color: '#991b1b' }}>{this.state.error?.message || String(this.state.error)}</p>
          <p style={{ fontSize: '0.875rem', color: '#6b7280' }}>
            Open Developer Tools (F12) → Console for details. Fix the error and refresh the page.
          </p>
          <button
            type="button"
            onClick={() => window.location.reload()}
            style={{
              marginTop: '0.5rem',
              padding: '0.5rem 1rem',
              background: '#dc2626',
              color: 'white',
              border: 'none',
              borderRadius: '6px',
              cursor: 'pointer',
            }}
          >
            Reload page
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
