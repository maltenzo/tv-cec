import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import { viteSingleFile } from 'vite-plugin-singlefile';

// Todo en un solo ../index.html: main.py lo sirve tal cual en GET /. `npm run dev` hace proxy a la API real.
export default defineConfig({
  plugins: [react(), viteSingleFile()],
  build: { outDir: '..', emptyOutDir: false },
  server: { proxy: Object.fromEntries(['/state', '/status', '/command', '/media'].map(p => [p, { target: process.env.API || 'http://localhost:8000', changeOrigin: true }])) },
});
