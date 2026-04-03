import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        ws: true,
        configure: (proxy) => {
          proxy.on('error', (err) => {
            console.error(
              '[Vite proxy /api]',
              err?.message || err,
              '→ Start backend: python -m uvicorn backend.app.main:app --reload --port 8000',
            )
          })
        },
      },
    },
  },
})
