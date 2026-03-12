import { bodyFont, displayFont } from '@/lib/fonts'

import type { Metadata } from 'next'

import './globals.css'

export const metadata: Metadata = {
  title: {
    default: 'ResuBoost AI',
    template: '%s | ResuBoost AI',
  },
  description:
    'Search-first job search workspace for tracking applications, tuning resumes, and staying interview ready.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html
      lang="en"
      className={`${bodyFont.variable} ${displayFont.variable}`}
    >
      <body className="font-body antialiased">
        {children}
      </body>
    </html>
  )
}
