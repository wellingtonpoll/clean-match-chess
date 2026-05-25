'use client'

// Feature 006 / T017 — Renders the layperson "Análise detalhada" section
// inside an expanded GameRow.
//
// 2026-05-25 follow-up (Issue: "explicação detalhada de como a plataforma
// chegou nesse resultado"): adds a per-game reasoning summary at the top
// of the section so the reader sees a narrative explanation of the score
// (numeric value + risk class + confidence-interval width + signal framing)
// before the individual signal cards.

import { explainSignal, summarizeGame } from '../lib/signalExplanations'
import type { GameResult } from './GameRow'

interface ExpandedAnalysisProps {
  game: GameResult
}

export function ExpandedAnalysis({ game }: ExpandedAnalysisProps) {
  const signals = game.dominantSignals ?? []
  const summary = summarizeGame({
    score: game.score,
    riskLevel: game.riskLevel,
    confidenceInterval: game.confidenceInterval,
    dominantSignals: signals,
  })

  return (
    <div
      data-testid="expanded-analysis"
      style={{
        marginTop: '12px',
        paddingTop: '12px',
        borderTop: '1px solid rgba(242,239,232,0.08)',
      }}
    >
      <div
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '9px',
          textTransform: 'uppercase',
          letterSpacing: '0.14em',
          color: '#7A7A80',
          marginBottom: '12px',
        }}
      >
        Análise detalhada
      </div>

      <section
        data-testid="score-summary"
        style={{
          marginBottom: '16px',
          paddingBottom: '12px',
          borderBottom: '1px solid rgba(242,239,232,0.06)',
        }}
      >
        <div
          data-testid="score-summary__headline"
          style={{
            fontFamily: 'Instrument Serif, Georgia, serif',
            fontSize: '17px',
            color: '#F2EFE8',
            marginBottom: '6px',
          }}
        >
          {summary.headline}
        </div>
        <p
          data-testid="score-summary__intro"
          style={{
            fontSize: '12px',
            color: '#A0A0A8',
            fontFamily: 'Space Grotesk, sans-serif',
            lineHeight: 1.6,
            margin: 0,
            marginBottom: '8px',
          }}
        >
          {summary.intro}
        </p>
        <p
          data-testid="score-summary__signals-lead-in"
          style={{
            fontSize: '12px',
            color: '#7A7A80',
            fontFamily: 'Space Grotesk, sans-serif',
            lineHeight: 1.55,
            margin: 0,
          }}
        >
          {summary.signalsLeadIn}
        </p>
      </section>

      {signals.length === 0 ? (
        <p
          data-testid="expanded-analysis__empty"
          style={{
            fontSize: '13px',
            color: '#7A7A80',
            fontFamily: 'Space Grotesk, sans-serif',
            lineHeight: 1.5,
          }}
        >
          Nenhum sinal específico predominou neste score.
        </p>
      ) : (
        <ul
          style={{
            listStyle: 'none',
            padding: 0,
            margin: 0,
            display: 'flex',
            flexDirection: 'column',
            gap: '12px',
          }}
        >
          {signals.map((sig) => {
            const exp = explainSignal(sig)
            return (
              <li key={sig} data-testid="signal-explanation" data-signal-name={sig}>
                <div
                  style={{
                    fontFamily: 'Instrument Serif, Georgia, serif',
                    fontSize: '15px',
                    color: '#F2EFE8',
                    marginBottom: '4px',
                  }}
                >
                  {exp.headline}
                </div>
                <p
                  style={{
                    fontSize: '12px',
                    color: '#A0A0A8',
                    fontFamily: 'Space Grotesk, sans-serif',
                    lineHeight: 1.55,
                    margin: 0,
                  }}
                >
                  {exp.body}
                </p>
              </li>
            )
          })}
        </ul>
      )}
    </div>
  )
}
