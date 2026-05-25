'use client'

// Feature 006 / T005 — Lifts runAnalysis + session state out of `page.tsx`
// so Header (US3) and PlayerLink (US1) can share the same actions.

import {
  createContext,
  useCallback,
  useContext,
  useRef,
  useState,
} from 'react'
import type { GameResult, RiskLevel } from '../components/GameRow'
import type { PlayerProfile } from './profileTypes'

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

export function AnalysisProvider({ children }: { children: React.ReactNode }) {
  const [username, setUsername] = useState('')
  const [platform, setPlatform] = useState<Platform>('chesscom')
  const [sessions, setSessions] = useState<Session[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const [activeUsername, setActiveUsername] = useState('')
  const [profile, setProfile] = useState<PlayerProfile | null>(null)
  const [profileStatus, setProfileStatus] = useState<ProfileStatus>('idle')
  const [profileError, setProfileError] = useState<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)
  const profileAbortRef = useRef<AbortController | null>(null)

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

      // Sync the override back into the context state so the Header
      // search field reflects what is being analyzed.
      if (opts?.newUsername !== undefined && opts.newUsername !== username) {
        setUsername(opts.newUsername)
      }

      // Abort any previous stream.
      abortRef.current?.abort()
      const abort = new AbortController()
      abortRef.current = abort

      setIsAnalyzing(true)
      if (offset === 0) {
        setActiveUsername(effectiveUsername)
        setSessions([])
        // Fire the profile fetch in parallel with the SSE stream. The hero
        // section subscribes to `profile` / `profileStatus` and swaps the
        // default HorseLabs lockup for the searched-player lockup as soon
        // as this resolves.
        void fetchProfile(effectiveUsername, platform)
      }

      const sessionId = generateId()
      const initialGames = buildInitialGames(offset, GAMES_PER_PAGE)

      setSessions((prev) =>
        offset === 0
          ? [{ id: sessionId, offset, games: initialGames, done: false }]
          : [...prev, { id: sessionId, offset, games: initialGames, done: false }]
      )

      const params = new URLSearchParams({
        username: effectiveUsername,
        platform,
        count: String(GAMES_PER_PAGE),
        offset: String(offset),
      })

      try {
        const res = await fetch(`/api/analyze?${params}`, { signal: abort.signal })

        if (!res.ok) {
          const errText = await res.text()
          setSessions((prev) =>
            prev.map((s) => (s.id === sessionId ? { ...s, done: true, error: errText } : s))
          )
          return
        }

        const reader = res.body?.getReader()
        if (!reader) return

        const decoder = new TextDecoder()
        let partial = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          partial += decoder.decode(value, { stream: true })
          const lines = partial.split('\n')
          partial = lines.pop() || ''

          for (const line of lines) {
            const trimmed = line.trim()
            if (!trimmed.startsWith('data:')) continue
            const jsonStr = trimmed.slice(5).trim()
            if (!jsonStr) continue

            let payload: Record<string, unknown>
            try {
              payload = JSON.parse(jsonStr)
            } catch {
              continue
            }

            if (payload.done) {
              setSessions((prev) =>
                prev.map((s) => (s.id === sessionId ? { ...s, done: true } : s))
              )
              break
            }

            if (payload.error && payload.idx === undefined) {
              setSessions((prev) =>
                prev.map((s) =>
                  s.id === sessionId
                    ? {
                        ...s,
                        done: true,
                        error: String(payload.error),
                        games: s.games.map((g) => ({
                          ...g,
                          status: 'error' as const,
                          error: String(payload.error),
                        })),
                      }
                    : s
                )
              )
              break
            }

            const idx = payload.idx as number
            const updatedGame: GameResult = payload.error
              ? {
                  idx,
                  status: 'error',
                  error: String(payload.error),
                  headers: payload.headers as Record<string, string> | undefined,
                }
              : {
                  idx,
                  status: 'done',
                  runId: payload.run_id as string | undefined,
                  score: payload.score as number | undefined,
                  riskLevel: payload.risk_level as RiskLevel | undefined,
                  confidenceInterval: payload.confidence_interval as
                    | [number, number]
                    | undefined,
                  dominantSignals: payload.dominant_signals as string[] | undefined,
                  headers: payload.headers as Record<string, string> | undefined,
                  plyCount: payload.ply_count as number | undefined,
                }

            setSessions((prev) =>
              prev.map((s) => {
                if (s.id !== sessionId) return s
                const games = s.games.map((g) => (g.idx === idx ? updatedGame : g))
                return { ...s, games }
              })
            )
          }
        }
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
