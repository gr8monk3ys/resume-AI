import { cn } from '@/lib/utils'

/**
 * Props for the Skeleton component
 */
interface SkeletonProps {
  /** Additional CSS classes */
  className?: string
  /** Width of the skeleton (e.g., 'w-full', 'w-32', '200px') */
  width?: string
  /** Height of the skeleton (e.g., 'h-4', 'h-8', '40px') */
  height?: string
  /** Shape variant of the skeleton */
  variant?: 'text' | 'circular' | 'rectangular' | 'rounded'
  /** Animation style */
  animation?: 'pulse' | 'wave' | 'none'
}

/**
 * Base skeleton component for loading states
 * Uses Tailwind's animate-pulse for smooth loading animation
 *
 * @example
 * // Text skeleton
 * <Skeleton variant="text" width="w-3/4" />
 *
 * @example
 * // Avatar skeleton
 * <Skeleton variant="circular" width="w-10" height="h-10" />
 *
 * @example
 * // Card skeleton
 * <Skeleton variant="rounded" height="h-32" />
 */
export function Skeleton({
  className,
  width = 'w-full',
  height = 'h-4',
  variant = 'rectangular',
  animation = 'pulse',
}: SkeletonProps) {
  const baseStyles = 'bg-gray-200'

  const variantStyles = {
    text: 'rounded',
    circular: 'rounded-full',
    rectangular: '',
    rounded: 'rounded-lg',
  }

  const animationStyles = {
    pulse: 'animate-pulse',
    wave: 'animate-pulse', // Could be extended with custom wave animation
    none: '',
  }

  return (
    <div
      className={cn(
        baseStyles,
        variantStyles[variant],
        animationStyles[animation],
        width,
        height,
        className
      )}
      role="status"
      aria-label="Loading"
      aria-busy="true"
    />
  )
}

/**
 * Skeleton text line with configurable width
 * Useful for simulating text content
 */
export function SkeletonText({
  lines = 1,
  className,
  lastLineWidth = 'w-3/4',
}: {
  lines?: number
  className?: string
  lastLineWidth?: string
}) {
  return (
    <div className={cn('space-y-2', className)} role="status" aria-label="Loading text">
      {Array.from({ length: lines }).map((_, index) => (
        <Skeleton
          key={index}
          variant="text"
          width={index === lines - 1 && lines > 1 ? lastLineWidth : 'w-full'}
          height="h-4"
        />
      ))}
    </div>
  )
}

/**
 * Skeleton avatar/profile picture
 */
export function SkeletonAvatar({
  size = 'md',
  className,
}: {
  size?: 'sm' | 'md' | 'lg' | 'xl'
  className?: string
}) {
  const sizeStyles = {
    sm: 'w-8 h-8',
    md: 'w-10 h-10',
    lg: 'w-12 h-12',
    xl: 'w-16 h-16',
  }

  return (
    <Skeleton
      variant="circular"
      width={sizeStyles[size].split(' ')[0]}
      height={sizeStyles[size].split(' ')[1]}
      className={className}
    />
  )
}

/**
 * Skeleton button
 */
export function SkeletonButton({
  size = 'md',
  className,
}: {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}) {
  const sizeStyles = {
    sm: 'w-20 h-8',
    md: 'w-24 h-10',
    lg: 'w-32 h-12',
  }

  return (
    <Skeleton
      variant="rounded"
      width={sizeStyles[size].split(' ')[0]}
      height={sizeStyles[size].split(' ')[1]}
      className={className}
    />
  )
}

/**
 * Skeleton input field
 */
export function SkeletonInput({ className }: { className?: string }) {
  return (
    <Skeleton
      variant="rounded"
      width="w-full"
      height="h-10"
      className={cn('border border-gray-300', className)}
    />
  )
}

/**
 * Skeleton textarea
 */
export function SkeletonTextarea({
  rows = 4,
  className,
}: {
  rows?: number
  className?: string
}) {
  const height = `h-${rows * 6}`

  return (
    <Skeleton
      variant="rounded"
      width="w-full"
      className={cn('border border-gray-300', className)}
      height={height}
    />
  )
}

export default Skeleton
