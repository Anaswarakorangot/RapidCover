import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/tests/setup.js'],
    css: false,
    include: ['src/tests/**/*.{test,spec}.{js,jsx}'],
    exclude: ['src/tests/partner.test.js'],
  },
})
