import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Documents',
  description: 'Create cover letters, networking outreach, and professional emails from one workspace.',
}

export default function DocumentsLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
