'use client'

// Hero-section profile lockup. Replaces the default `HorseLabsLockup` once a
// search becomes active. Subscribes to `AnalysisContext` for `profile`,
// `profileStatus`, `profileError`, and the active username/platform so it
// can render: loading skeleton, profile detail, or upstream error.

import { useAnalysisContext } from '../lib/AnalysisContext'
import type { PlayerProfile, PlayerRating } from '../lib/profileTypes'

const MODE_LABEL: Record<string, string> = {
  bullet: 'Bullet',
  blitz: 'Blitz',
  rapid: 'Rapid',
  classical: 'Clássico',
  daily: 'Diário',
  correspondence: 'Correspondência',
}

function formatJoined(unixSeconds?: number): string | null {
  if (!unixSeconds || !Number.isFinite(unixSeconds)) return null
  const d = new Date(unixSeconds * 1000)
  if (Number.isNaN(d.getTime())) return null
  return d.toLocaleDateString('pt-BR', { year: 'numeric', month: 'short' })
}

function RatingPill({ rating }: { rating: PlayerRating }) {
  const label = MODE_LABEL[rating.mode] ?? rating.mode
  return (
    <div
      data-testid="profile-rating"
      data-mode={rating.mode}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '2px',
        padding: '10px 14px',
        border: '1px solid rgba(242,239,232,0.14)',
        minWidth: '92px',
      }}
    >
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '9px',
          textTransform: 'uppercase',
          letterSpacing: '0.14em',
          color: '#4A4A50',
        }}
      >
        {label}
      </span>
      <span
        style={{
          fontFamily: 'Instrument Serif, Georgia, serif',
          fontSize: '24px',
          color: '#F2EFE8',
          lineHeight: 1,
        }}
      >
        {rating.rating}
      </span>
      {rating.games !== undefined && (
        <span
          style={{
            fontFamily: 'JetBrains Mono, monospace',
            fontSize: '9px',
            color: '#4A4A50',
            letterSpacing: '0.05em',
          }}
        >
          {rating.games} partidas
        </span>
      )}
    </div>
  )
}

function ProfileBody({ profile }: { profile: PlayerProfile }) {
  const joined = formatJoined(profile.joinedAt)
  return (
    <div data-testid="profile-lockup" style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '20px', flexWrap: 'wrap' }}>
        {profile.avatarUrl && (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            data-testid="profile-avatar"
            src={profile.avatarUrl}
            alt={`Avatar de ${profile.username}`}
            width={96}
            height={96}
            style={{
              width: '96px',
              height: '96px',
              objectFit: 'cover',
              border: '1px solid rgba(242,239,232,0.14)',
              flexShrink: 0,
            }}
          />
        )}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', minWidth: 0 }}>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '12px', flexWrap: 'wrap' }}>
            {profile.title && (
              <span
                data-testid="profile-title"
                style={{
                  fontFamily: 'JetBrains Mono, monospace',
                  fontSize: '11px',
                  letterSpacing: '0.14em',
                  padding: '3px 8px',
                  border: '1px solid #E8535A',
                  color: '#E8535A',
                  textTransform: 'uppercase',
                }}
              >
                {profile.title}
              </span>
            )}
            <a
              href={profile.url}
              target="_blank"
              rel="noopener noreferrer"
              data-testid="profile-username"
              style={{
                fontFamily: 'Instrument Serif, Georgia, serif',
                fontSize: '48px',
                lineHeight: 1,
                color: '#F2EFE8',
                letterSpacing: '-0.02em',
                textDecoration: 'none',
                wordBreak: 'break-word',
              }}
            >
              {profile.username}
            </a>
          </div>
          <div
            style={{
              display: 'flex',
              gap: '16px',
              flexWrap: 'wrap',
              fontFamily: 'JetBrains Mono, monospace',
              fontSize: '10px',
              textTransform: 'uppercase',
              letterSpacing: '0.14em',
              color: '#4A4A50',
            }}
          >
            <span data-testid="profile-platform">
              {profile.platform === 'chesscom' ? 'chess.com' : 'Lichess'}
            </span>
            {profile.country && <span data-testid="profile-country">País: {profile.country}</span>}
            {joined && <span data-testid="profile-joined">Membro desde {joined}</span>}
            {profile.displayName && profile.displayName !== profile.username && (
              <span data-testid="profile-display-name">{profile.displayName}</span>
            )}
          </div>
        </div>
      </div>

      {profile.ratings.length > 0 ? (
        <div
          data-testid="profile-ratings"
          style={{
            display: 'flex',
            gap: '8px',
            flexWrap: 'wrap',
          }}
        >
          {profile.ratings.map((r) => (
            <RatingPill key={r.mode} rating={r} />
          ))}
        </div>
      ) : (
        <p
          data-testid="profile-no-ratings"
          style={{
            fontFamily: 'Space Grotesk, sans-serif',
            fontSize: '13px',
            color: '#4A4A50',
          }}
        >
          Sem ratings publicados para esta conta.
        </p>
      )}
    </div>
  )
}

function ProfileSkeleton({ username }: { username: string }) {
  return (
    <div data-testid="profile-loading" style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
      <span
        style={{
          fontFamily: 'Instrument Serif, Georgia, serif',
          fontSize: '48px',
          lineHeight: 1,
          color: '#F2EFE8',
          letterSpacing: '-0.02em',
        }}
      >
        {username}
      </span>
      <span
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '10px',
          textTransform: 'uppercase',
          letterSpacing: '0.14em',
          color: '#4A4A50',
        }}
      >
        Carregando perfil…
      </span>
      <div className="animate-shimmer" style={{ height: '60px', width: '100%', maxWidth: '420px' }} />
    </div>
  )
}

function ProfileError({
  username,
  status,
  message,
}: {
  username: string
  status: 'not_found' | 'error'
  message: string
}) {
  return (
    <div data-testid="profile-error" data-status={status} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <span
        style={{
          fontFamily: 'Instrument Serif, Georgia, serif',
          fontSize: '48px',
          lineHeight: 1,
          color: '#F2EFE8',
          letterSpacing: '-0.02em',
        }}
      >
        {username}
      </span>
      <p
        style={{
          fontFamily: 'JetBrains Mono, monospace',
          fontSize: '11px',
          color: '#B81820',
          letterSpacing: '0.06em',
          textTransform: 'uppercase',
        }}
      >
        {status === 'not_found' ? 'Perfil não encontrado' : 'Erro ao carregar perfil'}
      </p>
      <p
        style={{
          fontFamily: 'Space Grotesk, sans-serif',
          fontSize: '13px',
          color: '#4A4A50',
        }}
      >
        {message}
      </p>
    </div>
  )
}

export function ProfileLockup() {
  const { activeUsername, profile, profileStatus, profileError } = useAnalysisContext()

  if (!activeUsername) return null

  if (profileStatus === 'loading' || profileStatus === 'idle') {
    return <ProfileSkeleton username={activeUsername} />
  }

  if (profileStatus === 'not_found' || profileStatus === 'error') {
    return (
      <ProfileError
        username={activeUsername}
        status={profileStatus}
        message={profileError ?? 'Sem detalhes adicionais.'}
      />
    )
  }

  if (profile) {
    return <ProfileBody profile={profile} />
  }

  return null
}
