import Link from 'next/link'
import { requireManager } from '@/lib/auth/requireManager'

export default async function AdminPage() {
  const { session, company } = await requireManager()

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Admin</h1>
          <p className="text-sm text-zinc-700">
            部署「{company.name}」の案件ディレクター管理
          </p>
        </div>
        <div className="text-sm text-zinc-700">
          <div className="font-medium">{session.user?.email}</div>
          <Link className="text-xs text-zinc-600 hover:text-zinc-950" href="/api/auth/signout">
            サインアウト
          </Link>
        </div>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <Link
          href="/admin/allowed-emails"
          className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm transition hover:border-zinc-300 hover:shadow"
        >
          <div className="text-sm font-semibold">Allowed emails</div>
          <div className="mt-2 text-sm leading-6 text-zinc-600">
            ログインを許可するメール（ホワイトリスト）
          </div>
        </Link>

        <Link
          href="/admin/projects"
          className="rounded-xl border border-zinc-200 bg-white p-5 shadow-sm transition hover:border-zinc-300 hover:shadow"
        >
          <div className="text-sm font-semibold">Projects</div>
          <div className="mt-2 text-sm leading-6 text-zinc-600">
            案件とディレクター（director）割当
          </div>
        </Link>
      </div>
    </div>
  )
}

