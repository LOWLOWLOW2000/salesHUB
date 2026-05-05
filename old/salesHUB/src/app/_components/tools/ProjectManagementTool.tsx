import { revalidatePath } from 'next/cache'
import type { AppRole } from '@prisma/client'
import { prisma } from '@/lib/db/prisma'
import { getSession } from '@/lib/auth/session'
import { canConfigureProject } from '@/lib/auth/rbac'
import { appRoleUiLabel } from '@/lib/auth/app-role-labels'
import {
  sortMembersForManagement,
  toDisplayName,
  toRoleCategory,
  toSavedProjectRole,
  type MemberRow,
  type RoleCategory
} from '@/lib/projects/projectManagement'

type Props = {
  projectId: string
  canConfigure: boolean
}

const parseRoleEdits = (formData: FormData) =>
  Array.from(formData.entries()).reduce((acc, [key, value]) => {
    if (!key.startsWith('role:')) return acc
    const userId = key.slice('role:'.length).trim()
    if (userId.length === 0) return acc
    const raw = String(value ?? '').trim() as RoleCategory
    if (raw !== 'director' && raw !== 'leader' && raw !== 'member') return acc
    return { ...acc, [userId]: raw }
  }, {} as Record<string, RoleCategory>)

const saveProjectMembers = async (formData: FormData) => {
  'use server'

  const projectId = String(formData.get('projectId') ?? '').trim()
  if (projectId.length === 0) return

  const session = await getSession()
  const actorId = session?.user?.id
  if (!actorId) return

  const ok = await canConfigureProject(actorId, projectId)
  if (!ok) return

  const edits = parseRoleEdits(formData)
  const userIds = Object.keys(edits)
  if (userIds.length === 0) return

  await Promise.all(
    userIds.map(async (userId) => {
      const category = edits[userId]
      const role = toSavedProjectRole(category)

      await prisma.projectMember.deleteMany({
        where: { projectId, userId }
      })

      await prisma.projectMember.create({
        data: { projectId, userId, role }
      })
    })
  )

  revalidatePath(`/project/${projectId}`)
}

export const ProjectManagementTool = async ({ projectId, canConfigure }: Props) => {
  const members = await prisma.projectMember.findMany({
    where: { projectId },
    select: {
      userId: true,
      role: true,
      user: { select: { name: true, email: true } }
    }
  })

  const byUser = members.reduce((map, m) => {
    const current = map.get(m.userId)
    const nextRoles = current ? [...current.roles, m.role] : [m.role]
    map.set(m.userId, {
      userId: m.userId,
      name: m.user.name ?? null,
      email: m.user.email ?? null,
      roles: nextRoles as AppRole[]
    } satisfies MemberRow)
    return map
  }, new Map<string, MemberRow>())

  const rows = sortMembersForManagement(Array.from(byUser.values()))

  const categories: Array<{ id: RoleCategory; label: string; hint: string }> = [
    { id: 'director', label: 'Director', hint: appRoleUiLabel('director') },
    { id: 'leader', label: 'リーダー', hint: appRoleUiLabel('leader') },
    { id: 'member', label: 'メンバー', hint: appRoleUiLabel('is') }
  ]

  return (
    <div className="space-y-5">
      <header>
        <h2 className="text-lg font-semibold tracking-tight text-zinc-950">Project管理</h2>
        <p className="mt-1 text-sm text-zinc-600">
          メンバーの役職を排他的に更新します（Director / リーダー / メンバー）。メンバーは現状 IS として保存します。
        </p>
        {!canConfigure ? (
          <p className="mt-2 text-sm text-zinc-600">
            保存は GM またはこの案件の Director / AS / Leader に限られます。閲覧は可能です。
          </p>
        ) : null}
      </header>

      <form action={saveProjectMembers} className="space-y-4">
        <input type="hidden" name="projectId" value={projectId} />

        <div className="overflow-hidden rounded-xl border border-zinc-200">
          <div className="grid grid-cols-12 gap-2 bg-zinc-50 px-4 py-2 text-xs font-semibold text-zinc-600">
            <div className="col-span-4">メンバー</div>
            <div className="col-span-8">役職</div>
          </div>

          <ul className="divide-y divide-zinc-100 bg-white">
            {rows.map((m) => {
              const displayName = toDisplayName(m.name, m.email)
              const current = toRoleCategory(m.roles)

              return (
                <li key={m.userId} className="grid grid-cols-12 gap-2 px-4 py-3">
                  <div className="col-span-4 min-w-0">
                    <div className="truncate text-sm font-medium text-zinc-900">{displayName || '(no name)'}</div>
                    <div className="truncate text-xs text-zinc-600">{m.email ?? '(no email)'}</div>
                    <div className="mt-2">
                      <span className="rounded-full bg-zinc-100 px-2 py-0.5 text-[10px] font-semibold text-zinc-700">
                        {current.toUpperCase()}
                      </span>
                    </div>
                  </div>

                  <fieldset className="col-span-8 flex flex-wrap items-center gap-3">
                    {categories.map((c) => (
                      <label key={c.id} className="flex items-center gap-2 text-sm text-zinc-800">
                        <input
                          type="radio"
                          name={`role:${m.userId}`}
                          value={c.id}
                          defaultChecked={current === c.id}
                          disabled={!canConfigure}
                          className="h-4 w-4 accent-zinc-900"
                        />
                        <span className="font-medium">{c.label}</span>
                        <span className="text-xs text-zinc-500">({c.hint})</span>
                      </label>
                    ))}
                  </fieldset>
                </li>
              )
            })}
          </ul>
        </div>

        <div className="flex items-center justify-end gap-3">
          <button
            type="submit"
            disabled={!canConfigure}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            Save
          </button>
        </div>
      </form>
    </div>
  )
}

