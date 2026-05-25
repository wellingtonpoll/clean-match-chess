'use client'

// Feature 006 / T011 — Renders a player's username as a clickable element.
// Subject (matches activeUsername in context) renders as plain text;
// opponent renders as a <button> that re-triggers analysis (FR-001..FR-003).

import { useAnalysisContext } from '../lib/AnalysisContext'

interface PlayerLinkProps {
  username: string
  /** Override aria-label. Defaults to `Analisar partidas de ${username}`. */
  ariaLabel?: string
}

export function PlayerLink({ username, ariaLabel }: PlayerLinkProps) {
  const { activeUsername, runAnalysis } = useAnalysisContext()
  const isSubject = username.toLowerCase() === activeUsername.toLowerCase()

  // Subject case: render plain text (FR-003: no-op).
  if (isSubject) {
    return (
      <span
        data-testid="player-link-self"
        style={{
          color: '#F2EFE8',
          fontWeight: 500,
        }}
      >
        {username}
      </span>
    )
  }

  return (
    <button
      type="button"
      data-testid="player-link"
      aria-label={ariaLabel ?? `Analisar partidas de ${username}`}
      onClick={(e) => {
        e.stopPropagation() // don't bubble into the GameRow expand toggle
        // Allowed during in-flight analysis — runAnalysis aborts + restarts
        // per US1 AS2 (same abortRef semantics as manual submit).
        runAnalysis(0, { newUsername: username })
      }}
      style={{
        fontFamily: 'inherit',
        fontSize: 'inherit',
        background: 'none',
        border: 'none',
        padding: 0,
        margin: 0,
        color: '#E8535A',
        textDecoration: 'underline',
        textUnderlineOffset: '3px',
        textDecorationColor: 'rgba(232,83,90,0.4)',
        cursor: 'pointer',
        transition: 'color 0.15s, text-decoration-color 0.15s',
      }}
      onMouseEnter={(e) => {
        ;(e.currentTarget as HTMLButtonElement).style.color = '#F2EFE8'
        ;(e.currentTarget as HTMLButtonElement).style.textDecorationColor = '#E8535A'
      }}
      onMouseLeave={(e) => {
        ;(e.currentTarget as HTMLButtonElement).style.color = '#E8535A'
        ;(e.currentTarget as HTMLButtonElement).style.textDecorationColor =
          'rgba(232,83,90,0.4)'
      }}
    >
      {username}
    </button>
  )
}
