import { z } from 'zod'

export const scriptCategories = [
  { id: 'talk', label: 'トーク' },
  { id: 'faq', label: 'FAQ' },
  { id: 'ng-counter', label: 'NG切返し' }
] as const

export type ScriptCategory = (typeof scriptCategories)[number]['id']

export const projectScriptFormSchema = z.object({
  projectId: z.string().min(1),
  category: z.enum(['talk', 'faq', 'ng-counter']),
  title: z.string().trim().min(1).max(120),
  body: z.string().trim().min(1).max(6000)
})

export const deleteProjectScriptSchema = z.object({
  projectId: z.string().min(1),
  scriptId: z.string().min(1)
})
