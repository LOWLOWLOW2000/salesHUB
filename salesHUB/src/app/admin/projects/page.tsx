import Link from 'next/link'
import type { AppRole } from '@prisma/client'
import { prisma } from '@/lib/db/prisma'
import { requireGm } from '@/lib/auth/requireGm'

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

export default async function ProjectsPage() {
  const { company } = await requireGm()

  const projects = await prisma.project.findMany({
    where: { companyId: company.id },
    orderBy: { createdAt: 'desc' },
    select: {
      id: true,
      name: true,
      createdAt: true,
      members: {
        orderBy: { createdAt: 'desc' },
        select: {
          id: true,
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
          <p className="text-sm text-zinc-700">案件と D / AS / IS / FS / CS 割当</p>
        </div>
        <Link className="text-sm text-zinc-700 hover:text-zinc-950" href="/admin">
          ← Admin
        </Link>
      </div>

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

      <div className="space-y-4">
        {projects.map((project) => (
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
                {project.members.map((m) => (
                  <li key={m.id} className="flex flex-wrap items-center justify-between gap-3">
                    <div className="text-sm text-zinc-800">
                      <span className="rounded bg-zinc-100 px-2 py-0.5 text-xs font-medium text-zinc-700">
                        {m.role}
                      </span>{' '}
                      {m.user.email ?? '(no email)'}
                      {m.user.name ? <span className="text-xs text-zinc-500"> ({m.user.name})</span> : null}
                    </div>
                    <form action={removeMember}>
                      <input type="hidden" name="projectMemberId" value={m.id} />
                      <button
                        type="submit"
                        className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:border-zinc-300 hover:text-zinc-950"
                      >
                        解除
                      </button>
                    </form>
                  </li>
                ))}
              </ul>

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

              <div className="text-xs text-zinc-600">
                未ログインユーザーは Allowed emails に追加後、本人に一度ログインしてもらってください。
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
