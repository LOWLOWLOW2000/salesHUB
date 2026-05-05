export const appConfig = {
  name: process.env.APP_NAME?.trim() || 'salesHUB',
  description:
    process.env.APP_DESCRIPTION?.trim() ||
    'AI-Augmented The Model + RevOps 思想の社内 CRM（架電・リスト・KPI）'
} as const
