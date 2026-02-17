import { SignUp } from '@clerk/nextjs'

/**
 * Registration page using Clerk's SignUp component.
 *
 * Clerk handles the entire sign-up flow including:
 * - Email/password registration
 * - Social login providers (if configured)
 * - Email verification
 * - Username collection
 *
 * The `routing="hash"` prop uses hash-based routing for the Clerk
 * component, keeping the URL clean while Clerk manages its internal
 * navigation state.
 */
export default function RegisterPage() {
  return (
    <div className="min-h-[80vh] flex items-center justify-center px-4 py-12">
      <SignUp
        routing="hash"
        afterSignUpUrl="/"
        signInUrl="/login"
      />
    </div>
  )
}
