import { NextRequest, NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const REPO_ROOT = '/home/mestre/Documents/repositories/clean-match-chess'

/**
 * POST /api/audit-username
 *
 * Body: { "username": "quaiada", "platform"?: "chesscom"|"lichess",
 *         "count"?: number, "offset"?: number }
 *
 * Fetches games from chess.com (server-side via the existing chess.com pub
 * client), enqueues one audit_job per game, returns the list of job_ids.
 * Frontend then polls `GET /api/audit/[job_id]` for each one in parallel.
 *
 * Reply:
 *   {
 *     "jobs": [
 *       { "idx": 0, "job_id": "<uuid>", "headers": {...}, "ply_count": 36 },
 *       { "idx": 1, "error": "too_short", "headers": {...} },
 *       ...
 *     ]
 *   }
 */
export async function POST(request: NextRequest): Promise<NextResponse> {
  let body: { username?: string; platform?: string; count?: number; offset?: number }
  try {
    body = await request.json()
  } catch {
    return NextResponse.json({ error: 'invalid JSON body' }, { status: 400 })
  }
  if (!body.username || typeof body.username !== 'string') {
    return NextResponse.json({ error: 'username required' }, { status: 400 })
  }

  const scriptPath = path.join(REPO_ROOT, 'apps', 'frontend', 'lib', 'enqueue_username.py')

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
              { error: parsed.error || `enqueue_username.py exited ${code}: ${stderr}` },
              { status: 500 },
            ),
          )
          return
        }
        resolve(NextResponse.json(parsed, { status: 202 }))
      } catch {
        resolve(
          NextResponse.json(
            { error: `failed to parse output: ${stdout || stderr}` },
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
