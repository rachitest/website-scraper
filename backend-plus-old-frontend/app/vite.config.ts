import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react-swc'
import path from 'path'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file from parent directory
  const env = loadEnv(mode, path.resolve(__dirname, '..'), '')
  
  const appPort = env.APP_URL ? parseInt(new URL(env.APP_URL).port) : 3015
  const apiUrl = env.API_URL || 'http://localhost:5015'

  return {
    plugins: [react()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, './src'),
      },
    },
    server: {
      port: appPort,
      host: true,
      strictPort: true,
      proxy: {
        '/api': {
          target: apiUrl,
          changeOrigin: true,
          secure: false,
        },
      },
      allowedHosts: true,
      hmr: {
        clientPort: 443
      }
    },
  }
})