import Link from 'next/link'

export default function NotFound(): React.ReactElement {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center">
        <h1 className="text-6xl font-display font-bold text-[var(--ink)] tracking-[-0.02em] mb-2">
          404
        </h1>
        <h2 className="text-xl font-semibold text-[var(--ink-secondary)] mb-4">
          Page not found
        </h2>
        <p className="text-[var(--muted)] text-sm mb-8">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link
          href="/"
          className="glass-button-primary"
        >
          Go home
        </Link>
      </div>
    </div>
  )
}
