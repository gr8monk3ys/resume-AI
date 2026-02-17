'use client'

import { createContext, useContext } from 'react'

import type { User } from '@/types'

/**
 * Authentication context interface
 *
 * Maintained for backward compatibility with existing components.
 * In production, AuthProvider populates this context using Clerk hooks.
 * In tests, test utilities wrap components with `<AuthContext.Provider>`
 * to inject mock auth state.
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
 * Auth context with default values.
 *
 * In production, AuthProvider reads from Clerk and provides values
 * to this context. In tests, test utilities use `<AuthContext.Provider>`
 * directly to inject mock state.
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
 * Hook to access auth context.
 *
 * @returns AuthContextType
 * @throws Error if used outside of AuthProvider or AuthContext.Provider
 */
export function useAuth(): AuthContextType {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
