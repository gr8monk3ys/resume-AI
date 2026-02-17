import { SignIn } from '@clerk/nextjs'

/**
 * Login page using Clerk's SignIn component.
 *
 * Clerk handles the entire sign-in flow including:
 * - Email/password authentication
 * - Social login providers (if configured)
 * - Multi-factor authentication
 * - Password reset
 *
 * The `routing="hash"` prop uses hash-based routing for the Clerk
 * component, keeping the URL clean while Clerk manages its internal
 * navigation state.
 */
export default function LoginPage() {
  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <SignIn
        routing="hash"
        afterSignInUrl="/"
        signUpUrl="/register"
      />
    </div>
  )
}
