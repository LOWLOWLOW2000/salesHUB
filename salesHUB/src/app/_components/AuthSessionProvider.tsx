'use client'

import type { ReactNode } from 'react'
import { SessionProvider } from 'next-auth/react'

/**
 * Client boundary for `next-auth/react` (e.g. `signIn` on the custom sign-in page).
 */
export const AuthSessionProvider = ({ children }: { children: ReactNode }) => (
  <SessionProvider>{children}</SessionProvider>
)
