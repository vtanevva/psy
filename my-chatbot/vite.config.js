import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { fileURLToPath, URL } from 'node:url'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  root: '.',              // default
  base: '/',              // assets served from root
  build: {
    outDir: 'build',      // MUST match Flask static_folder
    emptyOutDir: true,
  },
  resolve: {
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url))
    }
  }
})
