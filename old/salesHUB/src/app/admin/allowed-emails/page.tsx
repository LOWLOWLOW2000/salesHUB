import Link from 'next/link'
import { prisma } from '@/lib/db/prisma'
import { requireGm } from '@/lib/auth/requireGm'

const normalizeEmail = (email: string) => email.trim().toLowerCase()

const addAllowedEmail = async (formData: FormData) => {
  'use server'

  await requireGm()

  const raw = String(formData.get('email') ?? '')
  const email = normalizeEmail(raw)
  if (email.length === 0) return

  await prisma.allowedEmail.upsert({
    where: { email },
    update: {},
    create: { email }
  })
}

const removeAllowedEmail = async (formData: FormData) => {
  'use server'

  await requireGm()

  const raw = String(formData.get('email') ?? '')
  const email = normalizeEmail(raw)
  if (email.length === 0) return

  await prisma.allowedEmail.delete({ where: { email } }).catch(() => null)
}

export default async function AllowedEmailsPage() {
  await requireGm()

  const emails = await prisma.allowedEmail.findMany({
    orderBy: { email: 'asc' },
    select: { id: true, email: true, createdAt: true }
  })

  const users = await prisma.user.findMany({
    where: { email: { in: emails.map((e) => e.email) } },
    select: {
      email: true,
      name: true,
      onboardingCompletedAt: true
    }
  })

  const userByEmail = new Map(users.flatMap((u) => (u.email ? [[u.email, u] as const] : [])))

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div className="space-y-1">
          <h1 className="text-2xl font-semibold tracking-tight">Allowed emails</h1>
          <p className="text-sm text-zinc-700">ログインを許可するメール（ホワイトリスト）</p>
        </div>
        <Link className="text-sm text-zinc-700 hover:text-zinc-950" href="/admin">
          ← Admin
        </Link>
      </div>

      <form action={addAllowedEmail} className="flex flex-wrap gap-2">
        <input
          name="email"
          type="email"
          required
          placeholder="director@example.com"
          className="w-full max-w-sm rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-300"
        />
        <button
          type="submit"
          className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
        >
          追加
        </button>
      </form>

      <div className="overflow-hidden rounded-xl border border-zinc-200 bg-white">
        <div className="border-b border-zinc-200 px-4 py-3 text-sm font-semibold">一覧</div>
        <ul className="divide-y divide-zinc-100">
          {emails.map((row) => {
            const user = userByEmail.get(row.email)

            return (
              <li key={row.id} className="flex flex-wrap items-center justify-between gap-3 px-4 py-3">
                <div className="text-sm">
                  <div className="font-medium text-zinc-950">{row.email}</div>
                  <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-xs text-zinc-600">
                    <span>登録: {row.createdAt.toISOString()}</span>
                    <span>
                      プロフィール: {user?.name ? user.name : '(未入力)'}
                    </span>
                    <span>
                      Onboarding:{' '}
                      {user?.onboardingCompletedAt ? '完了' : '未完了/未ログイン'}
                    </span>
                  </div>
                </div>
                <form action={removeAllowedEmail}>
                  <input type="hidden" name="email" value={row.email} />
                  <button
                    type="submit"
                    className="rounded-lg border border-zinc-200 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 hover:border-zinc-300 hover:text-zinc-950"
                  >
                    削除
                  </button>
                </form>
              </li>
            )
          })}
        </ul>
      </div>
    </div>
  )
}

