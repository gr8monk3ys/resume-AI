import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Analytics',
  description: 'Review job search performance, response rates, funnel trends, and resume outcomes.',
}

export default function AnalyticsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
