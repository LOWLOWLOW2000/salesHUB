import Link from 'next/link'
import {
  getProjectToolSection,
  projectToolNavItems,
  type ProjectToolId
} from '@/lib/projectTools/toolSections'
import { DailyReportTool } from '@/app/_components/tools/DailyReportTool'
import { IsOpsTool } from '@/app/_components/tools/IsOpsTool'
import { KpiDashboardTool } from '@/app/_components/tools/KpiDashboardTool'

type Props = {
  projectId: string
  activeId: ProjectToolId
}

/**
 * プロジェクト配下の「実行ツール」: 左ナビ + クエリ `tool` で本文切替。
 */
export const ProjectToolWorkspace = ({ projectId, activeId }: Props) => {
  const section = getProjectToolSection(activeId)

  const hrefFor = (id: ProjectToolId) =>
    `/project/${encodeURIComponent(projectId)}?tool=${encodeURIComponent(id)}`

  return (
    <div className="flex flex-col gap-4 lg:flex-row lg:items-start">
      <nav
        aria-label="プロジェクト実行ツール"
        className="w-full shrink-0 rounded-2xl border border-zinc-200 bg-zinc-50 p-2 lg:w-56"
      >
        <div className="px-2 pb-2 pt-1 text-xs font-semibold uppercase tracking-wide text-zinc-500">
          実行ツール
        </div>
        <ul className="space-y-1">
          {projectToolNavItems.map((item) => {
            const active = item.id === activeId
            return (
              <li key={item.id}>
                <Link
                  href={hrefFor(item.id)}
                  className={[
                    'block rounded-xl px-3 py-2 text-sm transition',
                    active
                      ? 'bg-zinc-900 text-white shadow-sm'
                      : 'text-zinc-800 hover:bg-white hover:text-zinc-950'
                  ].join(' ')}
                >
                  <div className="font-medium">{item.label}</div>
                  <div className={active ? 'mt-0.5 text-xs text-zinc-300' : 'mt-0.5 text-xs text-zinc-500'}>
                    {item.summary}
                  </div>
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      <article className="min-w-0 flex-1 space-y-5">
        {activeId === 'daily-report' ? <DailyReportTool projectId={projectId} /> : null}
        {activeId === 'kpi-dashboard' ? <KpiDashboardTool projectId={projectId} /> : null}
        {activeId === 'is-ops' ? <IsOpsTool projectId={projectId} section={section} /> : null}

        {activeId !== 'daily-report' && activeId !== 'kpi-dashboard' && activeId !== 'is-ops' && section ? (
          <>
            <header>
              <h2 className="text-lg font-semibold tracking-tight text-zinc-950">{section.title}</h2>
              <p className="mt-1 text-sm text-zinc-600">{section.summary}</p>
            </header>

            <div className="space-y-6">
              {section.blocks.map((b) => (
                <section key={b.heading}>
                  <h3 className="text-sm font-semibold text-zinc-900">{b.heading}</h3>
                  <ul className="mt-2 list-disc space-y-1.5 pl-5 text-sm leading-6 text-zinc-700">
                    {b.bullets.map((line) => (
                      <li key={line}>{line}</li>
                    ))}
                  </ul>
                </section>
              ))}
            </div>

            {section.references?.length ? (
              <footer className="border-t border-zinc-100 pt-4 text-xs text-zinc-500">
                <div className="font-medium text-zinc-600">参照リンク</div>
                <ul className="mt-2 space-y-1">
                  {section.references.map((url) => (
                    <li key={url}>
                      <a href={url} className="break-all underline-offset-2 hover:underline" target="_blank" rel="noreferrer">
                        {url}
                      </a>
                    </li>
                  ))}
                </ul>
              </footer>
            ) : null}
          </>
        ) : null}
      </article>
    </div>
  )
}
