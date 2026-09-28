ARG UV_VERSION=0.11.2
FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

FROM ubuntu:24.04

ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        coreutils \
        curl \
        git \
        libseccomp2 \
        mount \
        procps \
        python3 \
        python3-venv \
        sudo \
        util-linux \
    && rm -rf /var/lib/apt/lists/*

COPY --from=uv /uv /uvx /usr/local/bin/

RUN groupadd --gid 10001 benchmark \
    && useradd --uid 10001 --gid benchmark --create-home --shell /bin/bash benchmark \
    && printf '%s\n' \
        'benchmark ALL=(root) NOPASSWD: /usr/bin/unshare *' \
        'benchmark ALL=(root) NOPASSWD: /usr/bin/timeout *' \
        'benchmark ALL=(root) NOPASSWD: /usr/bin/kill *' \
        > /etc/sudoers.d/sidetaskbench \
    && chmod 0440 /etc/sudoers.d/sidetaskbench

WORKDIR /app
COPY --chown=benchmark:benchmark . /app
RUN chown benchmark:benchmark /app

USER benchmark
RUN uv sync --frozen --no-dev

USER root
RUN chmod 0755 /app/scripts/docker-entrypoint.sh

ENV HOME=/home/benchmark \
    PATH=/app/.venv/bin:/usr/local/bin:/usr/bin:/bin \
    PYTHONUNBUFFERED=1

ENTRYPOINT ["/app/scripts/docker-entrypoint.sh"]
CMD ["--help"]
