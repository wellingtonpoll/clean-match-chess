'use client'

// Feature 006 / T021 — Sticky header carrying HorseLabs brand + search + platform toggle.
//
// Layout:
//  - Desktop (≥ 768px): brand left, search + toggle right, single row, height var(--header-h).
//  - Mobile (< 480px): stacking via CSS — brand row 1, search row 2, total height var(--header-h).
// Brand click resets analysis state (Clarifications 2026-05-24).

import { useAnalysisContext, type Platform } from '../lib/AnalysisContext'

function BrandMark({ onClick }: { onClick: () => void }) {
  return (
    <button
      type="button"
      data-testid="header-brand"
      aria-label="HorseLabs — voltar ao início"
      onClick={onClick}
      style={{
        background: 'transparent',
        border: 'none',
        padding: 0,
        cursor: 'pointer',
        display: 'inline-flex',
        alignItems: 'baseline',
        gap: '8px',
        color: '#F2EFE8',
        fontFamily: 'Instrument Serif, Georgia, serif',
        fontSize: '22px',
        letterSpacing: '-0.02em',
      }}
    >
      <span>
        Horse<span style={{ color: '#E8535A' }}>Labs</span>
        <span style={{ color: '#E8535A' }}>.</span>
      </span>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '9px',
          textTransform: 'uppercase',
          letterSpacing: '0.18em',
          color: '#4A4A50',
        }}
      >
        Clean Match Chess
      </span>
    </button>
  )
}

function PlatformToggle({
  value,
  onChange,
  disabled,
}: {
  value: Platform
  onChange: (p: Platform) => void
  disabled?: boolean
}) {
  const options: { key: Platform; label: string }[] = [
    { key: 'chesscom', label: 'Chess.com' },
    { key: 'lichess', label: 'Lichess' },
  ]
  return (
    <div
      data-testid="header-platform-toggle"
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
            type="button"
            onClick={() => onChange(opt.key)}
            disabled={disabled}
            style={{
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '9px',
              textTransform: 'uppercase',
              letterSpacing: '0.14em',
              padding: '6px 12px',
              background: active ? '#B81820' : 'transparent',
              color: active ? '#F2EFE8' : '#7A7A80',
              border: 'none',
              cursor: disabled ? 'not-allowed' : 'pointer',
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

export function Header() {
  const {
    username,
    setUsername,
    platform,
    setPlatform,
    isAnalyzing,
    runAnalysis,
    reset,
  } = useAnalysisContext()

  return (
    <header
      data-testid="header"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: 50,
        background: '#0B0B0D',
        borderBottom: '1px solid rgba(242,239,232,0.14)',
        padding: '0 24px',
      }}
    >
      <div
        className="header__row"
        style={{
          maxWidth: '64rem',
          margin: '0 auto',
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          minHeight: 'var(--header-h, 64px)',
        }}
      >
        <div style={{ flexShrink: 0 }}>
          <BrandMark onClick={reset} />
        </div>

        <form
          data-testid="header-search-form"
          onSubmit={(e) => {
            e.preventDefault()
            runAnalysis(0)
          }}
          style={{
            flex: 1,
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            justifyContent: 'flex-end',
            flexWrap: 'wrap',
          }}
        >
          <PlatformToggle value={platform} onChange={setPlatform} disabled={isAnalyzing} />
          <div
            style={{
              display: 'inline-flex',
              border: '1px solid rgba(242,239,232,0.14)',
              flex: '1 1 220px',
              minWidth: '160px',
              maxWidth: '360px',
            }}
          >
            <input
              type="text"
              data-testid="header-search-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Nome de usuário..."
              disabled={isAnalyzing}
              style={{
                flex: 1,
                padding: '8px 12px',
                fontFamily: 'Instrument Serif, Georgia, serif',
                fontSize: '15px',
                color: '#F2EFE8',
                background: '#131316',
                border: 'none',
                outline: 'none',
                opacity: isAnalyzing ? 0.6 : 1,
                minWidth: 0,
              }}
            />
            <button
              type="submit"
              data-testid="header-search-submit"
              disabled={isAnalyzing || !username.trim()}
              style={{
                fontFamily: 'JetBrains Mono, monospace',
                fontSize: '10px',
                textTransform: 'uppercase',
                letterSpacing: '0.14em',
                padding: '0 16px',
                background: isAnalyzing ? '#4A4A50' : '#8B0F14',
                color: '#F2EFE8',
                border: 'none',
                cursor: isAnalyzing || !username.trim() ? 'not-allowed' : 'pointer',
                flexShrink: 0,
              }}
            >
              {isAnalyzing ? '...' : 'Analisar'}
            </button>
          </div>
        </form>
      </div>
    </header>
  )
}
