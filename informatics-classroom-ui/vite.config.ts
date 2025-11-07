import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // Use esbuild instead of Rollup to avoid native module issues
    minify: 'esbuild',
    rollupOptions: {
      external: []
    }
  }
})
