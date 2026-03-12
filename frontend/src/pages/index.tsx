import Head from 'next/head'

import { LandingPage } from '@/app/LandingPage'

export default function MarketingHomePage() {
  return (
    <>
      <Head>
        <title>Search-First Job Search Workspace | ResuBoost AI</title>
        <meta
          name="description"
          content="Keep your target roles, application pipeline, resume tuning, and interview prep in one search-first workspace."
        />
      </Head>
      <main id="main-content">
        <LandingPage />
      </main>
    </>
  )
}
