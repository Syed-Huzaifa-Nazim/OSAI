// defineConfig comes from vitest/config, not vite, so the `test` block below is
// typed. The triple-slash reference alone stopped being enough in Vitest 2.x,
// which is what broke `npm run build` while `tsc --noEmit` stayed clean.
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'node:path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  build: {
    rollupOptions: {
      output: {
        // Recharts and framer-motion are large and only needed on the app
        // pages; splitting them keeps the marketing entry chunk small.
        manualChunks: {
          react: ['react', 'react-dom', 'react-router-dom'],
          charts: ['recharts'],
          motion: ['framer-motion'],
          data: ['@tanstack/react-query', '@supabase/supabase-js'],
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_PROXY_TARGET ?? 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
    // Worker threads rather than child processes. Vitest's default `forks`
    // pool dies with ERR_IPC_CHANNEL_CLOSED partway through this suite on
    // Node 24, which surfaces as an unhandled rejection and takes the run
    // with it regardless of whether the tests themselves passed.
    pool: 'threads',
  },
})
