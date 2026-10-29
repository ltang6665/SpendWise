import path from "path"
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(import.meta.dirname, "./src"),
    },
  },
  server: {
    allowedHosts: ["192.168.0.108", "localhost"],
    // We are explicitly telling Vite exactly which words to forward to Python
    proxy: {
      '/authentication': 'http://127.0.0.1:8000',
      '/users': 'http://127.0.0.1:8000',
      '/settings': 'http://127.0.0.1:8000',
      '/dashboard': 'http://127.0.0.1:8000',
      '/basket': 'http://127.0.0.1:8000',
      '/categories': 'http://127.0.0.1:8000',
      '/expenses': 'http://127.0.0.1:8000',
      '/budget': 'http://127.0.0.1:8000',
      '/alerts': 'http://127.0.0.1:8000',
      '/import': 'http://127.0.0.1:8000',
      '/bot': 'http://127.0.0.1:8000'
    }
  }
})