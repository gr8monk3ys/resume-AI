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
  '/dashboard',
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

function isProtectedRoute(pathname: string): boolean {
  return PROTECTED_ROUTES.some(
    (route) => pathname === route || pathname.startsWith(`${route}/`)
  )
}

function isSafeRedirectPath(pathname: string | null): pathname is string {
  return Boolean(pathname && pathname.startsWith('/') && !pathname.startsWith('//'))
}

function getPostLoginRedirect(): string {
  if (typeof window === 'undefined') {
    return '/'
  }

  const queryRedirect = new URLSearchParams(window.location.search).get(
    'redirectTo'
  )
  if (isSafeRedirectPath(queryRedirect)) {
    return queryRedirect
  }

  const storedRedirect = sessionStorage.getItem('redirectAfterLogin')
  if (isSafeRedirectPath(storedRedirect)) {
    sessionStorage.removeItem('redirectAfterLogin')
    return storedRedirect
  }

  return '/'
}

interface AuthState {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  authError: string | null
}

const INITIAL_AUTH_STATE: AuthState = {
  user: null,
  isAuthenticated: false,
  isLoading: true,
  authError: null,
}

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
  const [authState, setAuthState] = useState<AuthState>(INITIAL_AUTH_STATE)
  const refreshTimerRef = useRef<NodeJS.Timeout | null>(null)
  const isRefreshingRef = useRef(false)
  const { user, isAuthenticated, isLoading, authError } = authState

  const applyAuthenticatedUser = useCallback((userData: User) => {
    setAuthState({
      user: userData,
      isAuthenticated: true,
      isLoading: false,
      authError: null,
    })
  }, [])

  /**
   * Clear all auth state
   * Note: Cookies are cleared server-side via the logout endpoint
   */
  const clearAuthState = useCallback((nextIsLoading = false) => {
    // Clear any legacy localStorage tokens
    clearStoredTokens()
    setAuthState({
      user: null,
      isAuthenticated: false,
      isLoading: nextIsLoading,
      authError: null,
    })

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
      setAuthState((prev) => ({ ...prev, authError: null }))
      return true
    } catch (error) {
      // If refresh fails, user needs to log in again
      console.error('Token refresh failed:', error)
      clearAuthState()
      const currentPathname = pathname ?? '/'

      // Only redirect if on a protected route
      if (isProtectedRoute(currentPathname)) {
        router.push(`/login?redirectTo=${encodeURIComponent(currentPathname)}`)
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
   * Check authentication status with a non-error bootstrap endpoint
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
   * Since we use HTTP-only cookies, we verify auth status with the server
   */
  useEffect(() => {
    let isMounted = true

    async function initializeAuth() {
      try {
        // Check if user is authenticated without treating logged-out visitors as failures
        const userData = await checkAuthStatus()

        if (!isMounted) return

        if (userData) {
          applyAuthenticatedUser(userData)
          setupRefreshTimer()
        } else {
          clearAuthState()
        }
      } catch (error) {
        if (!isMounted) return
        console.error('Auth initialization failed:', error)
        clearAuthState()
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
  }, [applyAuthenticatedUser, checkAuthStatus, clearAuthState, setupRefreshTimer])

  /**
   * Login with username and password
   * Server sets HTTP-only cookies on successful login
   */
  const login = useCallback(
    async (username: string, password: string) => {
      setAuthState((prev) => ({ ...prev, authError: null }))

      try {
        // Login - cookies are set by the server response
        await authApi.login(username, password)

        // Fetch user info to update state
        const userData = await authApi.checkAuth()
        if (!userData) {
          throw new Error('Failed to get user info after login')
        }

        applyAuthenticatedUser(userData)
        setupRefreshTimer()

        // Handle redirect after successful login
        router.push(getPostLoginRedirect())
      } catch (error) {
        if (error instanceof ApiError) {
          setAuthState((prev) => ({ ...prev, authError: error.message }))
          throw error
        }
        setAuthState((prev) => ({
          ...prev,
          authError: 'An unexpected error occurred',
        }))
        throw new Error('An unexpected error occurred')
      }
    },
    [applyAuthenticatedUser, router, setupRefreshTimer]
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
      setAuthState((prev) => ({ ...prev, authError: null }))

      try {
        await authApi.register(data)
        // Auto-login after successful registration
        await login(data.username, data.password)
      } catch (error) {
        if (error instanceof ApiError) {
          setAuthState((prev) => ({ ...prev, authError: error.message }))
          throw error
        }
        setAuthState((prev) => ({
          ...prev,
          authError: 'An unexpected error occurred',
        }))
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
