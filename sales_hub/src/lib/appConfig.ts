export const appConfig = {
  name: process.env.APP_NAME?.trim() || 'Sales Consulting Hub',
  description:
    process.env.APP_DESCRIPTION?.trim() ||
    'セールスコンサルティング部署の案件ドキュメントとKPIデータを管理する内部ツール'
} as const

