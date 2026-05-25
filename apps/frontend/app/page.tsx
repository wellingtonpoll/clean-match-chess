'use client'

import { GameRow } from '../components/GameRow'
import { Header } from '../components/Header'
import { ProfileLockup } from '../components/ProfileLockup'
import type { Session } from '../lib/AnalysisContext'
import { useAnalysisContext } from '../lib/AnalysisContext'

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

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function HomePage() {
  const {
    sessions,
    isAnalyzing,
    activeUsername,
    runAnalysis,
  } = useAnalysisContext()

  const totalOffset = sessions.reduce((acc, s) => acc + s.games.length, 0)

  const handleLoadMore = () => {
    runAnalysis(totalOffset)
  }

  const lastSession = sessions[sessions.length - 1]
  const showResults = sessions.length > 0
  const hasActiveSearch = activeUsername.length > 0

  return (
    <div
      style={{
        minHeight: '100vh',
        background: '#0B0B0D',
        color: '#F2EFE8',
      }}
    >
      <Header />
      <main
        style={{
          maxWidth: '64rem',
          margin: '0 auto',
          padding: '0 24px 80px',
          paddingTop: 'var(--header-h, 64px)',
        }}
      >
        <section
          data-testid="hero"
          data-mode={hasActiveSearch ? 'profile' : 'default'}
          style={
            hasActiveSearch
              ? {
                  // Sticky just below the fixed Header so the searched-user
                  // profile stays in view while the results list scrolls
                  // beneath it. zIndex < Header's 50 so the Header always
                  // wins layering. Solid bg required so scrolling rows
                  // don't bleed through.
                  position: 'sticky',
                  top: 'var(--header-h, 64px)',
                  zIndex: 40,
                  background: '#0B0B0D',
                  borderBottom: '1px solid rgba(242,239,232,0.14)',
                  paddingTop: '20px',
                  paddingBottom: '20px',
                }
              : {
                  paddingTop: '64px',
                  paddingBottom: '48px',
                }
          }
        >
          {hasActiveSearch ? (
            <ProfileLockup />
          ) : (
            <>
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
                Stockfish e heurísticas estatísticas avançadas. Digite o nome de
                um jogador no campo acima para iniciar.
              </p>
            </>
          )}
        </section>

        {showResults && (
          <section style={{ paddingTop: '32px' }}>
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

              <SummaryStats sessions={sessions} />
            </div>

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
