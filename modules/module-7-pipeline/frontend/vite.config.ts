import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: parseInt(process.env.FRONTEND_PORT || '5173'),
    proxy: {
      '/api': {
        target: `http://localhost:${process.env.VITE_BACKEND_PORT || '8000'}`,
        changeOrigin: true,
      },
    },
  },
})
