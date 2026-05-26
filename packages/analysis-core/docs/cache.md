# Analysis cache (feature 008)

Postgres-backed cache around `pipeline.run.run_single_game`. Cache hit
returns the previously-persisted `AuditRun` in <100 ms; cache miss runs
the full Stockfish pipeline and persists the result for next time.

## Cache key

Composite `UNIQUE (pgn_sha256, manifest_sha256)`:

| Field             | Source                                                  |
|-------------------|---------------------------------------------------------|
| `pgn_sha256`      | sha256 of the raw input PGN bytes                       |
| `manifest_sha256` | `analysis_core.manifest.manifest_hash(manifest)` output |

`manifest_hash` covers engine binary sha256, opening book sha256,
heuristic versions, scoring threshold version, signal versions, rating
baselines version + sha256, design system version. Any of these
changing produces a different `manifest_sha256` → old rows naturally
stop matching → next audit re-runs at full cost and writes a new row.

This means: re-running an audit after a scoring algorithm bump
correctly serves the NEW scoring (no stale cache hits), and the OLD row
is preserved for historical comparison.

## Schema

```sql
CREATE TABLE audit_runs (
    id              UUID PK DEFAULT gen_random_uuid(),
    pgn_sha256      BYTEA NOT NULL,
    manifest_sha256 BYTEA NOT NULL,
    platform        VARCHAR(16),
    game_id         VARCHAR(64),
    white_username  VARCHAR(64),
    black_username  VARCHAR(64),
    score           DOUBLE PRECISION,
    risk_level      VARCHAR(8),
    ply_count       INT,
    run_json        JSONB NOT NULL,    -- full AuditRun envelope
    manifest_json   JSONB NOT NULL,    -- ReproducibilityManifest
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    user_id         UUID,              -- reserved for feature 009+
    tenant_id       UUID,              -- reserved for feature 009+
    UNIQUE (pgn_sha256, manifest_sha256)
);

-- Secondary indexes for future history queries (feature 010+):
idx_audit_runs_platform_game  (platform, game_id)
idx_audit_runs_white          (white_username)
idx_audit_runs_black          (black_username)
idx_audit_runs_created        (created_at DESC)
```

`user_id` + `tenant_id` columns are reserved nullable for the incoming
auth + multi-tenancy feature. No FK constraints yet — those land with
feature 009 when the `users` table arrives.

## Environment variables

| Variable        | Required | Default                                            | Notes                              |
|-----------------|----------|----------------------------------------------------|------------------------------------|
| `DATABASE_URL`  | optional | (none — cache disabled)                            | SQLAlchemy URI with `+psycopg`     |
| `POSTGRES_USER` | optional | `cleanmatch` (compose default)                     | docker-compose only                |
| `POSTGRES_PASSWORD` | optional | `cleanmatch` (compose default)                 | docker-compose only                |
| `POSTGRES_DB`   | optional | `cleanmatch` (compose default)                     | docker-compose only                |
| `POSTGRES_PORT` | optional | `5432`                                             | docker-compose only                |

Dev default URI:

```
postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch
```

Production: override every variable via the deployment environment.
Never commit production credentials.

## Graceful degradation

If `DATABASE_URL` is unset OR Postgres is unreachable:

- `db.cache.lookup()` returns `None` (treated as cache miss).
- `db.cache.persist()` is a no-op.
- A structured warning lands on stderr (`event=db.cache.lookup_unreachable`
  or `db.cache.persist_unreachable`).
- The audit pipeline runs at full Stockfish cost and exits 0 with the
  normal JSON envelope on stdout.

Developer machines without a running Postgres continue to work
unchanged.

## Operations

### Start Postgres locally

```bash
docker compose -f infra/docker/compose.yml up -d postgres
# or: podman compose -f infra/docker/compose.yml up -d postgres
```

### Apply migrations

```bash
uv run alembic -c packages/analysis-core/alembic.ini upgrade head
```

### Bypass the cache for a single run

```bash
cleanmatch audit-game --no-cache PGN_FILE
```

`--no-cache` skips both lookup AND persist, so a forced re-run never
adds a duplicate row to `audit_runs`.

### Inspect cached rows

```bash
psql "$DATABASE_URL" -c "
  SELECT created_at, white_username, black_username, score, risk_level
  FROM audit_runs
  ORDER BY created_at DESC
  LIMIT 20;
"
```

### Nuke the cache

```bash
# In-place truncate (keeps schema):
psql "$DATABASE_URL" -c "TRUNCATE TABLE audit_runs;"

# Drop + recreate via alembic:
uv run alembic -c packages/analysis-core/alembic.ini downgrade base
uv run alembic -c packages/analysis-core/alembic.ini upgrade head

# Full reset including volume:
docker compose -f infra/docker/compose.yml down -v
docker compose -f infra/docker/compose.yml up -d postgres
uv run alembic -c packages/analysis-core/alembic.ini upgrade head
```

### Retention policy (stub)

The current schema retains every successful audit indefinitely. At
~50 KB per row, 10k audits ≈ 0.5 GB on disk. Beyond that scale,
consider:

- A TTL pruner that drops rows older than N days where N is
  configurable.
- Partitioning by `created_at` month (feature 010+).

Until retention lands, prefer `TRUNCATE` over `DELETE` for full purges
to reclaim disk immediately.

## Security notes

- The `_mask_url()` helper in `session.py` redacts the password
  component before any log line that references the URI (`scheme://
  user:***@host:port/db`). Verified by inspecting `db.cache.engine_initialised`
  log output.
- No PII is read from PGN bytes; usernames stored in `white_username` /
  `black_username` come from the PGN header which is already public
  data on chess.com / Lichess.
- When auth lands (feature 009), `user_id` becomes a hard FK to
  `users(id)` and row-level security (RLS) will scope per-tenant reads.
