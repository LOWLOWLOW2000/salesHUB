'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { appRoleUiLabel } from '@/lib/auth/app-role-labels'

const roles = (
  ['manager', 'as', 'is', 'fs', 'cs'] as const
).map((id) => ({ id, label: appRoleUiLabel(id) }))

type Props = {
  isGm: boolean
}

const postJson = async (body: unknown) => {
  const res = await fetch('/api/onboarding', {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || 'request failed')
  }
}

/**
 * First-time setup: display name + company role (GM skips role; already gm).
 */
export const OnboardingWizard = ({ isGm }: Props) => {
  const router = useRouter()
  const [displayName, setDisplayName] = useState('')
  const [role, setRole] = useState<(typeof roles)[number]['id']>('is')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const finish = async () => {
    setBusy(true)
    setError(null)
    try {
      await postJson({
        action: 'complete',
        displayName,
        role: isGm ? 'manager' : role
      })
      router.replace('/')
      router.refresh()
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed')
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="mx-auto max-w-lg space-y-4">
      <h1 className="text-xl font-semibold tracking-tight">初期設定</h1>
      <p className="text-sm text-zinc-600">表示名を入力してください。{isGm ? 'GM はロール選択をスキップします。' : '会社スコープの主ロールを選びます。'}</p>

      <label className="block space-y-1 text-sm">
        <span className="font-medium text-zinc-800">表示名</span>
        <input
          value={displayName}
          onChange={(e) => setDisplayName(e.target.value)}
          className="w-full rounded-lg border border-zinc-200 px-3 py-2"
          placeholder="山田 太郎"
        />
      </label>

      {!isGm ? (
        <label className="block space-y-1 text-sm">
          <span className="font-medium text-zinc-800">主ロール</span>
          <select
            value={role}
            onChange={(e) => setRole(e.target.value as (typeof roles)[number]['id'])}
            className="w-full rounded-lg border border-zinc-200 px-3 py-2"
          >
            {roles.map((r) => (
              <option key={r.id} value={r.id}>
                {r.label}
              </option>
            ))}
          </select>
        </label>
      ) : null}

      {error ? <p className="text-sm text-red-600">{error}</p> : null}

      <button
        type="button"
        disabled={busy || displayName.trim().length === 0}
        onClick={() => void finish()}
        className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
      >
        完了
      </button>
    </div>
  )
}
