'use client'

import { ClerkProvider, useUser, useAuth as useClerkAuth, useClerk } from '@clerk/nextjs'
import { ReactNode, useMemo } from 'react'

import { AuthContext, AuthContextType } from '@/lib/auth'

import type { User } from '@/types'

/**
 * Map Clerk user data to the application's User type.
 *
 * Clerk provides its own user object structure. This function translates
 * the Clerk fields into the shape expected by the rest of the application.
 */
function mapClerkUserToAppUser(
  clerkUser: ReturnType<typeof useUser>['user']
): User | null {
  if (!clerkUser) {
    return null
  }

  return {
    id: clerkUser.id as unknown as number,
    username:
      clerkUser.username ??
      clerkUser.primaryEmailAddress?.emailAddress ??
      '',
    email: clerkUser.primaryEmailAddress?.emailAddress ?? '',
    full_name:
      [clerkUser.firstName, clerkUser.lastName].filter(Boolean).join(' ') ||
      null,
    is_active: true,
    is_admin: false,
    created_at: clerkUser.createdAt?.toISOString() ?? '',
    last_login: clerkUser.lastSignInAt?.toISOString() ?? null,
  }
}

/**
 * Inner component that reads Clerk hooks and bridges the values
 * into the legacy AuthContext so that existing components and the
 * `useAuth` hook continue to work unchanged.
 */
function ClerkAuthBridge({ children }: { children: ReactNode }) {
  const { user: clerkUser, isLoaded: isUserLoaded } = useUser()
  const { isSignedIn, isLoaded: isAuthLoaded } = useClerkAuth()
  const clerk = useClerk()

  const value: AuthContextType = useMemo(() => {
    const isLoading = !isUserLoaded || !isAuthLoaded
    const isAuthenticated = !!isSignedIn
    const user = mapClerkUserToAppUser(clerkUser ?? null)

    const login = async (): Promise<void> => {
      clerk.redirectToSignIn()
    }

    const logout = async (): Promise<void> => {
      await clerk.signOut()
    }

    const register = async (): Promise<void> => {
      clerk.redirectToSignUp()
    }

    const refreshAuth = async (): Promise<boolean> => {
      return !!isSignedIn
    }

    return {
      user,
      isAuthenticated,
      isLoading,
      authError: null,
      login,
      logout,
      register,
      refreshAuth,
    }
  }, [clerkUser, isUserLoaded, isSignedIn, isAuthLoaded, clerk])

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  )
}

/**
 * Authentication provider that wraps the application with Clerk
 * and bridges Clerk's auth state into the legacy AuthContext.
 *
 * Clerk manages all authentication state, session tokens, and user
 * data internally. The ClerkAuthBridge component reads Clerk hooks
 * and populates AuthContext so that existing components using
 * `useAuth()` continue to work without changes.
 */
export function AuthProvider({ children }: { children: ReactNode }) {
  return (
    <ClerkProvider>
      <ClerkAuthBridge>
        {children}
      </ClerkAuthBridge>
    </ClerkProvider>
  )
}
