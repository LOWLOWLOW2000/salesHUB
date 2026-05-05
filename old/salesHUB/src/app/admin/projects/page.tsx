import Link from 'next/link'
import type { AppRole } from '@prisma/client'
import { redirect } from 'next/navigation'
import { prisma } from '@/lib/db/prisma'
import { requireGm } from '@/lib/auth/requireGm'
import { requireProjectMgmt } from '@/lib/auth/requireMgmt'
import { getSession } from '@/lib/auth/session'
import { getOrCreateDefaultCompany } from '@/lib/auth/company'
import { hasCompanyRole } from '@/lib/auth/rbac'
import { appRoleUiLabel } from '@/lib/auth/app-role-labels'

const normalizeEmail = (email: string) => email.trim().toLowerCase()

const projectRoles: AppRole[] = ['director', 'as', 'is', 'fs', 'cs']

const createProject = async (formData: FormData) => {
  'use server'

  const { company } = await requireGm()

  const name = String(formData.get('name') ?? '').trim()
  if (name.length === 0) return

  await prisma.project.create({
    data: { name, companyId: company.id }
  })
}

const assignMember = async (formData: FormData) => {
  'use server'

  await requireGm()

  const projectId = String(formData.get('projectId') ?? '')
  const email = normalizeEmail(String(formData.get('email') ?? ''))
  const role = String(formData.get('role') ?? '') as AppRole
  if (projectId.length === 0 || email.length === 0) return
  if (!projectRoles.includes(role)) return

  const user = await prisma.user.findUnique({
    where: { email },
    select: { id: true }
  })

  if (!user) return

  await prisma.projectMember.upsert({
    where: {
      projectId_userId_role: {
        projectId,
        userId: user.id,
        role
      }
    },
    update: {},
    create: {
      projectId,
      userId: user.id,
      role
    }
  })
}

const removeMember = async (formData: FormData) => {
  'use server'

  await requireGm()

  const projectMemberId = String(formData.get('projectMemberId') ?? '')
  if (projectMemberId.length === 0) return

  await prisma.projectMember.delete({ where: { id: projectMemberId } }).catch(() => null)
}

const assignLeader = async (formData: FormData) => {
  'use server'

  const projectId = String(formData.get('projectId') ?? '')
  const userId = String(formData.get('userId') ?? '')
  if (projectId.length === 0 || userId.length === 0) return

  await requireProjectMgmt(projectId)

  const existing = await prisma.projectMember.findFirst({
    where: { projectId, userId },
    select: { id: true }
  })
  if (!existing) return

  await prisma.projectMember.upsert({
    where: {
      projectId_userId_role: {
        projectId,
        userId,
        role: 'leader'
      }
    },
    update: {},
    create: {
      projectId,
      userId,
      role: 'leader'
    }
  })
}

const removeLeader = async (formData: FormData) => {
  'use server'

  const projectId = String(formData.get('projectId') ?? '')
  const projectMemberId = String(formData.get('projectMemberId') ?? '')
  if (projectId.length === 0 || projectMemberId.length === 0) return

  await requireProjectMgmt(projectId)

  await prisma.projectMember.delete({ where: { id: projectMemberId } }).catch(() => null)
}

export default async function ProjectsPage() {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const company = await getOrCreateDefaultCompany()
  const isGm = await hasCompanyRole(userId, company.id, 'gm')

  const projects = await prisma.project.findMany({
    where: isGm
      ? { companyId: company.id }
      : {
          companyId: company.id,
          members: { some: { userId, role: { in: ['director', 'as'] } } }
        },
    orderBy: { createdAt: 'desc' },
    select: {
      id: true,
      name: true,
      createdAt: true,
      members: {
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
          userId: true,
          role: true,
          user: { select: { email: true, name: true } }
        }
      }
    }
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Projects</h1>
          <p className="text-sm text-zinc-700">案件と Director・AS・Leader・IS・FS・CS の割当</p>
        </div>
        {isGm ? (
          <Link className="text-sm text-zinc-700 hover:text-zinc-950" href="/admin">
            ← Admin
          </Link>
        ) : (
          <Link className="text-sm text-zinc-700 hover:text-zinc-950" href="/">
            ← Home
          </Link>
        )}
      </div>

      {isGm ? (
        <form action={createProject} className="flex flex-wrap gap-2">
          <input
            name="name"
            required
            placeholder="案件名"
            className="w-full max-w-sm rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-300"
          />
          <button
            type="submit"
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
          >
            追加
          </button>
        </form>
      ) : null}

      <div className="space-y-4">
        {projects.map((project) => {
          const leaderMembers = project.members.filter((m) => m.role === 'leader')
          const nonLeaderMembers = project.members.filter((m) => m.role !== 'leader')
          const canManageLeader = isGm || project.members.some((m) => m.role === 'director' || m.role === 'as')

          const leaderUserIds = new Set(leaderMembers.map((m) => m.userId))
          const candidateUserRows = Array.from(
            nonLeaderMembers.reduce((map, m) => {
              if (!map.has(m.userId)) map.set(m.userId, m)
              return map
            }, new Map<string, (typeof nonLeaderMembers)[number]>())
          ).filter((m) => !leaderUserIds.has(m.userId))

          return (
            <div key={project.id} className="rounded-xl border border-zinc-200 bg-white shadow-sm">
              <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-200 px-4 py-3">
                <div>
                  <div className="text-sm font-semibold">{project.name}</div>
                  <div className="text-xs text-zinc-600">{project.createdAt.toISOString()}</div>
                </div>
                <Link
                  className="text-xs font-medium text-zinc-700 hover:text-zinc-950"
                  href={`/sales-room/${project.id}`}
                >
                  架電ルーム →
                </Link>
              </div>

              <div className="space-y-3 px-4 py-4">
                <div className="text-xs font-semibold text-zinc-700">Members</div>

                <ul className="space-y-2">
                  {nonLeaderMembers.map((m) => (
                    <li key={m.id} className="flex flex-wrap items-center justify-between gap-3">
                      <div className="text-sm text-zinc-800">
                        <span
                          className="rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-700"
                          title={appRoleUiLabel(m.role)}
                        >
                          {m.role}
                        </span>{' '}
                        {m.user.email ?? '(no email)'}
                        {m.user.name ? <span className="text-xs text-zinc-500"> ({m.user.name})</span> : null}
                      </div>
                      {isGm ? (
                        <form action={removeMember}>
                          <input type="hidden" name="projectMemberId" value={m.id} />
                          <button
                            type="submit"
                            className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:border-zinc-300 hover:text-zinc-950"
                          >
                            解除
                          </button>
                        </form>
                      ) : null}
                    </li>
                  ))}
                </ul>

                {isGm ? (
                  <form action={assignMember} className="flex flex-wrap items-end gap-2 pt-2">
                    <input type="hidden" name="projectId" value={project.id} />
                    <input
                      name="email"
                      type="email"
                      required
                      placeholder="user@example.com"
                      className="w-full max-w-xs rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-300"
                    />
                    <select
                      name="role"
                      className="rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-300"
                      defaultValue="director"
                    >
                      {projectRoles.map((r) => (
                        <option key={r} value={r}>
                          {r}
                        </option>
                      ))}
                    </select>
                    <button
                      type="submit"
                      className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
                    >
                      割当
                    </button>
                  </form>
                ) : null}

                {canManageLeader ? (
                  <div className="mt-4 space-y-3 border-t border-zinc-200 pt-4">
                    <div>
                      <div className="text-xs font-semibold text-zinc-700">Leader（PJ運用リーダー）</div>
                      <div className="mt-1 text-xs text-zinc-600">Director/AS が一時的に Director 相当の権限を付与します</div>
                    </div>

                    <ul className="space-y-2">
                      {leaderMembers.length === 0 ? (
                        <li className="text-sm text-zinc-500">現在、Leader は未設定です</li>
                      ) : (
                        leaderMembers.map((m) => (
                          <li key={m.id} className="flex flex-wrap items-center justify-between gap-3">
                            <div className="text-sm text-zinc-800">
                              <span
                                className="rounded bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700"
                                title={appRoleUiLabel(m.role)}
                              >
                                leader
                              </span>{' '}
                              {m.user.email ?? '(no email)'}
                              {m.user.name ? <span className="text-xs text-amber-600"> ({m.user.name})</span> : null}
                            </div>
                            <form action={removeLeader}>
                              <input type="hidden" name="projectId" value={project.id} />
                              <input type="hidden" name="projectMemberId" value={m.id} />
                              <button
                                type="submit"
                                className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:border-zinc-300 hover:text-zinc-950"
                              >
                                解除
                              </button>
                            </form>
                          </li>
                        ))
                      )}
                    </ul>

                    <form action={assignLeader} className="flex flex-wrap items-end gap-2 pt-2">
                      <input type="hidden" name="projectId" value={project.id} />
                      <select
                        name="userId"
                        className="min-w-[220px] rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-300"
                        disabled={candidateUserRows.length === 0}
                      >
                        {candidateUserRows.length === 0 ? (
                          <option value="" disabled>
                            付与できる候補がありません
                          </option>
                        ) : (
                          candidateUserRows.map((u) => (
                            <option key={u.userId} value={u.userId}>
                              {u.user.name ?? '(no name)'}
                              {u.user.email ? ` (${u.user.email})` : ''}
                            </option>
                          ))
                        )}
                      </select>
                      <button
                        type="submit"
                        disabled={candidateUserRows.length === 0}
                        className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        付与
                      </button>
                    </form>
                  </div>
                ) : null}

                {isGm ? (
                  <div className="text-xs text-zinc-600">
                    未ログインユーザーは Allowed emails に追加後、本人に一度ログインしてもらってください。
                  </div>
                ) : null}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
