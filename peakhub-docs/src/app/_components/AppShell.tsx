'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useMemo, useState } from 'react'

type NavItem = {
  href: string
  label: string
  description?: string
}

const navItems: NavItem[] = [
  { href: '/', label: 'ホーム' },
  { href: '/admin', label: 'Admin', description: '許可メール/案件など' },
  { href: '/api/auth/signout', label: 'サインアウト' }
]

const isActiveHref = (pathname: string, href: string) =>
  href === '/' ? pathname === '/' : pathname.startsWith(href)

export const AppShell = ({
  title,
  subtitle,
  children
}: {
  title: string
  subtitle?: string
  children: React.ReactNode
}) => {
  const pathname = usePathname()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const items = useMemo(
    () =>
      navItems.map((i) => ({
        ...i,
        active: isActiveHref(pathname, i.href)
      })),
    [pathname]
  )

  return (
    <div className="relative -mx-4 -my-10 min-h-[calc(100vh-7.5rem)] bg-zinc-50">
      <div className="mx-auto w-full max-w-5xl px-4 py-6">
        <div className="flex items-start gap-4">
          <aside className="hidden w-64 shrink-0 lg:block">
            <div className="sticky top-20 rounded-2xl border border-zinc-200 bg-white p-3 shadow-sm">
              <div className="px-3 pb-2 text-xs font-semibold text-zinc-600">メニュー</div>
              <nav className="space-y-1">
                {items.map((i) => (
                  <Link
                    key={i.href}
                    href={i.href}
                    className={[
                      'block rounded-xl px-3 py-2 text-sm transition',
                      i.active
                        ? 'bg-zinc-900 text-white'
                        : 'text-zinc-700 hover:bg-zinc-50 hover:text-zinc-950'
                    ].join(' ')}
                  >
                    <div className="font-medium">{i.label}</div>
                    {i.description ? (
                      <div className={i.active ? 'text-xs text-zinc-200' : 'text-xs text-zinc-500'}>
                        {i.description}
                      </div>
                    ) : null}
                  </Link>
                ))}
              </nav>
            </div>
          </aside>

          <div className="min-w-0 flex-1">
            <div className="sticky top-16 z-10 rounded-2xl border border-zinc-200/70 bg-white/80 p-4 backdrop-blur">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <div className="truncate text-base font-semibold tracking-tight">{title}</div>
                  {subtitle ? (
                    <div className="mt-1 truncate text-sm text-zinc-600">{subtitle}</div>
                  ) : null}
                </div>
                <button
                  type="button"
                  onClick={() => setSidebarOpen((v) => !v)}
                  className="inline-flex items-center rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm font-medium text-zinc-700 hover:border-zinc-300 hover:text-zinc-950 lg:hidden"
                >
                  メニュー
                </button>
              </div>
            </div>

            {sidebarOpen ? (
              <div className="mt-3 rounded-2xl border border-zinc-200 bg-white p-3 shadow-sm lg:hidden">
                <nav className="space-y-1">
                  {items.map((i) => (
                    <Link
                      key={i.href}
                      href={i.href}
                      onClick={() => setSidebarOpen(false)}
                      className={[
                        'block rounded-xl px-3 py-2 text-sm transition',
                        i.active
                          ? 'bg-zinc-900 text-white'
                          : 'text-zinc-700 hover:bg-zinc-50 hover:text-zinc-950'
                      ].join(' ')}
                    >
                      <div className="font-medium">{i.label}</div>
                      {i.description ? (
                        <div className={i.active ? 'text-xs text-zinc-200' : 'text-xs text-zinc-500'}>
                          {i.description}
                        </div>
                      ) : null}
                    </Link>
                  ))}
                </nav>
              </div>
            ) : null}

            <div className="mt-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">
              {children}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

