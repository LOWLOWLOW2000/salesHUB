import Link from 'next/link'
import type { AppRole } from '@prisma/client'
import { prisma } from '@/lib/db/prisma'
import { requireGm } from '@/lib/auth/requireGm'
import { appRoleUiLabel } from '@/lib/auth/app-role-labels'

const normalizeEmail = (email: string) => email.trim().toLowerCase()

/** Company-scoped tiers GM can grant (`director` is project-scope only). */
const assignableCompanyRoles: AppRole[] = ['manager', 'as', 'is', 'fs', 'cs']

const assignCompanyRole = async (formData: FormData) => {
  'use server'

  const { company } = await requireGm()

  const email = normalizeEmail(String(formData.get('email') ?? ''))
  const role = String(formData.get('role') ?? '') as AppRole
  if (email.length === 0 || !assignableCompanyRoles.includes(role)) return

  const user = await prisma.user.findUnique({
    where: { email },
    select: { id: true }
  })
  if (!user) return

  await prisma.companyMember.upsert({
    where: {
      companyId_userId_role: {
        companyId: company.id,
        userId: user.id,
        role
      }
    },
    update: {},
    create: {
      companyId: company.id,
      userId: user.id,
      role
    }
  })
}

const removeCompanyRole = async (formData: FormData) => {
  'use server'

  await requireGm()

  const memberId = String(formData.get('companyMemberId') ?? '')
  if (memberId.length === 0) return

  await prisma.companyMember.delete({ where: { id: memberId } }).catch(() => null)
}

export default async function AdminUsersPage() {
  const { company } = await requireGm()

  const members = await prisma.companyMember.findMany({
    where: { companyId: company.id },
    orderBy: { createdAt: 'desc' },
    select: {
      id: true,
      role: true,
      user: { select: { email: true, name: true } }
    }
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Company roles</h1>
          <p className="text-sm text-zinc-700">会社スコープ（Manager は全PJ閲覧〜、Director は案件メンバーで付与）</p>
        </div>
        <Link className="text-sm text-zinc-700 hover:text-zinc-950" href="/admin">
          ← Admin
        </Link>
      </div>

      <ul className="space-y-2 rounded-xl border border-zinc-200 bg-white p-4">
        {members.map((m) => (
          <li key={m.id} className="flex flex-wrap items-center justify-between gap-2">
            <div className="text-sm text-zinc-800">
              <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium" title={appRoleUiLabel(m.role)}>
                {m.role}
              </span>{' '}
              {m.user.email} {m.user.name ? <span className="text-xs text-zinc-500">({m.user.name})</span> : null}
            </div>
            {m.role !== 'gm' ? (
              <form action={removeCompanyRole}>
                <input type="hidden" name="companyMemberId" value={m.id} />
                <button
                  type="submit"
                  className="rounded-lg border border-zinc-200 px-2 py-1 text-xs text-zinc-700 hover:bg-zinc-50"
                >
                  解除
                </button>
              </form>
            ) : (
              <span className="text-xs text-zinc-500">GM</span>
            )}
          </li>
        ))}
      </ul>

      <form action={assignCompanyRole} className="flex flex-wrap items-end gap-2">
        <input
          name="email"
          type="email"
          required
          placeholder="user@example.com"
          className="w-full max-w-xs rounded-lg border border-zinc-200 px-3 py-2 text-sm"
        />
        <select name="role" className="rounded-lg border border-zinc-200 px-3 py-2 text-sm" defaultValue="manager">
          {assignableCompanyRoles.map((r) => (
            <option key={r} value={r}>
              {r} — {appRoleUiLabel(r)}
            </option>
          ))}
        </select>
        <button
          type="submit"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
        >
          付与
        </button>
      </form>
    </div>
  )
}
