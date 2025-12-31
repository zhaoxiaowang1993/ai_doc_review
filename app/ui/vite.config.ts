import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    outDir: '../api/www'
  },
  server: {
    host: '127.0.0.1',
    port: 1230,
    proxy: {
      // Default to the local FastAPI port used in this repo.
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:1231',
        changeOrigin: true,
        secure: false
      },
      '/ws': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:1231',
        ws: true,
        changeOrigin: true,
        secure: false
      }
    }
  }
})
