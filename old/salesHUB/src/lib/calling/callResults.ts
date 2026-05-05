/**
 * Canonical calling results (IS_01 / @is-crm/domain parity).
 */
export const CALLING_RESULT_VALUES = [
  'アポ',
  '資料送付',
  '再架電',
  '折り返し依頼',
  '担当NG',
  '受付NG',
  '不在',
  '未着電',
  'クレーム',
  '番号違い'
] as const

export type CallingResult = (typeof CALLING_RESULT_VALUES)[number]

export const isCallingResult = (v: string): v is CallingResult =>
  (CALLING_RESULT_VALUES as readonly string[]).includes(v)
