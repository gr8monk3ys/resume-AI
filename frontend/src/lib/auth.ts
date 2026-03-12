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
 * Removes any legacy tokens left in localStorage from the pre-cookie auth flow.
 */
export function clearLegacyTokens(): void {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('token_type')
  }
}
