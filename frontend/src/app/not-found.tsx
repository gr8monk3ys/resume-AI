import Link from 'next/link'

export default function NotFound(): React.ReactElement {
  return (
    <div className="min-h-screen flex items-center justify-center p-4">
      <div className="max-w-md w-full text-center">
        <h1 className="text-6xl font-display font-bold text-gray-900 mb-2">
          404
        </h1>
        <h2 className="text-xl font-semibold text-gray-700 mb-4">
          Page not found
        </h2>
        <p className="text-gray-500 text-sm mb-8">
          The page you&apos;re looking for doesn&apos;t exist or has been moved.
        </p>
        <Link
          href="/"
          className="inline-flex items-center justify-center px-6 py-2.5 text-sm font-medium text-white bg-primary-600 rounded-lg hover:bg-primary-700 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-primary-500"
        >
          Go home
        </Link>
      </div>
    </div>
  )
}
