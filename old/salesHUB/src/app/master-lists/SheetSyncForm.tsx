'use client'

import { useState } from 'react'

type Props = {
  /** 既存のPJシートリストIDがある場合は再同期として扱う */
  existingListId?: string
  existingSheetUrl?: string
  existingSheetName?: string
}

/**
 * Google Spreadsheet URLとシートタブ名を入力して
 * /api/lists/sync-sheet へ POSTする。
 */
export const SheetSyncForm = ({ existingListId, existingSheetUrl, existingSheetName }: Props) => {
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState<string | null>(null)
  const [isError, setIsError] = useState(false)
  const [sheetUrl, setSheetUrl] = useState(existingSheetUrl ?? '')
  const [sheetName, setSheetName] = useState(existingSheetName ?? '')
  const [listName, setListName] = useState('')

  /** SpreadsheetのURLからIDを抽出する */
  const extractSpreadsheetId = (url: string): string | null => {
    const match = url.match(/\/spreadsheets\/d\/([a-zA-Z0-9-_]+)/)
    return match?.[1] ?? null
  }

  const onSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setBusy(true)
    setMessage(null)
    setIsError(false)

    const spreadsheetId = extractSpreadsheetId(sheetUrl.trim()) ?? sheetUrl.trim()
    const trimmedSheetName = sheetName.trim()

    if (!spreadsheetId || !trimmedSheetName) {
      setMessage('Spreadsheet URL とシート名は必須です')
      setIsError(true)
      setBusy(false)
      return
    }

    try {
      const res = await fetch('/api/lists/sync-sheet', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          spreadsheetId,
          sheetName: trimmedSheetName,
          listId: existingListId,
          listName: listName.trim() || trimmedSheetName
        })
      })

      const json = (await res.json().catch(() => ({}))) as {
        ok?: boolean
        imported?: number
        error?: string
      }

      if (!res.ok) {
        setIsError(true)
        setMessage(json.error ?? `HTTP ${res.status}`)
        return
      }

      setMessage(`${json.imported ?? 0} 件を取り込みました`)
      window.location.reload()
    } catch (err) {
      setIsError(true)
      setMessage(err instanceof Error ? err.message : 'エラーが発生しました')
    } finally {
      setBusy(false)
    }
  }

  return (
    <form className="space-y-3" onSubmit={(e) => void onSubmit(e)}>
      <div className="space-y-2">
        <label className="block text-xs font-medium text-zinc-700">
          Google Spreadsheet URL
        </label>
        <input
          type="url"
          value={sheetUrl}
          onChange={(e) => setSheetUrl(e.target.value)}
          placeholder="https://docs.google.com/spreadsheets/d/xxxxx/edit"
          className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200"
          disabled={busy}
          required
        />
        <p className="text-xs text-zinc-500">
          Google Driveの PJシートの URL を貼り付けてください
        </p>
      </div>

      <div className="space-y-2">
        <label className="block text-xs font-medium text-zinc-700">
          シートタブ名
        </label>
        <input
          type="text"
          value={sheetName}
          onChange={(e) => setSheetName(e.target.value)}
          placeholder="例: リスト、Sheet1、架電リスト"
          className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200"
          disabled={busy}
          required
        />
      </div>

      {!existingListId ? (
        <div className="space-y-2">
          <label className="block text-xs font-medium text-zinc-700">
            リスト名（省略時はシート名を使用）
          </label>
          <input
            type="text"
            value={listName}
            onChange={(e) => setListName(e.target.value)}
            placeholder="例: PJシート 2026-04"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400 focus:ring-2 focus:ring-zinc-200"
            disabled={busy}
          />
        </div>
      ) : null}

      <button
        type="submit"
        disabled={busy}
        className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
      >
        {busy ? '取り込み中…' : existingListId ? '再同期' : '取り込む'}
      </button>

      {message ? (
        <p className={`text-xs ${isError ? 'text-red-600' : 'text-green-700'}`}>{message}</p>
      ) : null}
    </form>
  )
}
