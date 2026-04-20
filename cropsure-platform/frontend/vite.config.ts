import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/farms': 'http://localhost:8000',
      '/trigger': 'http://localhost:8000',
    },
  },
})
