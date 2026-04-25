import type { Metadata } from 'next'
import { Geist, Geist_Mono } from 'next/font/google'
import Link from 'next/link'
import './globals.css'
import { appConfig } from '@/lib/appConfig'

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin']
})

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin']
})

export const metadata: Metadata = {
  title: appConfig.name,
  description: appConfig.description
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html
      lang="ja"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-zinc-50 text-zinc-950">
        <header className="sticky top-0 z-20 border-b border-zinc-200/70 bg-white/80 backdrop-blur">
          <div className="mx-auto flex w-full max-w-5xl items-center justify-between gap-4 px-4 py-3">
            <Link href="/" className="font-semibold tracking-tight">
              {appConfig.name}
            </Link>
            <nav className="flex items-center gap-3 text-sm text-zinc-700">
              <Link className="hover:text-zinc-950" href="/admin">
                Admin
              </Link>
              <Link className="hover:text-zinc-950" href="/api/auth/signin">
                Sign in
              </Link>
            </nav>
          </div>
        </header>
        <main className="flex-1">
          <div className="mx-auto w-full max-w-5xl px-4 py-10">{children}</div>
        </main>
        <footer className="border-t border-zinc-200/70 bg-white">
          <div className="mx-auto w-full max-w-5xl px-4 py-6 text-xs text-zinc-600">
            {appConfig.name}
          </div>
        </footer>
      </body>
    </html>
  )
}
