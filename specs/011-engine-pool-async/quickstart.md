# Feature 011 — Quickstart

## Prerequisites

- Postgres up (`podman compose -f infra/docker/compose.yml up -d postgres`)
- `cleanmatch-stockfish:sf16` image built
- `uv sync --all-packages --all-extras`
- `alembic upgrade head` to land 0003_audit_jobs

## Set env vars

```bash
cat > .env << 'EOF'
DATABASE_URL=postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch
CLEANMATCH_ENGINE_IMAGE=cleanmatch-stockfish:sf16
CLEANMATCH_ENGINE_DEPTH=12
CLEANMATCH_ENGINE_MULTIPV=3
CLEANMATCH_POOL_SIZE=4
EOF
```

## Start worker

```bash
# Terminal 1 — audit worker daemon
export $(cat .env | xargs)
uv run python apps/frontend/lib/audit_worker.py
# Heartbeat: every 30s logs `audit_worker.heartbeat pool_size=4 queue_depth=N`
```

## Start frontend

```bash
# Terminal 2
cd apps/frontend
export $(cat ../../.env | xargs)
npm run dev
# → http://localhost:3000
```

## Submit an audit via the API directly

```bash
JOB=$(curl -sX POST -H 'Content-Type: application/json' \
  -d @<(echo '{"pgn_text": "'$(cat tests/fixtures/audit_v2_smoke.pgn)'", "subject_color": "white"}') \
  http://localhost:3000/api/audit | jq -r .job_id)

echo "Submitted: $JOB"

# Poll for completion
while true; do
  STATUS=$(curl -s http://localhost:3000/api/audit/$JOB | jq -r .status)
  echo "status=$STATUS"
  [ "$STATUS" = "completed" ] && break
  sleep 1
done
curl -s http://localhost:3000/api/audit/$JOB | jq .result
```

## Verify timing signal is now active

```bash
# Run audit on a recent chess.com game
JOB=$(curl -sX POST -H 'Content-Type: application/json' \
  -d "{\"pgn_text\": \"$(curl -s https://api.chess.com/pub/player/quaiada/games/2026/03 | jq -r '.games[-1].pgn')\", \"subject_color\": \"white\"}" \
  http://localhost:3000/api/audit | jq -r .job_id)

# Wait for completion
while [ "$(curl -s http://localhost:3000/api/audit/$JOB | jq -r .status)" != "completed" ]; do sleep 1; done

# Inspect result — timing-analysis should be visible with samples > 0
curl -s http://localhost:3000/api/audit/$JOB | jq '.result.signals[] | select(.signal_name == "timing-analysis")'
# Expected output: {"signal_name": "timing-analysis", "mean": <float>, "samples": <int > 0>, ...}
```

## Run integration tests

```bash
uv run pytest tests/integration/test_audit_queue.py -v
```

## Inspect queue

```sql
SELECT id, status, pgn_sha256, started_at, finished_at, error_message
FROM audit_jobs
ORDER BY created_at DESC
LIMIT 10;
```

## Tear down

```bash
# Stop frontend (Ctrl-C terminal 2)
# Stop worker (Ctrl-C terminal 1)
# Optional: nuke queue history
psql $DATABASE_URL -c "TRUNCATE TABLE audit_jobs"
```
