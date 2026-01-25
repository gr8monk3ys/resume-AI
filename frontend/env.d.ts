/// <reference types="node" />

// eslint-disable-next-line @typescript-eslint/no-unused-vars
declare namespace NodeJS {
  interface ProcessEnv {
    // Node environment
    NODE_ENV: 'development' | 'production' | 'test'

    // Next.js public environment variables (accessible in browser)
    NEXT_PUBLIC_API_URL?: string
    NEXT_PUBLIC_APP_NAME?: string
    NEXT_PUBLIC_APP_VERSION?: string
    NEXT_PUBLIC_ENABLE_ANALYTICS?: string
    NEXT_PUBLIC_SENTRY_DSN?: string

    // Server-side only environment variables
    API_SECRET_KEY?: string
    DATABASE_URL?: string
    BACKEND_URL?: string

    // Authentication
    NEXTAUTH_URL?: string
    NEXTAUTH_SECRET?: string

    // LLM Provider Configuration (matching backend)
    LLM_PROVIDER?: 'openai' | 'anthropic' | 'google' | 'ollama' | 'mock'
    OPENAI_API_KEY?: string
    ANTHROPIC_API_KEY?: string
    GOOGLE_API_KEY?: string
    OLLAMA_BASE_URL?: string

    // Feature flags
    ENABLE_DEMO_MODE?: string
    SHOW_DEMO_CREDENTIALS?: string
  }
}

// Extend Window interface for client-side globals if needed
declare global {
  interface Window {
    __ENV__?: Record<string, string | undefined>
  }
}

export {}
