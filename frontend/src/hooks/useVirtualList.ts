/**
 * Custom hook for list virtualization using @tanstack/react-virtual
 *
 * This hook provides a simplified interface for virtualizing lists,
 * handling common patterns like estimateSize, overscan, and scroll handling.
 */

import { useVirtualizer } from '@tanstack/react-virtual'
import { useCallback, useRef, type RefObject } from 'react'

export interface UseVirtualListOptions<TItem> {
  /** Array of items to virtualize */
  items: TItem[]
  /** Estimated size of each item in pixels */
  estimateSize: number
  /** Number of items to render outside the visible area (default: 5) */
  overscan?: number
  /** Whether to enable horizontal virtualization (default: false, uses vertical) */
  horizontal?: boolean
  /** Function to get unique key for each item */
  getItemKey?: (index: number) => string | number
  /** Gap between items in pixels (default: 0) */
  gap?: number
}

/** Virtual item returned by the virtualizer */
export interface VirtualItemInfo {
  key: string | number
  index: number
  start: number
  end: number
  size: number
}

export interface UseVirtualListReturn {
  /** Ref to attach to the scrollable container element */
  parentRef: RefObject<HTMLDivElement | null>
  /** Array of virtual items to render */
  virtualItems: VirtualItemInfo[]
  /** Total size of all items in pixels */
  totalSize: number
  /** Whether any items are currently being measured */
  isScrolling: boolean
  /** Scroll to a specific index */
  scrollToIndex: (index: number, options?: { align?: 'start' | 'center' | 'end' | 'auto'; behavior?: 'auto' | 'smooth' }) => void
  /** Scroll to a specific offset in pixels */
  scrollToOffset: (offset: number, options?: { align?: 'start' | 'center' | 'end' | 'auto'; behavior?: 'auto' | 'smooth' }) => void
  /** Get the offset for a specific index */
  getOffsetForIndex: (index: number, align?: 'start' | 'center' | 'end' | 'auto') => number | undefined
  /** Measure element at index (for dynamic sizing) */
  measureElement: (element: Element | null) => void
}

/**
 * Hook for virtualizing vertical or horizontal lists
 *
 * @example
 * ```tsx
 * const { parentRef, virtualItems, totalSize } = useVirtualList({
 *   items: myItems,
 *   estimateSize: 50,
 *   overscan: 5,
 * })
 *
 * return (
 *   <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
 *     <div style={{ height: totalSize, position: 'relative' }}>
 *       {virtualItems.map((virtualItem) => (
 *         <div
 *           key={virtualItem.key}
 *           style={{
 *             position: 'absolute',
 *             top: virtualItem.start,
 *             height: virtualItem.size,
 *           }}
 *         >
 *           {myItems[virtualItem.index].name}
 *         </div>
 *       ))}
 *     </div>
 *   </div>
 * )
 * ```
 */
export function useVirtualList<TItem>(
  options: UseVirtualListOptions<TItem>
): UseVirtualListReturn {
  const {
    items,
    estimateSize,
    overscan = 5,
    horizontal = false,
    getItemKey,
    gap = 0,
  } = options

  const parentRef = useRef<HTMLDivElement | null>(null)

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => estimateSize + gap,
    overscan,
    horizontal,
    ...(getItemKey && { getItemKey }),
  })

  const virtualItems = virtualizer.getVirtualItems()
  const totalSize = virtualizer.getTotalSize()

  const scrollToIndex = useCallback(
    (index: number, options?: { align?: 'start' | 'center' | 'end' | 'auto'; behavior?: 'auto' | 'smooth' }) => {
      virtualizer.scrollToIndex(index, options)
    },
    [virtualizer]
  )

  const scrollToOffset = useCallback(
    (offset: number, options?: { align?: 'start' | 'center' | 'end' | 'auto'; behavior?: 'auto' | 'smooth' }) => {
      virtualizer.scrollToOffset(offset, options)
    },
    [virtualizer]
  )

  const getOffsetForIndex = useCallback(
    (index: number, align?: 'start' | 'center' | 'end' | 'auto') => {
      const result = virtualizer.getOffsetForIndex(index, align)
      return result ? result[0] : undefined
    },
    [virtualizer]
  )

  const measureElement = useCallback(
    (element: Element | null) => {
      if (element) {
        virtualizer.measureElement(element)
      }
    },
    [virtualizer]
  )

  return {
    parentRef,
    virtualItems: virtualItems as VirtualItemInfo[],
    totalSize,
    isScrolling: virtualizer.isScrolling,
    scrollToIndex,
    scrollToOffset,
    getOffsetForIndex,
    measureElement,
  }
}

/**
 * Hook for virtualizing table rows (tbody)
 * Specialized version for table elements with proper row handling
 */
export interface UseVirtualTableOptions<TItem> extends Omit<UseVirtualListOptions<TItem>, 'horizontal'> {
  /** Height of each table row in pixels */
  rowHeight: number
}

export interface UseVirtualTableReturn extends UseVirtualListReturn {
  /** Padding to add before the first rendered row */
  paddingTop: number
  /** Padding to add after the last rendered row */
  paddingBottom: number
}

/**
 * Hook specifically for virtualizing table rows
 * Handles the complexities of table element virtualization
 *
 * @example
 * ```tsx
 * const { parentRef, virtualItems, paddingTop, paddingBottom, totalSize } = useVirtualTable({
 *   items: tableData,
 *   rowHeight: 48,
 *   overscan: 10,
 * })
 *
 * return (
 *   <div ref={parentRef} style={{ height: '400px', overflow: 'auto' }}>
 *     <table>
 *       <thead>...</thead>
 *       <tbody>
 *         {paddingTop > 0 && (
 *           <tr><td style={{ height: paddingTop }} /></tr>
 *         )}
 *         {virtualItems.map((virtualRow) => (
 *           <tr key={virtualRow.key} data-index={virtualRow.index}>
 *             {tableData[virtualRow.index].cells}
 *           </tr>
 *         ))}
 *         {paddingBottom > 0 && (
 *           <tr><td style={{ height: paddingBottom }} /></tr>
 *         )}
 *       </tbody>
 *     </table>
 *   </div>
 * )
 * ```
 */
export function useVirtualTable<TItem>(
  options: UseVirtualTableOptions<TItem>
): UseVirtualTableReturn {
  const { rowHeight, ...restOptions } = options

  const result = useVirtualList<TItem>({
    ...restOptions,
    estimateSize: rowHeight,
    horizontal: false,
  })

  const virtualItems = result.virtualItems

  // Calculate padding for proper table virtualization
  const paddingTop = virtualItems.length > 0 ? virtualItems[0]?.start ?? 0 : 0
  const paddingBottom = virtualItems.length > 0
    ? result.totalSize - (virtualItems[virtualItems.length - 1]?.end ?? result.totalSize)
    : 0

  return {
    ...result,
    paddingTop,
    paddingBottom,
  }
}

export type { VirtualItem } from '@tanstack/react-virtual'
