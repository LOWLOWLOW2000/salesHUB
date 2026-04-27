import fs from 'fs/promises'
import path from 'path'
import crypto from 'crypto'
import { PrismaClient } from '@prisma/client'
import { buildFileSets } from '@/lib/recordings/recordingFiles'
import { getDurationSec } from '@/lib/recordings/ffprobe'
import { parseVttToText } from '@/lib/recordings/transcript'
import { transcribeWithOpenAi } from '@/lib/recordings/asrOpenAI'

type Args = {
  rawDir: string
  source: 'zoom_phone'
  matchWindowMin: number
  dryRun: boolean
}

const parseArgs = (): Args => {
  const argv = process.argv.slice(2)
  const rawDir = argv.find((a) => a.startsWith('--raw-dir='))?.split('=')[1] ?? '../data_project/02_data_raw/zoom_recordings'
  const matchWindowMin = Number(argv.find((a) => a.startsWith('--match-window-min='))?.split('=')[1] ?? '180')
  const dryRun = argv.includes('--dry-run')

  return {
    rawDir,
    source: 'zoom_phone',
    matchWindowMin: Number.isFinite(matchWindowMin) ? matchWindowMin : 180,
    dryRun
  }
}

const walkFiles = async (dir: string): Promise<string[]> => {
  const entries = await fs.readdir(dir, { withFileTypes: true })
  const nested = await Promise.all(
    entries.map((e) =>
      e.isDirectory()
        ? walkFiles(path.join(dir, e.name))
        : Promise.resolve([path.join(dir, e.name)])
    )
  )
  return nested.flat()
}

const cuidLike = () => `cr_${crypto.randomBytes(16).toString('hex')}`

const safeWrite = (s: string) => process.stdout.write(s)

const normalizePhone = (raw: string) => raw.replace(/[^\d]/g, '').trim()

type SidecarMeta = {
  calleePhone?: string
  calleePhoneNorm?: string
  direction?: string
  status?: string
  recordedAt?: string
  callerLabel?: string
  sourceRecordingRef?: string
}

const readSidecarMeta = async (audioPath: string): Promise<SidecarMeta | null> => {
  const dir = path.dirname(audioPath)
  const base = path.basename(audioPath).replace(/\.[^.]+$/, '')

  const candidates = [
    path.join(dir, `${base}.json`),
    path.join(dir, `${base}_meta.json`),
    path.join(dir, `${base}.meta.json`)
  ]

  const firstExisting = await Promise.all(
    candidates.map(async (p) => {
      try {
        await fs.access(p)
        return p
      } catch {
        return null
      }
    })
  ).then((xs) => xs.find((x) => x != null) ?? null)

  if (!firstExisting) return null

  try {
    const raw = await fs.readFile(firstExisting, 'utf8')
    const json = JSON.parse(raw) as SidecarMeta
    return json && typeof json === 'object' ? json : null
  } catch {
    return null
  }
}

const matchCallLog = async (prisma: PrismaClient, params: { recordedAt: Date; calleePhoneNorm: string; windowMin: number }) => {
  const { recordedAt, calleePhoneNorm, windowMin } = params
  if (calleePhoneNorm.length === 0) return null

  const account = await prisma.salesAccount.findFirst({
    where: { phoneNorm: calleePhoneNorm },
    select: { id: true }
  })
  if (!account) return null

  const from = new Date(recordedAt.getTime() - windowMin * 60 * 1000)
  const to = new Date(recordedAt.getTime() + windowMin * 60 * 1000)

  const logs = await prisma.callLog.findMany({
    where: { accountId: account.id, startedAt: { gte: from, lte: to } },
    select: { id: true, projectId: true, startedAt: true },
    take: 20
  })

  const scored = logs
    .map((l) => ({
      ...l,
      diffMs: Math.abs(l.startedAt.getTime() - recordedAt.getTime())
    }))
    .sort((a, b) => a.diffMs - b.diffMs)

  const best = scored[0]
  if (!best) return null

  const confidence = Math.max(0, 100 - Math.round(best.diffMs / (60 * 1000)))
  return { callLogId: best.id, projectId: best.projectId, confidence }
}

const readTranscriptText = async (transcriptPath: string) => {
  const raw = await fs.readFile(transcriptPath, 'utf8')
  const ext = path.extname(transcriptPath).toLowerCase()
  if (ext === '.vtt') return { text: parseVttToText(raw), format: 'vtt' as const, source: 'zoom' as const }
  if (ext === '.txt') return { text: raw.trim(), format: 'txt' as const, source: 'zoom' as const }
  if (ext === '.json') return { text: raw.trim(), format: 'json' as const, source: 'zoom' as const }
  return { text: raw.trim(), format: 'txt' as const, source: 'zoom' as const }
}

const main = async () => {
  const args = parseArgs()
  const prisma = new PrismaClient()

  try {
    const absRaw = path.isAbsolute(args.rawDir) ? args.rawDir : path.resolve(process.cwd(), args.rawDir)
    safeWrite(`[ingest] rawDir=${absRaw}\n`)

    const files = await walkFiles(absRaw)
    const sets = buildFileSets(files)
    safeWrite(`[ingest] candidates=${sets.length}\n`)

    for (const s of sets) {
      const durationSec = await getDurationSec(s.audioPath)

      const meta = await readSidecarMeta(s.audioPath)
      const calleePhoneNorm =
        normalizePhone(meta?.calleePhoneNorm ?? meta?.calleePhone ?? '')

      const direction = meta?.direction ?? ''
      const status = meta?.status ?? ''

      const transcriptFromFile = s.transcriptPath ? await readTranscriptText(s.transcriptPath) : null
      const asrText = transcriptFromFile ? null : await transcribeWithOpenAi(s.audioPath)
      const transcriptText = transcriptFromFile?.text ?? asrText ?? ''

      const transcriptSource =
        transcriptFromFile?.source ??
        (transcriptText.length > 0 ? ('asr' as const) : null)

      const transcriptFormat =
        transcriptFromFile?.format ??
        (transcriptText.length > 0 ? ('txt' as const) : null)

      const transcriptPath =
        s.transcriptPath ??
        (asrText
          ? await (async () => {
              const out = `${s.audioPath}.asr.txt`
              try {
                await fs.access(out)
                return out
              } catch {
                await fs.writeFile(out, asrText, 'utf8')
                return out
              }
            })()
          : null)

      const matched =
        !args.dryRun
          ? await matchCallLog(prisma, {
              recordedAt: s.recordedAt,
              calleePhoneNorm,
              windowMin: args.matchWindowMin
            })
          : null

      const id = cuidLike()

      if (args.dryRun) {
        safeWrite(`[dry-run] ${s.sourceRecordingRef} recordedAt=${s.recordedAt.toISOString()} audio=${s.audioPath}\n`)
        continue
      }

      await prisma.callRecording.upsert({
        where: { sourceRecordingRef: meta?.sourceRecordingRef ?? s.sourceRecordingRef },
        create: {
          id,
          source: args.source,
          sourceRecordingRef: meta?.sourceRecordingRef ?? s.sourceRecordingRef,
          audioPath: s.audioPath,
          transcriptPath,
          transcriptText,
          transcriptSource: transcriptSource ?? undefined,
          transcriptFormat: transcriptFormat ?? undefined,
          recordedAt: s.recordedAt,
          durationSec: durationSec ?? undefined,
          callerLabel: meta?.callerLabel ?? s.callerLabel,
          calleePhoneNorm,
          direction,
          status,
          matchStatus: matched ? 'matched_auto' : 'unmatched',
          matchConfidence: matched?.confidence ?? 0,
          matchedAt: matched ? new Date() : undefined,
          projectId: matched?.projectId ?? undefined,
          callLogId: matched?.callLogId ?? undefined
        },
        update: {
          audioPath: s.audioPath,
          transcriptPath,
          transcriptText,
          transcriptSource: transcriptSource ?? undefined,
          transcriptFormat: transcriptFormat ?? undefined,
          recordedAt: s.recordedAt,
          durationSec: durationSec ?? undefined,
          callerLabel: meta?.callerLabel ?? s.callerLabel,
          calleePhoneNorm,
          direction,
          status,
          matchStatus: matched ? 'matched_auto' : 'unmatched',
          matchConfidence: matched?.confidence ?? 0,
          matchedAt: matched ? new Date() : null,
          projectId: matched?.projectId ?? null,
          callLogId: matched?.callLogId ?? null
        }
      })
    }

    safeWrite('[ingest] done\n')
  } finally {
    await prisma.$disconnect()
  }
}

main().catch((e) => {
  process.stderr.write(String(e))
  process.exit(1)
})

