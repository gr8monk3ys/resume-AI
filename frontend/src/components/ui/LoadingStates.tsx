import { cn } from '@/lib/utils'

import { Skeleton, SkeletonText, SkeletonAvatar, SkeletonButton, SkeletonInput } from './Skeleton'

/**
 * Loading skeleton for card components (resume cards, job cards, etc.)
 * Matches the card design pattern used throughout the application
 */
export function CardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'bg-white rounded-xl shadow-md p-6 border border-gray-100',
        className
      )}
      role="status"
      aria-label="Loading card"
    >
      <div className="flex items-start gap-4">
        {/* Icon placeholder */}
        <Skeleton variant="rounded" width="w-12" height="h-12" />

        <div className="flex-1 min-w-0">
          {/* Title */}
          <Skeleton variant="text" width="w-3/4" height="h-5" className="mb-2" />

          {/* Subtitle */}
          <Skeleton variant="text" width="w-1/2" height="h-4" className="mb-3" />

          {/* Description or metadata */}
          <SkeletonText lines={2} lastLineWidth="w-2/3" />
        </div>

        {/* Action buttons or badge */}
        <div className="flex items-center gap-2">
          <Skeleton variant="rounded" width="w-16" height="h-6" />
        </div>
      </div>

      {/* Footer section */}
      <div className="mt-4 pt-4 border-t border-gray-100 flex justify-between items-center">
        <Skeleton variant="text" width="w-24" height="h-4" />
        <div className="flex gap-2">
          <Skeleton variant="circular" width="w-8" height="h-8" />
          <Skeleton variant="circular" width="w-8" height="h-8" />
        </div>
      </div>
    </div>
  )
}

/**
 * Compact card skeleton for smaller card variants
 */
export function CompactCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'bg-white rounded-lg shadow p-4 border-l-4 border-gray-200',
        className
      )}
      role="status"
      aria-label="Loading card"
    >
      <div className="flex items-start gap-2">
        <Skeleton variant="rectangular" width="w-4" height="h-4" className="mt-1" />

        <div className="flex-1 min-w-0">
          <div className="flex justify-between items-start">
            <div className="flex-1">
              <Skeleton variant="text" width="w-2/3" height="h-4" className="mb-1" />
              <Skeleton variant="text" width="w-1/2" height="h-3" />
            </div>
            <Skeleton variant="rounded" width="w-12" height="h-5" />
          </div>

          <div className="mt-2 flex items-center gap-2">
            <Skeleton variant="text" width="w-24" height="h-3" />
          </div>

          <div className="mt-3 flex items-center justify-between">
            <Skeleton variant="rounded" width="w-20" height="h-6" />
            <Skeleton variant="circular" width="w-6" height="h-6" />
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Loading skeleton for data tables
 * Configurable rows and columns
 */
export function TableSkeleton({
  rows = 5,
  columns = 5,
  showHeader = true,
  className,
}: {
  rows?: number
  columns?: number
  showHeader?: boolean
  className?: string
}) {
  return (
    <div
      className={cn('bg-white rounded-lg shadow overflow-hidden', className)}
      role="status"
      aria-label="Loading table"
    >
      <table className="min-w-full divide-y divide-gray-200">
        {showHeader && (
          <thead className="bg-gray-50">
            <tr>
              {Array.from({ length: columns }).map((_, index) => (
                <th key={index} className="px-6 py-3">
                  <Skeleton
                    variant="text"
                    width={index === 0 ? 'w-32' : 'w-20'}
                    height="h-3"
                  />
                </th>
              ))}
            </tr>
          </thead>
        )}
        <tbody className="bg-white divide-y divide-gray-200">
          {Array.from({ length: rows }).map((_, rowIndex) => (
            <tr key={rowIndex} className="animate-pulse">
              {Array.from({ length: columns }).map((_, colIndex) => (
                <td key={colIndex} className="px-6 py-4 whitespace-nowrap">
                  {colIndex === 0 ? (
                    <div className="flex items-center gap-3">
                      <Skeleton variant="rectangular" width="w-5" height="h-5" />
                      <Skeleton variant="text" width="w-32" height="h-4" />
                    </div>
                  ) : colIndex === columns - 1 ? (
                    <div className="flex justify-end gap-2">
                      <Skeleton variant="circular" width="w-8" height="h-8" />
                      <Skeleton variant="circular" width="w-8" height="h-8" />
                    </div>
                  ) : (
                    <Skeleton
                      variant="text"
                      width={colIndex === 1 ? 'w-16' : 'w-24'}
                      height="h-4"
                    />
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

/**
 * Loading skeleton for forms
 * Includes input fields, labels, and submit button
 */
export function FormSkeleton({
  fields = 4,
  showTextarea = false,
  showSubmitButton = true,
  className,
}: {
  fields?: number
  showTextarea?: boolean
  showSubmitButton?: boolean
  className?: string
}) {
  return (
    <div
      className={cn('space-y-6', className)}
      role="status"
      aria-label="Loading form"
    >
      {Array.from({ length: fields }).map((_, index) => (
        <div key={index}>
          {/* Label */}
          <Skeleton variant="text" width="w-24" height="h-4" className="mb-2" />

          {/* Input */}
          <SkeletonInput />
        </div>
      ))}

      {showTextarea && (
        <div>
          <Skeleton variant="text" width="w-32" height="h-4" className="mb-2" />
          <Skeleton
            variant="rounded"
            width="w-full"
            height="h-32"
            className="border border-gray-300"
          />
        </div>
      )}

      {showSubmitButton && (
        <div className="flex justify-end gap-3 pt-4">
          <SkeletonButton size="md" />
          <Skeleton
            variant="rounded"
            width="w-24"
            height="h-10"
            className="bg-gray-300"
          />
        </div>
      )}
    </div>
  )
}

/**
 * Loading skeleton for full page content
 * Includes header, stats cards, and content area
 */
export function PageSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn('max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8', className)}
      role="status"
      aria-label="Loading page"
    >
      {/* Page header */}
      <div className="mb-8">
        <Skeleton variant="text" width="w-64" height="h-8" className="mb-2" />
        <Skeleton variant="text" width="w-96" height="h-5" />
      </div>

      {/* Stats cards row */}
      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4 mb-8">
        {Array.from({ length: 4 }).map((_, index) => (
          <div
            key={index}
            className="bg-white rounded-xl shadow-md p-6 border border-gray-100"
          >
            <div className="flex items-center">
              <Skeleton variant="rounded" width="w-12" height="h-12" />
              <div className="ml-4 flex-1">
                <Skeleton variant="text" width="w-20" height="h-4" className="mb-1" />
                <Skeleton variant="text" width="w-12" height="h-6" />
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Main content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Main content area */}
        <div className="lg:col-span-2">
          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
            <div className="flex items-center justify-between mb-6">
              <Skeleton variant="text" width="w-40" height="h-6" />
              <Skeleton variant="text" width="w-16" height="h-4" />
            </div>

            <div className="space-y-4">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="py-4 border-b border-gray-100 last:border-0">
                  <div className="flex items-center justify-between">
                    <div className="flex-1 min-w-0">
                      <Skeleton variant="text" width="w-48" height="h-4" className="mb-1" />
                      <Skeleton variant="text" width="w-32" height="h-3" />
                    </div>
                    <div className="flex items-center gap-3">
                      <Skeleton variant="rounded" width="w-20" height="h-5" />
                      <Skeleton variant="text" width="w-16" height="h-3" />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Sidebar */}
        <div>
          <div className="bg-white rounded-xl shadow-md p-6 border border-gray-100">
            <Skeleton variant="text" width="w-32" height="h-6" className="mb-6" />

            <div className="space-y-3">
              {Array.from({ length: 6 }).map((_, index) => (
                <div key={index} className="flex items-center p-3">
                  <Skeleton variant="rounded" width="w-10" height="h-10" />
                  <div className="ml-4 flex-1">
                    <Skeleton variant="text" width="w-24" height="h-4" />
                  </div>
                  <Skeleton variant="rectangular" width="w-4" height="h-4" />
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Loading skeleton for lists of items
 * Useful for displaying loading state for repeated content
 */
export function ListSkeleton({
  items = 5,
  showAvatar = false,
  showActions = true,
  variant = 'default',
  className,
}: {
  items?: number
  showAvatar?: boolean
  showActions?: boolean
  variant?: 'default' | 'compact' | 'detailed'
  className?: string
}) {
  return (
    <div
      className={cn('divide-y divide-gray-100', className)}
      role="status"
      aria-label="Loading list"
    >
      {Array.from({ length: items }).map((_, index) => (
        <div
          key={index}
          className={cn(
            'flex items-center',
            variant === 'compact' ? 'py-3' : 'py-4'
          )}
        >
          {showAvatar && (
            <SkeletonAvatar
              size={variant === 'compact' ? 'sm' : 'md'}
              className="mr-4"
            />
          )}

          <div className="flex-1 min-w-0">
            <Skeleton
              variant="text"
              width={variant === 'detailed' ? 'w-3/4' : 'w-1/2'}
              height={variant === 'compact' ? 'h-3' : 'h-4'}
              className="mb-1"
            />
            {variant !== 'compact' && (
              <Skeleton variant="text" width="w-1/3" height="h-3" />
            )}
            {variant === 'detailed' && (
              <Skeleton variant="text" width="w-2/3" height="h-3" className="mt-1" />
            )}
          </div>

          {showActions && (
            <div className="flex items-center gap-2 ml-4">
              {variant === 'detailed' ? (
                <>
                  <Skeleton variant="rounded" width="w-16" height="h-6" />
                  <Skeleton variant="circular" width="w-8" height="h-8" />
                </>
              ) : (
                <Skeleton variant="text" width="w-16" height="h-4" />
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  )
}

/**
 * Loading skeleton for Kanban board columns
 */
export function KanbanColumnSkeleton({
  cards = 3,
  className,
}: {
  cards?: number
  className?: string
}) {
  return (
    <div
      className={cn('bg-gray-50 rounded-lg p-4 min-w-[300px]', className)}
      role="status"
      aria-label="Loading kanban column"
    >
      {/* Column header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Skeleton variant="rounded" width="w-3" height="h-6" />
          <Skeleton variant="text" width="w-24" height="h-5" />
          <Skeleton variant="circular" width="w-6" height="h-6" />
        </div>
      </div>

      {/* Cards */}
      <div className="space-y-3">
        {Array.from({ length: cards }).map((_, index) => (
          <CompactCardSkeleton key={index} />
        ))}
      </div>
    </div>
  )
}

/**
 * Loading skeleton for Kanban board
 */
export function KanbanBoardSkeleton({
  columns = 6,
  cardsPerColumn = 3,
  className,
}: {
  columns?: number
  cardsPerColumn?: number
  className?: string
}) {
  return (
    <div
      className={cn('flex gap-4 overflow-x-auto pb-4', className)}
      role="status"
      aria-label="Loading kanban board"
    >
      {Array.from({ length: columns }).map((_, index) => (
        <KanbanColumnSkeleton key={index} cards={cardsPerColumn} />
      ))}
    </div>
  )
}

/**
 * Loading skeleton for profile/user card
 */
export function ProfileCardSkeleton({ className }: { className?: string }) {
  return (
    <div
      className={cn(
        'bg-white rounded-xl shadow-md p-6 border border-gray-100',
        className
      )}
      role="status"
      aria-label="Loading profile"
    >
      <div className="flex items-center gap-4 mb-6">
        <SkeletonAvatar size="xl" />
        <div className="flex-1">
          <Skeleton variant="text" width="w-40" height="h-6" className="mb-2" />
          <Skeleton variant="text" width="w-32" height="h-4" />
        </div>
      </div>

      <div className="space-y-4">
        <div>
          <Skeleton variant="text" width="w-20" height="h-3" className="mb-1" />
          <Skeleton variant="text" width="w-48" height="h-4" />
        </div>
        <div>
          <Skeleton variant="text" width="w-20" height="h-3" className="mb-1" />
          <Skeleton variant="text" width="w-36" height="h-4" />
        </div>
        <div>
          <Skeleton variant="text" width="w-20" height="h-3" className="mb-1" />
          <Skeleton variant="text" width="w-56" height="h-4" />
        </div>
      </div>
    </div>
  )
}

/**
 * Loading skeleton for analytics/chart card
 */
export function ChartSkeleton({
  height = 'h-64',
  className,
}: {
  height?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        'bg-white rounded-xl shadow-md p-6 border border-gray-100',
        className
      )}
      role="status"
      aria-label="Loading chart"
    >
      <div className="flex items-center justify-between mb-4">
        <Skeleton variant="text" width="w-32" height="h-6" />
        <Skeleton variant="rounded" width="w-24" height="h-8" />
      </div>

      <Skeleton variant="rounded" width="w-full" className={height} />
    </div>
  )
}

/**
 * Inline loading spinner for buttons and small areas
 */
export function InlineLoader({
  size = 'md',
  className,
}: {
  size?: 'sm' | 'md' | 'lg'
  className?: string
}) {
  const sizeStyles = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  }

  return (
    <div
      className={cn(
        'animate-spin rounded-full border-2 border-current border-t-transparent',
        sizeStyles[size],
        className
      )}
      role="status"
      aria-label="Loading"
    />
  )
}

/**
 * Centered loading spinner for full sections
 */
export function CenteredLoader({
  size = 'md',
  text,
  className,
}: {
  size?: 'sm' | 'md' | 'lg'
  text?: string
  className?: string
}) {
  const sizeStyles = {
    sm: 'h-6 w-6',
    md: 'h-8 w-8',
    lg: 'h-12 w-12',
  }

  return (
    <div
      className={cn('flex flex-col items-center justify-center py-12', className)}
      role="status"
      aria-label={text || 'Loading'}
    >
      <div
        className={cn(
          'animate-spin rounded-full border-2 border-primary-600 border-t-transparent',
          sizeStyles[size]
        )}
      />
      {text && <p className="mt-4 text-sm text-gray-500">{text}</p>}
    </div>
  )
}

