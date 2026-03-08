import React from 'react'
import ReactDOM from 'react-dom/client'
import 'leaflet/dist/leaflet.css'
import './styles/index.css'

function showError(msg) {
  const root = document.getElementById('root')
  if (root) {
    root.innerHTML = `<div style="padding: 2rem; font-family: system-ui; max-width: 600px; margin: 2rem auto;">
      <h1 style="color: #b91c1c;">SmartRiver failed to load</h1>
      <pre style="background: #fef2f2; padding: 1rem; border-radius: 8px; overflow: auto;">${String(msg).replace(/</g, '&lt;')}</pre>
      <p style="color: #6b7280;">Open DevTools (F12) → Console for details.</p>
    </div>`
  }
}

async function bootstrap() {
  try {
    const { default: App } = await import('./App')
    const { default: ErrorBoundary } = await import('./components/common/ErrorBoundary')

    ReactDOM.createRoot(document.getElementById('root')).render(
      <React.StrictMode>
        <ErrorBoundary>
          <App />
        </ErrorBoundary>
      </React.StrictMode>
    )
  } catch (err) {
    console.error('SmartRiver bootstrap error:', err)
    showError(err?.message || err?.stack || String(err))
  }
}

bootstrap()
