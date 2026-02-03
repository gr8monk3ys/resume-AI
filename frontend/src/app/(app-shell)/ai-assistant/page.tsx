import AIAssistantPageClient from './AIAssistantPageClient'

import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'AI Assistant',
  description: 'Use AI tools to tailor resumes, draft answers, and prepare interview responses.',
}

export default function AIAssistantPage() {
  return <AIAssistantPageClient />
}
