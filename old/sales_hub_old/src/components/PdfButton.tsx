import Link from 'next/link'

type Props = {
  path: string
  label?: string
}

const toPdfHref = (path: string) => `/api/pdf?path=${encodeURIComponent(path)}`

/**
 * 指定ページをPDFとしてダウンロードする導線
 */
export const PdfButton = ({ path, label = 'PDF出力' }: Props) => (
  <Link
    href={toPdfHref(path)}
    className="inline-flex items-center gap-2 rounded-md border border-zinc-200 bg-white px-3 py-1.5 text-sm font-medium text-zinc-900 shadow-sm hover:bg-zinc-50"
  >
    <span className="text-[12px] leading-none">⬇</span>
    {label}
  </Link>
)

