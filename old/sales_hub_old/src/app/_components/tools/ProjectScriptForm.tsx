'use client'

import { scriptCategories } from '@/lib/isHub/projectScript'

type Props = {
  projectId: string
  action: (formData: FormData) => Promise<void>
}

/**
 * ディレクターがプロジェクト固有のトーク・FAQ・切返しを追加するフォーム。
 */
export const ProjectScriptForm = ({ projectId, action }: Props) => (
  <form action={action} className="space-y-4 rounded-xl border border-zinc-200 bg-white p-4 shadow-sm">
    <input type="hidden" name="projectId" value={projectId} />

    <div className="grid gap-4 md:grid-cols-3">
      <label className="space-y-1 text-sm">
        <span className="font-medium text-zinc-800">カテゴリ</span>
        <select
          name="category"
          className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
        >
          {scriptCategories.map((category) => (
            <option key={category.id} value={category.id}>{category.label}</option>
          ))}
        </select>
      </label>

      <label className="space-y-1 text-sm md:col-span-2">
        <span className="font-medium text-zinc-800">タイトル</span>
        <input
          name="title"
          required
          placeholder="例: 忙しいと言われた時の切返し"
          className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
        />
      </label>
    </div>

    <label className="space-y-1 text-sm">
      <span className="font-medium text-zinc-800">本文</span>
      <textarea
        name="body"
        required
        rows={5}
        placeholder="結論ファーストで短く。最後は次アクションに戻す。"
        className="w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm outline-none focus:border-zinc-400"
      />
    </label>

    <button
      type="submit"
      className="rounded-lg bg-zinc-900 px-4 py-2 text-sm font-medium text-white hover:bg-zinc-800"
    >
      スクリプトを追加
    </button>
  </form>
)
