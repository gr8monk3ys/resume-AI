'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'

import { cn } from '@/lib/utils'

/**
 * Toast notification types
 */
export type ToastType = 'success' | 'error' | 'warning' | 'info'

/**
 * Individual toast data
 */
export interface ToastData {
  id: string
  type: ToastType
  message: string
  duration: number
  isExiting: boolean
}

/**
 * Options for creating a toast
 */
export interface ToastOptions {
  /** Duration in milliseconds before auto-dismiss. Set to 0 to disable. */
  duration?: number
}

/**
 * Maximum number of visible toasts at once
 */
const MAX_VISIBLE_TOASTS = 3

/**
 * Default durations by toast type in milliseconds
 */
const DEFAULT_DURATIONS: Record<ToastType, number> = {
  success: 5000,
  error: 8000,
  warning: 6000,
  info: 5000,
}

/**
 * Exit animation duration in milliseconds
 */
const EXIT_ANIMATION_DURATION = 300

/**
 * Toast context interface
 */
interface ToastContextValue {
  addToast: (type: ToastType, message: string, options?: ToastOptions) => string
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextValue | null>(null)

/**
 * Generate a unique toast ID
 */
function generateToastId(): string {
  return `toast-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
}

/**
 * Hook to access toast functionality
 *
 * @returns Object with addToast and removeToast methods
 * @throws Error if used outside of ToastProvider
 *
 * @example
 * ```tsx
 * const { addToast, removeToast } = useToast()
 * addToast('success', 'Changes saved!')
 * addToast('error', 'Something went wrong', { duration: 10000 })
 * ```
 */
export function useToast(): ToastContextValue {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return context
}

/**
 * Imperative toast API for use outside of React components.
 *
 * This object exposes convenience methods that delegate to the
 * ToastProvider context. It is initialized when the ToastProvider
 * mounts. Calling methods before the provider mounts is a no-op
 * to avoid runtime errors during SSR or early initialization.
 *
 * @example
 * ```ts
 * import { toast } from '@/components/ui/Toast'
 *
 * toast.success('Profile saved!')
 * toast.error('Upload failed. Please try again.')
 * toast.warning('Your session will expire soon.')
 * toast.info('A new version is available.')
 * ```
 */
export const toast = {
  _addToast: null as ((type: ToastType, message: string, options?: ToastOptions) => string) | null,

  success(message: string, options?: ToastOptions): string {
    return this._addToast?.('success', message, options) ?? ''
  },

  error(message: string, options?: ToastOptions): string {
    return this._addToast?.('error', message, options) ?? ''
  },

  warning(message: string, options?: ToastOptions): string {
    return this._addToast?.('warning', message, options) ?? ''
  },

  info(message: string, options?: ToastOptions): string {
    return this._addToast?.('info', message, options) ?? ''
  },
}

/**
 * Toast provider component that manages toast state and rendering.
 *
 * Wrap your application (or a subtree) with this provider to enable
 * toast notifications via the useToast hook or the imperative toast API.
 *
 * @example
 * ```tsx
 * <ToastProvider>
 *   <App />
 * </ToastProvider>
 * ```
 */
export function ToastProvider({ children }: { children: React.ReactNode }): React.ReactNode {
  const [toasts, setToasts] = useState<ToastData[]>([])
  const timersRef = useRef<Map<string, NodeJS.Timeout>>(new Map())

  /**
   * Remove a toast by ID, triggering exit animation first
   */
  const removeToast = useCallback((id: string) => {
    // Clear any existing timer for this toast
    const timer = timersRef.current.get(id)
    if (timer) {
      clearTimeout(timer)
      timersRef.current.delete(id)
    }

    // Trigger exit animation
    setToasts((prev) =>
      prev.map((t) => (t.id === id ? { ...t, isExiting: true } : t))
    )

    // Remove from DOM after animation completes
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id))
    }, EXIT_ANIMATION_DURATION)
  }, [])

  /**
   * Add a new toast notification
   */
  const addToast = useCallback(
    (type: ToastType, message: string, options?: ToastOptions): string => {
      const id = generateToastId()
      const duration = options?.duration ?? DEFAULT_DURATIONS[type]

      const newToast: ToastData = {
        id,
        type,
        message,
        duration,
        isExiting: false,
      }

      setToasts((prev) => {
        const updated = [...prev, newToast]
        // If exceeding max visible, mark the oldest for removal
        if (updated.length > MAX_VISIBLE_TOASTS) {
          const excess = updated.length - MAX_VISIBLE_TOASTS
          for (let i = 0; i < excess; i++) {
            const oldest = updated[i]
            if (oldest && !oldest.isExiting) {
              removeToast(oldest.id)
            }
          }
        }
        return updated
      })

      // Set auto-dismiss timer if duration is greater than 0
      if (duration > 0) {
        const timer = setTimeout(() => {
          removeToast(id)
        }, duration)
        timersRef.current.set(id, timer)
      }

      return id
    },
    [removeToast]
  )

  // Register the imperative toast API on mount
  useEffect(() => {
    toast._addToast = addToast
    return () => {
      toast._addToast = null
    }
  }, [addToast])

  // Clean up all timers on unmount
  useEffect(() => {
    return () => {
      timersRef.current.forEach((timer) => clearTimeout(timer))
      timersRef.current.clear()
    }
  }, [])

  return (
    <ToastContext.Provider value={{ addToast, removeToast }}>
      {children}
      <ToastContainer toasts={toasts} onDismiss={removeToast} />
    </ToastContext.Provider>
  )
}

/**
 * Props for ToastContainer
 */
interface ToastContainerProps {
  toasts: ToastData[]
  onDismiss: (id: string) => void
}

/**
 * Container that renders toast notifications in a fixed position.
 * Toasts are displayed in the bottom-right corner of the viewport.
 */
function ToastContainer({ toasts, onDismiss }: ToastContainerProps): React.ReactNode {
  if (toasts.length === 0) {
    return null
  }

  return (
    <div
      aria-live="polite"
      aria-label="Notifications"
      className="fixed bottom-4 right-4 z-50 flex flex-col-reverse gap-3 w-full max-w-sm pointer-events-none"
    >
      {toasts.map((toastItem) => (
        <ToastItem
          key={toastItem.id}
          toast={toastItem}
          onDismiss={onDismiss}
        />
      ))}
    </div>
  )
}

/**
 * Props for a single ToastItem
 */
interface ToastItemProps {
  toast: ToastData
  onDismiss: (id: string) => void
}

/**
 * Style configuration per toast type
 */
const TOAST_STYLES: Record<ToastType, {
  container: string
  icon: string
  iconPath: string
  viewBox: string
}> = {
  success: {
    container: 'bg-green-50 border-green-200 text-green-800',
    icon: 'text-green-500',
    viewBox: '0 0 20 20',
    iconPath: 'M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z',
  },
  error: {
    container: 'bg-red-50 border-red-200 text-red-800',
    icon: 'text-red-500',
    viewBox: '0 0 20 20',
    iconPath: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z',
  },
  warning: {
    container: 'bg-amber-50 border-amber-200 text-amber-800',
    icon: 'text-amber-500',
    viewBox: '0 0 20 20',
    iconPath: 'M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 10-2 0 1 1 0 002 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z',
  },
  info: {
    container: 'bg-blue-50 border-blue-200 text-blue-800',
    icon: 'text-blue-500',
    viewBox: '0 0 20 20',
    iconPath: 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z',
  },
}

/**
 * Accessible labels for each toast type
 */
const TOAST_LABELS: Record<ToastType, string> = {
  success: 'Success',
  error: 'Error',
  warning: 'Warning',
  info: 'Information',
}

/**
 * Individual toast notification item with icon, message, and dismiss button.
 * Supports enter/exit animations via Tailwind CSS transitions.
 */
function ToastItem({ toast: toastItem, onDismiss }: ToastItemProps): React.ReactNode {
  const style = TOAST_STYLES[toastItem.type]
  const label = TOAST_LABELS[toastItem.type]

  return (
    <div
      role="alert"
      aria-label={label}
      className={cn(
        'pointer-events-auto flex items-start gap-3 rounded-lg border p-4 shadow-lg',
        'transition-all duration-300 ease-in-out',
        toastItem.isExiting
          ? 'translate-x-full opacity-0'
          : 'translate-x-0 opacity-100 animate-slide-in-right',
        style.container
      )}
    >
      {/* Icon */}
      <svg
        className={cn('h-5 w-5 flex-shrink-0 mt-0.5', style.icon)}
        viewBox={style.viewBox}
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fillRule="evenodd"
          d={style.iconPath}
          clipRule="evenodd"
        />
      </svg>

      {/* Message */}
      <p className="flex-1 text-sm font-medium leading-5">
        {toastItem.message}
      </p>

      {/* Dismiss button */}
      <button
        type="button"
        onClick={() => onDismiss(toastItem.id)}
        className={cn(
          'flex-shrink-0 rounded-md p-1 -m-1',
          'transition-colors duration-150',
          'hover:bg-black/5 focus:outline-none focus:ring-2 focus:ring-offset-1',
          toastItem.type === 'success' && 'focus:ring-green-500',
          toastItem.type === 'error' && 'focus:ring-red-500',
          toastItem.type === 'warning' && 'focus:ring-amber-500',
          toastItem.type === 'info' && 'focus:ring-blue-500'
        )}
        aria-label={`Dismiss ${label.toLowerCase()} notification`}
      >
        <svg
          className="h-4 w-4"
          viewBox="0 0 20 20"
          fill="currentColor"
          aria-hidden="true"
        >
          <path
            fillRule="evenodd"
            d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
            clipRule="evenodd"
          />
        </svg>
      </button>
    </div>
  )
}
