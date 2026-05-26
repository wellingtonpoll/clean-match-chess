'use client'

// Feature 006 / T005 — Lifts runAnalysis + session state out of `page.tsx`
// so Header (US3) and PlayerLink (US1) can share the same actions.

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import type { GameResult, RiskLevel } from '../components/GameRow'
import type { PlayerProfile } from './profileTypes'

export interface WorkerHealth {
  alive: boolean
  queued: number
  running: number
  lastDrain: string | null
}

export type Platform = 'chesscom' | 'lichess'

export interface Session {
  id: string
  offset: number
  games: GameResult[]
  done: boolean
  error?: string
}

export interface RunOptions {
  /** Override the current username for this invocation. Also syncs back into the context state. */
  newUsername?: string
}

export type ProfileStatus = 'idle' | 'loading' | 'ready' | 'not_found' | 'error'

export interface AnalysisContextValue {
  username: string
  setUsername: (u: string) => void
  platform: Platform
  setPlatform: (p: Platform) => void
  sessions: Session[]
  isAnalyzing: boolean
  activeUsername: string
  profile: PlayerProfile | null
  profileStatus: ProfileStatus
  profileError: string | null
  workerHealth: WorkerHealth
  runAnalysis: (offset: number, opts?: RunOptions) => Promise<void>
  reset: () => void
}

const AnalysisContext = createContext<AnalysisContextValue | null>(null)

const GAMES_PER_PAGE = 10

function buildInitialGames(offset: number, count: number): GameResult[] {
  return Array.from({ length: count }, (_, i) => ({
    idx: offset + i,
    status: 'pending' as const,
  }))
}

function generateId(): string {
  return Math.random().toString(36).slice(2, 10)
}

interface PollJobInput {
  idx: number
  job_id: string
  headers?: Record<string, string>
  ply_count?: number
}

interface AuditStatusResponse {
  job_id: string
  status: 'queued' | 'running' | 'completed' | 'failed' | 'aborted' | 'not_found'
  result: {
    run_id?: string
    score?: number
    risk_level?: RiskLevel
    confidence_interval?: [number, number]
    dominant_signals?: string[]
    headers?: Record<string, string>
    ply_count?: number
  } | null
  error: string | null
}

// Feature 012 — abort the poll if the worker is silent (no status
// transition past 'queued') for this many ms. Avoids the previous
// "pending forever" UX when the daemon isn't running.
const POLL_NO_PROGRESS_TIMEOUT_MS = 60_000

/**
 * Poll `/api/audit/[job_id]` with linear backoff (1s → 2s → 4s, cap 4s)
 * until the job reaches a terminal state. If `POLL_NO_PROGRESS_TIMEOUT_MS`
 * elapses without seeing the status advance past 'queued', mark the game
 * as error so the UI doesn't spin forever.
 */
async function pollJob(
  job: PollJobInput,
  sessionId: string,
  setSessions: React.Dispatch<React.SetStateAction<Session[]>>,
  abortSignal: AbortSignal,
): Promise<void> {
  const delays = [1000, 2000, 4000]
  let attempt = 0
  const startedAt = Date.now()
  let lastObservedStatus: AuditStatusResponse['status'] | null = null

  while (!abortSignal.aborted) {
    const res = await fetch(`/api/audit/${job.job_id}`, { signal: abortSignal })
    const data = (await res.json()) as AuditStatusResponse

    if (data.status === 'completed' && data.result) {
      const updated: GameResult = {
        idx: job.idx,
        status: 'done',
        runId: data.result.run_id,
        score: data.result.score,
        riskLevel: data.result.risk_level,
        confidenceInterval: data.result.confidence_interval,
        dominantSignals: data.result.dominant_signals,
        headers: data.result.headers ?? job.headers,
        plyCount: data.result.ply_count ?? job.ply_count,
      }
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, games: s.games.map((g) => (g.idx === job.idx ? updated : g)) }
            : s
        )
      )
      return
    }

    if (data.status === 'failed' || data.status === 'aborted' || data.status === 'not_found') {
      const errored: GameResult = {
        idx: job.idx,
        status: 'error',
        error: data.error ?? data.status,
        headers: job.headers,
      }
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, games: s.games.map((g) => (g.idx === job.idx ? errored : g)) }
            : s
        )
      )
      return
    }

    // No-progress timeout: status stayed 'queued' for too long → worker dead.
    if (
      data.status === 'queued' &&
      lastObservedStatus === 'queued' &&
      Date.now() - startedAt > POLL_NO_PROGRESS_TIMEOUT_MS
    ) {
      const errored: GameResult = {
        idx: job.idx,
        status: 'error',
        error: 'worker not responding (run ./scripts/dev.sh)',
        headers: job.headers,
      }
      setSessions((prev) =>
        prev.map((s) =>
          s.id === sessionId
            ? { ...s, games: s.games.map((g) => (g.idx === job.idx ? errored : g)) }
            : s
        )
      )
      return
    }
    lastObservedStatus = data.status

    const delay = delays[Math.min(attempt, delays.length - 1)]
    attempt++
    await new Promise((r) => setTimeout(r, delay))
  }
}

const WORKER_HEALTH_REFRESH_MS = 30_000

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState('')
  const [platform, setPlatform] = useState<Platform>('chesscom')
  const [sessions, setSessions] = useState<Session[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [activeUsername, setActiveUsername] = useState('')
  const [profile, setProfile] = useState<PlayerProfile | null>(null)
  const [profileStatus, setProfileStatus] = useState<ProfileStatus>('idle')
  const [profileError, setProfileError] = useState<string | null>(null)
  // Feature 012 — track worker daemon liveness for the WorkerBanner.
  const [workerHealth, setWorkerHealth] = useState<WorkerHealth>({
    alive: true,
    queued: 0,
    running: 0,
    lastDrain: null,
  })
  const abortRef = useRef<AbortController | null>(null)
  const profileAbortRef = useRef<AbortController | null>(null)

  // Health probe: once on mount, then every 30s. Failures (DB down, route
  // 5xx) are treated as worker-down so the banner appears immediately.
  useEffect(() => {
    let cancelled = false
    async function probe() {
      try {
        const res = await fetch('/api/audit/health', { cache: 'no-store' })
        const data = (await res.json()) as {
          worker_alive: boolean
          queued: number
          running: number
          last_drain: string | null
        }
        if (!cancelled) {
          setWorkerHealth({
            alive: data.worker_alive,
            queued: data.queued,
            running: data.running,
            lastDrain: data.last_drain,
          })
        }
      } catch {
        if (!cancelled) {
          setWorkerHealth((s) => ({ ...s, alive: false }))
        }
      }
    }
    void probe()
    const handle = setInterval(probe, WORKER_HEALTH_REFRESH_MS)
    return () => {
      cancelled = true
      clearInterval(handle)
    }
  }, [])

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    profileAbortRef.current?.abort()
    profileAbortRef.current = null
    setSessions([])
    setActiveUsername('')
    setUsername('')
    setIsAnalyzing(false)
    setProfile(null)
    setProfileStatus('idle')
    setProfileError(null)
  }, [])

  const fetchProfile = useCallback(
    async (uname: string, plat: Platform): Promise<void> => {
      profileAbortRef.current?.abort()
      const abort = new AbortController()
      profileAbortRef.current = abort
      setProfileStatus('loading')
      setProfile(null)
      setProfileError(null)
      try {
        const res = await fetch(
          `/api/profile?username=${encodeURIComponent(uname)}&platform=${plat}`,
          { signal: abort.signal }
        )
        if (res.status === 404) {
          setProfileStatus('not_found')
          const body = (await res.json().catch(() => ({}))) as { message?: string }
          setProfileError(body.message ?? 'Perfil não encontrado')
          return
        }
        if (!res.ok) {
          setProfileStatus('error')
          const body = (await res.json().catch(() => ({}))) as { message?: string }
          setProfileError(body.message ?? `HTTP ${res.status}`)
          return
        }
        const data = (await res.json()) as PlayerProfile
        setProfile(data)
        setProfileStatus('ready')
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
        setProfileStatus('error')
        setProfileError((e as Error).message)
      }
    },
    []
  )

  const runAnalysis = useCallback(
    async (offset: number, opts?: RunOptions) => {
      const effectiveUsername = (opts?.newUsername ?? username).trim()
      if (!effectiveUsername) return

      if (opts?.newUsername !== undefined && opts.newUsername !== username) {
        setUsername(opts.newUsername)
      }

      // Abort any previous in-flight poll cycle.
      abortRef.current?.abort()
      const abort = new AbortController()
      abortRef.current = abort

      setIsAnalyzing(true)
      if (offset === 0) {
        setActiveUsername(effectiveUsername)
        setSessions([])
        void fetchProfile(effectiveUsername, platform)
      }

      const sessionId = generateId()
      const initialGames = buildInitialGames(offset, GAMES_PER_PAGE)

      setSessions((prev) =>
        offset === 0
          ? [{ id: sessionId, offset, games: initialGames, done: false }]
          : [...prev, { id: sessionId, offset, games: initialGames, done: false }]
      )

      // Feature 011 Phase 4 — async audit queue. POST to enqueue all games,
      // get back a list of job_ids, poll each until terminal. Replaces the
      // previous /api/analyze SSE stream which spawned Stockfish in-process
      // per audit.
      try {
        const enqueueRes = await fetch('/api/audit-username', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            username: effectiveUsername,
            platform,
            count: GAMES_PER_PAGE,
            offset,
          }),
          signal: abort.signal,
        })

        if (!enqueueRes.ok) {
          const body = (await enqueueRes.json().catch(() => ({}))) as { error?: string }
          setSessions((prev) =>
            prev.map((s) =>
              s.id === sessionId
                ? { ...s, done: true, error: body.error ?? `HTTP ${enqueueRes.status}` }
                : s
            )
          )
          return
        }

        const { jobs } = (await enqueueRes.json()) as {
          jobs: Array<{
            idx: number
            job_id?: string
            error?: string
            headers?: Record<string, string>
            ply_count?: number
          }>
        }

        // Immediate updates: render headers + mark errored-at-enqueue games.
        setSessions((prev) =>
          prev.map((s) => {
            if (s.id !== sessionId) return s
            const games = s.games.map((g) => {
              const job = jobs.find((j) => j.idx === g.idx)
              if (!job) return g
              if (job.error) {
                return {
                  idx: g.idx,
                  status: 'error' as const,
                  error: job.error,
                  headers: job.headers,
                } satisfies GameResult
              }
              return {
                idx: g.idx,
                status: 'pending' as const,
                headers: job.headers,
                plyCount: job.ply_count,
              } satisfies GameResult
            })
            return { ...s, games }
          })
        )

        const pollable = jobs.filter((j) => j.job_id) as Array<{
          idx: number
          job_id: string
          headers?: Record<string, string>
          ply_count?: number
        }>
        if (pollable.length === 0) {
          setSessions((prev) =>
            prev.map((s) => (s.id === sessionId ? { ...s, done: true } : s))
          )
          return
        }

        // Poll each job in parallel. Each game's status updates as it
        // finishes; once all reach terminal, mark the session done.
        await Promise.all(
          pollable.map((job) => pollJob(job, sessionId, setSessions, abort.signal))
        )

        setSessions((prev) =>
          prev.map((s) => (s.id === sessionId ? { ...s, done: true } : s))
        )
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId ? { ...s, done: true, error: (e as Error).message } : s
          )
        )
      } finally {
        setIsAnalyzing(false)
      }
    },
    [username, platform, fetchProfile]
  )

  return (
    <AnalysisContext.Provider
      value={{
        username,
        setUsername,
        platform,
        setPlatform,
        sessions,
        isAnalyzing,
        activeUsername,
        profile,
        profileStatus,
        profileError,
        workerHealth,
        runAnalysis,
        reset,
      }}
    >
      {children}
    </AnalysisContext.Provider>
  )
}

export function useAnalysisContext(): AnalysisContextValue {
  const ctx = useContext(AnalysisContext)
  if (!ctx) {
    throw new Error('useAnalysisContext must be used within AnalysisProvider')
  }
  return ctx
}
