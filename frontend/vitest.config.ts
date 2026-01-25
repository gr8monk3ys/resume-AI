import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import { resolve } from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    // Use happy-dom for better memory efficiency
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./vitest.setup.tsx'],
    include: ['**/*.{test,spec}.{ts,tsx}'],
    exclude: ['node_modules', '.next', 'dist'],
    // Increase timeout for async tests
    testTimeout: 10000,
    hookTimeout: 10000,
    teardownTimeout: 10000,
    // Use forks pool - separate processes with isolated memory
    pool: 'forks',
    poolOptions: {
      forks: {
        maxForks: 1,
        minForks: 1,
        isolate: true,
        singleFork: true,
      },
    },
    // Run tests sequentially to avoid memory issues
    sequence: {
      concurrent: false,
      shuffle: false,
    },
    fileParallelism: false,
    // Enable isolation for better memory management between test files
    isolate: true,
    // Clear mocks between tests
    clearMocks: true,
    restoreMocks: true,
    mockReset: true,
    unstubEnvs: true,
    unstubGlobals: true,
    // Reduce memory usage
    maxConcurrency: 1,
    // Limit workers
    maxWorkers: 1,
    minWorkers: 1,
    // Fail fast in CI environments
    bail: process.env.CI ? 1 : 0,
    // Suppress noisy console warnings during tests
    onConsoleLog(log, type) {
      // Suppress React hydration warnings and other noisy logs
      if (log.includes('Warning:') || log.includes('act(...)')) {
        return false
      }
      return true
    },
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        '.next/',
        '**/*.d.ts',
        '**/*.config.*',
        '**/vitest.setup.tsx',
      ],
    },
    css: {
      modules: {
        classNameStrategy: 'non-scoped',
      },
    },
  },
  resolve: {
    alias: {
      '@': resolve(__dirname, './src'),
    },
  },
})
