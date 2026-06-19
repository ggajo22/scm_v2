import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/test/setup.ts'],
    server: {
      deps: {
        // Force ESM modules to be treated correctly
        inline: [/@testing-library/],
      },
    },
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: [
        'src/components/ui/**',
        'src/test/**',
        'src/main.tsx',
        'src/vite-env.d.ts',
        'src/router/index.tsx',
        'src/App.tsx',
        'src/lib/queryClient.ts',
        'src/types/**',
        'src/components/AppLayout.tsx',
        'src/features/auth/LoginPage.tsx',
      ],
      thresholds: {
        lines: 80,
        functions: 80,
        branches: 80,
        statements: 80,
      },
    },
  },
})
