import { execFile } from 'child_process'
import { promisify } from 'util'

const execFileAsync = promisify(execFile)

type FfprobeFormat = {
  duration?: string
}

type FfprobeResult = {
  format?: FfprobeFormat
}

/**
 * Returns duration seconds if ffprobe is available.
 */
export const getDurationSec = async (audioPath: string) => {
  try {
    const { stdout } = await execFileAsync('ffprobe', [
      '-v',
      'error',
      '-show_format',
      '-of',
      'json',
      audioPath
    ])
    const json = JSON.parse(stdout) as FfprobeResult
    const dur = Number(json.format?.duration ?? '')
    return Number.isFinite(dur) ? Math.round(dur) : null
  } catch {
    return null
  }
}

