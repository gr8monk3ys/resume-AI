'use client'

import Link from 'next/link'
import { useAuth } from '@/lib/auth'
import { usePathname } from 'next/navigation'
import { cn } from '@/lib/utils'
import {
  Home,
  FileText,
  Briefcase,
  FileEdit,
  Mic,
  Award,
  User,
  LogOut,
  Menu,
  X,
  Settings,
  LogIn,
  UserPlus,
  BarChart3,
  Filter,
} from 'lucide-react'
import { useState, useEffect, useRef } from 'react'

/**
 * Navigation items for authenticated users
 * Matches the 6 core features of the application
 */
const navigation = [
  { name: 'Dashboard', href: '/', icon: Home },
  { name: 'Resume Hub', href: '/resumes', icon: FileText },
  { name: 'Job Pipeline', href: '/jobs', icon: Briefcase },
  { name: 'Job Filters', href: '/jobs/filters', icon: Filter },
  { name: 'Analytics', href: '/analytics', icon: BarChart3 },
  { name: 'Interview Center', href: '/interview', icon: Mic },
  { name: 'Document Generator', href: '/documents', icon: FileEdit },
  { name: 'Career Tools', href: '/career', icon: Award },
]

/**
 * User menu items
 */
const userMenuItems = [
  { name: 'Profile', href: '/profile', icon: User },
  { name: 'Account & Settings', href: '/settings', icon: Settings },
]

/**
 * Main navigation component
 * Handles responsive design with mobile menu
 * Shows different navigation based on authentication state
 */
export function Navbar() {
  const { user, logout, isLoading } = useAuth()
  const pathname = usePathname()
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const mobileMenuRef = useRef<HTMLDivElement>(null)

  // Close mobile menu on route change
  useEffect(() => {
    setMobileMenuOpen(false)
  }, [pathname])

  // Close mobile menu when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        mobileMenuRef.current &&
        !mobileMenuRef.current.contains(event.target as Node)
      ) {
        setMobileMenuOpen(false)
      }
    }

    if (mobileMenuOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [mobileMenuOpen])

  // Handle escape key to close mobile menu
  useEffect(() => {
    function handleEscapeKey(event: KeyboardEvent) {
      if (event.key === 'Escape') {
        setMobileMenuOpen(false)
      }
    }

    if (mobileMenuOpen) {
      document.addEventListener('keydown', handleEscapeKey)
    }

    return () => {
      document.removeEventListener('keydown', handleEscapeKey)
    }
  }, [mobileMenuOpen])

  /**
   * Handle logout action
   */
  const handleLogout = () => {
    setMobileMenuOpen(false)
    logout()
  }

  /**
   * Check if a path is currently active
   */
  const isActivePath = (href: string): boolean => {
    if (href === '/') {
      return pathname === '/'
    }
    return pathname.startsWith(href)
  }

  return (
    <nav
      className="bg-white shadow-sm border-b sticky top-0 z-50"
      role="navigation"
      aria-label="Main navigation"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          {/* Logo and Brand */}
          <div className="flex items-center">
            <Link
              href="/"
              className="flex items-center focus:outline-none focus:ring-2 focus:ring-primary-500 focus:ring-offset-2 rounded-md"
            >
              <span className="text-xl font-bold text-primary-600">
                ResuBoost AI
              </span>
            </Link>
          </div>

          {/* Desktop Navigation */}
          <div className="hidden lg:flex lg:items-center lg:space-x-1">
            {!isLoading && user && (
              <>
                {/* Main Navigation Links */}
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                      isActivePath(item.href)
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    )}
                    aria-current={isActivePath(item.href) ? 'page' : undefined}
                  >
                    <item.icon className="w-4 h-4 mr-2" aria-hidden="true" />
                    {item.name}
                  </Link>
                ))}

                {/* Divider */}
                <div
                  className="h-6 w-px bg-gray-200 mx-2"
                  aria-hidden="true"
                />

                {/* User Menu Items */}
                {userMenuItems.map((item) => (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'inline-flex items-center px-3 py-2 text-sm font-medium rounded-md transition-colors',
                      isActivePath(item.href)
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    )}
                    aria-current={isActivePath(item.href) ? 'page' : undefined}
                  >
                    <item.icon className="w-4 h-4 mr-2" aria-hidden="true" />
                    {item.name}
                  </Link>
                ))}

                {/* Logout Button */}
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 rounded-md transition-colors"
                >
                  <LogOut className="w-4 h-4 mr-2" aria-hidden="true" />
                  Logout
                </button>
              </>
            )}

            {/* Auth Links for Unauthenticated Users */}
            {!isLoading && !user && (
              <>
                <Link
                  href="/login"
                  className={cn(
                    'inline-flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors',
                    pathname === '/login'
                      ? 'bg-primary-50 text-primary-700'
                      : 'text-gray-600 hover:text-gray-900'
                  )}
                >
                  <LogIn className="w-4 h-4 mr-2" aria-hidden="true" />
                  Login
                </Link>
                <Link
                  href="/register"
                  className="inline-flex items-center px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-md transition-colors"
                >
                  <UserPlus className="w-4 h-4 mr-2" aria-hidden="true" />
                  Register
                </Link>
              </>
            )}
          </div>

          {/* Mobile Menu Button */}
          <div className="flex items-center lg:hidden">
            <button
              type="button"
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 rounded-md text-gray-600 hover:text-gray-900 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
              aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
              aria-expanded={mobileMenuOpen}
              aria-controls="mobile-menu"
            >
              {mobileMenuOpen ? (
                <X className="w-6 h-6" aria-hidden="true" />
              ) : (
                <Menu className="w-6 h-6" aria-hidden="true" />
              )}
            </button>
          </div>
        </div>
      </div>

      {/* Mobile Menu */}
      <div
        ref={mobileMenuRef}
        id="mobile-menu"
        className={cn(
          'lg:hidden transition-all duration-200 ease-in-out overflow-hidden',
          mobileMenuOpen ? 'max-h-screen opacity-100' : 'max-h-0 opacity-0'
        )}
        aria-hidden={!mobileMenuOpen}
      >
        <div className="bg-white border-t shadow-lg">
          {!isLoading && user ? (
            <div className="py-2">
              {/* User Info */}
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900">
                  {user.full_name || user.username}
                </p>
                <p className="text-xs text-gray-500 truncate">{user.email}</p>
              </div>

              {/* Navigation Links */}
              <nav className="py-2" aria-label="Mobile navigation">
                {navigation.map((item) => (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'flex items-center px-4 py-3 text-base font-medium transition-colors',
                      isActivePath(item.href)
                        ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-600'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    )}
                    aria-current={isActivePath(item.href) ? 'page' : undefined}
                  >
                    <item.icon className="w-5 h-5 mr-3" aria-hidden="true" />
                    {item.name}
                  </Link>
                ))}
              </nav>

              {/* User Menu Section */}
              <div className="border-t border-gray-100 py-2">
                {userMenuItems.map((item) => (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'flex items-center px-4 py-3 text-base font-medium transition-colors',
                      isActivePath(item.href)
                        ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-600'
                        : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                    )}
                    aria-current={isActivePath(item.href) ? 'page' : undefined}
                  >
                    <item.icon className="w-5 h-5 mr-3" aria-hidden="true" />
                    {item.name}
                  </Link>
                ))}
                <button
                  onClick={handleLogout}
                  className="flex items-center w-full px-4 py-3 text-base font-medium text-gray-600 hover:bg-gray-50 hover:text-gray-900 transition-colors"
                >
                  <LogOut className="w-5 h-5 mr-3" aria-hidden="true" />
                  Logout
                </button>
              </div>
            </div>
          ) : !isLoading ? (
            <div className="py-3 space-y-1">
              <Link
                href="/login"
                className={cn(
                  'flex items-center px-4 py-3 text-base font-medium transition-colors',
                  pathname === '/login'
                    ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-600'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )}
              >
                <LogIn className="w-5 h-5 mr-3" aria-hidden="true" />
                Login
              </Link>
              <Link
                href="/register"
                className={cn(
                  'flex items-center px-4 py-3 text-base font-medium transition-colors',
                  pathname === '/register'
                    ? 'bg-primary-50 text-primary-700 border-l-4 border-primary-600'
                    : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
                )}
              >
                <UserPlus className="w-5 h-5 mr-3" aria-hidden="true" />
                Register
              </Link>
            </div>
          ) : null}
        </div>
      </div>
    </nav>
  )
}
