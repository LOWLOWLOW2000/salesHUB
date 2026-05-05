import bcrypt from 'bcryptjs'

const BCRYPT_COST = 12

/** Hash a plaintext password for storage on `User.passwordHash`. */
export const hashPassword = (plain: string) => bcrypt.hash(plain, BCRYPT_COST)

/** Constant-time compare for login. */
export const verifyPassword = (plain: string, passwordHash: string) =>
  bcrypt.compare(plain, passwordHash)
