import type { Metadata } from 'next'

export const metadata: Metadata = {
  title: 'Job Filters',
  description: 'Manage company filters, keyword filters, and saved answer templates for applications.',
}

export default function JobFiltersLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return children
}
