import { cn } from '@/lib/utils'

export function BrandMark({
  className,
  compact = false,
  subdued = false,
}: {
  className?: string
  compact?: boolean
  subdued?: boolean
}) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <span className="relative flex h-11 w-11 items-center justify-center overflow-hidden rounded-2xl border border-white/40 bg-[#10243f] shadow-[0_20px_40px_-20px_rgba(16,36,63,0.55)]">
        <span className="absolute inset-0 bg-[radial-gradient(circle_at_28%_28%,rgba(255,255,255,0.26),transparent_42%),linear-gradient(140deg,#15345a_0%,#08111f_100%)]" />
        <span className="relative h-5 w-5 rounded-full border border-white/30">
          <span className="absolute -right-1 top-1/2 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-[#ff7a1a]" />
        </span>
      </span>
      <span className="flex flex-col">
        <span className="font-display text-lg font-semibold tracking-[-0.05em] text-slate-950">
          ResuBoost AI
        </span>
        {!compact && (
          <span
            className={cn(
              'text-[0.68rem] font-semibold uppercase tracking-[0.22em]',
              subdued ? 'text-slate-500' : 'text-slate-600'
            )}
          >
            Job Search System
          </span>
        )}
      </span>
    </div>
  )
}
