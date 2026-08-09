import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API URL is injected at runtime by the deployment environment.
// For local development the dev proxy keeps the browser on the same origin.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY || 'http://localhost:8000',
        changeOrigin: true,
        ws: true,
      },
      '/health': {
        target: process.env.VITE_API_PROXY || 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
