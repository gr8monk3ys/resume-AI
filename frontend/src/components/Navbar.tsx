'use client'

import {
  BarChart3,
  Briefcase,
  FileEdit,
  FileText,
  Filter,
  LogIn,
  LogOut,
  Menu,
  Mic,
  Settings,
  User,
  UserPlus,
  X,
} from 'lucide-react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'

import { BrandMark } from '@/components/BrandMark'
import { useAuth } from '@/lib/auth'
import { cn } from '@/lib/utils'

const productNavigation = [
  { name: 'Dashboard', href: '/dashboard', icon: BarChart3 },
  { name: 'Pipeline', href: '/jobs', icon: Briefcase },
  { name: 'Search Filters', href: '/jobs/filters', icon: Filter },
  { name: 'Resume Lab', href: '/resumes', icon: FileText },
  { name: 'Documents', href: '/documents', icon: FileEdit },
  { name: 'Interviews', href: '/interview', icon: Mic },
]

const accountNavigation = [
  { name: 'Profile', href: '/profile', icon: User },
  { name: 'Settings', href: '/settings', icon: Settings },
]

function getDisplayName(user: {
  full_name: string | null
  username: string
}) {
  return user.full_name || user.username
}

function getInitials(user: {
  full_name: string | null
  username: string
}) {
  const source = getDisplayName(user)
  const parts = source.split(' ').filter(Boolean)

  if (parts.length > 1) {
    return `${parts[0]?.[0] ?? ''}${parts[1]?.[0] ?? ''}`.toUpperCase()
  }

  return source.slice(0, 2).toUpperCase()
}

export function Navbar() {
  const { user, logout, isLoading } = useAuth()
  const pathname = usePathname() ?? '/'
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false)
  const mobileMenuRef = useRef<HTMLDivElement>(null)

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

  const closeMobileMenu = () => {
    setMobileMenuOpen(false)
  }

  const handleLogout = () => {
    setMobileMenuOpen(false)
    void logout()
  }

  const isActivePath = (href: string): boolean => {
    if (href === '/dashboard') {
      return pathname === '/' || pathname === '/dashboard'
    }

    return pathname === href || pathname.startsWith(`${href}/`)
  }

  const authenticatedShell = !isLoading && Boolean(user)

  return (
    <nav
      className="sticky top-0 z-50 border-b border-black/5 bg-[rgba(252,250,245,0.88)] backdrop-blur-xl"
      aria-label="Main navigation"
    >
      <div className="shell-width py-3">
        <div className="surface-card-strong overflow-hidden">
          <div className="flex items-center justify-between gap-4 px-4 py-4 sm:px-6">
            <Link
              href={authenticatedShell ? '/dashboard' : '/'}
              onClick={closeMobileMenu}
              className="rounded-2xl focus:outline-none focus:ring-2 focus:ring-[color:var(--accent)] focus:ring-offset-2"
            >
              <BrandMark subdued />
            </Link>

            {authenticatedShell && user ? (
              <div className="hidden min-w-0 flex-1 items-center justify-center xl:flex">
                <Link
                  href="/jobs/filters"
                  className="flex w-full max-w-xl items-center justify-between gap-3 rounded-full border border-black/8 bg-white/80 px-4 py-3 text-sm text-slate-700 transition hover:-translate-y-0.5 hover:border-black/12 hover:bg-white"
                >
                  <span className="flex items-center gap-3">
                    <Filter className="h-4 w-4 text-[color:var(--accent)]" />
                    <span className="truncate font-medium">
                      Tune target roles, company rules, and search focus
                    </span>
                  </span>
                  <span className="rounded-full bg-[color:var(--accent-soft)] px-3 py-1 text-[0.68rem] font-semibold uppercase tracking-[0.18em] text-[color:var(--accent-strong)]">
                    Search-first
                  </span>
                </Link>
              </div>
            ) : (
              <div className="hidden items-center gap-3 lg:flex">
                <p className="max-w-md text-sm text-slate-600">
                  One place to keep your search brief, application memory, resume tuning, and interview prep together.
                </p>
              </div>
            )}

            <div className="hidden items-center gap-3 lg:flex">
              {authenticatedShell && user ? (
                <>
                  <div className="hidden items-center gap-3 rounded-full border border-black/8 bg-white/80 px-3 py-2 xl:flex">
                    <span className="flex h-10 w-10 items-center justify-center rounded-full bg-[#10243f] text-sm font-semibold text-white">
                      {getInitials(user)}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">
                        {getDisplayName(user)}
                      </p>
                      <p className="truncate text-xs text-slate-500">{user.email}</p>
                    </div>
                  </div>
                  <button
                    type="button"
                    onClick={handleLogout}
                    className="inline-flex items-center gap-2 rounded-full border border-black/8 bg-white/80 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-white"
                  >
                    <LogOut className="h-4 w-4" />
                    Sign out
                  </button>
                </>
              ) : !isLoading ? (
                <>
                  <Link
                    href="/login"
                    className="inline-flex items-center gap-2 rounded-full px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-white/70"
                  >
                    <LogIn className="h-4 w-4" />
                    Sign in
                  </Link>
                  <Link
                    href="/register"
                    className="inline-flex items-center gap-2 rounded-full bg-[#10243f] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#0b1728]"
                  >
                    <UserPlus className="h-4 w-4" />
                    Start free
                  </Link>
                </>
              ) : null}
            </div>

            <div className="flex items-center gap-3 lg:hidden">
              {authenticatedShell && user ? (
                <Link
                  href="/jobs/filters"
                  onClick={closeMobileMenu}
                  className="inline-flex items-center gap-2 rounded-full border border-black/8 bg-white/80 px-3 py-2 text-xs font-semibold uppercase tracking-[0.18em] text-slate-700"
                >
                  <Filter className="h-3.5 w-3.5 text-[color:var(--accent)]" />
                  Focus
                </Link>
              ) : null}
              <button
                type="button"
                onClick={() => setMobileMenuOpen((isOpen) => !isOpen)}
                className="inline-flex h-11 w-11 items-center justify-center rounded-full border border-black/8 bg-white/80 text-slate-700 transition hover:bg-white"
                aria-label={mobileMenuOpen ? 'Close menu' : 'Open menu'}
                aria-expanded={mobileMenuOpen}
                aria-controls="mobile-menu"
              >
                {mobileMenuOpen ? (
                  <X className="h-5 w-5" aria-hidden="true" />
                ) : (
                  <Menu className="h-5 w-5" aria-hidden="true" />
                )}
              </button>
            </div>
          </div>

          {authenticatedShell && user && (
            <div className="hidden border-t border-black/6 px-4 py-3 lg:block sm:px-6">
              <div className="flex flex-wrap items-center gap-2">
                {productNavigation.map((item) => (
                  <Link
                    key={item.name}
                    href={item.href}
                    className={cn(
                      'inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-medium transition',
                      isActivePath(item.href)
                        ? 'bg-[#10243f] text-white shadow-[0_16px_30px_-22px_rgba(16,36,63,0.8)]'
                        : 'text-slate-600 hover:bg-white/80 hover:text-slate-900'
                    )}
                    aria-current={isActivePath(item.href) ? 'page' : undefined}
                  >
                    <item.icon className="h-4 w-4" aria-hidden="true" />
                    {item.name}
                  </Link>
                ))}
                <div className="ml-auto flex items-center gap-2">
                  {accountNavigation.map((item) => (
                    <Link
                      key={item.name}
                      href={item.href}
                      className={cn(
                        'inline-flex items-center gap-2 rounded-full px-3 py-2 text-sm font-medium transition',
                        isActivePath(item.href)
                          ? 'bg-white text-slate-900'
                          : 'text-slate-500 hover:bg-white/70 hover:text-slate-900'
                      )}
                      aria-current={isActivePath(item.href) ? 'page' : undefined}
                    >
                      <item.icon className="h-4 w-4" aria-hidden="true" />
                      {item.name}
                    </Link>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>

      {mobileMenuOpen && (
        <div ref={mobileMenuRef} id="mobile-menu" className="shell-width pb-3 lg:hidden">
          <div className="surface-card-strong overflow-hidden px-4 py-4">
            {authenticatedShell && user ? (
              <div className="space-y-4">
                <div className="rounded-3xl border border-black/6 bg-white/80 p-4">
                  <div className="flex items-center gap-3">
                    <span className="flex h-11 w-11 items-center justify-center rounded-full bg-[#10243f] text-sm font-semibold text-white">
                      {getInitials(user)}
                    </span>
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-slate-900">
                        {getDisplayName(user)}
                      </p>
                      <p className="truncate text-xs text-slate-500">{user.email}</p>
                    </div>
                  </div>
                </div>

                <nav className="grid gap-2" aria-label="Mobile navigation">
                  {[...productNavigation, ...accountNavigation].map((item) => (
                    <Link
                      key={item.name}
                      href={item.href}
                      onClick={closeMobileMenu}
                      className={cn(
                        'flex items-center gap-3 rounded-2xl px-4 py-3 text-sm font-medium transition',
                        isActivePath(item.href)
                          ? 'bg-[#10243f] text-white'
                          : 'bg-white/70 text-slate-700 hover:bg-white'
                      )}
                      aria-current={isActivePath(item.href) ? 'page' : undefined}
                    >
                      <item.icon className="h-4 w-4" aria-hidden="true" />
                      {item.name}
                    </Link>
                  ))}
                </nav>

                <button
                  type="button"
                  onClick={handleLogout}
                  className="flex w-full items-center justify-center gap-2 rounded-2xl border border-black/8 bg-white/70 px-4 py-3 text-sm font-semibold text-slate-700"
                >
                  <LogOut className="h-4 w-4" aria-hidden="true" />
                  Sign out
                </button>
              </div>
            ) : !isLoading ? (
              <div className="space-y-3">
                <p className="rounded-3xl bg-white/70 p-4 text-sm leading-6 text-slate-600">
                  Keep your target roles, search filters, resumes, applications, and interview prep in one operating surface.
                </p>
                <Link
                  href="/register"
                  onClick={closeMobileMenu}
                  className="flex items-center justify-center gap-2 rounded-2xl bg-[#10243f] px-4 py-3 text-sm font-semibold text-white"
                >
                  <UserPlus className="h-4 w-4" aria-hidden="true" />
                  Create account
                </Link>
                <Link
                  href="/login"
                  onClick={closeMobileMenu}
                  className="flex items-center justify-center gap-2 rounded-2xl border border-black/8 bg-white/70 px-4 py-3 text-sm font-semibold text-slate-700"
                >
                  <LogIn className="h-4 w-4" aria-hidden="true" />
                  Sign in
                </Link>
              </div>
            ) : null}
          </div>
        </div>
      )}
    </nav>
  )
}
