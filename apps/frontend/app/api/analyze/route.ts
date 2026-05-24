import { NextRequest } from 'next/server'
import { spawn } from 'child_process'
import path from 'path'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl
  const username = searchParams.get('username') || ''
  const platform = searchParams.get('platform') || 'chesscom'
  const count = searchParams.get('count') || '10'
  const offset = searchParams.get('offset') || '0'

  if (!username) {
    return new Response('Missing username', { status: 400 })
  }

  const scriptPath = path.join(process.cwd(), 'lib', 'analyze.py')
  const repoRoot = '/home/mestre/Documents/repositories/clean-match-chess'

  const encoder = new TextEncoder()

  const stream = new ReadableStream({
    start(controller) {
      const proc = spawn(
        path.join(repoRoot, '.venv', 'bin', 'python'),
        [scriptPath, username, platform, count, offset],
        { env: { ...process.env, PYTHONPATH: repoRoot } }
      )

      const send = (data: string) => {
        controller.enqueue(encoder.encode(`data: ${data}\n\n`))
      }

      let buffer = ''
      proc.stdout.on('data', (chunk: Buffer) => {
        buffer += chunk.toString()
        const lines = buffer.split('\n')
        buffer = lines.pop() || ''
        lines.filter((l) => l.trim()).forEach((line) => send(line))
      })

      proc.stderr.on('data', (_chunk: Buffer) => {
        // ignore verbose logs from analysis pipeline
      })

      proc.on('close', () => {
        if (buffer.trim()) send(buffer.trim())
        send(JSON.stringify({ done: true }))
        controller.close()
      })

      proc.on('error', (err) => {
        send(JSON.stringify({ error: err.message }))
        controller.close()
      })
    },
    cancel() {
      // stream cancelled by client — nothing to clean up here
    },
  })

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  })
}
