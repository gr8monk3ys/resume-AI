'use client'

import { CheckCircle, Loader2, XCircle } from 'lucide-react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import { Suspense, useEffect, useState } from 'react'

type VerificationStatus = 'loading' | 'success' | 'error'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

function VerifyEmailContent(): React.ReactElement {
  const searchParams = useSearchParams()
  const token = searchParams.get('token')
  const [status, setStatus] = useState<VerificationStatus>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!token) {
      setStatus('error')
      setMessage('No verification token provided.')
      return
    }

    let isMounted = true

    async function verify(): Promise<void> {
      try {
        const response = await fetch(
          `${API_BASE_URL}/api/auth/verify-email?token=${encodeURIComponent(token as string)}`,
          { credentials: 'include' }
        )

        if (!response.ok) {
          const data = (await response.json().catch(() => null)) as { detail?: string } | null
          throw new Error(data?.detail ?? 'Verification failed')
        }

        if (isMounted) {
          setStatus('success')
          setMessage('Your email has been verified successfully.')
        }
      } catch (err) {
        if (isMounted) {
          setStatus('error')
          setMessage(
            err instanceof Error ? err.message : 'Verification failed. The link may have expired.'
          )
        }
      }
    }

    void verify()

    return () => {
      isMounted = false
    }
  }, [token])

  return (
    <div className="mx-auto max-w-md px-4 py-16 sm:px-6">
      <div className="surface-card rounded-lg p-8 text-center">
        {status === 'loading' && (
          <>
            <Loader2 className="mx-auto h-12 w-12 animate-spin text-[var(--accent)]" />
            <h1 className="mt-4 font-display text-xl font-semibold text-[var(--ink)]">
              Verifying your email...
            </h1>
            <p className="mt-2 text-sm text-[var(--muted)]">
              Please wait while we confirm your email address.
            </p>
          </>
        )}

        {status === 'success' && (
          <>
            <CheckCircle className="mx-auto h-12 w-12 text-green-500" />
            <h1 className="mt-4 font-display text-xl font-semibold text-[var(--ink)]">
              Email verified
            </h1>
            <p className="mt-2 text-sm text-[var(--muted)]">{message}</p>
            <Link
              href="/"
              className="mt-6 inline-flex items-center justify-center rounded-full bg-[#10243f] px-6 py-3 text-sm font-semibold text-white transition hover:bg-[#0b1728]"
            >
              Go to Dashboard
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <XCircle className="mx-auto h-12 w-12 text-red-500" />
            <h1 className="mt-4 font-display text-xl font-semibold text-[var(--ink)]">
              Verification failed
            </h1>
            <p className="mt-2 text-sm text-[var(--muted)]">{message}</p>
            <Link
              href="/"
              className="mt-6 inline-flex items-center justify-center rounded-full border border-[var(--line)] bg-white px-6 py-3 text-sm font-semibold text-[var(--ink)] transition hover:bg-[var(--surface)]"
            >
              Go to Dashboard
            </Link>
          </>
        )}
      </div>
    </div>
  )
}

export default function VerifyEmailPage(): React.ReactElement {
  return (
    <Suspense
      fallback={
        <div className="mx-auto max-w-md px-4 py-16 sm:px-6">
          <div className="surface-card rounded-lg p-8 text-center">
            <Loader2 className="mx-auto h-12 w-12 animate-spin text-[var(--accent)]" />
            <h1 className="mt-4 font-display text-xl font-semibold text-[var(--ink)]">
              Verifying your email...
            </h1>
          </div>
        </div>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  )
}
