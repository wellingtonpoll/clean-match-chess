#!/usr/bin/env bash
# Feature 012 — single-command dev orchestrator.
#
# Boots everything needed to develop/run the frontend:
#   1. Postgres container (podman compose)
#   2. Alembic migrations
#   3. Cleanup of zombie Stockfish containers from prior runs
#   4. Audit worker daemon (background)
#   5. Next.js dev server (foreground)
#
# SIGINT (Ctrl-C) propagates to all child processes — worker stops, frontend
# stops, Postgres stays up (it's a named-volume service, dev wants it
# persistent across sessions).
#
# Usage:
#   ./scripts/dev.sh
#
# Override env (see .env.example):
#   CLEANMATCH_POOL_SIZE=2 ./scripts/dev.sh
#   CLEANMATCH_ENGINE_DEPTH=8 ./scripts/dev.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

# ── Defaults (overridable via env) ───────────────────────────────────────

: "${DATABASE_URL:=postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch}"
: "${CLEANMATCH_ENGINE_IMAGE:=cleanmatch-stockfish:sf16}"
: "${CLEANMATCH_POOL_SIZE:=$(( $(nproc) - 2 < 2 ? 2 : $(nproc) - 2 ))}"
: "${CLEANMATCH_ENGINE_DEPTH:=12}"
: "${CLEANMATCH_ENGINE_MULTIPV:=3}"

export DATABASE_URL CLEANMATCH_ENGINE_IMAGE CLEANMATCH_POOL_SIZE
export CLEANMATCH_ENGINE_DEPTH CLEANMATCH_ENGINE_MULTIPV

WORKER_PID=""
FRONTEND_PID=""

cleanup() {
  echo
  echo "[dev.sh] shutting down…"
  if [[ -n "$FRONTEND_PID" ]]; then
    kill -TERM "$FRONTEND_PID" 2>/dev/null || true
    wait "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [[ -n "$WORKER_PID" ]]; then
    kill -TERM "$WORKER_PID" 2>/dev/null || true
    wait "$WORKER_PID" 2>/dev/null || true
  fi
  # Drop any podman Stockfish containers spawned by this session.
  podman ps -q --filter ancestor="$CLEANMATCH_ENGINE_IMAGE" 2>/dev/null \
    | xargs -r podman rm -f >/dev/null 2>&1 || true
  echo "[dev.sh] done."
}
trap cleanup INT TERM EXIT

# ── 1. Postgres ─────────────────────────────────────────────────────────

if ! podman ps --format '{{.Names}}' | grep -q '^cleanmatch-postgres$'; then
  echo "[dev.sh] starting Postgres…"
  podman compose -f infra/docker/compose.yml up -d postgres
  # Wait for healthy.
  for i in {1..30}; do
    if podman exec cleanmatch-postgres pg_isready -U cleanmatch >/dev/null 2>&1; then
      break
    fi
    sleep 1
  done
fi
echo "[dev.sh] Postgres ready."

# ── 2. Stockfish image present? ─────────────────────────────────────────

if ! podman image exists "$CLEANMATCH_ENGINE_IMAGE"; then
  echo "[dev.sh] ERROR: image $CLEANMATCH_ENGINE_IMAGE not found locally."
  echo "         Build it first: podman build -t $CLEANMATCH_ENGINE_IMAGE -f infra/docker/stockfish.Containerfile ."
  exit 1
fi

# ── 3. Migrations ───────────────────────────────────────────────────────

echo "[dev.sh] applying migrations…"
uv run alembic -c packages/analysis-core/alembic.ini upgrade head >/dev/null

# ── 4. Cleanup zombie Stockfish containers ──────────────────────────────

ZOMBIES=$(podman ps -q --filter ancestor="$CLEANMATCH_ENGINE_IMAGE" 2>/dev/null | wc -l)
if [[ "$ZOMBIES" -gt 0 ]]; then
  echo "[dev.sh] cleaning $ZOMBIES zombie Stockfish container(s)…"
  podman ps -q --filter ancestor="$CLEANMATCH_ENGINE_IMAGE" \
    | xargs -r podman rm -f >/dev/null
fi

# ── 5. Audit worker daemon ──────────────────────────────────────────────

echo "[dev.sh] starting audit worker (pool_size=$CLEANMATCH_POOL_SIZE depth=$CLEANMATCH_ENGINE_DEPTH multipv=$CLEANMATCH_ENGINE_MULTIPV)…"
uv run python apps/frontend/lib/audit_worker.py >/tmp/audit_worker.log 2>&1 &
WORKER_PID=$!
sleep 2
if ! kill -0 "$WORKER_PID" 2>/dev/null; then
  echo "[dev.sh] ERROR: worker exited within 2s. Tail of log:"
  tail -20 /tmp/audit_worker.log
  exit 1
fi
echo "[dev.sh] worker pid=$WORKER_PID log=/tmp/audit_worker.log"

# ── 6. Frontend dev server (foreground) ─────────────────────────────────

echo "[dev.sh] starting Next.js (http://localhost:3000)…"
cd apps/frontend
npm run dev &
FRONTEND_PID=$!

# Wait for whichever exits first (foreground UX).
wait -n "$WORKER_PID" "$FRONTEND_PID" 2>/dev/null || true
