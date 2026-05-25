# Clean Match Chess — Local Infrastructure

This directory carries the Compose definition + supporting Dockerfiles for
running Clean Match Chess dependencies locally (and in CI services).

## Services

| Service    | Image              | Purpose                                       | Feature |
|------------|--------------------|-----------------------------------------------|---------|
| `postgres` | `postgres:17-alpine` | Analysis-result cache (`audit_runs` table)    | 008     |

(More to come as auth, billing, etc. land — keep this table current.)

## Quickstart

```bash
# Start Postgres
docker compose -f infra/docker/compose.yml up -d postgres

# Check health
docker compose -f infra/docker/compose.yml ps postgres
docker compose -f infra/docker/compose.yml exec postgres pg_isready -U cleanmatch

# Stop (keeps volume)
docker compose -f infra/docker/compose.yml down

# Nuke (drops volume too)
docker compose -f infra/docker/compose.yml down -v
```

## Environment

The compose file reads from `.env` at the repo root. Copy `.env.example`
and adjust if needed. Defaults are dev-safe and intentionally insecure:

```text
POSTGRES_USER=cleanmatch
POSTGRES_PASSWORD=cleanmatch
POSTGRES_DB=cleanmatch
POSTGRES_PORT=5432
DATABASE_URL=postgresql+psycopg://cleanmatch:cleanmatch@localhost:5432/cleanmatch
```

For production, override every value via the deployment environment —
never commit production credentials to this repo.

## Volume layout

The named volume `cleanmatch_pg_data` persists Postgres data across
`down`/`up` cycles. Inspect with:

```bash
docker volume inspect cleanmatch_pg_data
```

## Existing Dockerfiles

| File                    | Purpose                                                                |
|-------------------------|------------------------------------------------------------------------|
| `stockfish.Dockerfile`  | Reproducible Stockfish 16 image (used by `cleanmatch-stockfish:sf16`) |
| `cleanmatch.Dockerfile` | CLI image for shipping the cleanmatch binary                           |
