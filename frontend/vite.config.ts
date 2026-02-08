import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    watch: {
      usePolling: true, // Required for Docker hot reload
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor': ['react', 'react-dom', 'react-router-dom'],
          'three-js': ['three', '@react-three/fiber', '@react-three/drei'],
          'ui-viz': ['recharts', 'framer-motion', 'gsap', 'lucide-react'],
        }
      }
    }
  }
})
