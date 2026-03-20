'use client'

import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface AIMarkdownProps {
  content: string
  className?: string
}

export function AIMarkdown({ content, className }: AIMarkdownProps) {
  return (
    <div className={`prose prose-sm max-w-none dark:prose-invert prose-headings:text-[var(--ink)] prose-p:text-[var(--ink-secondary)] prose-strong:text-[var(--ink)] prose-li:text-[var(--ink-secondary)] prose-a:text-[var(--accent)] ${className ?? ''}`}>
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}
