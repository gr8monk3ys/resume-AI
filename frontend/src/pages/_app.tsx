import { bodyFont, displayFont } from '@/lib/fonts'

import type { AppProps } from 'next/app'

import '@/app/globals.css'

export default function App({ Component, pageProps }: AppProps) {
  return (
    <div
      className={`${bodyFont.variable} ${displayFont.variable} font-body antialiased`}
    >
      <Component {...pageProps} />
    </div>
  )
}
