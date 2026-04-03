import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig(async () => {
  const plugins = [react()]

  if (process.env.VITEST !== 'true') {
    const { default: tailwindcss } = await import('@tailwindcss/vite')
    plugins.push(tailwindcss())
  }

  return {
  plugins,
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  test: {
    // Vitest config – uses jsdom so React components can render
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.js'],
    css: false,
  },
  }
})
