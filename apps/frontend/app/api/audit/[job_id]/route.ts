import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const REPO_ROOT = '/home/mestre/Documents/repositories/clean-match-chess'

/**
 * GET /api/audit/[job_id]
 *
 * Reply:
 *   {
 *     "job_id": "<uuid>",
 *     "status": "queued"|"running"|"completed"|"failed"|"aborted"|"not_found",
 *     "result": {...}|null,
 *     "error": "..."|null,
 *     "audit_run_id": "<uuid>"|null
 *   }
 *
 * Frontend polls this every 1-2s with linear backoff. Returns within
 * ~100ms (one SELECT against an indexed PK).
 */
export async function GET(
  _request: NextRequest,
  context: { params: Promise<{ job_id: string }> },
): Promise<NextResponse> {
  const { job_id } = await context.params
  if (!job_id) {
    return NextResponse.json({ error: 'job_id required' }, { status: 400 })
  }

  const scriptPath = path.join(REPO_ROOT, 'apps', 'frontend', 'lib', 'get_audit_status.py')

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(
      path.join(REPO_ROOT, '.venv', 'bin', 'python'),
      [scriptPath, job_id],
      {
        env: { ...process.env, PYTHONPATH: REPO_ROOT },
        stdio: ['ignore', 'pipe', 'pipe'],
      },
    )

    let stdout = ''
    let stderr = ''
    proc.stdout.on('data', (chunk: Buffer) => {
      stdout += chunk.toString()
    })
    proc.stderr.on('data', (chunk: Buffer) => {
      stderr += chunk.toString()
    })

    proc.on('close', (code: number) => {
      // Python shim may emit structlog debug lines on stdout before the
      // result JSON; pick the LAST JSON-shaped line.
      const lastJsonLine = stdout
        .split('\n')
        .map((s) => s.trim())
        .filter((s) => s.startsWith('{') && s.endsWith('}'))
        .pop()
      try {
        const parsed = JSON.parse(lastJsonLine || stdout.trim())
        if (code !== 0 || parsed.error) {
          resolve(
            NextResponse.json(
              { error: parsed.error || `get_audit_status.py exited ${code}: ${stderr}` },
              { status: 500 },
            ),
          )
          return
        }
        const isTerminal = ['completed', 'failed', 'aborted'].includes(parsed.status)
        resolve(NextResponse.json(parsed, { status: isTerminal ? 200 : 202 }))
      } catch {
        resolve(
          NextResponse.json(
            { error: `failed to parse status output: ${stdout || stderr}` },
            { status: 500 },
          ),
        )
      }
    })

    proc.on('error', (err: Error) => {
      resolve(NextResponse.json({ error: err.message }, { status: 500 }))
    })
  })
}
