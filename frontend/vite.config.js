import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// In development the dev server proxies API calls to the FastAPI backend, so
// the browser only ever talks to one origin and CORS never comes into play.
// In production the same relative URLs are proxied by nginx (see
// frontend/nginx.conf), or you can point the app at a different host by
// setting VITE_API_BASE_URL at build time.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      '/api': { target: 'http://localhost:8000', changeOrigin: true },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    chunkSizeWarningLimit: 900,
  },
});
