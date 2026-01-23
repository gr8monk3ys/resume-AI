'use client'

import { useState, useEffect, useCallback, useRef, ReactNode } from 'react'
import { useRouter, usePathname } from 'next/navigation'
import {
  AuthContext,
  getStoredTokens,
  setStoredTokens,
  clearStoredTokens,
} from '@/lib/auth'
import { authApi, ApiError } from '@/lib/api'
import type { User, AuthTokens } from '@/types'

/**
 * Token refresh interval in milliseconds (14 minutes)
 * JWT tokens typically expire in 15 minutes, so we refresh slightly before
 */
const TOKEN_REFRESH_INTERVAL = 14 * 60 * 1000

/**
 * Minimum time before expiration to trigger refresh (1 minute)
 */
const MIN_REFRESH_BUFFER = 60 * 1000

/**
 * Protected routes that require authentication
 */
const PROTECTED_ROUTES = [
  '/resumes',
  '/jobs',
  '/interview',
  '/documents',
  '/career',
  '/profile',
  '/settings',
  '/cover-letters',
  '/ai-assistant',
]

/**
 * Auth routes that authenticated users should be redirected from
 */
const AUTH_ROUTES = ['/login', '/register']

/**
 * Parse JWT token to extract expiration time
 * @param token - JWT token string
 * @returns Expiration timestamp in milliseconds, or null if invalid
 */
function getTokenExpiration(token: string): number | null {
  try {
    const payload = token.split('.')[1]
    if (!payload) return null

    const decoded = JSON.parse(atob(payload))
    if (typeof decoded.exp === 'number') {
      return decoded.exp * 1000 // Convert to milliseconds
    }
    return null
  } catch {
    return null
  }
}

/**
 * Check if token is close to expiration or already expired
 * @param token - JWT token string
 * @returns true if token should be refreshed
 */
function shouldRefreshToken(token: string): boolean {
  const expiration = getTokenExpiration(token)
  if (!expiration) return true

  const now = Date.now()
  const timeUntilExpiry = expiration - now

  return timeUntilExpiry < MIN_REFRESH_BUFFER
}

/**
 * AuthProvider component that manages authentication state
 * Provides authentication context to the entire application
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<User | null>(null)
  const [tokens, setTokens] = useState<AuthTokens | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [authError, setAuthError] = useState<string | null>(null)
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null)
  const isRefreshingRef = useRef(false)

  /**
   * Clear all auth state and storage
   */
  const clearAuthState = useCallback(() => {
    clearStoredTokens()
    setTokens(null)
    setUser(null)
    setAuthError(null)

    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current)
      refreshTimerRef.current = null
    }
  }, [])

  /**
   * Refresh the access token using the refresh token
   * Handles token expiration and authentication errors gracefully
   */
  const refreshTokens = useCallback(async (): Promise<boolean> => {
    // Prevent concurrent refresh attempts
    if (isRefreshingRef.current) {
      return false
    }

    const currentTokens = getStoredTokens()
    if (!currentTokens?.refresh_token) {
      return false
    }

    isRefreshingRef.current = true

    try {
      const newTokens = await authApi.refresh(currentTokens.refresh_token)
      setStoredTokens(newTokens)
      setTokens(newTokens)
      setAuthError(null)
      return true
    } catch (error) {
      // If refresh fails, clear auth state
      console.error('Token refresh failed:', error)
      clearAuthState()

      // Only redirect if on a protected route
      if (PROTECTED_ROUTES.some((route) => pathname.startsWith(route))) {
        router.push('/login')
      }

      return false
    } finally {
      isRefreshingRef.current = false
    }
  }, [clearAuthState, pathname, router])

  /**
   * Set up automatic token refresh timer
   */
  const setupRefreshTimer = useCallback(() => {
    // Clear any existing timer
    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current)
    }

    // Set up periodic refresh
    refreshTimerRef.current = setInterval(async () => {
      const currentTokens = getStoredTokens()
      if (currentTokens?.access_token) {
        if (shouldRefreshToken(currentTokens.access_token)) {
          await refreshTokens()
        }
      }
    }, TOKEN_REFRESH_INTERVAL)
  }, [refreshTokens])

  /**
   * Initialize auth state from stored tokens on mount
   */
  useEffect(() => {
    async function initializeAuth() {
      const stored = getStoredTokens()

      if (!stored) {
        setIsLoading(false)
        return
      }

      // Check if access token needs refresh
      if (shouldRefreshToken(stored.access_token)) {
        const refreshed = await refreshTokens()
        if (!refreshed) {
          setIsLoading(false)
          return
        }
      } else {
        setTokens(stored)
      }

      // Fetch user info with current token
      const currentToken = getStoredTokens()?.access_token
      if (!currentToken) {
        setIsLoading(false)
        return
      }

      try {
        const userData = await authApi.me(currentToken)
        setUser(userData as User)
        setupRefreshTimer()
      } catch (error) {
        console.error('Failed to fetch user:', error)
        clearAuthState()
      } finally {
        setIsLoading(false)
      }
    }

    initializeAuth()

    // Cleanup timer on unmount
    return () => {
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current)
      }
    }
  }, [clearAuthState, refreshTokens, setupRefreshTimer])

  /**
   * Handle route protection
   * Redirect unauthenticated users from protected routes
   * Redirect authenticated users from auth routes
   */
  useEffect(() => {
    if (isLoading) return

    const isProtectedRoute = PROTECTED_ROUTES.some((route) =>
      pathname.startsWith(route)
    )
    const isAuthRoute = AUTH_ROUTES.includes(pathname)

    if (!user && isProtectedRoute) {
      // Store the intended destination for redirect after login
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('redirectAfterLogin', pathname)
      }
      router.push('/login')
    } else if (user && isAuthRoute) {
      // Redirect to stored destination or home
      let redirectTo = '/'
      if (typeof window !== 'undefined') {
        const stored = sessionStorage.getItem('redirectAfterLogin')
        if (stored) {
          redirectTo = stored
          sessionStorage.removeItem('redirectAfterLogin')
        }
      }
      router.push(redirectTo)
    }
  }, [user, isLoading, pathname, router])

  /**
   * Login with username and password
   * @param username - User's username
   * @param password - User's password
   * @throws ApiError if login fails
   */
  const login = useCallback(
    async (username: string, password: string) => {
      setAuthError(null)

      try {
        const tokenData = await authApi.login(username, password)
        setStoredTokens(tokenData)
        setTokens(tokenData)

        const userData = await authApi.me(tokenData.access_token)
        setUser(userData as User)

        setupRefreshTimer()

        // Handle redirect after successful login
        let redirectTo = '/'
        if (typeof window !== 'undefined') {
          const stored = sessionStorage.getItem('redirectAfterLogin')
          if (stored) {
            redirectTo = stored
            sessionStorage.removeItem('redirectAfterLogin')
          }
        }
        router.push(redirectTo)
      } catch (error) {
        if (error instanceof ApiError) {
          setAuthError(error.message)
          throw error
        }
        setAuthError('An unexpected error occurred')
        throw new Error('An unexpected error occurred')
      }
    },
    [router, setupRefreshTimer]
  )

  /**
   * Logout and clear all auth state
   */
  const logout = useCallback(() => {
    clearAuthState()
    router.push('/')
  }, [clearAuthState, router])

  /**
   * Register a new user account
   * @param data - Registration data
   * @throws ApiError if registration fails
   */
  const register = useCallback(
    async (data: {
      username: string
      email: string
      password: string
      full_name?: string
    }) => {
      setAuthError(null)

      try {
        await authApi.register(data)
        // Auto-login after successful registration
        await login(data.username, data.password)
      } catch (error) {
        if (error instanceof ApiError) {
          setAuthError(error.message)
          throw error
        }
        setAuthError('An unexpected error occurred')
        throw new Error('An unexpected error occurred')
      }
    },
    [login]
  )

  return (
    <AuthContext.Provider
      value={{
        user,
        tokens,
        isLoading,
        login,
        logout,
        register,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
