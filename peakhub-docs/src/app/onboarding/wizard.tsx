'use client'

import { useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'

type Track = 'client' | 'auto_squad'
type ClientRole = 'owner' | 'director' | 'member'
type AutoRole = 'is' | 'fs' | 'manager'

type Step =
  | { id: 'track' }
  | { id: 'clientWorkspace'; track: 'client' }
  | { id: 'autoSquadRole'; track: 'auto_squad' }
  | { id: 'profile'; track: Track; workspaceId: string; role: string }

const postJson = async <T,>(path: string, body: unknown): Promise<T> => {
  const res = await fetch(path, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify(body)
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(text || 'request failed')
  }

  return res.json() as Promise<T>
}

export const OnboardingWizard = () => {
  const router = useRouter()
  const [step, setStep] = useState<Step>({ id: 'track' })
  const [displayName, setDisplayName] = useState('')
  const [workspaceName, setWorkspaceName] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const progress = useMemo(() => {
    const current =
      step.id === 'track'
        ? 1
        : step.id === 'clientWorkspace' || step.id === 'autoSquadRole'
          ? 2
          : 3
    return { current, total: 3 }
  }, [step.id])

  const nextTrack = (track: Track) => {
    setError(null)
    setStep(track === 'client' ? { id: 'clientWorkspace', track } : { id: 'autoSquadRole', track })
  }

  const createClient = async (role: ClientRole) => {
    setBusy(true)
    setError(null)

    try {
      const { workspaceId } = await postJson<{ workspaceId: string }>('/api/onboarding', {
        action: 'createClientWorkspace',
        name: workspaceName,
        role
      })

      setStep({ id: 'profile', track: 'client', workspaceId, role })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed')
    } finally {
      setBusy(false)
    }
  }

  const joinAutoSquad = async (role: AutoRole) => {
    setBusy(true)
    setError(null)

    try {
      const { workspaceId } = await postJson<{ workspaceId: string }>('/api/onboarding', {
        action: 'joinAutoSquad',
        role
      })

      setStep({ id: 'profile', track: 'auto_squad', workspaceId, role })
    } catch (e) {
      setError(e instanceof Error ? e.message : 'failed')
    } finally {
      setBusy(false)
    }
  }

  const finish = async () => {
    if (step.id !== 'profile') return

    setBusy(true)
    setError(null)

    try {
      await postJson('/api/onboarding', {
        action: 'complete',
        workspaceId: step.workspaceId,
        displayName
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
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="text-xs font-medium text-zinc-600">
          {progress.current}/{progress.total}
        </div>
        <button
          type="button"
          disabled={busy}
          onClick={() => {
            setError(null)
            setStep({ id: 'track' })
          }}
          className="text-xs font-medium text-zinc-600 hover:text-zinc-950 disabled:opacity-50"
        >
          最初に戻る
        </button>
      </div>

      {error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-sm text-rose-800">
          {error}
        </div>
      ) : null}

      {step.id === 'track' ? (
        <div className="grid gap-3 sm:grid-cols-2">
          <button
            type="button"
            onClick={() => nextTrack('client')}
            className="rounded-xl border border-zinc-200 bg-white p-5 text-left shadow-sm transition hover:border-zinc-300 hover:shadow"
          >
            <div className="text-sm font-semibold">クライアントワーク</div>
            <div className="mt-2 text-sm leading-6 text-zinc-600">
              案件管理・戦略戦術・1on1・チーム/個人評価・戦略苦戦塾
            </div>
          </button>

          <button
            type="button"
            onClick={() => nextTrack('auto_squad')}
            className="rounded-xl border border-zinc-200 bg-white p-5 text-left shadow-sm transition hover:border-zinc-300 hover:shadow"
          >
            <div className="text-sm font-semibold">自動部隊（IS01管理）</div>
            <div className="mt-2 text-sm leading-6 text-zinc-600">
              インサイドセールス・FSなど自動部隊要素。基本はIS01で管理。
            </div>
          </button>
        </div>
      ) : null}

      {step.id === 'clientWorkspace' ? (
        <div className="space-y-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="space-y-1">
            <div className="text-sm font-semibold">ワークスペースを作成</div>
            <div className="text-sm text-zinc-600">クライアントワーク用の箱を作ります</div>
          </div>

          <input
            value={workspaceName}
            onChange={(e) => setWorkspaceName(e.target.value)}
            placeholder="例: PeakHUB クライアントワーク"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-300"
          />

          <div className="flex flex-wrap gap-2">
            {([
              { id: 'owner', label: 'Owner' },
              { id: 'director', label: 'Director' },
              { id: 'member', label: 'Member' }
            ] as const).map((r) => (
              <button
                key={r.id}
                type="button"
                disabled={busy || workspaceName.trim().length === 0}
                onClick={() => createClient(r.id)}
                className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
              >
                {r.label}として開始
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {step.id === 'autoSquadRole' ? (
        <div className="space-y-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="space-y-1">
            <div className="text-sm font-semibold">ロールを選択</div>
            <div className="text-sm text-zinc-600">自動部隊はIS01側の思想に合わせます</div>
          </div>

          <div className="flex flex-wrap gap-2">
            {([
              { id: 'is', label: 'IS' },
              { id: 'fs', label: 'FS' },
              { id: 'manager', label: 'Manager' }
            ] as const).map((r) => (
              <button
                key={r.id}
                type="button"
                disabled={busy}
                onClick={() => joinAutoSquad(r.id)}
                className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
              >
                {r.label}として開始
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {step.id === 'profile' ? (
        <div className="space-y-4 rounded-xl border border-zinc-200 bg-white p-5 shadow-sm">
          <div className="space-y-1">
            <div className="text-sm font-semibold">プロフィール（最小）</div>
            <div className="text-sm text-zinc-600">表示名だけ設定します（後から変更できます）</div>
          </div>

          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="表示名"
            className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-300"
          />

          <button
            type="button"
            disabled={busy || displayName.trim().length === 0}
            onClick={finish}
            className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800 disabled:opacity-50"
          >
            完了して進む
          </button>
        </div>
      ) : null}
    </div>
  )
}

