import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, /api/* is forwarded to the Python backend, so the browser only ever talks
// to one origin (like production, where the backend serves this app itself).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.FEMALOGY_API ?? 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
