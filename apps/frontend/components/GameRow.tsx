'use client'

import { ProgressBar } from './ProgressBar'
import { ExportButton } from './ExportButton'

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

function parseResult(headers?: Record<string, string>): string {
  if (!headers) return '?'
  const white = headers['White'] || ''
  const black = headers['Black'] || ''
  const result = headers['Result'] || '*'
  return `${white} vs ${black} — ${result}`
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
  const isSuspect = game.score !== undefined && game.score > 0.75
  const isWarning = game.score !== undefined && game.score >= 0.5 && game.score <= 0.75

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
  return (
    <div style={rowStyle}>
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          gap: '12px',
          flexWrap: 'wrap',
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
            {parseResult(game.headers)}
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

        {/* Right side: badge + signals + export */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'flex-end',
            gap: '6px',
            flexShrink: 0,
          }}
        >
          {game.riskLevel && <RiskBadge risk={game.riskLevel} />}
          {game.dominantSignals && game.dominantSignals.length > 0 && (
            <div style={{ display: 'flex', gap: '4px', flexWrap: 'wrap', justifyContent: 'flex-end' }}>
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
                  }}
                >
                  {sig}
                </span>
              ))}
            </div>
          )}
          {game.score !== undefined && game.score > 0.75 && game.runId && (
            <ExportButton runId={game.runId} />
          )}
        </div>
      </div>
    </div>
  )
}
