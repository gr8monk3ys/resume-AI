import Head from 'next/head'

import { LandingPage } from '@/app/LandingPage'

export default function MarketingHomePage() {
  return (
    <>
      <Head>
        <title>AI Job Search Toolkit | ResuBoost AI</title>
        <meta
          name="description"
          content="Optimize resumes, track applications, and prepare for interviews with AI-powered job search tools."
        />
      </Head>
      <main id="main-content">
        <LandingPage />
      </main>
    </>
  )
}
