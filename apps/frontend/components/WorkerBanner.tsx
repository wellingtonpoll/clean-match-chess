// Feature 012 — banner shown when the audit worker daemon is offline.
//
// Surfaces a clear, actionable error instead of the previous "pending
// forever" UX. `AnalysisContext` polls `/api/audit/health` on mount and
// every 30 s thereafter; this component renders only when the response
// reports `worker_alive: false`.

'use client'

interface WorkerBannerProps {
  queued: number
}

export function WorkerBanner({ queued }: WorkerBannerProps): React.ReactElement {
  return (
    <div
      role="alert"
      style={{
        background: '#B81820',
        color: '#FFFFFF',
        padding: '12px 24px',
        fontSize: '14px',
        fontWeight: 600,
        textAlign: 'center',
        borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
      }}
    >
      ⚠ Audit worker offline — {queued > 0 ? `${queued} análise(s) em fila` : 'análises pausadas'}.
      Inicie o worker:{' '}
      <code style={{ background: 'rgba(0,0,0,0.25)', padding: '2px 6px', borderRadius: '3px' }}>
        ./scripts/dev.sh
      </code>{' '}
      no diretório raiz do projeto.
    </div>
  )
}
