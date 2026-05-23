# Clean Match Chess CLI image (T098).
#
# Two-stage build: wheel build with uv, then a slim runtime carrying
# Stockfish 16 + WeasyPrint system deps.

FROM python:3.11-slim-bookworm AS build
SHELL ["/bin/bash", "-o", "pipefail", "-c"]

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh \
    && mv ~/.local/bin/uv /usr/local/bin/uv

WORKDIR /src
COPY pyproject.toml uv.lock ./
COPY apps/cli ./apps/cli
COPY packages ./packages
COPY tests ./tests

RUN uv sync --all-packages --no-dev --frozen

FROM python:3.11-slim-bookworm AS runtime

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        stockfish ca-certificates \
        libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b libcairo2 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV STOCKFISH_PATH=/usr/games/stockfish \
    CLEANMATCH_HOME=/data/.cleanmatch \
    PATH="/opt/venv/bin:${PATH}"

COPY --from=build /src/.venv /opt/venv
COPY tests/fixtures/forbidden-terms /usr/local/share/cleanmatch/forbidden-terms

VOLUME ["/data"]
WORKDIR /data
ENTRYPOINT ["/opt/venv/bin/cleanmatch"]
CMD ["--help"]
