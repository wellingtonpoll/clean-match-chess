# Reproducible Stockfish 16 builder image (T097).
#
# Produces /usr/local/bin/stockfish (the exact binary that Clean Match
# Chess audits will pin via reproducibility manifest). The binary's
# SHA256 is computed at the end and printed; this image is meant to be
# the canonical reference for the manifest's `engine_binary_sha256`.
FROM debian:12-slim AS build

ARG STOCKFISH_VERSION=sf_16
ARG STOCKFISH_URL=https://github.com/official-stockfish/Stockfish/archive/refs/tags/sf_16.tar.gz

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        ca-certificates curl tar gzip make g++ \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
RUN curl -fsSL "${STOCKFISH_URL}" | tar xz \
    && cd Stockfish-${STOCKFISH_VERSION}/src \
    && make -j"$(nproc)" build ARCH=x86-64-modern \
    && cp stockfish /usr/local/bin/stockfish \
    && chmod +x /usr/local/bin/stockfish

FROM debian:12-slim AS runtime
COPY --from=build /usr/local/bin/stockfish /usr/local/bin/stockfish
RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && sha256sum /usr/local/bin/stockfish > /usr/local/bin/stockfish.sha256

ENV STOCKFISH_PATH=/usr/local/bin/stockfish
ENTRYPOINT ["/usr/local/bin/stockfish"]
