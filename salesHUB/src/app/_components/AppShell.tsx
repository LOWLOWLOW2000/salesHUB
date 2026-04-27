'use client'

import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useMemo, useState } from 'react'

type NavItem = {
  href: string
  label: string
  description?: string
}

export type AppShellProject = {
  id: string
  name: string
}

const navItems: NavItem[] = [
  { href: '/', label: 'ホーム' },
  { href: '/master-lists', label: 'Master lists' },
  { href: '/materials', label: 'Materials' },
  { href: '/admin', label: 'Admin', description: 'GM / 許可メール / Projects' },
  { href: '/api/auth/signout', label: 'サインアウト' }
]

const isActiveHref = (pathname: string, href: string) =>
  href === '/' ? pathname === '/' : pathname.startsWith(href)

/** 現在パスから /project/[id] の id を取り出す */
const projectIdFromPath = (pathname: string) => pathname.match(/^\/project\/([^/?#]+)/)?.[1] ?? null

type SidebarNavProps = {
  pathname: string
  items: Array<NavItem & { active: boolean }>
  projects: AppShellProject[]
  onNavigate?: () => void
}

const ProjectSelect = ({
  projects,
  pathname,
  onNavigate
}: {
  projects: AppShellProject[]
  pathname: string
  onNavigate?: () => void
}) => {
  const router = useRouter()
  const activeProjectId = projectIdFromPath(pathname)

  if (projects.length === 0) {
    return (
      <p className="px-3 text-xs leading-5 text-zinc-500">
        Project がありません。Admin の Projects で管理者に作成を依頼してください。
      </p>
    )
  }

  return (
    <div className="px-1 pt-1">
      <select
        id="app-shell-project-select"
        aria-label="Project"
        value={activeProjectId ?? ''}
        onChange={(e) => {
          const id = e.target.value
          onNavigate?.()
          if (id.length > 0) router.push(`/project/${id}`)
          else router.push('/')
        }}
        className="w-full rounded-xl border border-zinc-200 bg-white px-3 py-2 text-sm text-zinc-900 shadow-sm focus:border-zinc-400 focus:outline-none focus:ring-2 focus:ring-zinc-300"
      >
        <option value="">選択なし（ホーム）</option>
        {projects.map((p) => (
          <option key={p.id} value={p.id}>
            {p.name}
          </option>
        ))}
      </select>
    </div>
  )
}

const SidebarNav = ({ pathname, items, projects, onNavigate }: SidebarNavProps) => {
  return (
    <div className="space-y-4">
      <div>
        <div className="px-3 pb-2 text-xs font-semibold text-zinc-600">Project</div>
        <ProjectSelect projects={projects} pathname={pathname} onNavigate={onNavigate} />
      </div>

      <div>
        <div className="px-3 pb-2 text-xs font-semibold text-zinc-600">メニュー</div>
        <nav className="space-y-1">
          {items.map((i) => (
            <Link
              key={i.href}
              href={i.href}
              onClick={onNavigate}
              className={[
                'block rounded-xl px-3 py-2 text-sm transition',
                i.active ? 'bg-zinc-900 text-white' : 'text-zinc-700 hover:bg-zinc-50 hover:text-zinc-950'
              ].join(' ')}
            >
              <div className="font-medium">{i.label}</div>
              {i.description ? (
                <div className={i.active ? 'text-xs text-zinc-200' : 'text-xs text-zinc-500'}>{i.description}</div>
              ) : null}
            </Link>
          ))}
        </nav>
      </div>
    </div>
  )
}

export const AppShell = ({
  title,
  subtitle,
  projects = [],
  children
}: {
  title: string
  subtitle?: string
  /** 左カラムの Project プルダウン用（Prisma の Project 行） */
  projects?: AppShellProject[]
  /** メインの白カード内コンテンツ。省略時はカード自体を出さない */
  children?: React.ReactNode
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
              <SidebarNav pathname={pathname} items={items} projects={projects} />
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
                <SidebarNav
                  pathname={pathname}
                  items={items}
                  projects={projects}
                  onNavigate={() => setSidebarOpen(false)}
                />
              </div>
            ) : null}

            {children != null ? (
              <div className="mt-4 rounded-2xl border border-zinc-200 bg-white p-5 shadow-sm">{children}</div>
            ) : null}
          </div>
        </div>
      </div>
    </div>
  )
}
