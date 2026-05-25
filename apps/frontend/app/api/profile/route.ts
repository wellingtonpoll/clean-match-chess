// Profile-proxy route: normalises chess.com + lichess account data into the
// shared `PlayerProfile` envelope so the frontend can render either platform
// with the same component. Server-side proxy (vs. fetching directly from the
// browser) keeps the upstream User-Agent under our control and lets us
// short-circuit obvious 404s before the streaming /api/analyze pipeline runs.

import { NextRequest } from 'next/server'
import type { PlayerProfile, PlayerRating } from '../../../lib/profileTypes'

export const runtime = 'nodejs'
export const dynamic = 'force-dynamic'

const CHESSCOM_UA = 'CleanMatchChess/006-frontend (contact: wellingtonpoleti@gmail.com)'

interface ChesscomProfile {
  url: string
  avatar?: string
  country?: string
  joined?: number
  title?: string
  name?: string
  username: string
}

interface ChesscomStatsEntry {
  last?: { rating?: number; date?: number; rd?: number }
  record?: { win?: number; loss?: number; draw?: number }
}

interface ChesscomStats {
  chess_rapid?: ChesscomStatsEntry
  chess_blitz?: ChesscomStatsEntry
  chess_bullet?: ChesscomStatsEntry
  chess_daily?: ChesscomStatsEntry
  tactics?: { highest?: { rating?: number } }
  puzzle_rush?: { best?: { score?: number } }
}

interface LichessPerf {
  games?: number
  rating?: number
  rd?: number
  prog?: number
}

interface LichessUser {
  id: string
  username: string
  title?: string
  createdAt?: number
  profile?: { country?: string; flag?: string; bio?: string }
  perfs?: Record<string, LichessPerf>
  url?: string
}

function gamesFromChesscomRecord(record?: ChesscomStatsEntry['record']): number | undefined {
  if (!record) return undefined
  const total = (record.win ?? 0) + (record.loss ?? 0) + (record.draw ?? 0)
  return total > 0 ? total : undefined
}

function ratingsFromChesscom(stats: ChesscomStats): PlayerRating[] {
  const out: PlayerRating[] = []
  const map: { key: keyof ChesscomStats; mode: string }[] = [
    { key: 'chess_rapid', mode: 'rapid' },
    { key: 'chess_blitz', mode: 'blitz' },
    { key: 'chess_bullet', mode: 'bullet' },
    { key: 'chess_daily', mode: 'daily' },
  ]
  for (const { key, mode } of map) {
    const entry = stats[key] as ChesscomStatsEntry | undefined
    const rating = entry?.last?.rating
    if (typeof rating === 'number') {
      out.push({ mode, rating, games: gamesFromChesscomRecord(entry?.record) })
    }
  }
  return out
}

function ratingsFromLichess(perfs: Record<string, LichessPerf> | undefined): PlayerRating[] {
  if (!perfs) return []
  const order = ['bullet', 'blitz', 'rapid', 'classical', 'correspondence']
  const out: PlayerRating[] = []
  for (const mode of order) {
    const perf = perfs[mode]
    if (!perf || typeof perf.rating !== 'number') continue
    out.push({ mode, rating: perf.rating, games: perf.games, rd: perf.rd })
  }
  return out
}

async function fetchChesscom(username: string): Promise<PlayerProfile | Response> {
  const headers = { 'User-Agent': CHESSCOM_UA, Accept: 'application/json' }
  const [profileRes, statsRes] = await Promise.all([
    fetch(`https://api.chess.com/pub/player/${encodeURIComponent(username)}`, { headers }),
    fetch(`https://api.chess.com/pub/player/${encodeURIComponent(username)}/stats`, { headers }),
  ])

  if (profileRes.status === 404) {
    return Response.json(
      { error: 'not_found', message: `chess.com player "${username}" not found` },
      { status: 404 }
    )
  }
  if (!profileRes.ok) {
    return Response.json(
      { error: 'upstream_failure', message: `chess.com profile fetch failed (${profileRes.status})` },
      { status: 502 }
    )
  }

  const profile = (await profileRes.json()) as ChesscomProfile
  const stats: ChesscomStats = statsRes.ok ? await statsRes.json() : {}

  return {
    username: profile.username,
    platform: 'chesscom',
    url: profile.url,
    avatarUrl: profile.avatar,
    country: profile.country?.split('/').pop()?.toUpperCase(),
    title: profile.title,
    displayName: profile.name,
    joinedAt: profile.joined,
    ratings: ratingsFromChesscom(stats),
  }
}

async function fetchLichess(username: string): Promise<PlayerProfile | Response> {
  const res = await fetch(`https://lichess.org/api/user/${encodeURIComponent(username)}`, {
    headers: { Accept: 'application/json' },
  })
  if (res.status === 404) {
    return Response.json(
      { error: 'not_found', message: `lichess player "${username}" not found` },
      { status: 404 }
    )
  }
  if (!res.ok) {
    return Response.json(
      { error: 'upstream_failure', message: `lichess fetch failed (${res.status})` },
      { status: 502 }
    )
  }
  const user = (await res.json()) as LichessUser

  return {
    username: user.username,
    platform: 'lichess',
    url: user.url ?? `https://lichess.org/@/${user.username}`,
    country: user.profile?.country?.toUpperCase(),
    title: user.title,
    joinedAt: typeof user.createdAt === 'number' ? Math.floor(user.createdAt / 1000) : undefined,
    ratings: ratingsFromLichess(user.perfs),
  }
}

export async function GET(request: NextRequest) {
  const { searchParams } = request.nextUrl
  const username = (searchParams.get('username') ?? '').trim()
  const platform = (searchParams.get('platform') ?? 'chesscom').toLowerCase()

  if (!username) {
    return Response.json({ error: 'invalid_platform', message: 'Missing username' }, { status: 400 })
  }
  if (platform !== 'chesscom' && platform !== 'lichess') {
    return Response.json({ error: 'invalid_platform', message: `Unknown platform: ${platform}` }, { status: 400 })
  }

  try {
    const result = platform === 'chesscom' ? await fetchChesscom(username) : await fetchLichess(username)
    if (result instanceof Response) return result
    return Response.json(result, { status: 200 })
  } catch (e) {
    const msg = e instanceof Error ? e.message : 'unknown'
    return Response.json({ error: 'upstream_failure', message: msg }, { status: 502 })
  }
}
