# Quickstart — Feature 008

One-command recipes per phase.

## §1 — Pre-flight (~2 min)

```bash
# Pull Postgres image (one-time)
docker pull postgres:17-alpine

# Bring up Postgres
docker compose -f infra/docker/compose.yml up -d postgres
sleep 3
docker compose -f infra/docker/compose.yml exec postgres pg_isready -U cleanmatch
#  must print "accepting connections"

# Export the dev DATABASE_URL into the shell (or copy from .env.example)
export DATABASE_URL=postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch
```

## §2 — Apply migrations (~5 s)

```bash
uv run alembic -c packages/analysis-core/alembic.ini upgrade head
psql "$DATABASE_URL" -c "\d audit_runs"
#  shows the table with all columns including user_id + tenant_id
```

## §3 — Cache-miss path (~30-60 s)

```bash
time uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/r1.json
#  ~30-60s on the reference machine
psql "$DATABASE_URL" -c "SELECT count(*) FROM audit_runs;"
#  1
```

## §4 — Cache-hit path (~< 500 ms)

```bash
time uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/r2.json
#  < 500 ms wall-clock
diff <(jq -S 'del(.run_id, .started_at)' /tmp/r1.json) <(jq -S 'del(.run_id, .started_at)' /tmp/r2.json)
#  empty (envelopes identical modulo run.id + started_at)
```

## §5 — `--no-cache` bypass (~30-60 s, no new row)

```bash
time uv run cleanmatch audit-game --no-cache tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/r3.json
#  ~30-60s
psql "$DATABASE_URL" -c "SELECT count(*) FROM audit_runs;"
#  still 1 — --no-cache skips persist too
```

## §6 — DB-down graceful path

```bash
docker compose -f infra/docker/compose.yml stop postgres
time uv run cleanmatch audit-game tests/fixtures/audit_v2_smoke.pgn --output json > /tmp/r4.json 2>/tmp/r4.err
#  ~30-60s; tail r4.err shows "event=db.cache.disabled" warning
docker compose -f infra/docker/compose.yml start postgres
```

## §7 — Migration roundtrip (SC-005)

```bash
# Burn a fresh database to a separate schema
psql "$DATABASE_URL" -c "CREATE DATABASE cleanmatch_migration_test;"
DATABASE_URL=postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch_migration_test \
  uv run alembic -c packages/analysis-core/alembic.ini upgrade head
DATABASE_URL=postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch_migration_test \
  uv run alembic -c packages/analysis-core/alembic.ini downgrade base
psql "$DATABASE_URL" -c "DROP DATABASE cleanmatch_migration_test;"
#  no errors
```

## §8 — Pre-PR gates

```bash
uv run ruff check . && uv run ruff format --check .
uv run mypy --strict packages/analysis-core/src
uv run pytest --cov --cov-fail-under=85
```

## §9 — Open PR

```bash
git push -u origin 008-analysis-cache-postgres
gh pr create --title "feat(infra): Postgres-backed analysis cache (feature 008)" \
  --label infra --label scoring \
  --body "..."
```
