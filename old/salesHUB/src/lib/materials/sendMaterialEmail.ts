import nodemailer from 'nodemailer'

export type SendMaterialEmailInput = {
  to: string
  subject: string
  text: string
}

/**
 * Sends a plain-text email when SMTP env is configured.
 */
export const sendMaterialEmail = async ({ to, subject, text }: SendMaterialEmailInput) => {
  const host = process.env.SMTP_HOST?.trim()
  const port = Number(process.env.SMTP_PORT ?? '587')
  const user = process.env.SMTP_USER?.trim()
  const pass = process.env.SMTP_PASS?.trim()
  const from = process.env.SMTP_FROM?.trim()

  if (!host || !from) {
    return { ok: false as const, error: 'smtp_not_configured' }
  }

  const transporter = nodemailer.createTransport({
    host,
    port,
    secure: port === 465,
    auth: user && pass ? { user, pass } : undefined
  })

  await transporter.sendMail({
    from,
    to,
    subject,
    text
  })

  return { ok: true as const }
}
