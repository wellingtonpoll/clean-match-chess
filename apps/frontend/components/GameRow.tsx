'use client'

import { useState } from 'react'
import { ProgressBar } from './ProgressBar'
import { ExportButton } from './ExportButton'
import { PlayerLink } from './PlayerLink'
import { ExpandedAnalysis } from './ExpandedAnalysis'

export type RiskLevel = 'low' | 'medium' | 'high'

export interface GameResult {
  idx: number
  status: 'pending' | 'analyzing' | 'done' | 'error'
  runId?: string
  score?: number
  riskLevel?: RiskLevel
  confidenceInterval?: [number, number]
  dominantSignals?: string[]
  headers?: Record<string, string>
  plyCount?: number
  error?: string
}

interface GameRowProps {
  game: GameResult
  sessionOffset?: number
}

function RiskBadge({ risk }: { risk: RiskLevel }) {
  const styles: Record<RiskLevel, React.CSSProperties> = {
    low: {
      color: '#4A4A50',
      border: 'none',
      background: 'transparent',
    },
    medium: {
      color: '#C9A030',
      border: '1px solid rgba(201,160,48,0.5)',
      background: 'rgba(201,160,48,0.06)',
    },
    high: {
      color: '#B81820',
      border: '1px solid rgba(184,24,32,0.6)',
      background: 'rgba(139,15,20,0.15)',
    },
  }

  const labels: Record<RiskLevel, string> = {
    low: 'LOW',
    medium: 'ATENÇÃO',
    high: 'SUSPEITO',
  }

  return (
    <span
      style={{
        fontFamily: 'JetBrains Mono, monospace',
        fontSize: '9px',
        textTransform: 'uppercase',
        letterSpacing: '0.14em',
        padding: '2px 6px',
        flexShrink: 0,
        ...styles[risk],
      }}
    >
      {labels[risk]}
    </span>
  )
}

function ScoreBar({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score * 100))
  const color =
    score > 0.75 ? '#B81820' : score >= 0.5 ? '#C9A030' : '#3A7D44'

  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: '8px', width: '100%' }}>
      <div style={{ flex: 1 }}>
        <ProgressBar value={score} color={color} />
      </div>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '11px',
          color: color,
          flexShrink: 0,
          minWidth: '38px',
          textAlign: 'right',
        }}
      >
        {pct.toFixed(1)}%
      </span>
    </div>
  )
}

function parsePlayers(headers?: Record<string, string>): {
  white: string
  black: string
  result: string
} {
  return {
    white: headers?.['White'] || '?',
    black: headers?.['Black'] || '?',
    result: headers?.['Result'] || '*',
  }
}

function parseDate(headers?: Record<string, string>): string {
  if (!headers) return ''
  const date = headers['Date'] || headers['UTCDate'] || ''
  return date.replace(/\./g, '-')
}

function parseTimeControl(headers?: Record<string, string>): string {
  if (!headers) return ''
  const tc = headers['TimeControl'] || ''
  return tc
}

export function GameRow({ game }: GameRowProps) {
  const [expanded, setExpanded] = useState(false)
  const isSuspect = game.score !== undefined && game.score > 0.75
  const isWarning = game.score !== undefined && game.score >= 0.5 && game.score <= 0.75
  const canExpand = game.status === 'done'

  const rowStyle: React.CSSProperties = {
    borderBottom: '1px solid rgba(242,239,232,0.08)',
    borderLeft: isSuspect
      ? '3px solid #8B0F14'
      : isWarning
      ? '3px solid rgba(201,160,48,0.6)'
      : '3px solid transparent',
    background: isSuspect
      ? 'rgba(139,15,20,0.06)'
      : isWarning
      ? 'rgba(201,160,48,0.04)'
      : 'transparent',
    padding: '12px 16px',
    transition: 'background 0.2s',
    animation: game.status === 'done' || game.status === 'error' ? 'fade-up 0.3s ease-out forwards' : undefined,
    // Clip any descendant overflow at the row boundary. Without this, a
    // long signal-chip name (e.g. `behavioral-patterns/precision-burst`)
    // forces the document `body` to grow horizontally, which in turn
    // grants the chip container enough width that `flex-wrap: wrap` never
    // fires. Clipping at the row level breaks that feedback loop —
    // chips inside the row see a bounded container and wrap correctly.
    overflow: 'hidden',
  }

  // Pending / analyzing skeleton
  if (game.status === 'pending' || game.status === 'analyzing') {
    return (
      <div style={rowStyle}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '10px',
              color: '#4A4A50',
              flexShrink: 0,
              minWidth: '28px',
            }}
          >
            #{game.idx + 1}
          </span>
          <div style={{ flex: 1 }}>
            {/* Skeleton text line */}
            <div
              className="animate-shimmer"
              style={{ height: '12px', width: '60%', marginBottom: '8px' }}
            />
            <ProgressBar />
          </div>
        </div>
      </div>
    )
  }

  // Error state
  if (game.status === 'error') {
    return (
      <div style={{ ...rowStyle, borderLeft: '3px solid rgba(242,239,232,0.14)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '10px',
              color: '#4A4A50',
              flexShrink: 0,
              minWidth: '28px',
            }}
          >
            #{game.idx + 1}
          </span>
          <div style={{ flex: 1 }}>
            <span
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '10px',
                color: '#4A4A50',
              }}
            >
              {game.error === 'too_short'
                ? 'PARTIDA MUITO CURTA — IGNORADA'
                : `ERRO: ${game.error || 'desconhecido'}`}
            </span>
          </div>
        </div>
      </div>
    )
  }

  // Done state — stacked layout (2026-05-25 redesign):
  // The previous multi-column layout (game-info | ScoreBar 180px | right
  // badge column) made the ScoreBar's horizontal position drift with
  // player-name length. Long usernames such as `DaianyDias` pushed the
  // score bar right; short usernames left it back at center. Cross-card
  // misalignment broke the eye's ability to compare scores at a glance.
  //
  // New layout puts everything in a single content column to the right of
  // the index gutter, so ScoreBar width and offset are constant per row
  // regardless of name length:
  //
  //   [#idx]  RiskBadge ('ATENÇÃO' / 'SUSPEITO' / 'LOW')
  //           PlayerWhite vs PlayerBlack — Result
  //           Date | TimeControl | plies
  //           [ScoreBar ============================ XX.X%]
  //           IC [low%–high%]
  //           [signal chips, max 3, ellipsis-truncated]
  //           [PDF] [TXT]  (only when suspect)
  const expandedId = game.runId ? `expanded-${game.runId}` : `expanded-${game.idx}`
  return (
    <div style={rowStyle} data-testid="game-row" data-expanded={expanded ? 'true' : 'false'}>
      <div
        data-testid="game-row__toggle"
        role={canExpand ? 'button' : undefined}
        aria-expanded={canExpand ? expanded : undefined}
        aria-controls={canExpand ? expandedId : undefined}
        tabIndex={canExpand ? 0 : undefined}
        onClick={() => canExpand && setExpanded((v) => !v)}
        onKeyDown={(e) => {
          if (!canExpand) return
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault()
            setExpanded((v) => !v)
          }
        }}
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          cursor: canExpand ? 'pointer' : 'default',
        }}
      >
        {/* Index gutter */}
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '10px',
            color: '#4A4A50',
            flexShrink: 0,
            minWidth: '28px',
            paddingTop: '2px',
          }}
        >
          #{game.idx + 1}
        </span>

        {/* Content column — everything stacks vertically here, ScoreBar
            width is `flex: 1` of this column so it stays constant per row. */}
        <div
          data-testid="game-row__content"
          style={{
            flex: 1,
            minWidth: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '6px',
          }}
        >
          {/* Risk badge — above the player names per maintainer request
              2026-05-25. Aligned left so eye can scan the column. */}
          {game.riskLevel && (
            <div data-testid="game-row__badge-row" style={{ display: 'flex' }}>
              <RiskBadge risk={game.riskLevel} />
            </div>
          )}

          {/* Players + result */}
          <div
            data-testid="game-row__players"
            style={{
              fontSize: '13px',
              color: '#F2EFE8',
              fontFamily: 'Space Grotesk, sans-serif',
              lineHeight: 1.4,
            }}
          >
            {(() => {
              const { white, black, result } = parsePlayers(game.headers)
              return (
                <>
                  <PlayerLink username={white} />
                  <span style={{ color: '#4A4A50', margin: '0 6px' }}>vs</span>
                  <PlayerLink username={black} />
                  <span style={{ color: '#4A4A50', margin: '0 8px' }}>—</span>
                  <span>{result}</span>
                </>
              )
            })()}
          </div>

          {/* Meta row — date, time control, plies */}
          <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
            {parseDate(game.headers) && (
              <span className="label">{parseDate(game.headers)}</span>
            )}
            {parseTimeControl(game.headers) && (
              <span className="label">{parseTimeControl(game.headers)}</span>
            )}
            {game.plyCount !== undefined && (
              <span className="label">{game.plyCount} lances</span>
            )}
          </div>

          {/* ScoreBar — full content-column width, predictable offset per row */}
          {game.score !== undefined && (
            <div data-testid="game-row__score" style={{ marginTop: '2px' }}>
              <ScoreBar score={game.score} />
              {game.confidenceInterval && (
                <div
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '9px',
                    color: '#4A4A50',
                    marginTop: '3px',
                  }}
                >
                  IC [{(game.confidenceInterval[0] * 100).toFixed(1)}%–
                  {(game.confidenceInterval[1] * 100).toFixed(1)}%]
                </div>
              )}
            </div>
          )}

          {/* Signal chips — each chip gets `flex: 0 1 auto` + `min-width: 0`
              so that text-overflow ellipsis can actually fire when a single
              chip's natural width exceeds the column. Without min-width: 0
              the `white-space: nowrap` text sets the flex item's min-content
              size to its full text width, defeating the ellipsis. */}
          {game.dominantSignals && game.dominantSignals.length > 0 && (
            <div
              data-testid="game-row__chips"
              style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '4px',
                marginTop: '2px',
                minWidth: 0,
              }}
            >
              {game.dominantSignals.slice(0, 3).map((sig) => (
                <span
                  key={sig}
                  style={{
                    fontFamily: 'JetBrains Mono, monospace',
                    fontSize: '9px',
                    textTransform: 'uppercase',
                    letterSpacing: '0.14em',
                    padding: '1px 5px',
                    border: '1px solid rgba(242,239,232,0.14)',
                    color: '#7A7A80',
                    flex: '0 1 auto',
                    minWidth: 0,
                    maxWidth: '100%',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                  title={sig}
                >
                  {sig}
                </span>
              ))}
            </div>
          )}

          {/* Export buttons — only when the game is flagged as suspect */}
          {game.score !== undefined && game.score > 0.75 && game.runId && (
            <div data-testid="game-row__export" style={{ display: 'flex', gap: '8px', marginTop: '2px' }}>
              <ExportButton runId={game.runId} />
            </div>
          )}
        </div>
      </div>

      {/* Expanded "Análise detalhada" section (US2) */}
      {canExpand && expanded && (
        <div id={expandedId}>
          <ExpandedAnalysis game={game} />
        </div>
      )}
    </div>
  )
}
