import fs from 'fs/promises'

export type OpenAiTranscriptionResult = {
  text: string
}

/**
 * Transcribes audio with OpenAI Whisper API when configured.
 *
 * Required env:
 * - OPENAI_API_KEY
 * Optional:
 * - OPENAI_TRANSCRIBE_MODEL (default: whisper-1)
 */
export const transcribeWithOpenAi = async (audioPath: string) => {
  const apiKey = process.env.OPENAI_API_KEY?.trim() ?? ''
  if (apiKey.length === 0) return null

  const model = process.env.OPENAI_TRANSCRIBE_MODEL?.trim() || 'whisper-1'
  const buf = await fs.readFile(audioPath)

  const form = new FormData()
  form.append('model', model)
  form.append('file', new Blob([buf]), 'audio.mp3')

  const res = await fetch('https://api.openai.com/v1/audio/transcriptions', {
    method: 'POST',
    headers: { authorization: `Bearer ${apiKey}` },
    body: form
  })

  if (!res.ok) return null
  const json = (await res.json()) as OpenAiTranscriptionResult
  return typeof json.text === 'string' ? json.text : null
}

