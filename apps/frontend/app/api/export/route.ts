import { NextRequest } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'
import { readFile } from 'fs/promises'
import { tmpdir } from 'os'
import { randomUUID } from 'crypto'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const run_id = request.nextUrl.searchParams.get('run_id')
  const format = request.nextUrl.searchParams.get('format') || 'pdf'

  if (!run_id) {
    return new Response('Missing run_id', { status: 400 })
  }

  if (!['pdf', 'txt', 'json'].includes(format)) {
    return new Response('Invalid format — must be pdf, txt or json', { status: 400 })
  }

  const ext = format === 'pdf' ? 'pdf' : 'json'
  const outPath = path.join(tmpdir(), `cleanmatch-${randomUUID()}.${ext}`)
  const repoRoot = '/home/mestre/Documents/repositories/clean-match-chess'

  const pythonPath = [
    `${repoRoot}/apps/cli/src`,
    `${repoRoot}/packages/analysis-core/src`,
    `${repoRoot}/packages/heuristics/src`,
    `${repoRoot}/packages/report-engine/src`,
    `${repoRoot}/packages/design-system/src`,
    `${repoRoot}/packages/shared-types/src`,
  ].join(':')

  try {
    await new Promise<void>((resolve, reject) => {
      const proc = spawn(
        path.join(repoRoot, '.venv', 'bin', 'python'),
        ['-m', 'cleanmatch_cli.main', 'export', run_id, '--format', format, '--out', outPath],
        {
          env: {
            ...process.env,
            PYTHONPATH: pythonPath,
          },
        }
      )

      let stderr = ''
      proc.stderr?.on('data', (chunk: Buffer) => {
        stderr += chunk.toString()
      })

      proc.on('close', (code) => {
        if (code === 0) {
          resolve()
        } else {
          reject(new Error(`CLI exited with code ${code}: ${stderr.slice(0, 400)}`))
        }
      })

      proc.on('error', (err) => {
        reject(new Error(`spawn error: ${err.message}`))
      })
    })

    const buf = await readFile(outPath)
    const mime = format === 'pdf' ? 'application/pdf' : 'application/json'

    return new Response(buf, {
      headers: {
        'Content-Type': mime,
        'Content-Disposition': `attachment; filename="cleanmatch-${run_id}.${ext}"`,
      },
    })
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e)
    return new Response(`Export failed: ${msg}`, { status: 500 })
  }
}
