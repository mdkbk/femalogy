import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// In dev, /api/* is forwarded to the Python backend, so the browser never
// talks to another origin. In production, set VITE_API_URL instead.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.FEMALOGY_API ?? 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
