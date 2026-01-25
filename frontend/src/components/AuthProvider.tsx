'use client'

import { useRouter, usePathname } from 'next/navigation'
import { useState, useEffect, useCallback, useRef, ReactNode } from 'react'

import { authApi, ApiError } from '@/lib/api'
import { AuthContext, clearStoredTokens } from '@/lib/auth'

import type { User } from '@/types'

/**
 * Token refresh interval in milliseconds (14 minutes)
 * JWT tokens typically expire in 15-30 minutes, so we refresh periodically
 */
const TOKEN_REFRESH_INTERVAL = 14 * 60 * 1000

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
  '/analytics',
]

/**
 * Auth routes that authenticated users should be redirected from
 */
const AUTH_ROUTES = ['/login', '/register']

/**
 * AuthProvider component that manages authentication state
 *
 * Uses HTTP-only cookies for secure token storage:
 * - Tokens are managed by the server and browser, not JavaScript
 * - XSS attacks cannot steal tokens from cookies
 * - Auth state is verified by checking with the server
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter()
  const pathname = usePathname()
  const [user, setUser] = useState<User | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const [authError, setAuthError] = useState<string | null>(null)
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null)
  const isRefreshingRef = useRef(false)

  /**
   * Clear all auth state
   * Note: Cookies are cleared server-side via the logout endpoint
   */
  const clearAuthState = useCallback(() => {
    // Clear any legacy localStorage tokens
    clearStoredTokens()
    setUser(null)
    setIsAuthenticated(false)
    setAuthError(null)

    if (refreshTimerRef.current) {
      clearInterval(refreshTimerRef.current)
      refreshTimerRef.current = null
    }
  }, [])

  /**
   * Refresh the access token using HTTP-only cookie
   * The refresh token is sent automatically via cookies
   */
  const refreshAuth = useCallback(async (): Promise<boolean> => {
    // Prevent concurrent refresh attempts
    if (isRefreshingRef.current) {
      return false
    }

    isRefreshingRef.current = true

    try {
      // Call refresh endpoint - cookies are sent automatically
      await authApi.refresh()
      setAuthError(null)
      return true
    } catch (error) {
      // If refresh fails, user needs to log in again
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
    refreshTimerRef.current = setInterval(() => {
      void refreshAuth()
    }, TOKEN_REFRESH_INTERVAL)
  }, [refreshAuth])

  /**
   * Check authentication status by calling the /me endpoint
   * This is the secure way to verify auth with HTTP-only cookies
   */
  const checkAuthStatus = useCallback(async (): Promise<User | null> => {
    try {
      const userData = await authApi.checkAuth()
      return userData
    } catch {
      return null
    }
  }, [])

  /**
   * Initialize auth state on mount
   * Since we use HTTP-only cookies, we need to verify auth status with the server
   */
  useEffect(() => {
    let isMounted = true

    async function initializeAuth() {
      try {
        // Check if user is authenticated by calling /me endpoint
        const userData = await checkAuthStatus()

        if (!isMounted) return

        if (userData) {
          setUser(userData)
          setIsAuthenticated(true)
          setupRefreshTimer()
        } else {
          clearAuthState()
        }
      } catch (error) {
        if (!isMounted) return
        console.error('Auth initialization failed:', error)
        clearAuthState()
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    void initializeAuth()

    // Cleanup timer on unmount
    return () => {
      isMounted = false
      if (refreshTimerRef.current) {
        clearInterval(refreshTimerRef.current)
      }
    }
  }, [checkAuthStatus, clearAuthState, setupRefreshTimer])

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

    if (!isAuthenticated && isProtectedRoute) {
      // Store the intended destination for redirect after login
      if (typeof window !== 'undefined') {
        sessionStorage.setItem('redirectAfterLogin', pathname)
      }
      router.push('/login')
    } else if (isAuthenticated && isAuthRoute) {
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
  }, [isAuthenticated, isLoading, pathname, router])

  /**
   * Login with username and password
   * Server sets HTTP-only cookies on successful login
   */
  const login = useCallback(
    async (username: string, password: string) => {
      setAuthError(null)

      try {
        // Login - cookies are set by the server response
        await authApi.login(username, password)

        // Fetch user info to update state
        const userData = await authApi.checkAuth()
        if (!userData) {
          throw new Error('Failed to get user info after login')
        }

        setUser(userData)
        setIsAuthenticated(true)
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
   * Logout and clear authentication
   * Calls the logout endpoint to clear HTTP-only cookies server-side
   */
  const logout = useCallback(async () => {
    try {
      // Call logout endpoint to clear cookies
      await authApi.logout()
    } catch (error) {
      console.warn('Logout request failed:', error)
    } finally {
      // Clear local state regardless of API response
      clearAuthState()
      router.push('/')
    }
  }, [clearAuthState, router])

  /**
   * Register a new user account
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
        isAuthenticated,
        isLoading,
        authError,
        login,
        logout,
        register,
        refreshAuth,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}
