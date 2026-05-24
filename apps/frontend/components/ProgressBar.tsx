'use client'

interface ProgressBarProps {
  /** 0–1 value. If undefined, renders as indeterminate. */
  value?: number
  /** Color override (CSS color string). Defaults to sangue-luz. */
  color?: string
}

export function ProgressBar({ value, color = '#B81820' }: ProgressBarProps) {
  const isIndeterminate = value === undefined

  return (
    <div
      style={{
        position: 'relative',
        height: '4px',
        background: 'rgba(242,239,232,0.08)',
        overflow: 'hidden',
        width: '100%',
      }}
    >
      {isIndeterminate ? (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            height: '100%',
            width: '60%',
            background: color,
            animation: 'progress-indeterminate 1.4s ease-in-out infinite',
          }}
        />
      ) : (
        <div
          className="animate-score-fill"
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            height: '100%',
            width: `${Math.min(100, Math.max(0, value * 100))}%`,
            background: color,
            transition: 'width 0.8s ease-out',
          }}
        />
      )}
    </div>
  )
}
