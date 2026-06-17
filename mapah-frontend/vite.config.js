import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, '.', '')
  const backendTarget = env.VITE_BACKEND_ORIGIN || 'http://localhost:5050'

  return {
    plugins: [react()],
    server: {
      proxy: {
        '/api': backendTarget,
        '/auth': backendTarget,
      },
    },
  }
})
