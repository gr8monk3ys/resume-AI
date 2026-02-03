import { NextResponse } from 'next/server'

import type { NextRequest } from 'next/server'

const AUTH_ROUTES = new Set(['/login', '/register'])

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

function hasValidAuthCookie(request: NextRequest): boolean {
  return Boolean(request.cookies.get('access_token')?.value)
}

function isSafeRedirectPath(pathname: string | null): pathname is string {
  return Boolean(pathname && pathname.startsWith('/') && !pathname.startsWith('//'))
}

export function middleware(request: NextRequest) {
  const { pathname, search } = request.nextUrl
  const isAuthenticated = hasValidAuthCookie(request)

  if (isAuthenticated && pathname === '/') {
    const dashboardUrl = request.nextUrl.clone()
    dashboardUrl.pathname = '/dashboard'
    return NextResponse.rewrite(dashboardUrl)
  }

  if (!isAuthenticated && pathname === '/') {
    const landingUrl = request.nextUrl.clone()
    landingUrl.pathname = '/landing.html'
    return NextResponse.rewrite(landingUrl)
  }

  if (!isAuthenticated && isProtectedRoute(pathname)) {
    const loginUrl = request.nextUrl.clone()
    loginUrl.pathname = '/login'
    loginUrl.search = ''
    loginUrl.searchParams.set('redirectTo', `${pathname}${search}`)
    return NextResponse.redirect(loginUrl)
  }

  if (isAuthenticated && AUTH_ROUTES.has(pathname)) {
    const requestedRedirect = request.nextUrl.searchParams.get('redirectTo')
    const redirectUrl = request.nextUrl.clone()
    redirectUrl.pathname = isSafeRedirectPath(requestedRedirect)
      ? requestedRedirect
      : '/'
    redirectUrl.search = ''
    return NextResponse.redirect(redirectUrl)
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|.*\\..*).*)'],
}
