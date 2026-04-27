'use client'

import { useState } from 'react'
import { SheetSyncForm } from './SheetSyncForm'
import { CsvImportForm } from './CsvImportForm'
import { ListTable, type ListItem } from './ListTable'

export type MasterListSummary = {
  id: string
  name: string
  listType: 'project_sheet' | 'house_list'
  googleSpreadsheetId: string | null
  googleSheetName: string | null
  lastSyncedAt: string | null
  createdAt: string
  itemCount: number
  items: ListItem[]
}

type KpiProps = {
  label: string
  value: number
  color: string
}

const KpiCard = ({ label, value, color }: KpiProps) => (
  <div className={`rounded-2xl border p-4 ${color}`}>
    <div className="text-2xl font-bold tabular-nums">{value.toLocaleString()}</div>
    <div className="mt-1 text-xs font-medium text-zinc-600">{label}</div>
  </div>
)

type DedupButtonProps = {
  houseListId: string
}

const DedupButton = ({ houseListId }: DedupButtonProps) => {
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState<string | null>(null)
  const [isError, setIsError] = useState(false)

  const onClick = async () => {
    if (!confirm('PJシートと重複している行をハウスリストから削除します。よろしいですか？')) return
    setBusy(true)
    setResult(null)
    setIsError(false)
    try {
      const res = await fetch('/api/lists/dedup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ houseListId })
      })
      const json = (await res.json().catch(() => ({}))) as {
        ok?: boolean
        removed?: number
        error?: string
        message?: string
      }
      if (!res.ok) {
        setIsError(true)
        setResult(json.error ?? `HTTP ${res.status}`)
        return
      }
      if (json.message === 'no_project_sheet_data') {
        setResult('PJシートのデータがないため重複除外をスキップしました')
        return
      }
      setResult(`${json.removed ?? 0} 件を削除しました`)
      window.location.reload()
    } catch (err) {
      setIsError(true)
      setResult(err instanceof Error ? err.message : 'エラー')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="flex flex-wrap items-center gap-3">
      <button
        onClick={() => void onClick()}
        disabled={busy}
        className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-1.5 text-xs font-medium text-amber-700 hover:bg-amber-100 disabled:opacity-50"
      >
        {busy ? '処理中…' : 'PJシート重複を除外'}
      </button>
      {result ? (
        <span className={`text-xs ${isError ? 'text-red-600' : 'text-amber-700'}`}>{result}</span>
      ) : null}
    </div>
  )
}

type ListSectionProps = {
  list: MasterListSummary
  type: 'project_sheet' | 'house_list'
}

const ListSection = ({ list, type }: ListSectionProps) => {
  const [open, setOpen] = useState(false)

  return (
    <div className="rounded-2xl border border-zinc-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-start justify-between gap-3 border-b border-zinc-100 px-5 py-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <span
              className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                type === 'project_sheet'
                  ? 'bg-blue-100 text-blue-700'
                  : 'bg-emerald-100 text-emerald-700'
              }`}
            >
              {type === 'project_sheet' ? 'PJシート' : 'ハウスリスト'}
            </span>
            <span className="truncate font-semibold text-zinc-900">{list.name}</span>
          </div>
          <div className="mt-1 text-xs text-zinc-500">
            {list.itemCount.toLocaleString()} 件
            {list.lastSyncedAt
              ? ` · 最終同期: ${new Date(list.lastSyncedAt).toLocaleString('ja-JP')}`
              : ''}
            {list.googleSheetName ? ` · シート: ${list.googleSheetName}` : ''}
          </div>
        </div>
        <button
          onClick={() => setOpen((v) => !v)}
          className="shrink-0 rounded-lg border border-zinc-200 px-3 py-1.5 text-xs font-medium text-zinc-700 hover:border-zinc-300"
        >
          {open ? '閉じる' : 'リスト表示'}
        </button>
      </div>

      {open ? (
        <div className="px-5 py-4">
          <ListTable items={list.items} />
        </div>
      ) : null}
    </div>
  )
}

type Props = {
  projectSheetLists: MasterListSummary[]
  houseListLists: MasterListSummary[]
  kpi: {
    projectSheetCount: number
    houseListCount: number
    totalCount: number
  }
}

type Tab = 'project_sheet' | 'house_list'

/**
 * Master Lists ページのクライアント部分。
 * KPIカード・タブ切替・各リストセクションを担当する。
 */
export const MasterListsClient = ({ projectSheetLists, houseListLists, kpi }: Props) => {
  const [activeTab, setActiveTab] = useState<Tab>('project_sheet')

  return (
    <div className="space-y-6">
      {/* KPI カード */}
      <div className="grid grid-cols-3 gap-3">
        <KpiCard label="PJシート" value={kpi.projectSheetCount} color="border-blue-200 bg-blue-50" />
        <KpiCard label="ハウスリスト" value={kpi.houseListCount} color="border-emerald-200 bg-emerald-50" />
        <KpiCard label="合計" value={kpi.totalCount} color="border-zinc-200 bg-zinc-50" />
      </div>

      {/* タブ */}
      <div className="flex gap-1 rounded-xl border border-zinc-200 bg-zinc-50 p-1">
        {([['project_sheet', 'PJシート'], ['house_list', 'ハウスリスト']] as [Tab, string][]).map(
          ([tab, label]) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={[
                'flex-1 rounded-lg px-3 py-2 text-sm font-medium transition',
                activeTab === tab
                  ? 'bg-white text-zinc-900 shadow-sm'
                  : 'text-zinc-500 hover:text-zinc-700'
              ].join(' ')}
            >
              {label}
              <span className="ml-1.5 rounded-full bg-zinc-200 px-1.5 py-0.5 text-xs tabular-nums">
                {tab === 'project_sheet' ? projectSheetLists.length : houseListLists.length}
              </span>
            </button>
          )
        )}
      </div>

      {/* PJシート タブ */}
      {activeTab === 'project_sheet' ? (
        <div className="space-y-4">
          {/* 新規取込フォーム */}
          <div className="rounded-2xl border border-blue-200 bg-blue-50/50 p-5">
            <h3 className="mb-3 text-sm font-semibold text-blue-900">
              Google Spreadsheet から取り込む
            </h3>
            <SheetSyncForm />
          </div>

          {/* 既存リスト一覧 */}
          {projectSheetLists.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-zinc-300 py-8 text-center text-sm text-zinc-400">
              PJシートがありません。上のフォームから取り込んでください
            </p>
          ) : (
            <div className="space-y-3">
              {projectSheetLists.map((list) => (
                <div key={list.id} className="space-y-2">
                  <ListSection list={list} type="project_sheet" />
                  {/* 既存PJシートの再同期フォーム */}
                  <div className="rounded-xl border border-zinc-100 bg-zinc-50 px-4 py-3">
                    <p className="mb-2 text-xs font-medium text-zinc-600">このリストを再同期</p>
                    <SheetSyncForm
                      existingListId={list.id}
                      existingSheetUrl={
                        list.googleSpreadsheetId
                          ? `https://docs.google.com/spreadsheets/d/${list.googleSpreadsheetId}`
                          : ''
                      }
                      existingSheetName={list.googleSheetName ?? ''}
                    />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}

      {/* ハウスリスト タブ */}
      {activeTab === 'house_list' ? (
        <div className="space-y-4">
          {/* CSV インポートフォーム */}
          <div className="rounded-2xl border border-emerald-200 bg-emerald-50/50 p-5">
            <h3 className="mb-3 text-sm font-semibold text-emerald-900">
              ハウスリストを CSV から追加
            </h3>
            <CsvImportForm listType="house_list" />
          </div>

          {/* 既存リスト一覧 */}
          {houseListLists.length === 0 ? (
            <p className="rounded-2xl border border-dashed border-zinc-300 py-8 text-center text-sm text-zinc-400">
              ハウスリストがありません。上のフォームからインポートしてください
            </p>
          ) : (
            <div className="space-y-3">
              {houseListLists.map((list) => (
                <div key={list.id} className="space-y-2">
                  <ListSection list={list} type="house_list" />
                  <div className="px-1">
                    <DedupButton houseListId={list.id} />
                  </div>
                  {/* 追加CSV取込フォーム */}
                  <div className="rounded-xl border border-zinc-100 bg-zinc-50 px-4 py-3">
                    <p className="mb-2 text-xs font-medium text-zinc-600">
                      このリストへ行を追加
                    </p>
                    <CsvImportForm listId={list.id} />
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      ) : null}
    </div>
  )
}
