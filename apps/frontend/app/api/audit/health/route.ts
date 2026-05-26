import { NextResponse } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const REPO_ROOT = '/home/mestre/Documents/repositories/clean-match-chess'

/**
 * GET /api/audit/health
 *
 * Worker-health probe. The frontend calls this once on AnalysisProvider
 * mount and shows a banner when `worker_alive === false`.
 *
 * Reply:
 *   {
 *     "worker_alive": boolean,
 *     "queued": number,
 *     "running": number,
 *     "completed_recent": number,
 *     "last_drain": ISO8601 | null
 *   }
 */
export async function GET(): Promise<NextResponse> {
  const scriptPath = path.join(REPO_ROOT, 'apps', 'frontend', 'lib', 'audit_health.py')

  return new Promise<NextResponse>((resolve) => {
    const proc = spawn(
      path.join(REPO_ROOT, '.venv', 'bin', 'python'),
      [scriptPath],
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
      const lastJsonLine = stdout
        .split('\n')
        .map((s) => s.trim())
        .filter((s) => s.startsWith('{') && s.endsWith('}'))
        .pop()
      try {
        const parsed = JSON.parse(lastJsonLine || stdout.trim())
        if (code !== 0 || parsed.error) {
          // Treat DB outage as worker-down: frontend banner is the right UX.
          resolve(
            NextResponse.json(
              {
                worker_alive: false,
                queued: 0,
                running: 0,
                completed_recent: 0,
                last_drain: null,
                error: parsed.error || `health probe exited ${code}: ${stderr}`,
              },
              { status: 200 },
            ),
          )
          return
        }
        resolve(NextResponse.json(parsed, { status: 200 }))
      } catch {
        resolve(
          NextResponse.json(
            {
              worker_alive: false,
              queued: 0,
              running: 0,
              completed_recent: 0,
              last_drain: null,
              error: `failed to parse output: ${stdout || stderr}`,
            },
            { status: 200 },
          ),
        )
      }
    })

    proc.on('error', (err: Error) => {
      resolve(
        NextResponse.json(
          {
            worker_alive: false,
            queued: 0,
            running: 0,
            completed_recent: 0,
            last_drain: null,
            error: err.message,
          },
          { status: 200 },
        ),
      )
    })
  })
}
