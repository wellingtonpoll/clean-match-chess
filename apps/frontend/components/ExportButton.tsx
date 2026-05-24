'use client'

import { useState } from 'react'

interface ExportButtonProps {
  runId: string
}

export function ExportButton({ runId }: ExportButtonProps) {
  const [loadingFmt, setLoadingFmt] = useState<'pdf' | 'txt' | null>(null)

  const handleExport = async (format: 'pdf' | 'txt') => {
    setLoadingFmt(format)
    try {
      const url = `/api/export?run_id=${encodeURIComponent(runId)}&format=${format}`
      const res = await fetch(url)
      if (!res.ok) {
        const err = await res.text()
        alert(`Export failed: ${err}`)
        return
      }
      const blob = await res.blob()
      const objectUrl = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = objectUrl
      a.download = `cleanmatch-${runId}.${format === 'txt' ? 'json' : format}`
      a.click()
      URL.revokeObjectURL(objectUrl)
    } catch (e) {
      alert(`Export error: ${e instanceof Error ? e.message : String(e)}`)
    } finally {
      setLoadingFmt(null)
    }
  }

  const btnStyle: React.CSSProperties = {
    fontFamily: 'JetBrains Mono, monospace',
    fontSize: '9px',
    textTransform: 'uppercase',
    letterSpacing: '0.14em',
    padding: '4px 8px',
    border: '1px solid rgba(242,239,232,0.14)',
    background: 'transparent',
    color: '#7A7A80',
    cursor: 'pointer',
    transition: 'border-color 0.15s, color 0.15s',
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
  }

  const btnHoverStyle: React.CSSProperties = {
    borderColor: 'rgba(242,239,232,0.4)',
    color: '#F2EFE8',
  }

  return (
    <div style={{ display: 'flex', gap: '4px', flexShrink: 0 }}>
      {(['pdf', 'txt'] as const).map((fmt) => (
        <button
          key={fmt}
          onClick={() => handleExport(fmt)}
          disabled={loadingFmt !== null}
          style={btnStyle}
          onMouseEnter={(e) => Object.assign((e.target as HTMLElement).style, btnHoverStyle)}
          onMouseLeave={(e) => Object.assign((e.target as HTMLElement).style, btnStyle)}
        >
          {loadingFmt === fmt ? '...' : `↓ ${fmt.toUpperCase()}`}
        </button>
      ))}
    </div>
  )
}
