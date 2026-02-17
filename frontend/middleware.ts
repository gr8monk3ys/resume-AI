import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'

/**
 * Routes that require authentication.
 *
 * Public routes (/, /login, /register, static assets) are accessible
 * without authentication. All application feature routes listed below
 * require a signed-in Clerk session.
 */
const isProtectedRoute = createRouteMatcher([
  '/resumes(.*)',
  '/jobs(.*)',
  '/interview(.*)',
  '/documents(.*)',
  '/career(.*)',
  '/profile(.*)',
  '/settings(.*)',
  '/cover-letters(.*)',
  '/ai-assistant(.*)',
  '/analytics(.*)',
])

export default clerkMiddleware(async (auth, req) => {
  if (isProtectedRoute(req)) {
    await auth.protect()
  }
})

export const config = {
  matcher: [
    // Skip Next.js internals and all static files unless found in search params
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    // Always run for API routes
    '/(api|trpc)(.*)',
  ],
}
