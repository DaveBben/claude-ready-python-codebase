# syntax=docker/dockerfile:1
# Multi-stage build for a uv-managed Python app.
# https://docs.astral.sh/uv/guides/integration/docker/

# --- Build stage: resolve deps into a venv, compile bytecode ---
# Rolling uv tag; pin (e.g. uv:0.9-python3.13-...) for reproducibility.
FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS builder

WORKDIR /app

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_NO_DEV=1 \
    UV_PYTHON_DOWNLOADS=0

# Install deps first as a cached layer. Bind-mount the manifests so the layer
# only busts when uv.lock / pyproject.toml change, not on every source edit.
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

COPY . /app

# Install the project itself into the venv (builds the wheel; needs README + LICENSE).
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-editable

# --- Runtime stage: minimal image, non-root ---
FROM python:3.13-slim-bookworm AS runtime

# Non-root user for security.
RUN groupadd --system --gid 1000 app \
    && useradd --system --gid 1000 --uid 1000 --create-home app

COPY --from=builder --chown=app:app /app /app

WORKDIR /app
# Put the venv on PATH so the console script resolves.
ENV PATH="/app/.venv/bin:$PATH"
USER 1000:1000

# Runs the `example-project` console script; args pass through.
ENTRYPOINT ["example-project"]
