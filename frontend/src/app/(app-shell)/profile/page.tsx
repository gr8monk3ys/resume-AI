import ProfilePageClient from './ProfilePageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Profile',
  description: 'Update your contact details, portfolio links, and core profile information.',
}

export default function ProfilePage() {
  return <ProfilePageClient />
}
