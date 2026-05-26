import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const REPO_ROOT = '/home/mestre/Documents/repositories/clean-match-chess'

/**
 * POST /api/audit
 *
 * Body: { "pgn_text": "...", "subject_color"?: "white"|"black" }
 * Reply (sync): { "job_id": "<uuid>" }
 *
 * Spawns the Python `enqueue.py` shim which writes one row to
 * `audit_jobs` (status='queued'). The Postgres trigger fires
 * `NOTIFY audit_jobs_new` so the worker daemon wakes up. The HTTP
 * response returns within ~200 ms regardless of how long the audit
 * itself takes — frontend polls `GET /api/audit/[job_id]` for the
 * result.
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: { pgn_text?: string; subject_color?: string }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'invalid JSON body' }, { status: 400 })
  }

  if (!body.pgn_text || typeof body.pgn_text !== 'string') {
    return NextResponse.json({ error: 'pgn_text is required' }, { status: 400 })
  }

  const scriptPath = path.join(REPO_ROOT, 'apps', 'frontend', 'lib', 'enqueue.py')

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(
      path.join(REPO_ROOT, '.venv', 'bin', 'python'),
      [scriptPath],
      {
        env: { ...process.env, PYTHONPATH: REPO_ROOT },
        stdio: ['pipe', 'pipe', 'pipe'],
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
              { error: parsed.error || `enqueue.py exited ${code}: ${stderr}` },
              { status: 500 },
            ),
          )
          return
        }
        resolve(NextResponse.json(parsed, { status: 202 }))
      } catch {
        resolve(
          NextResponse.json(
            { error: `failed to parse enqueue output: ${stdout || stderr}` },
            { status: 500 },
          ),
        )
      }
    })

    proc.on('error', (err: Error) => {
      resolve(NextResponse.json({ error: err.message }, { status: 500 }))
    })

    proc.stdin.write(JSON.stringify(body))
    proc.stdin.end()
  })
}
