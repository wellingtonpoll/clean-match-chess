'use client'

import { useState, useCallback, useRef } from 'react'
import { GameRow, GameResult, RiskLevel } from '../components/GameRow'

// ─── Types ────────────────────────────────────────────────────────────────────

interface Session {
  id: string
  offset: number
  games: GameResult[]
  done: boolean
  error?: string
}

// ─── Constants ────────────────────────────────────────────────────────────────

const GAMES_PER_PAGE = 10

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildInitialGames(offset: number, count: number): GameResult[] {
  return Array.from({ length: count }, (_, i) => ({
    idx: offset + i,
    status: 'pending' as const,
  }))
}

function generateId(): string {
  return Math.random().toString(36).slice(2, 10)
}

// ─── Horse Labs Lockup ────────────────────────────────────────────────────────

function HorseLabsLockup() {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-start', gap: '12px' }}>
      <span
        style={{
          fontFamily: 'Instrument Serif, Georgia, serif',
          fontSize: '48px',
          fontWeight: 400,
          lineHeight: 1,
          color: '#F2EFE8',
          letterSpacing: '-0.02em',
        }}
      >
        Horse<span style={{ color: '#E8535A' }}>Labs</span>
        <span style={{ color: '#E8535A' }}>.</span>
      </span>

      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '14px',
          textTransform: 'uppercase',
          letterSpacing: '0.18em',
          color: '#4A4A50',
        }}
      >
        Clean Match Chess
      </div>
    </div>
  )
}

// ─── Platform toggle ──────────────────────────────────────────────────────────

function PlatformToggle({
  value,
  onChange,
}: {
  value: 'chesscom' | 'lichess'
  onChange: (v: 'chesscom' | 'lichess') => void
}) {
  const options: { key: 'chesscom' | 'lichess'; label: string }[] = [
    { key: 'chesscom', label: 'Chess.com' },
    { key: 'lichess', label: 'Lichess' },
  ]

  return (
    <div
      style={{
        display: 'inline-flex',
        border: '1px solid rgba(242,239,232,0.14)',
        overflow: 'hidden',
      }}
    >
      {options.map((opt) => {
        const active = value === opt.key
        return (
          <button
            key={opt.key}
            onClick={() => onChange(opt.key)}
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.14em',
              padding: '8px 16px',
              background: active ? '#B81820' : 'transparent',
              color: active ? '#F2EFE8' : '#7A7A80',
              border: 'none',
              cursor: 'pointer',
              transition: 'background 0.15s, color 0.15s',
              borderRight: opt.key === 'chesscom' ? '1px solid rgba(242,239,232,0.14)' : 'none',
            }}
          >
            {opt.label}
          </button>
        )
      })}
    </div>
  )
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function HomePage() {
  const [username, setUsername] = useState('')
  const [platform, setPlatform] = useState<'chesscom' | 'lichess'>('chesscom')
  const [sessions, setSessions] = useState<Session[]>([])
  const [isAnalyzing, setIsAnalyzing] = useState(false)
  const abortRef = useRef<AbortController | null>(null)

  // Current username used for analysis (locked once started)
  const [activeUsername, setActiveUsername] = useState('')

  const totalOffset = sessions.reduce((acc, s) => acc + s.games.length, 0)

  const runAnalysis = useCallback(
    async (offset: number) => {
      if (!username.trim()) return

      // Abort any previous stream
      abortRef.current?.abort()
      const abort = new AbortController()
      abortRef.current = abort

      setIsAnalyzing(true)
      if (offset === 0) {
        setActiveUsername(username.trim())
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
        username: username.trim(),
        platform,
        count: String(GAMES_PER_PAGE),
        offset: String(offset),
      })

      try {
        const res = await fetch(`/api/analyze?${params}`, {
          signal: abort.signal,
        })

        if (!res.ok) {
          const errText = await res.text()
          setSessions((prev) =>
            prev.map((s) =>
              s.id === sessionId ? { ...s, done: true, error: errText } : s
            )
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

            // Stream done sentinel
            if (payload.done) {
              setSessions((prev) =>
                prev.map((s) => (s.id === sessionId ? { ...s, done: true } : s))
              )
              break
            }

            // Global error
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

            // Game result
            const idx = payload.idx as number
            const updatedGame: GameResult =
              payload.error
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
                    confidenceInterval: payload.confidence_interval as [number, number] | undefined,
                    dominantSignals: payload.dominant_signals as string[] | undefined,
                    headers: payload.headers as Record<string, string> | undefined,
                    plyCount: payload.ply_count as number | undefined,
                  }

            setSessions((prev) =>
              prev.map((s) => {
                if (s.id !== sessionId) return s
                const games = s.games.map((g) =>
                  g.idx === idx ? updatedGame : g
                )
                return { ...s, games }
              })
            )
          }
        }
      } catch (e) {
        if ((e as Error).name === 'AbortError') return
        setSessions((prev) =>
          prev.map((s) =>
            s.id === sessionId
              ? { ...s, done: true, error: (e as Error).message }
              : s
          )
        )
      } finally {
        setIsAnalyzing(false)
      }
    },
    [username, platform]
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    runAnalysis(0)
  }

  const handleLoadMore = () => {
    runAnalysis(totalOffset)
  }

  const lastSession = sessions[sessions.length - 1]
  const showResults = sessions.length > 0

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0B0B0D',
        color: '#F2EFE8',
      }}
    >
      {/* ── Main content ── */}
      <main
        style={{
          maxWidth: '64rem',
          margin: '0 auto',
          padding: '0 24px 80px',
        }}
      >
        {/* ── Hero / Search section ── */}
        <section
          style={{
            paddingTop: sessions.length > 0 ? '40px' : '80px',
            paddingBottom: '48px',
            transition: 'padding-top 0.3s ease',
          }}
        >
          {sessions.length === 0 && (
            <div style={{ marginBottom: '48px' }}>
              <HorseLabsLockup />
              <p
                style={{
                  fontFamily: 'Space Grotesk, sans-serif',
                  fontSize: '15px',
                  color: '#4A4A50',
                  maxWidth: '480px',
                  lineHeight: 1.6,
                  marginTop: '32px',
                }}
              >
                Análise probabilística de fairplay em partidas de xadrez via
                Stockfish e heurísticas estatísticas avançadas.
              </p>
            </div>
          )}

          {/* Search form */}
          <form onSubmit={handleSubmit}>
            <div style={{ marginBottom: '16px' }}>
              <PlatformToggle value={platform} onChange={setPlatform} />
            </div>

            <div
              style={{
                display: 'flex',
                gap: '0',
                border: '1px solid rgba(242,239,232,0.14)',
                overflow: 'hidden',
              }}
            >
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Nome de usuário..."
                disabled={isAnalyzing}
                style={{
                  flex: 1,
                  padding: '16px 20px',
                  fontFamily: 'Instrument Serif, Georgia, serif',
                  fontSize: '22px',
                  fontStyle: username ? 'normal' : 'italic',
                  fontWeight: 400,
                  color: '#F2EFE8',
                  background: '#131316',
                  border: 'none',
                  outline: 'none',
                  opacity: isAnalyzing ? 0.6 : 1,
                }}
              />
              <button
                type="submit"
                disabled={isAnalyzing || !username.trim()}
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '11px',
                  textTransform: 'uppercase',
                  letterSpacing: '0.14em',
                  padding: '0 28px',
                  background: isAnalyzing ? '#4A4A50' : '#8B0F14',
                  color: '#F2EFE8',
                  border: 'none',
                  cursor: isAnalyzing || !username.trim() ? 'not-allowed' : 'pointer',
                  transition: 'background 0.15s',
                  minWidth: '120px',
                  flexShrink: 0,
                }}
                onMouseEnter={(e) => {
                  if (!isAnalyzing && username.trim())
                    (e.currentTarget as HTMLButtonElement).style.background = '#B81820'
                }}
                onMouseLeave={(e) => {
                  if (!isAnalyzing)
                    (e.currentTarget as HTMLButtonElement).style.background = '#8B0F14'
                }}
              >
                {isAnalyzing ? 'Analisando...' : 'Analisar'}
              </button>
            </div>
          </form>
        </section>

        {/* ── Results section ── */}
        {showResults && (
          <section>
            {/* Eyebrow */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                marginBottom: '16px',
                paddingBottom: '16px',
                borderBottom: '1px solid rgba(242,239,232,0.14)',
              }}
            >
              <div>
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '10px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.14em',
                    color: '#4A4A50',
                    marginBottom: '4px',
                  }}
                >
                  Análise
                </div>
                <h2
                  style={{
                    fontFamily: 'Instrument Serif, Georgia, serif',
                    fontWeight: 400,
                    fontSize: '24px',
                    color: '#F2EFE8',
                  }}
                >
                  {activeUsername}
                </h2>
              </div>

              {/* Summary stats */}
              <SummaryStats sessions={sessions} />
            </div>

            {/* Game rows */}
            <div
              style={{
                border: '1px solid rgba(242,239,232,0.14)',
              }}
            >
              {sessions.flatMap((session) =>
                session.games.map((game) => (
                  <GameRow key={`${session.id}-${game.idx}`} game={game} />
                ))
              )}
            </div>

            {/* Load more */}
            {lastSession?.done && !isAnalyzing && (
              <div
                style={{
                  marginTop: '24px',
                  display: 'flex',
                  justifyContent: 'center',
                }}
              >
                <button
                  onClick={handleLoadMore}
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '11px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.14em',
                    padding: '12px 32px',
                    background: 'transparent',
                    color: '#7A7A80',
                    border: '1px solid rgba(242,239,232,0.14)',
                    cursor: 'pointer',
                    transition: 'border-color 0.15s, color 0.15s',
                  }}
                  onMouseEnter={(e) => {
                    const el = e.currentTarget as HTMLButtonElement
                    el.style.borderColor = 'rgba(242,239,232,0.4)'
                    el.style.color = '#F2EFE8'
                  }}
                  onMouseLeave={(e) => {
                    const el = e.currentTarget as HTMLButtonElement
                    el.style.borderColor = 'rgba(242,239,232,0.14)'
                    el.style.color = '#7A7A80'
                  }}
                >
                  Próximas 10 Partidas →
                </button>
              </div>
            )}

            {/* Error state */}
            {lastSession?.error && (
              <div
                style={{
                  marginTop: '16px',
                  padding: '12px 16px',
                  border: '1px solid rgba(184,24,32,0.4)',
                  background: 'rgba(139,15,20,0.08)',
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '11px',
                  color: '#B81820',
                  letterSpacing: '0.06em',
                }}
              >
                ERRO: {lastSession.error}
              </div>
            )}
          </section>
        )}
      </main>
    </div>
  )
}

// ─── Summary stats component ──────────────────────────────────────────────────

function SummaryStats({ sessions }: { sessions: Session[] }) {
  const allGames = sessions.flatMap((s) => s.games)
  const done = allGames.filter((g) => g.status === 'done')
  const suspect = done.filter((g) => g.score !== undefined && g.score > 0.75)
  const total = allGames.length

  if (done.length === 0) return null

  return (
    <div style={{ display: 'flex', gap: '24px', alignItems: 'flex-end' }}>
      <Stat label="Analisadas" value={`${done.length}/${total}`} />
      <Stat
        label="Suspeitas"
        value={String(suspect.length)}
        accent={suspect.length > 0}
      />
    </div>
  )
}

function Stat({
  label,
  value,
  accent = false,
}: {
  label: string
  value: string
  accent?: boolean
}) {
  return (
    <div>
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '9px',
          textTransform: 'uppercase',
          letterSpacing: '0.14em',
          color: '#4A4A50',
          marginBottom: '2px',
        }}
      >
        {label}
      </div>
      <div
        style={{
          fontFamily: 'Instrument Serif, Georgia, serif',
          fontSize: '22px',
          fontWeight: 400,
          color: accent ? '#B81820' : '#F2EFE8',
        }}
      >
        {value}
      </div>
    </div>
  )
}
