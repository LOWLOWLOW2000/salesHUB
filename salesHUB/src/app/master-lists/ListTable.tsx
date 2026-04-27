'use client'

import { useState } from 'react'

export type ListItem = {
  id: string
  companyName: string
  phone: string
  address: string
  targetUrl: string
  status: 'new' | 'done' | 'excluded'
  lastResult: string | null
}

type Props = {
  items: ListItem[]
}

const STATUS_LABEL: Record<ListItem['status'], string> = {
  new: '未架電',
  done: '完了',
  excluded: '除外'
}

const STATUS_COLOR: Record<ListItem['status'], string> = {
  new: 'bg-blue-50 text-blue-700',
  done: 'bg-green-50 text-green-700',
  excluded: 'bg-zinc-100 text-zinc-500'
}

const PAGE_SIZE = 50

/**
 * MasterListItem の表一覧。ページネーション付き。
 */
export const ListTable = ({ items }: Props) => {
  const [page, setPage] = useState(0)

  const totalPages = Math.ceil(items.length / PAGE_SIZE)
  const slice = items.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  if (items.length === 0) {
    return <p className="py-6 text-center text-sm text-zinc-500">データがありません</p>
  }

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto rounded-xl border border-zinc-200">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-200 bg-zinc-50 text-left">
              <th className="px-3 py-2 font-semibold text-zinc-700">会社名</th>
              <th className="px-3 py-2 font-semibold text-zinc-700">電話</th>
              <th className="hidden px-3 py-2 font-semibold text-zinc-700 sm:table-cell">住所</th>
              <th className="hidden px-3 py-2 font-semibold text-zinc-700 md:table-cell">URL</th>
              <th className="px-3 py-2 font-semibold text-zinc-700">状態</th>
            </tr>
          </thead>
          <tbody>
            {slice.map((item, idx) => (
              <tr
                key={item.id}
                className={[
                  'border-b border-zinc-100 transition hover:bg-zinc-50',
                  idx % 2 === 0 ? '' : 'bg-zinc-50/50'
                ].join(' ')}
              >
                <td className="max-w-[180px] truncate px-3 py-2 font-medium text-zinc-900">
                  {item.companyName || '—'}
                </td>
                <td className="whitespace-nowrap px-3 py-2 font-mono text-xs text-zinc-700">
                  {item.phone || '—'}
                </td>
                <td className="hidden max-w-[200px] truncate px-3 py-2 text-zinc-600 sm:table-cell">
                  {item.address || '—'}
                </td>
                <td className="hidden max-w-[200px] px-3 py-2 md:table-cell">
                  {item.targetUrl ? (
                    <a
                      href={item.targetUrl.startsWith('http') ? item.targetUrl : `https://${item.targetUrl}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="truncate text-blue-600 hover:underline"
                    >
                      {item.targetUrl}
                    </a>
                  ) : (
                    '—'
                  )}
                </td>
                <td className="px-3 py-2">
                  <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${STATUS_COLOR[item.status]}`}>
                    {STATUS_LABEL[item.status]}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {totalPages > 1 ? (
        <div className="flex items-center justify-between px-1 text-xs text-zinc-500">
          <span>
            {page * PAGE_SIZE + 1}–{Math.min((page + 1) * PAGE_SIZE, items.length)} / {items.length} 件
          </span>
          <div className="flex gap-1">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="rounded-lg border border-zinc-200 px-2 py-1 disabled:opacity-40"
            >
              前へ
            </button>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="rounded-lg border border-zinc-200 px-2 py-1 disabled:opacity-40"
            >
              次へ
            </button>
          </div>
        </div>
      ) : (
        <p className="px-1 text-xs text-zinc-500">{items.length} 件</p>
      )}
    </div>
  )
}
