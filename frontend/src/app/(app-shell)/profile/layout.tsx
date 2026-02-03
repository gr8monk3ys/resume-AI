import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Profile',
  description: 'Update your contact details, portfolio links, and core profile information.',
}

export default function ProfileLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
