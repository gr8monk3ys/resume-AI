'use client'

import { createContext, useContext } from 'react'

import type { User } from '@/types'

/**
 * Authentication context interface
 *
 * With HTTP-only cookie-based auth, tokens are managed by the browser
 * and not accessible to JavaScript. The frontend only tracks:
 * - User information (for UI display)
 * - Authentication state (isAuthenticated boolean)
 * - Loading state
 */
export interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  authError: string | null
  login: (username: string, password: string) => Promise<void>
  logout: () => Promise<void>
  register: (data: {
    username: string
    email: string
    password: string
    full_name?: string
  }) => Promise<void>
  refreshAuth: () => Promise<boolean>
}

/**
 * Auth context with default values
 */
export const AuthContext = createContext<AuthContextType>({
  user: null,
  isAuthenticated: false,
  isLoading: true,
  authError: null,
  login: async () => {},
  logout: async () => {},
  register: async () => {},
  refreshAuth: () => Promise.resolve(false),
})

/**
 * Hook to access auth context
 * @returns AuthContextType
 * @throws Error if used outside of AuthProvider
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

/**
 * NOTE: localStorage token storage has been removed for security.
 *
 * Tokens are now stored in HTTP-only cookies which:
 * 1. Cannot be accessed by JavaScript (XSS protection)
 * 2. Are automatically sent with requests (credentials: 'include')
 * 3. Are managed by the browser, not the application
 *
 * The following functions are kept as no-ops for backward compatibility
 * during migration, but will be removed in a future version.
 */

/**
 * @deprecated Tokens are now stored in HTTP-only cookies
 */
export function getStoredTokens(): null {
  console.warn(
    'getStoredTokens is deprecated. Tokens are now stored in HTTP-only cookies.'
  )
  return null
}

/**
 * @deprecated Tokens are now stored in HTTP-only cookies
 */
export function setStoredTokens(): void {
  console.warn(
    'setStoredTokens is deprecated. Tokens are now stored in HTTP-only cookies.'
  )
}

/**
 * @deprecated Tokens are now stored in HTTP-only cookies
 */
export function clearStoredTokens(): void {
  console.warn(
    'clearStoredTokens is deprecated. Use logout() to clear auth cookies.'
  )
  // Clean up any legacy tokens that might still exist
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('token_type')
  }
}
