# Frontend Dockerfile for ResuBoost AI (Bun)
FROM oven/bun:1 AS base
WORKDIR /app

# Install dependencies only when needed
FROM base AS deps
COPY package.json bun.lockb* ./
RUN bun install --frozen-lockfile

# Rebuild the source code only when needed
FROM base AS builder
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .

ENV NEXT_TELEMETRY_DISABLED 1

RUN bun run build

# Production image - use debian-slim for user management
FROM oven/bun:1-debian AS runner
WORKDIR /app

ENV NODE_ENV production
ENV NEXT_TELEMETRY_DISABLED 1

# Install wget for health check and create non-root user
RUN apt-get update && apt-get install -y --no-install-recommends wget && \
    rm -rf /var/lib/apt/lists/* && \
    groupadd --system --gid 1001 nodejs && \
    useradd --system --uid 1001 --gid nodejs nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT 3000

CMD ["bun", "run", "server.js"]
