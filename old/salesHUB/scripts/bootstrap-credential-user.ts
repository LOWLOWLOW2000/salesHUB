/**
 * One-shot: create or update a user with passwordHash for local / Credentials login.
 *
 * Env:
 * - CREDENTIALS_BOOTSTRAP_EMAIL (required)
 * - CREDENTIALS_BOOTSTRAP_PASSWORD (required)
 * - CREDENTIALS_BOOTSTRAP_ALLOW_EXISTING_GOOGLE_USER=true … allow adding password when user exists with Google only
 *
 * Run from repo root: `cd salesHUB && npm run auth:bootstrap-user`
 */
import 'dotenv/config'
import { randomUUID } from 'crypto'
import { prisma } from '@/lib/db/prisma'
import { hashPassword } from '@/lib/auth/password'
import { isGmEmail } from '@/lib/auth/gmEmail'

const truthyEnv = (raw: string | undefined) => {
  const v = raw?.trim().toLowerCase() ?? ''
  return v === 'true' || v === '1' || v === 'yes'
}

const main = async () => {
  const email =
    process.env.CREDENTIALS_BOOTSTRAP_EMAIL?.trim().toLowerCase() ?? ''
  const password = process.env.CREDENTIALS_BOOTSTRAP_PASSWORD ?? ''
  const allowGoogleOnly = truthyEnv(
    process.env.CREDENTIALS_BOOTSTRAP_ALLOW_EXISTING_GOOGLE_USER
  )

  if (email.length === 0 || password.length === 0) {
    console.error(
      'Set CREDENTIALS_BOOTSTRAP_EMAIL and CREDENTIALS_BOOTSTRAP_PASSWORD'
    )
    process.exit(1)
  }

  if (!isGmEmail(email)) {
    await prisma.allowedEmail.upsert({
      where: { email },
      update: {},
      create: { email }
    })
  }

  const existing = await prisma.user.findUnique({
    where: { email },
    select: {
      id: true,
      passwordHash: true,
      accounts: { where: { provider: 'google' }, select: { id: true } }
    }
  })

  const passwordHash = await hashPassword(password)

  if (existing) {
    const hasGoogle = existing.accounts.length > 0
    if (hasGoogle && !existing.passwordHash && !allowGoogleOnly) {
      console.error(
        'User exists with Google link only. Set CREDENTIALS_BOOTSTRAP_ALLOW_EXISTING_GOOGLE_USER=true to add a password, or use a different email.'
      )
      process.exit(1)
    }

    await prisma.user.update({
      where: { id: existing.id },
      data: { passwordHash }
    })
    console.log('Updated passwordHash for', email)
    return
  }

  await prisma.user.create({
    data: {
      id: randomUUID(),
      email,
      passwordHash,
      emailVerified: new Date()
    }
  })
  console.log('Created user', email)
}

main()
  .catch((e) => {
    console.error(e)
    process.exit(1)
  })
  .finally(() => prisma.$disconnect())
