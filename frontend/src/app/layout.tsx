import type { Metadata } from 'next'

import './globals.css'

export const metadata: Metadata = {
  title: {
    default: 'ResuBoost AI',
    template: '%s | ResuBoost AI',
  },
  description:
    'AI-powered job search toolkit for resume optimization, application tracking, and interview prep.',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="font-sans antialiased">
        {children}
      </body>
    </html>
  )
}
