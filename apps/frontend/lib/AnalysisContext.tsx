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

export interface AnalysisContextValue {
  username: string
  setUsername: (u: string) => void
  platform: Platform
  setPlatform: (p: Platform) => void
  sessions: Session[]
  isAnalyzing: boolean
  activeUsername: string
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
  const abortRef = useRef<AbortController | null>(null)

  const reset = useCallback(() => {
    abortRef.current?.abort()
    abortRef.current = null
    setSessions([])
    setActiveUsername('')
    setUsername('')
    setIsAnalyzing(false)
  }, [])

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
    [username, platform]
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
