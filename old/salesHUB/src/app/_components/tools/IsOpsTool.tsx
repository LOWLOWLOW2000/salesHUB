import { revalidatePath } from 'next/cache'
import { redirect } from 'next/navigation'
import type { ProjectToolSection } from '@/lib/projectTools/toolSections'
import { prisma } from '@/lib/db/prisma'
import { getSession } from '@/lib/auth/session'
import { canConfigureProject } from '@/lib/auth/rbac'
import { canAccessProject } from '@/lib/projects/accessibleProjects'
import {
  deleteProjectScriptSchema,
  projectScriptFormSchema,
  scriptCategories
} from '@/lib/isHub/projectScript'
import { ProjectScriptForm } from '@/app/_components/tools/ProjectScriptForm'

type Props = {
  projectId: string
  section?: ProjectToolSection
  /** From parent `getProjectCapabilityFlags` to avoid duplicate RBAC queries. */
  canConfigure: boolean
}

const addProjectScript = async (formData: FormData) => {
  'use server'

  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const parsed = projectScriptFormSchema.parse(Object.fromEntries(formData))
  if (!(await canConfigureProject(userId, parsed.projectId))) redirect('/')

  const last = await prisma.projectScript.findFirst({
    where: { projectId: parsed.projectId, category: parsed.category },
    orderBy: { seq: 'desc' },
    select: { seq: true }
  })

  await prisma.projectScript.create({
    data: {
      projectId: parsed.projectId,
      category: parsed.category,
      title: parsed.title,
      body: parsed.body,
      seq: (last?.seq ?? 0) + 1
    }
  })

  revalidatePath(`/project/${parsed.projectId}`)
}

const deleteProjectScript = async (formData: FormData) => {
  'use server'

  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')

  const parsed = deleteProjectScriptSchema.parse(Object.fromEntries(formData))
  if (!(await canConfigureProject(userId, parsed.projectId))) redirect('/')

  await prisma.projectScript.delete({
    where: { id: parsed.scriptId }
  }).catch(() => null)

  revalidatePath(`/project/${parsed.projectId}`)
}

/**
 * IS運用メソッドを表示しつつ、案件固有のトーク/FAQ/切返しを編集可能にする。
 */
export const IsOpsTool = async ({ projectId, section, canConfigure }: Props) => {
  const session = await getSession()
  const userId = session?.user?.id
  if (!userId) redirect('/auth/signin')
  if (!(await canAccessProject(userId, projectId))) redirect('/')

  const editable = canConfigure
  const scripts = await prisma.projectScript.findMany({
    where: { projectId },
    orderBy: [{ category: 'asc' }, { seq: 'asc' }, { createdAt: 'asc' }]
  })

  return (
    <div className="space-y-7">
      <header>
        <h2 className="text-lg font-semibold tracking-tight text-zinc-950">IS運用</h2>
        <p className="mt-1 text-sm text-zinc-600">
          標準メソッドを土台に、案件固有のトーク・FAQ・NG切返しをナレッジ化します。
        </p>
        {!editable ? (
          <p id="is-ops-readonly-hint" className="mt-2 text-sm text-zinc-600">
            スクリプトの追加・削除は GM またはこの案件の Director / AS に限られます。登録済みの内容は閲覧できます。
          </p>
        ) : null}
      </header>

      {section ? (
        <section className="space-y-5 rounded-xl border border-zinc-200 bg-zinc-50 p-4">
          {section.blocks.map((block) => (
            <div key={block.heading}>
              <h3 className="text-sm font-semibold text-zinc-900">{block.heading}</h3>
              <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6 text-zinc-700">
                {block.bullets.map((bullet) => <li key={bullet}>{bullet}</li>)}
              </ul>
            </div>
          ))}
        </section>
      ) : null}

      {editable ? <ProjectScriptForm projectId={projectId} action={addProjectScript} /> : null}

      <div className="grid gap-4 lg:grid-cols-3">
        {scriptCategories.map((category) => {
          const rows = scripts.filter((script) => script.category === category.id)

          return (
            <section key={category.id} className="space-y-3 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
              <h3 className="text-sm font-semibold text-zinc-900">{category.label}</h3>
              <div className="space-y-3">
                {rows.map((script) => (
                  <article key={script.id} className="rounded-lg border border-zinc-100 bg-zinc-50 p-3">
                    <div className="flex items-start justify-between gap-3">
                      <h4 className="text-sm font-semibold text-zinc-900">{script.title}</h4>
                      {editable ? (
                        <form action={deleteProjectScript}>
                          <input type="hidden" name="projectId" value={projectId} />
                          <input type="hidden" name="scriptId" value={script.id} />
                          <button type="submit" className="text-xs font-medium text-zinc-500 hover:text-rose-700">
                            削除
                          </button>
                        </form>
                      ) : null}
                    </div>
                    <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-zinc-700">{script.body}</p>
                  </article>
                ))}
                {rows.length === 0 ? <p className="text-sm text-zinc-500">未登録</p> : null}
              </div>
            </section>
          )
        })}
      </div>
    </div>
  )
}
