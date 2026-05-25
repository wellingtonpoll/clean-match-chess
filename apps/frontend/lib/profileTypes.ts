// Unified player-profile shape served by /api/profile.
//
// The route normalises chess.com (/pub/player/{u} + /pub/player/{u}/stats)
// and lichess (/api/user/{u}) responses into the same envelope so the
// `ProfileLockup` component can render them without branching on platform.

import type { Platform } from './AnalysisContext'

export interface PlayerRating {
  /** Lower-case time-control or variant identifier (e.g. "rapid", "blitz", "bullet", "classical", "daily", "puzzle"). */
  mode: string
  /** Current displayed rating. */
  rating: number
  /** Total games played in this mode, when reported by the platform. */
  games?: number
  /** Rating deviation, lichess-only. */
  rd?: number
}

export interface PlayerProfile {
  username: string
  platform: Platform
  /** Canonical profile URL on the upstream platform. */
  url: string
  avatarUrl?: string
  /** ISO-3166-1 alpha-2 country code, when reported. */
  country?: string
  /** GM / IM / FM / NM / WGM / WIM / WFM / WNM / CM / WCM if held. */
  title?: string
  /** Display name (chess.com `name`, lichess `username` if no display name). */
  displayName?: string
  /** Unix-seconds account creation timestamp. */
  joinedAt?: number
  ratings: PlayerRating[]
}

export interface PlayerProfileError {
  error: 'not_found' | 'upstream_failure' | 'invalid_platform'
  message: string
}
