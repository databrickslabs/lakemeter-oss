import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    // Output directly to backend/static for deployment
    // This ensures the served files are always in sync with the build
    outDir: '../backend/static',
    emptyOutDir: false,  // Don't delete pricing/ folder and other static assets
    rollupOptions: {
      output: {
        // Keep assets in assets/ subfolder with content hashes for cache busting
        assetFileNames: 'assets/[name]-[hash][extname]',
        chunkFileNames: 'assets/[name]-[hash].js',
        entryFileNames: 'assets/[name]-[hash].js',
      }
    }
  }
})

