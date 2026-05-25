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

  // Done state
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
          flexWrap: 'wrap',
          cursor: canExpand ? 'pointer' : 'default',
        }}
      >
        {/* Index */}
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

        {/* Game info */}
        <div style={{ flex: 1, minWidth: '200px' }}>
          <div
            style={{
              fontSize: '13px',
              color: '#F2EFE8',
              marginBottom: '2px',
              fontFamily: 'Space Grotesk, sans-serif',
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
        </div>

        {/* Score section */}
        <div style={{ minWidth: '180px', flex: '0 0 180px' }}>
          {game.score !== undefined && (
            <>
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
                  IC [{(game.confidenceInterval[0] * 100).toFixed(1)}%–{(game.confidenceInterval[1] * 100).toFixed(1)}%]
                </div>
              )}
            </>
          )}
        </div>

        {/* Right side: badge + export only. Dominant-signal chips render
            on their own full-width wrap row below — moving them out of this
            column prevents long signal names like
            `behavioral-patterns/precision-burst` from expanding this column's
            natural width and shoving the score section right (or wrapping
            the whole column off the row). */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
            gap: '6px',
            flexShrink: 0,
            maxWidth: '160px',
          }}
        >
          {game.riskLevel && <RiskBadge risk={game.riskLevel} />}
          {game.score !== undefined && game.score > 0.75 && game.runId && (
            <ExportButton runId={game.runId} />
          )}
        </div>

        {/* Dominant-signal chips occupy their own row by forcing
            flex-basis: 100% inside the wrapping toggle. Chips themselves can
            wrap to multiple lines if a single chip is wider than what fits
            in the remaining width (e.g. very long signal names). */}
        {game.dominantSignals && game.dominantSignals.length > 0 && (
          <div
            data-testid="game-row__chips"
            style={{
              flexBasis: '100%',
              display: 'flex',
              flexWrap: 'wrap',
              gap: '4px',
              paddingLeft: '40px',
              marginTop: '4px',
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
