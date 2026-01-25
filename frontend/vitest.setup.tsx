/// <reference types="@testing-library/jest-dom" />
import '@testing-library/jest-dom'
import { cleanup } from '@testing-library/react'
import { afterEach, beforeEach, vi } from 'vitest'
import { configure } from '@testing-library/react'

// Configure Testing Library to reduce async warnings
configure({
  asyncUtilTimeout: 5000,
})

// Mock localStorage and sessionStorage
const createStorageMock = () => {
  let store: Record<string, string> = {}
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key]
    }),
    clear: vi.fn(() => {
      store = {}
    }),
    get length() {
      return Object.keys(store).length
    },
    key: vi.fn((index: number) => Object.keys(store)[index] || null),
  }
}

Object.defineProperty(window, 'localStorage', {
  value: createStorageMock(),
  writable: true,
})

Object.defineProperty(window, 'sessionStorage', {
  value: createStorageMock(),
  writable: true,
})

// Cleanup after each test case
afterEach(async () => {
  // Clean up any pending timers or async operations
  vi.clearAllTimers()
  vi.clearAllMocks()

  // Clean up React Testing Library state
  cleanup()

  // Clear the document body to free memory
  while (document.body.firstChild) {
    document.body.removeChild(document.body.firstChild)
  }

  // Allow async state updates to complete
  await new Promise((resolve) => setTimeout(resolve, 0))

  // Explicitly trigger garbage collection if available (requires --expose-gc flag)
  if (global.gc) {
    global.gc()
  }
})

// Reset storage mocks before each test
beforeEach(() => {
  // Clear all timers and mocks
  vi.clearAllTimers()

  // Reset localStorage
  const localStorageMock = createStorageMock()
  Object.defineProperty(window, 'localStorage', {
    value: localStorageMock,
    writable: true,
  })

  // Reset sessionStorage
  const sessionStorageMock = createStorageMock()
  Object.defineProperty(window, 'sessionStorage', {
    value: sessionStorageMock,
    writable: true,
  })
})

// Mock Next.js router
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    prefetch: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
    refresh: vi.fn(),
  }),
  usePathname: () => '/',
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
}))

// Mock Next.js image component
vi.mock('next/image', () => ({
  default: ({ src, alt, ...props }: { src: string; alt: string }) => {
    // eslint-disable-next-line @next/next/no-img-element
    return <img src={src} alt={alt} {...props} />
  },
}))
